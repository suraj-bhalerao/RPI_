import serial
import threading
import time
import serial.tools.list_ports
import os
import re
import queue
import platform

class SerialManager:
    def __init__(self, ui):
        self.ui = ui
        self.serial_port = None
        self.thread = None
        self.logging_active = False
        self.log_queue = queue.Queue()
        self.log_file = None
        self.fallback_log_file = None
        self.buffered_lines = []
        self.imei = None
        self.detecting_imei = False

        self.monitor_thread = threading.Thread(target=self.auto_monitor_ports, daemon=True)
        self.monitor_thread.start()

        if not os.path.exists("logs"):
            os.makedirs("logs")

        self.ui.root.after(50, self.process_log_queue)

    def _get_log_folder(self):
        date_str = time.strftime("%Y-%m-%d")
        folder_path = os.path.join("logs", date_str)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        return folder_path

    def _generate_log_path(self):
        user = platform.node()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"serial_log_{self.imei}_{user}_{timestamp}.log"
        return os.path.join(self._get_log_folder(), filename)

    def _prepare_fallback_log(self):
        fallback_path = os.path.join(self._get_log_folder(), "default.log")
        self.fallback_log_file = open(fallback_path, 'a', encoding='utf-8', errors='ignore')

    def auto_monitor_ports(self):
        known_ports = set()
        while True:
            try:
                current_ports = set(p.device for p in serial.tools.list_ports.comports())
                lost_ports = known_ports - current_ports

                if lost_ports and self.serial_port and self.serial_port.port in lost_ports:
                    self.ui.root.title("AEPL Logger (Disconnected)")
                    self.stop_logging()
                    self.serial_port = None

                if not self.serial_port or not (self.serial_port.is_open and self.logging_active):
                    for port in current_ports:
                        try:
                            temp_port = serial.Serial(port, baudrate=115200, timeout=0.1)
                            data_found = False
                            start_time = time.time()
                            while time.time() - start_time < 0.1:
                                if temp_port.in_waiting > 0:
                                    data = temp_port.read(temp_port.in_waiting)
                                    if data:
                                        data_found = True
                                        break
                                time.sleep(0.005)

                            if data_found:
                                if self.serial_port and self.serial_port.is_open:
                                    self.serial_port.close()
                                self.serial_port = temp_port
                                self.ui.root.title(f"AEPL Logger (Connected: {port})")
                                self.start_logging()
                                break
                            else:
                                temp_port.close()
                        except (serial.SerialException, PermissionError) as e:
                            self.log_queue.put(f"Could not open {port}: {e}")

                known_ports = current_ports
                time.sleep(0.05)
            except Exception as e:
                self.log_queue.put(f"Port monitor error: {e}")

    def start_logging(self):
        if not self.serial_port or self.logging_active:
            return

        self.logging_active = True
        self.detecting_imei = True
        self.thread = threading.Thread(target=self.read_serial, daemon=True)
        self.thread.start()
        self.detect_and_send_imei_command()

    def stop_logging(self):
        self.logging_active = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        if self.log_file:
            try:
                self.log_file.close()
            except:
                pass
            self.log_file = None
        if self.fallback_log_file:
            try:
                self.fallback_log_file.close()
            except:
                pass
            self.fallback_log_file = None
        self.buffered_lines.clear()
        self.log_queue.put("Logging stopped.")

    def send_command(self, command):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.write((command + '\n').encode())

    def detect_and_send_imei_command(self):
        commands = ["*GET#IMEI#","*GET,IMEI#", "CMN *GET#IMEI#" ]
        for i, cmd in enumerate(commands):
            self.ui.root.after(i * 2000, lambda c=cmd: self.send_command(c))
        self.ui.root.after(7000, lambda: setattr(self, 'detecting_imei', False))

    def read_serial(self):
        ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
        imei_pattern = re.compile(r'IMEI[:#\s]*(\d{14,17})', re.IGNORECASE)

        buffer = ""

        while self.logging_active:
            try:
                if self.serial_port.in_waiting:
                    raw_data = self.serial_port.read(self.serial_port.in_waiting).decode('utf-8', errors='ignore')
                    buffer += raw_data
                    lines = buffer.splitlines(keepends=False)
                    if raw_data and not raw_data.endswith("\n"):
                        buffer = lines.pop() if lines else buffer
                    else:
                        buffer = ""

                    for line in lines:
                        clean_line = ansi_escape.sub('', line)
                        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

                        if self.detecting_imei and self.imei is None:
                            self.buffered_lines.append(clean_line)
                            match = imei_pattern.search(clean_line)
                            if match:
                                self.imei = match.group(1)
                                self.detecting_imei = False
                                self.log_file = open(self._generate_log_path(), 'a', encoding='utf-8', errors='ignore')
                                # self.log_queue.put(f"IMEI Detected: {self.imei}")

                                for buffered in self.buffered_lines:
                                    self.log_file.write(f"{timestamp} - {buffered}\n")
                                self.log_file.flush()
                                self.buffered_lines.clear()

                                if self.fallback_log_file:
                                    try:
                                        self.fallback_log_file.close()
                                        fallback_path = os.path.join(self._get_log_folder(), "default.log")
                                        if os.path.exists(fallback_path):
                                            os.remove(fallback_path)
                                    except Exception as e:
                                        self.log_queue.put(f"Error deleting fallback log: {e}")
                                    finally:
                                        self.fallback_log_file = None

                        if self.imei and self.log_file:
                            self.log_file.write(f"{timestamp} - {clean_line}\n")
                            self.log_file.flush()
                        else:
                            if not self.fallback_log_file:
                                self._prepare_fallback_log()
                            self.fallback_log_file.write(f"{timestamp} - {clean_line}\n")
                            self.fallback_log_file.flush()

                        self.log_queue.put(clean_line)

            except Exception as e:
                self.log_queue.put(f"Error: {e}")
                break
            time.sleep(0.01)

    def process_log_queue(self):
        while not self.log_queue.empty():
            message = self.log_queue.get_nowait()
            self.ui.insert_log(message)
        self.ui.root.after(50, self.process_log_queue)