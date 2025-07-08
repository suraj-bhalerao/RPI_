import time
import json
from tkinter import filedialog, messagebox

class MacroExecutor:
    def __init__(self, ui):
        self.ui = ui
        self.commands = []
        self.current_index = 0
        self.validation_data = self.load_validation_file()

    def load_validation_file(self):
        try:
            with open("ota_validation.json", "r") as f:
                return json.load(f)
        except Exception as e:
            messagebox.showerror("Validation Config Error", f"Could not load OTA validation file.\n{e}")
            return {}

    def load_and_run(self):
        file_path = filedialog.askopenfilename(filetypes=[("TTL Files", "*.ttl")])
        if not file_path:
            return
        try:
            self.commands = []
            with open(file_path, 'r') as f:
                self.commands = [line.strip() for line in f if line.strip()]
            self.current_index = 0
            self.execute_next_command()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def execute_next_command(self):
        if self.current_index >= len(self.commands):
            self.ui.insert_log("✅ Macro execution completed.")
            return

        cmd = self.commands[self.current_index]
        self.current_index += 1

        if cmd.lower().startswith("pause"):
            try:
                delay = float(cmd.split()[1])
                self.ui.root.after(int(delay * 1000), self.execute_next_command)
            except:
                self.ui.insert_log("⚠️ Invalid pause command. Skipping...")
                self.ui.root.after(100, self.execute_next_command)
        elif cmd.startswith('*'):
            if self.ui.serial_manager.serial_port and self.ui.serial_manager.serial_port.is_open:
                self.ui.serial_manager.serial_port.reset_input_buffer()
                self.ui.serial_manager.serial_port.write((cmd + '\n').encode())

                if cmd in self.validation_data:
                    expected = self.validation_data[cmd]["expected"]
                    correction = self.validation_data[cmd].get("set_command")
                    self.ui.root.after(1000, lambda: self.validate_response(cmd, expected, correction))
                else:
                    self.ui.root.after(500, self.execute_next_command)
            else:
                self.ui.insert_log("⚠️ Serial port not open.")
                self.ui.root.after(500, self.execute_next_command)
        else:
            self.ui.insert_log(f"ℹ️ Ignored non-command: {cmd}")
            self.ui.root.after(100, self.execute_next_command)

    def validate_response(self, command, expected, correction=None):
        try:
            if self.ui.serial_manager.serial_port.in_waiting:
                response = self.ui.serial_manager.serial_port.read(
                    self.ui.serial_manager.serial_port.in_waiting
                ).decode('utf-8', errors='ignore')

                matched = expected in response
                if matched:
                    self.ui.insert_log(f"✅ [{command}] matched: {expected}")
                else:
                    self.ui.insert_log(f"❌ [{command}] mismatch. Expected: {expected}")
                    if correction:
                        self.ui.insert_log(f"⚙️ Sending correction: {correction}")
                        self.ui.serial_manager.serial_port.write((correction + '\n').encode())

        except Exception as e:
            self.ui.insert_log(f"❌ Validation Error: {e}")
        finally:
            self.ui.root.after(500, self.execute_next_command)
