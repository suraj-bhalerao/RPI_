import threading
import time
from tkinter import filedialog, messagebox

class MacroExecutor:
    def __init__(self, ui):
        self.ui = ui
        self.commands = []

    def load_and_run(self):
        file_path = filedialog.askopenfilename(filetypes=[("TTL Files", "*.ttl")])
        if not file_path:
            return
        try:
            with open(file_path, 'r') as f:
                self.commands = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            threading.Thread(target=self.run_macro, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def run_macro(self):
        for cmd in self.commands:
            if cmd.lower().startswith("pause"):
                try:
                    delay = float(cmd.split()[1])
                    self.ui.insert_log(f"Pausing for {delay} seconds...")
                    time.sleep(delay)
                except:
                    self.ui.insert_log("Invalid pause command.")
            else:
                self.ui.insert_log(f"Executing: {cmd}")
                if self.ui.serial_manager.serial_port and self.ui.serial_manager.serial_port.is_open:
                    self.ui.serial_manager.serial_port.write((cmd + '\n').encode())
                    while True:
                        if self.ui.serial_manager.serial_port.in_waiting:
                            response = self.ui.serial_manager.serial_port.readline().decode('utf-8').strip()
                            self.ui.insert_log(f"Device Response: {response}")
                            if "done" in response.lower() or "command completed" in response.lower():
                                break
                        time.sleep(0.1)
