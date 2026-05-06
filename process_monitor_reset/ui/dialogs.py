"""
设置对话框
允许修改热键、黑名单、HTTP API 配置等，以及文件接收目录
"""
import tkinter as tk
from tkinter import ttk, filedialog

class SettingsDialog:
    def __init__(self, parent, config, save_callback):
        self.parent = parent
        self.config = config.copy()
        self.save_callback = save_callback
        self.window = tk.Toplevel(parent)
        self.window.title("设置")
        self.window.geometry("550x580")
        self.window.transient(parent)
        self.window.grab_set()
        self.create_widgets()

    def create_widgets(self):
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)

        hotkey_frame = ttk.Frame(notebook)
        notebook.add(hotkey_frame, text="热键")
        self.create_hotkey_ui(hotkey_frame)

        blacklist_frame = ttk.Frame(notebook)
        notebook.add(blacklist_frame, text="黑名单")
        self.create_blacklist_ui(blacklist_frame)

        api_frame = ttk.Frame(notebook)
        notebook.add(api_frame, text="HTTP API")
        self.create_api_ui(api_frame)

        perf_frame = ttk.Frame(notebook)
        notebook.add(perf_frame, text="其他")
        self.create_perf_ui(perf_frame)

        # 新增：文件传输设置页
        file_frame = ttk.Frame(notebook)
        notebook.add(file_frame, text="文件传输")
        self.create_file_ui(file_frame)

        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="保存", command=self.save).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="取消", command=self.window.destroy).pack(side='left', padx=5)

    def create_hotkey_ui(self, parent):
        row = 0
        self.hotkey_vars = {}
        labels = {
            'refresh': '刷新进程列表',
            'show_all': '显示所有监控窗口',
            'hide_all': '隐藏所有监控窗口',
            'toggle_ui': '显示/隐藏主界面',
            'kill_selected': '结束选中进程'
        }
        for key, desc in labels.items():
            ttk.Label(parent, text=desc).grid(row=row, column=0, sticky='w', padx=5, pady=5)
            var = tk.StringVar(value=self.config['hotkeys'].get(key, ''))
            self.hotkey_vars[key] = var
            entry = ttk.Entry(parent, textvariable=var, width=15)
            entry.grid(row=row, column=1, padx=5, pady=5)
            row += 1

    def create_blacklist_ui(self, parent):
        self.blacklist_text = tk.Text(parent, height=10, width=40)
        self.blacklist_text.insert('1.0', '\n'.join(self.config.get('blacklist', [])))
        self.blacklist_text.pack(padx=10, pady=10, fill='both', expand=True)

    def create_api_ui(self, parent):
        self.api_enabled_var = tk.BooleanVar(value=self.config.get('http_api_enabled', False))
        ttk.Checkbutton(parent, text="启用HTTP API", variable=self.api_enabled_var).pack(anchor='w', pady=5)
        ttk.Label(parent, text="端口:").pack(anchor='w')
        self.api_port_var = tk.StringVar(value=str(self.config.get('http_api_port', 5000)))
        ttk.Entry(parent, textvariable=self.api_port_var).pack(anchor='w', pady=5)

    def create_perf_ui(self, parent):
        ttk.Label(parent, text="刷新间隔(秒):").pack(anchor='w', pady=(5,0))
        self.refresh_interval_var = tk.IntVar(value=self.config.get('refresh_interval', 5))
        spin_refresh = ttk.Spinbox(parent, from_=1, to=60, textvariable=self.refresh_interval_var, width=10)
        spin_refresh.pack(anchor='w', pady=2)

        ttk.Label(parent, text="设备发现端口:").pack(anchor='w', pady=(5,0))
        self.discovery_port_var = tk.StringVar(value=str(self.config.get('discovery_port', 5001)))
        ttk.Entry(parent, textvariable=self.discovery_port_var).pack(anchor='w', pady=2)

    def create_file_ui(self, parent):
        """文件传输设置界面"""
        ttk.Label(parent, text="文件接收目录:").pack(anchor='w', pady=(5,0))
        dir_frame = ttk.Frame(parent)
        dir_frame.pack(fill=tk.X, pady=2)
        self.receive_dir_var = tk.StringVar(value=self.config.get('receive_dir', ''))
        entry = ttk.Entry(dir_frame, textvariable=self.receive_dir_var, width=40)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        ttk.Button(dir_frame, text="浏览", command=self.browse_dir).pack(side=tk.RIGHT)
        ttk.Label(parent, text="提示: 其他设备发送的文件将保存到此目录", foreground="gray").pack(anchor='w', pady=(5,0))

    def browse_dir(self):
        dir_path = filedialog.askdirectory(title="选择文件接收目录")
        if dir_path:
            self.receive_dir_var.set(dir_path)

    def save(self):
        for key, var in self.hotkey_vars.items():
            self.config['hotkeys'][key] = var.get().strip()
        blacklist = [line.strip() for line in self.blacklist_text.get('1.0', 'end').splitlines() if line.strip()]
        self.config['blacklist'] = blacklist
        self.config['http_api_enabled'] = self.api_enabled_var.get()
        self.config['http_api_port'] = int(self.api_port_var.get())
        self.config['refresh_interval'] = self.refresh_interval_var.get()
        self.config['discovery_port'] = int(self.discovery_port_var.get())
        self.config['receive_dir'] = self.receive_dir_var.get().strip()
        self.save_callback(self.config)
        self.window.destroy()
