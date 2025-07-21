import json
import threading
import time
import logging


class OTAValidator:
    def __init__(self, serial_manager):
        self.serial_manager = serial_manager
        self.config = self.load_config()
        self.uin = None
        self.logger = logging.getLogger("OTAValidator")

    def load_config(self):
        try:
            with open("./config/ota_config.json", "r") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            return {}

    def start_validation_after_delay(self, delay_seconds):
        threading.Thread(target=self._delayed_start, args=(delay_seconds,), daemon=True).start()

    def _delayed_start(self, delay_seconds):
        self.logger.info(f"Waiting {delay_seconds}s before OTA validation...")
        time.sleep(delay_seconds)
        self.validate_device()

    def validate_device(self):
        uin = self.detect_uin()
        if not uin:
            self.logger.warning("UIN detection failed.")
            return

        self.uin = uin
        profile = self.config.get("device_profiles", {}).get("TCU 4G")  # Hardcoded for now

        if not profile:
            self.logger.warning("No profile found for TCU 4G.")
            return

        for get_cmd, params in profile.items():
            expected = params.get("expected")
            set_cmd = params.get("set_command")
            set_expected = params.get("set_expected")  ## why this ?

            success = self.attempt_get_and_validate(get_cmd, expected)
            if success:
                continue

            if set_cmd and set_expected:
                self.logger.info(f"Sending SET command: {set_cmd}")
                if self.send_and_validate(set_cmd, set_expected):
                    self.logger.info(f"Successfully applied setting via: {set_cmd}")
                else:
                    self.logger.warning(f"SET failed for: {set_cmd}")

    def detect_uin(self):
        for cmd in self.config.get("uin_commands", []):
            for attempt in range(self.config.get("retries", 1)):
                self.logger.info(f"Attempt {attempt + 1}: Sending UIN command: {cmd}")
                self.serial_manager.send_command(cmd)
                lines = self.wait_for_response(keyword="STATUS#UIN#", timeout=self.config.get("timeout", 10))
                for line in lines:
                    if "STATUS#UIN#" in line:
                        uin = line.split("STATUS#UIN#")[-1].strip("# \r\n")
                        self.logger.info(f"Detected UIN: {uin}")
                        return uin
                time.sleep(1)
        return None

    def attempt_get_and_validate(self, command, expected_value):
        retries = self.config.get("retries", 1)
        for attempt in range(retries):
            self.logger.info(f"[Attempt {attempt + 1}] Sending GET command: {command}")
            self.serial_manager.send_command(command)
            lines = self.wait_for_response(expected_value, timeout=self.config.get("timeout", 10))
            if any(expected_value in line for line in lines):
                self.logger.info(f"[OK] {command} returned expected value.")
                return True
            time.sleep(1)
        return False

    def send_and_validate(self, command, expected_response):
        self.logger.info(f"[SET] Sending command: {command}")
        self.serial_manager.send_command(command)
        lines = self.wait_for_response(expected_response, timeout=self.config.get("timeout", 10))
        if any(expected_response in line for line in lines):
            self.logger.info(f"[SET OK] Confirmed: {expected_response}")
            return True
        else:
            self.logger.warning(f"[SET FAIL] No matching response for: {expected_response}")
        return False

    def wait_for_response(self, keyword=None, timeout=10):
        start_time = time.time()
        while time.time() - start_time < timeout:
            lines = self.serial_manager.get_recent_lines(clear_after_read=False)
            if keyword:
                for line in lines:
                    if keyword in line:
                        # Clear only if we get what we want
                        self.serial_manager.get_recent_lines(clear_after_read=True)
                        return [line]
            else:
                if lines:
                    self.serial_manager.get_recent_lines(clear_after_read=True)
                    return lines
            time.sleep(0.3)
        return []

