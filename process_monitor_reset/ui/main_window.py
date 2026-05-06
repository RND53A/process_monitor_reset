"""
主窗口模块
提供进程列表和监控列表的UI布局，支持热键按钮文字同步更新
"""
import tkinter as tk
from tkinter import ttk
from ui.process_tree import ProcessTree
from ui.monitor_tree import MonitorTree

class MainWindow:
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller
        self.is_visible = True
        self.is_minimized = False

        self.root.title("Process Monitor")
        self.root.geometry("1300x800")
        self.root.resizable(True, True)

        # 按钮引用（用于更新热键文字）
        self.btn_toggle_visible = None
        self.btn_hide_all = None
        self.btn_show_all = None
        self.btn_kill_process = None
        self.btn_refresh = None

        self.setup_ui()
        self.controller.process_tree = self.process_tree
        self.controller.monitor_tree = self.monitor_tree

    def setup_ui(self):
        """构建界面布局"""
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(2, weight=1)

        # 控制面板
        self.control_frame = ttk.LabelFrame(self.main_frame, text="控制面板", padding="10")
        self.control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # 第一行
        ttk.Label(self.control_frame, text="进程ID:").grid(row=0, column=0, padx=(0,5))
        self.pid_entry = ttk.Entry(self.control_frame, width=12)
        self.pid_entry.grid(row=0, column=1, padx=(0,5))
        self.btn_search_pid = ttk.Button(self.control_frame, text="搜索PID", command=self.search_pid)
        self.btn_search_pid.grid(row=0, column=2, padx=(0,10))

        self.btn_toggle_visible = ttk.Button(self.control_frame, text="主程序 F12", command=self.toggle_visible)
        self.btn_toggle_visible.grid(row=0, column=3, padx=(0,10))
        self.btn_hide_all = ttk.Button(self.control_frame, text="隐藏应用 F11", command=self.controller.hide_all_and_minimize)
        self.btn_hide_all.grid(row=0, column=4, padx=(0,10))
        self.btn_show_all = ttk.Button(self.control_frame, text="恢复应用 F10", command=self.controller.show_all_and_restore)
        self.btn_show_all.grid(row=0, column=5, padx=(0,10))

        # 第二行
        ttk.Label(self.control_frame, text="进程名:").grid(row=1, column=0, padx=(0,5))
        self.name_entry = ttk.Entry(self.control_frame, width=12)
        self.name_entry.grid(row=1, column=1, padx=(0,5))
        self.btn_search_name = ttk.Button(self.control_frame, text="搜索名称", command=self.search_name)
        self.btn_search_name.grid(row=1, column=2, padx=(0,10))
        self.btn_kill_process = ttk.Button(self.control_frame, text="结束进程 K", command=self.kill_selected_from_any)
        self.btn_kill_process.grid(row=1, column=3, padx=(0,10))
        self.btn_debug = ttk.Button(self.control_frame, text="启动日志 F3", command=self.controller.toggle_debug_window)
        self.btn_debug.grid(row=1, column=4, padx=(0,10))
        self.btn_settings = ttk.Button(self.control_frame, text="设置", command=self.controller.open_settings)
        self.btn_settings.grid(row=1, column=5, padx=(0,10))
        self.btn_devices = ttk.Button(self.control_frame, text="局域网设备", command=self.controller.show_device_discovery_window)
        self.btn_devices.grid(row=1, column=6, padx=(10,0))

        # 左右列表区域
        list_frame = ttk.Frame(self.main_frame)
        list_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0,10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.columnconfigure(1, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.process_tree = ProcessTree(list_frame, self.controller)
        self.monitor_tree = MonitorTree(list_frame, self.controller)

        # 底部信息栏
        info_frame = ttk.Frame(self.main_frame)
        info_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        self.info_label = ttk.Label(info_frame, text="Process Monitor 1K34 Reset")
        self.info_label.pack(side=tk.LEFT)

        self.bsod_button = ttk.Button(info_frame, text=":(", command=self.controller.launch_bluescreen, width=3)
        self.bsod_button.pack(side=tk.RIGHT, padx=5)

        # 保存需要禁用的控件列表（用于窗口隐藏时）
        self.controls_to_disable = [
            self.pid_entry, self.name_entry,
            self.btn_search_pid, self.btn_search_name,
            self.btn_hide_all, self.btn_show_all,
            self.btn_kill_process, self.btn_settings, self.btn_debug, self.btn_devices
        ]

    def update_hotkey_labels(self, hotkeys):
        """根据热键配置更新按钮文字"""
        if self.btn_toggle_visible:
            key = hotkeys.get('toggle_ui', 'F12').upper()
            self.btn_toggle_visible.config(text=f"主程序 {key}")
        if self.btn_hide_all:
            key = hotkeys.get('hide_all', 'F11').upper()
            self.btn_hide_all.config(text=f"隐藏应用 {key}")
        if self.btn_show_all:
            key = hotkeys.get('show_all', 'F10').upper()
            self.btn_show_all.config(text=f"恢复应用 {key}")
        if self.btn_kill_process:
            key = hotkeys.get('kill_selected', 'K').upper()
            self.btn_kill_process.config(text=f"结束进程 {key}")
        # 如果有刷新按钮，也可以在此更新
        # if self.btn_refresh:
        #     key = hotkeys.get('refresh', 'F5').upper()
        #     self.btn_refresh.config(text=f"刷新 {key}")

    def search_pid(self):
        """通过PID搜索进程"""
        pid_str = self.pid_entry.get().strip()
        if not pid_str:
            tk.messagebox.showwarning("警告", "请输入PID")
            return
        try:
            pid = int(pid_str)
        except ValueError:
            tk.messagebox.showerror("错误", "PID必须是数字")
            return
        import psutil
        if not psutil.pid_exists(pid):
            tk.messagebox.showwarning("警告", f"PID为 {pid} 的进程不存在")
            return
        if tk.messagebox.askyesno("确认", f"是否将PID {pid}添加到监控列表？"):
            self.controller.add_pid_to_monitor(pid)

    def search_name(self):
        """通过进程名搜索"""
        name = self.name_entry.get().strip().lower()
        if not name:
            tk.messagebox.showwarning("警告", "请输入进程名称")
            return
        found = self.process_tree.search_name(name)
        if not found:
            tk.messagebox.showinfo("搜索结果", f"未找到包含'{name}'的进程")

    def kill_selected_from_any(self):
        """结束选中的进程（优先进程树，其次监控树）"""
        selection = self.process_tree.tree.selection()
        if selection:
            item = selection[0]
            tags = self.process_tree.tree.item(item, 'tags')
            if 'process' in tags:
                values = self.process_tree.tree.item(item, 'values')
                pid = int(values[0])
                name = self.process_tree.tree.item(item, 'text')
                self.controller.kill_selected_process_tree(pid, name)
                return
        selection = self.monitor_tree.tree.selection()
        if selection:
            self.monitor_tree.kill_selected_process()
            return
        tk.messagebox.showinfo("提示", "请先在进程列表或监控列表中选择一个进程")

    def toggle_visible(self):
        """显示/隐藏主窗口"""
        if self.is_visible:
            self.root.withdraw()
            self.is_visible = False
        else:
            self.root.deiconify()
            self.is_visible = True
            if self.is_minimized:
                self.root.geometry("1300x150")
            else:
                self.root.geometry("1300x800")
        self.set_controls_state()

    def set_controls_state(self, state=None):
        """设置控件状态（保留备用）"""
        pass

    def minimize(self):
        """最小化主窗口（仅缩小高度）"""
        if self.is_visible:
            self.root.geometry("1300x150")
            self.root.update()
            self.is_minimized = True

    def restore(self):
        """恢复主窗口原始大小"""
        if self.is_visible:
            self.root.geometry("1300x800")
            self.root.update()
            self.is_minimized = False
            self.process_tree.refresh()
            self.monitor_tree.refresh()
