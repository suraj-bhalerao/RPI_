import os
import re
import time
import queue
import serial
import platform
import threading
import serial.tools.list_ports
from datetime import datetime
from ota_validator import OTAValidator


class SerialManager:
    def __init__(self, ui):
        self.ui = ui
        self.serial_port = None
        self.read_thread = None
        self.monitor_thread = threading.Thread(target=self.auto_monitor_ports, daemon=True)
        self.logging_active = False

        self.log_queue = queue.Queue()
        self.log_file = None
        self.fallback_log_file = None
        self.buffered_lines = []

        self.imei = None
        self.detecting_imei = False
        self.imei_commands = ["*GET#IMEI#", "*GET,IMEI#", "CMN *GET#IMEI#"]
        self.current_imei_index = 0

        self.recent_lines = []
        self.recent_lines_lock = threading.Lock()
        self.ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
        self.imei_pattern = re.compile(r"IMEI[:#\s]*(\d{14,17})", re.IGNORECASE)

        self.ota_validator = OTAValidator(self)

        os.makedirs("logs", exist_ok=True)
        self.monitor_thread.start()
        self.ui.root.after(50, self.process_log_queue)

    def _get_log_folder(self):
        folder = os.path.join("logs", time.strftime("%Y-%m-%d"))
        os.makedirs(folder, exist_ok=True)
        return folder

    def _generate_log_path(self):
        user = platform.node()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"serial_log_{self.imei}_{user}_{timestamp}.log"
        return os.path.join(self._get_log_folder(), filename)

    def _prepare_fallback_log(self):
        path = os.path.join(self._get_log_folder(), "default.log")
        self.fallback_log_file = open(path, "a", encoding="utf-8", errors="ignore")

    def auto_monitor_ports(self):
        known_ports = set()
        last_good_port = None

        while True:
            try:
                current_ports = set(p.device for p in serial.tools.list_ports.comports())
                lost_ports = known_ports - current_ports

                if self.serial_port and self.serial_port.port in lost_ports:
                    self.ui.root.title("AEPL Logger (Disconnected)")
                    self.stop_logging()
                    self.serial_port = None

                if not self.serial_port or not (self.serial_port.is_open and self.logging_active):
                    ports_to_check = list(current_ports)
                    if last_good_port in ports_to_check:
                        ports_to_check.remove(last_good_port)
                        ports_to_check.insert(0, last_good_port)

                    for port in ports_to_check:
                        try:
                            temp_port = serial.Serial(port, baudrate=115200, timeout=0.05)
                            data_found = self._port_has_data(temp_port)

                            if data_found:
                                if self.serial_port and self.serial_port.is_open:
                                    self.serial_port.close()
                                self.serial_port = temp_port
                                last_good_port = port
                                self.ui.root.title(f"AEPL Logger (Connected: {port})")
                                self.start_logging()
                                break
                            else:
                                temp_port.close()
                        except Exception as e:
                            self.log_queue.put(f"Could not open {port}: {e}")

                known_ports = current_ports
                time.sleep(0.05)
            except Exception as e:
                self.log_queue.put(f"Port monitor error: {e}")

    def _port_has_data(self, port):
        start_time = time.time()
        while time.time() - start_time < 0.15:
            if port.in_waiting:
                return True
            if port.read(32):
                return True
            time.sleep(0.01)
        return False

    def start_logging(self):
        if not self.serial_port or self.logging_active:
            return

        self.logging_active = True
        self.detecting_imei = True
        self.read_thread = threading.Thread(target=self.read_serial, daemon=True)
        self.read_thread.start()
        self.try_next_imei_command()

        if self.ota_validator:
            self.ota_validator.start_validation_after_delay(20)

    def stop_logging(self):
        self.logging_active = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        for f in [self.log_file, self.fallback_log_file]:
            try:
                if f:
                    f.close()
            except:
                pass
        self.log_file = self.fallback_log_file = None
        self.buffered_lines.clear()
        self.log_queue.put("Logging stopped.")

    def send_command(self, command):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.write((command + "\n").encode())
            self.log_queue.put(f"[TX] {command}")

    def try_next_imei_command(self):
        if not self.detecting_imei or self.imei is not None:
            return

        if self.current_imei_index >= len(self.imei_commands):
            self.detecting_imei = False
            return

        command = self.imei_commands[self.current_imei_index]
        self.current_imei_index += 1
        self.send_command(command)
        self.ui.root.after(2000, self.try_next_imei_command)

    def read_serial(self):
        buffer = ""

        while self.logging_active:
            try:
                if self.serial_port.in_waiting:
                    raw = self.serial_port.read(self.serial_port.in_waiting).decode("utf-8", errors="ignore")
                    buffer += raw
                    lines = buffer.splitlines()
                    buffer = "" if raw.endswith("\n") else lines.pop() if lines else buffer

                    for line in lines:
                        self.handle_line(self.ansi_escape.sub("", line).strip())
            except Exception as e:
                self.log_queue.put(f"Error: {e}")
                break
            time.sleep(0.01)

    def handle_line(self, line):
        if not line:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        if self.detecting_imei and self.imei is None:
            self.buffered_lines.append(line)
            match = self.imei_pattern.search(line)
            if match:
                self.imei = match.group(1)
                self.detecting_imei = False
                self._finalize_imei_detection(timestamp)

        if self.imei and self.log_file:
            self.log_file.write(f"{timestamp} - {line}\n")
            self.log_file.flush()
        else:
            if not self.fallback_log_file:
                self._prepare_fallback_log()
            self.fallback_log_file.write(f"{timestamp} - {line}\n")
            self.fallback_log_file.flush()

        self.log_queue.put(line)
        with self.recent_lines_lock:
            self.recent_lines.append(line)
            if len(self.recent_lines) > 100:
                self.recent_lines.pop(0)

    def _finalize_imei_detection(self, timestamp):
        self.log_file = open(self._generate_log_path(), "a", encoding="utf-8", errors="ignore")
        for line in self.buffered_lines:
            if line.strip():
                self.log_file.write(f"{timestamp} - {line.strip()}\n")
        self.log_file.flush()
        self.buffered_lines.clear()

        if self.fallback_log_file:
            try:
                self.fallback_log_file.close()
                os.remove(os.path.join(self._get_log_folder(), "default.log"))
            except Exception as e:
                self.log_queue.put(f"Error deleting fallback log: {e}")
            self.fallback_log_file = None

    def process_log_queue(self):
        while not self.log_queue.empty():
            self.ui.insert_log(self.log_queue.get_nowait())
        self.ui.root.after(50, self.process_log_queue)

    def get_recent_lines(self, clear_after_read=False):
        with self.recent_lines_lock:
            lines = list(self.recent_lines)
            if clear_after_read:
                self.recent_lines.clear()
            return lines
