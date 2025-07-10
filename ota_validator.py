import json
import time
import threading
import re


class OTAValidator:
    def __init__(self, serial_manager):
        self.serial_manager = serial_manager
        self.ota_config = self.load_ota_config()
        self.uin_commands = self.ota_config.get("uin_commands", [])
        self.timeout = self.ota_config.get("timeout", 10)
        self.retries = self.ota_config.get("retries", 2)
        self.device_profiles = self.ota_config.get("device_profiles", {})

    def load_ota_config(self):
        with open("./config/ota_config.json", "r") as f:
            return json.load(f)

    def start_validation_after_delay(self, delay=50):
        threading.Thread(target=self._delayed_start, args=(delay,), daemon=True).start()

    def _delayed_start(self, delay):
        print(f"[INFO] Waiting {delay}s before OTA validation...")
        time.sleep(delay)
        self.validate_device()

    def send_and_wait_response(self, command, keyword=None, timeout=None):
        timeout = timeout or self.timeout
        self.serial_manager.send_command(command)
        start_time = time.time()

        while time.time() - start_time < timeout:
            lines = self.serial_manager.get_recent_lines()
            for line in reversed(lines):
                if keyword and keyword in line:
                    return line
                elif not keyword:
                    return line
            time.sleep(0.2)
        return None

    def extract_device_type(self, uin_line):
        match = re.search(r"ACON4(..)", uin_line)
        if match:
            code = match.group(1)
            if code == "NA":
                return "TCU 2G"
            elif code == "IA":
                return "TCU 4G"
            elif code == "CA":
                return "Sampark"
        return None

    def validate_device(self):
        print("[INFO] Starting UIN detection...")

        uin_line = None
        for attempt in range(self.retries):
            for cmd in self.uin_commands:
                print(f"[INFO] Attempt {attempt+1}: Sending UIN command: {cmd}")
                uin_line = self.send_and_wait_response(cmd, keyword="ACON4")
                if uin_line:
                    break
            if uin_line:
                break

        if not uin_line:
            print("[ERROR] UIN response not received after all retries.")
            return

        device_type = self.extract_device_type(uin_line)
        if not device_type:
            print("[ERROR] Could not identify device type from UIN line.")
            return

        print(f"[INFO] Detected device type: {device_type}")

        device_config = self.device_profiles.get(device_type)
        if not device_config:
            print(f"[ERROR] No OTA config found for device: {device_type}")
            return

        for get_cmd, data in device_config.items():
            expected = data["expected"]
            set_cmd = data["set_command"]
            keyword = expected.split("#")[1] if "#" in expected else None

            print(f"[INFO] Sending GET command: {get_cmd}")
            response = self.send_and_wait_response(get_cmd, keyword=keyword)

            if response and expected in response:
                print(f"[OK] Validated: {get_cmd}")
            else:
                print(f"[FIX] Sending SET for: {get_cmd}")
                self.serial_manager.send_command(set_cmd)
