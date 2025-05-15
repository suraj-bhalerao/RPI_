import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox
from serial_handler import SerialManager
from macro_executor import MacroExecutor
from log_utils import view_log, change_directory
import re

class SerialUtility:
    def __init__(self, root):
        self.root = root
        self.root.title("AEPL Logger (Disconnected)")
        self.root.geometry("800x600")

        try:
            self.root.iconbitmap(r"img.ico")
        except Exception as e:
            print(f"Error setting icon: {e}")

        self.log_console = scrolledtext.ScrolledText(self.root, wrap=tk.NONE, bg="black", fg="white", font=("Consolas", 10))
        self.log_console.pack(expand=True, fill=tk.BOTH)

        self.color_tags = {
            'AIS': '#0039a6', 'CVP': 'blue', 'CAN': 'magenta',
            'NET': 'green', 'PLA': 'yellow', 'FOT': 'magenta'
        }
        for tag, color in self.color_tags.items():
            self.log_console.tag_configure(tag.lower(), foreground=color)

        self.serial_manager = SerialManager(self)
        self.macro_executor = MacroExecutor(self)

        self.create_menu()

        self.root.bind_all("<Control-l>", lambda e: self.serial_manager.start_logging())
        self.root.bind_all("<Control-q>", lambda e: self.serial_manager.stop_logging())
        self.root.bind_all("<Control-m>", lambda e: self.root.iconify())
        self.root.bind_all("<space>", lambda e: self.scroll_to_bottom())
        self.log_console.bind("<MouseWheel>", self.on_mouse_scroll)

        self.user_scrolled = False

    def create_menu(self):
        menu_bar = tk.Menu(self.root)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Start Logging", command=self.serial_manager.start_logging, accelerator="Ctrl+L")
        file_menu.add_command(label="Stop Logging", command=self.serial_manager.stop_logging, accelerator="Ctrl+Q")
        file_menu.add_command(label="View Log", command=view_log)
        file_menu.add_command(label="Change Directory", command=change_directory)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Alt+Q")
        menu_bar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menu_bar, tearoff=0)
        edit_menu.add_command(label="Copy", command=self.copy_text)
        edit_menu.add_command(label="Paste", command=self.paste_text)
        menu_bar.add_cascade(label="Edit", menu=edit_menu)

        macro_menu = tk.Menu(menu_bar, tearoff=0)
        macro_menu.add_command(label="Run Macro", command=self.macro_executor.load_and_run)
        menu_bar.add_cascade(label="Macros", menu=macro_menu)

        window_menu = tk.Menu(menu_bar, tearoff=0)
        window_menu.add_command(label="Minimize", command=self.root.iconify, accelerator="Ctrl+M")
        window_menu.add_command(label="Maximize", command=self.maximize_window)
        menu_bar.add_cascade(label="Window", menu=window_menu)

        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menu_bar)

    def insert_log(self, message):
        tag = None
        for keyword, tagname in self.color_tags.items():
            if keyword in message:
                tag = keyword.lower()
                break

        if tag:
            self.log_console.insert(tk.END, message + "\n", tag)
        else:
            self.log_console.insert(tk.END, message + "\n")

        if not self.user_scrolled:
            self.log_console.yview(tk.END)

    def copy_text(self):
        try:
            selected = self.log_console.get("sel.first", "sel.last")
            self.root.clipboard_clear()
            self.root.clipboard_append(selected)
        except tk.TclError:
            messagebox.showwarning("Copy", "No text selected to copy.")

    def paste_text(self):
        try:
            clipboard = self.root.clipboard_get()
            self.log_console.insert(tk.END, clipboard + "\n")
            self.log_console.yview(tk.END)

            if self.serial_manager.serial_port and self.serial_manager.serial_port.is_open:
                for line in clipboard.strip().splitlines():
                    if line.startswith('*'):
                        self.serial_manager.serial_port.write((line + '\n').encode())
                        self.insert_log(f"Sent command: {line}")
        except tk.TclError:
            messagebox.showwarning("Paste", "Clipboard is empty or cannot be accessed.")

    def on_mouse_scroll(self, event):
        self.user_scrolled = not self.at_bottom()

    def scroll_to_bottom(self):
        self.user_scrolled = False
        self.log_console.yview(tk.END)

    def at_bottom(self):
        return self.log_console.yview()[1] == 1.0

    def maximize_window(self):
        self.root.state('zoomed')

    def show_about(self):
        messagebox.showinfo("About", "AEPL Logger\nVersion 1.0")