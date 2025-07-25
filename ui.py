import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox, PhotoImage
from serial_handler import SerialManager
from macro_executor import MacroExecutor
import re
import sys


class UI:
    dev_name = "Suraj Bhalerao"

    def __init__(self, root):
        self.root = root
        self.root.title("AEPL Logger (Disconnected)")
        self.root.geometry("800x600")

        try:
            if sys.platform.startswith("win"):
                self.root.iconbitmap(r"./Assets/img.ico")
            else:
                icon = PhotoImage(file="./Assets/icon.png")
                self.root.iconphoto(True, icon)
        except Exception as e:
            print(f"Error setting icon: {e}")

        self.log_console = scrolledtext.ScrolledText(
            self.root, wrap=tk.NONE, bg="black", fg="white", font=("Consolas", 10)
        )
        self.log_console.pack(expand=True, fill=tk.BOTH)
        self.log_console.bind("<KeyPress>", self.block_typing_during_logging)

        self.color_tags = {
        "AIS": "#0039a6",  # Deep blue
        "CVP": "#0000ff",  # Blue
        "CAN": "#ff00ff",  # Magenta
        "NET": "#008000",  # Green
        "PLA": "#ffff00",  # Yellow
        "FOT": "#bd309f",  # Magenta 
    }
        for tag, color in self.color_tags.items():
            self.log_console.tag_configure(tag.lower(), foreground=color)

        self.serial_manager = SerialManager(self)
        self.macro_executor = MacroExecutor(self)

        self.create_menu()

        # Global key bindings
        self.root.bind_all("<Control-l>", lambda e: self.serial_manager.start_logging())
        self.root.bind_all("<Control-q>", lambda e: self.serial_manager.stop_logging())
        self.root.bind_all("<Control-m>", lambda e: self.root.iconify())
        self.root.bind_all("<space>", lambda e: self.scroll_to_bottom())
        self.root.bind_all("<Return>", lambda e: self.scroll_to_bottom())
        self.log_console.bind("<Control-c>", self.copy_text)
        self.log_console.bind("<Control-v>", self.paste_text)
        self.log_console.bind("<Control-a>", self.select_all)

        self.log_console.bind("<MouseWheel>", self.on_mouse_scroll)
        self.log_console.bind("<Button-4>", self.on_mouse_scroll_linux_up)
        self.log_console.bind("<Button-5>", self.on_mouse_scroll_linux_down)

        self.user_scrolled = False

    def create_menu(self):
        menu_bar = tk.Menu(self.root)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(
            label="Start Logging",
            command=self.serial_manager.start_logging,
            accelerator="Ctrl+L",
        )
        file_menu.add_command(
            label="Stop Logging",
            command=self.serial_manager.stop_logging,
            accelerator="Ctrl+Q",
        )
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Alt+Q")
        menu_bar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menu_bar, tearoff=0)
        edit_menu.add_command(
            label="Copy", command=self.copy_text, accelerator="Ctrl+C"
        )
        edit_menu.add_command(
            label="Paste", command=self.paste_text, accelerator="Ctrl+V"
        )
        menu_bar.add_cascade(label="Edit", menu=edit_menu)

        macro_menu = tk.Menu(menu_bar, tearoff=0)
        macro_menu.add_command(
            label="Run Macro", command=self.macro_executor.load_and_run
        )
        menu_bar.add_cascade(label="Macros", menu=macro_menu)

        window_menu = tk.Menu(menu_bar, tearoff=0)
        window_menu.add_command(
            label="Minimize", command=self.root.iconify, accelerator="Ctrl+M"
        )
        window_menu.add_command(label="Maximize", command=self.maximize_window)
        menu_bar.add_cascade(label="Window", menu=window_menu)

        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menu_bar)

    def insert_log(self, message):
        split_lines = re.split(r"(?<!\n)[|+](?=\w)", message)

        for line in split_lines:
            line = line.strip()
            if not line:
                continue

            tag = None
            for keyword in self.color_tags:
                if keyword in line:
                    tag = keyword.lower()
                    break

            if tag:
                self.log_console.insert(tk.END, line + "\n", tag)
            else:
                self.log_console.insert(tk.END, line + "\n")

        if not self.user_scrolled:
            self.log_console.yview(tk.END)

    def copy_text(self, event=None):
        try:
            selected = self.log_console.get("sel.first", "sel.last")
            self.root.clipboard_clear()
            self.root.clipboard_append(selected)
        except tk.TclError:
            messagebox.showwarning("Copy", "No text selected to copy.")
        return "break"

    def paste_text(self, event=None):
        try:
            clipboard = self.root.clipboard_get()
            self.log_console.insert(tk.END, clipboard + "\n")
            self.log_console.yview(tk.END)

            if (
                self.serial_manager.serial_port
                and self.serial_manager.serial_port.is_open
            ):
                for line in clipboard.strip().splitlines():
                    if line.startswith("*"):
                        self.serial_manager.serial_port.write((line + "\n").encode())
                        self.insert_log(f"{line}")
        except tk.TclError:
            messagebox.showwarning("Paste", "Clipboard is empty or cannot be accessed.")
        return "break"

    def select_all(self, event=None):
        self.log_console.tag_add("sel", "1.0", "end")
        return "break"

    def on_mouse_scroll(self, event):
        self.user_scrolled = not self.at_bottom()

    def scroll_to_bottom(self):
        self.user_scrolled = False
        self.root.after(10, lambda: self.log_console.yview_moveto(1.0))

    def at_bottom(self):
        return self.log_console.yview()[1] == 1.0

    def on_mouse_scroll_linux_up(self, event):
        self.log_console.yview_scroll(-1, "units")
        self.user_scrolled = not self.at_bottom()
        return "break"

    def on_mouse_scroll_linux_down(self, event):
        self.log_console.yview_scroll(1, "units")
        self.user_scrolled = not self.at_bottom()
        return "break"

    def maximize_window(self):
        self.root.state("zoomed")

    def show_about(self):
        messagebox.showinfo(
            f"About",
            f"AEPL Logger\nVersion 3.0\n\nDeveloped by - {self.dev_name} \n\nThis application logs and manages AEPL data.",
        )

    def block_typing_during_logging(self, event):
        if self.serial_manager.logging_active:
            if event.state & 0x0004 or event.keysym in ["space", "Return"]:
                return None
            return "break"
