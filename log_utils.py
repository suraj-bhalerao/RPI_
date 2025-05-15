from tkinter import filedialog, messagebox, Toplevel, Text, BOTH, END


def view_log():
    file_path = filedialog.askopenfilename(filetypes=[("Log Files", "*.log")])
    if file_path:
        with open(file_path, 'r') as file:
            content = file.read()
        win = Toplevel()
        win.title("View Log")
        text = Text(win)
        text.pack(expand=True, fill=BOTH)
        text.insert(END, content)
        text.config(state='disabled')


def change_directory():
    path = filedialog.askdirectory()
    if path:
        messagebox.showinfo("Change Directory", f"Changed to: {path}")