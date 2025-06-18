import serial
import threading
import time
import serial.tools.list_ports
import os
import re
import queue

class SerialManager:
    def __init__(self, ui):
        self.ui = ui
        self.serial_port = None
        self.thread = None
        self.logging_active = False
        self.waiting_for_imei = False
        self.imei_log_file = None
        self.fallback_log_file = None
        self.log_queue = queue.Queue()
        self.buffered_lines = []

        self.monitor_thread = threading.Thread(target=self.auto_monitor_ports, daemon=True)
        self.monitor_thread.start()

        if not os.path.exists("logs"):
            os.makedirs("logs")

        self._prepare_fallback_log()
        self.ui.root.after(50, self.process_log_queue)

    def _get_log_folder(self):
        date_str = time.strftime("%Y-%m-%d")
        folder_path = os.path.join("logs", date_str)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        return folder_path

    def _prepare_fallback_log(self):
        log_folder = self._get_log_folder()
        fallback_path = os.path.join(log_folder, "default.log")
        if self.fallback_log_file:
            try:
                self.fallback_log_file.close()
            except:
                pass
        self.fallback_log_file = open(fallback_path, 'a')

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
                            while time.time() - start_time < 0.2:
                                if temp_port.in_waiting > 0:
                                    data = temp_port.read(temp_port.in_waiting)
                                    if data:
                                        data_found = True
                                        break
                                time.sleep(0.01) 
                            
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
                time.sleep(1) 
            except Exception as e:
                self.log_queue.put(f"Port monitor error: {e}")

    def start_logging(self):
        if not self.serial_port:
            return
        if not self.logging_active:
            self.logging_active = True
            if not self.fallback_log_file:
                self._prepare_fallback_log()
            self.waiting_for_imei = True
            if self.imei_log_file:
                try:
                    self.imei_log_file.close()
                except:
                    pass
                self.imei_log_file = None
            self.buffered_lines.clear()
            self.thread = threading.Thread(target=self.read_serial, daemon=True)
            self.thread.start()
            # self.log_queue.put("Logging started...")
            self.send_command("*GET#IMEI#")

    def stop_logging(self):
        self.logging_active = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        if self.imei_log_file:
            try:
                self.imei_log_file.close()
            except:
                pass
            self.imei_log_file = None
        if self.fallback_log_file:
            try:
                self.fallback_log_file.close()
            except:
                pass
            self.fallback_log_file = None
        self.log_queue.put("Logging stopped.")

    def send_command(self, command):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.write((command + '\n').encode())
            # self.log_queue.put(f"Sent command: {command}")
            if command.strip().upper() == '*GET#IMEI#':
                self.waiting_for_imei = True

    def read_serial(self):
        imei_pattern = re.compile(r'STATUS#IMEI#(\d{14,17})#', re.IGNORECASE)
        ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

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
                        self.log_queue.put(clean_line)

                        if self.waiting_for_imei:
                            self.buffered_lines.append(clean_line)
                            match = imei_pattern.search(clean_line)
                            if match:
                                imei = match.group(1)
                                log_folder = self._get_log_folder()
                                timestamp_str = time.strftime("%Y-%m-%d - %H.%M")
                                new_log_name = f"{imei} - {timestamp_str}.log"
                                new_log_path = os.path.join(log_folder, new_log_name)

                                try:
                                    self.imei_log_file = open(new_log_path, 'a')
                                    for buffered in self.buffered_lines:
                                        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                                        self.imei_log_file.write(f"{timestamp} - {buffered}\n")
                                    self.buffered_lines.clear()
                                except Exception as e:
                                    self.log_queue.put(f"Error creating IMEI log file: {e}")

                                # self.log_queue.put(f"IMEI detected: {imei} — Log file: {new_log_path}")
                                self.waiting_for_imei = False

                        log_target = self.imei_log_file if self.imei_log_file else self.fallback_log_file
                        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                        log_target.write(f"{timestamp} - {clean_line}\n")
                        log_target.flush()

            except Exception as e:
                self.log_queue.put(f"Error: {e}")
                break
            time.sleep(0.01)

    def process_log_queue(self):
        while not self.log_queue.empty():
            message = self.log_queue.get_nowait()
            self.ui.insert_log(message)
        self.ui.root.after(50, self.process_log_queue)