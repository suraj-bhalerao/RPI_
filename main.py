import tkinter as tk
from ui import SerialUtility

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialUtility(root)
    root.mainloop()