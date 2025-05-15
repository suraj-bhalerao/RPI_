# File: serial_handler.py

import serial
import threading
import time
import serial.tools.list_ports
import os
import re

class SerialManager:
    def __init__(self, ui):
        self.ui = ui
        self.serial_port = None
        self.thread = None
        self.logging_active = False
        self.waiting_for_imei = False
        self.imei_log_file = None

        self.monitor_thread = threading.Thread(target=self.auto_monitor_ports, daemon=True)
        self.monitor_thread.start()

        if not os.path.exists("logs"):
            os.makedirs("logs")

    def auto_monitor_ports(self):
        known_ports = set()
        while True:
            try:
                current_ports = set(p.device for p in serial.tools.list_ports.comports())
                new_ports = current_ports - known_ports
                lost_ports = known_ports - current_ports

                if new_ports:
                    port = new_ports.pop()
                    self.serial_port = serial.Serial(port, baudrate=115200, timeout=1)
                    self.ui.root.title("AEPL Logger (Connected)")
                    self.start_logging()

                if lost_ports:
                    self.ui.root.title("AEPL Logger (Disconnected)")
                    self.stop_logging()

                known_ports = current_ports
                time.sleep(2)
            except Exception as e:
                self.ui.insert_log(f"Port monitor error: {e}")

    def start_logging(self):
        if not self.serial_port:
            return
        if not self.logging_active:
            self.logging_active = True
            self.thread = threading.Thread(target=self.read_serial, daemon=True)
            self.thread.start()
            self.ui.insert_log("Logging started...")

    def stop_logging(self):
        self.logging_active = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        if self.imei_log_file:
            self.imei_log_file.close()
            self.imei_log_file = None
        self.ui.insert_log("Logging stopped.")

    def send_command(self, command):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.write((command + '\n').encode())
            self.ui.insert_log(f"Sent command: {command}")
            if command.strip().upper() == '*GET#IMEI#':
                self.waiting_for_imei = True

    def read_serial(self):
        imei_pattern = re.compile(r'IMEI\s*[:\-]?\s*(\d{14,17})', re.IGNORECASE)

        while self.logging_active:
            try:
                if self.serial_port.in_waiting:
                    line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                    self.ui.insert_log(line)

                    if self.waiting_for_imei:
                        match = imei_pattern.search(line)
                        if match:
                            imei = match.group(1)
                            log_path = os.path.join("logs", f"log_{imei}.log")

                            if self.imei_log_file:
                                self.imei_log_file.close()

                            self.imei_log_file = open(log_path, 'a')
                            self.ui.insert_log(f"IMEI detected: {imei} — Log file: {log_path}")
                            self.waiting_for_imei = False

                    if self.imei_log_file:
                        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                        self.imei_log_file.write(f"{timestamp} - {line}\n")

            except Exception as e:
                self.ui.insert_log(f"Error: {e}")
                break
            time.sleep(0.1)
