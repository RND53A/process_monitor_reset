"""
调试窗口模块
实时显示日志，支持清空和保存
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
from core.logger import get_logger, set_log_callback

class DebugWindow:
    def __init__(self, root):
        self.root = root
        self.window = None
        self.text_widget = None
        self.is_visible = False
        self.log_queue = []
        self.lock = threading.Lock()

        set_log_callback(self.on_log)

    def create_window(self):
        if self.window is not None and self.window.winfo_exists():
            self.window.lift()
            return
        self.window = tk.Toplevel(self.root)
        self.window.title("调试日志 - Process Monitor")
        self.window.geometry("800x500")
        self.window.protocol("WM_DELETE_WINDOW", self.hide)

        self.text_widget = scrolledtext.ScrolledText(
            self.window, wrap=tk.WORD, font=("Consolas", 10)
        )
        self.text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(btn_frame, text="清空", command=self.clear).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="保存", command=self.save_log).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="关闭", command=self.hide).pack(side=tk.RIGHT, padx=2)

        with self.lock:
            for level, msg in self.log_queue:
                self._append_log(level, msg)
            self.log_queue.clear()

        self.is_visible = True

    def show(self):
        if self.window is None or not self.window.winfo_exists():
            self.create_window()
        else:
            self.window.deiconify()
            self.window.lift()
        self.is_visible = True

    def hide(self):
        if self.window and self.window.winfo_exists():
            self.window.withdraw()
        self.is_visible = False

    def toggle(self):
        if self.is_visible:
            self.hide()
        else:
            self.show()

    def on_log(self, level, msg):
        if self.text_widget and self.is_visible:
            self.root.after(0, self._append_log, level, msg)
        else:
            with self.lock:
                self.log_queue.append((level, msg))
                if len(self.log_queue) > 1000:
                    self.log_queue.pop(0)

    def _append_log(self, level, msg):
        if not self.text_widget:
            return
        tag = None
        if "ERROR" in level:
            tag = "error"
        elif "WARNING" in level:
            tag = "warning"
        elif "DEBUG" in level:
            tag = "debug"

        self.text_widget.insert(tk.END, msg + "\n", tag)
        self.text_widget.see(tk.END)

        self.text_widget.tag_config("error", foreground="red")
        self.text_widget.tag_config("warning", foreground="orange")
        self.text_widget.tag_config("debug", foreground="gray")

    def clear(self):
        if self.text_widget:
            self.text_widget.delete(1.0, tk.END)

    def save_log(self):
        from tkinter import filedialog
        from datetime import datetime
        default_name = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        filename = filedialog.asksaveasfilename(
            defaultextension=".log",
            initialfile=default_name,
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt")]
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                if self.text_widget:
                    f.write(self.text_widget.get(1.0, tk.END))
