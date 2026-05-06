"""
监控树控件
显示已监控的进程列表，支持隐藏/显示、移除、终止等操作
"""
import tkinter as tk
from tkinter import ttk, messagebox
import psutil
import os
import time
from core.logger import get_logger

logger = get_logger()

class MonitorTree:
    def __init__(self, parent_frame, controller):
        self.controller = controller
        self.monitor_frame = ttk.LabelFrame(parent_frame, text="监控列表")
        self.monitor_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5,0))
        self.monitor_frame.columnconfigure(0, weight=1)
        self.monitor_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(self.monitor_frame, columns=('pid', 'status'),
                                 show='tree headings', selectmode='extended')
        self.tree.heading('#0', text="进程")
        self.tree.heading('pid', text="PID")
        self.tree.heading('status', text="状态")
        self.tree.column('#0', width=200)
        self.tree.column('pid', width=80)
        self.tree.column('status', width=100)

        scrollbar = ttk.Scrollbar(self.monitor_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        self.tree.bind('<Double-1>', self.remove_from_monitor)
        self.tree.bind('<Button-3>', self.show_menu)

        self.setup_context_menu()
        self.refresh()

    def setup_context_menu(self):
        self.menu = tk.Menu(self.tree, tearoff=0)
        self.menu.add_command(label="从监控移除", command=self.remove_selected_from_monitor)
        self.menu.add_separator()
        self.menu.add_command(label="查看详情", command=self.view_selected_details)
        self.menu.add_command(label="终止进程", command=self.kill_selected_process)
        self.menu.add_separator()
        self.menu.add_command(label="复制PID", command=self.copy_selected_pid)
        self.menu.add_command(label="复制名称", command=self.copy_selected_name)

    def show_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.menu.post(event.x_root, event.y_root)

    def refresh(self):
        logger.debug(f"开始刷新监控列表，当前监控 PID: {self.controller.config.monitored_pids}")
        """刷新监控列表"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        with self.controller.config.lock:
            pids = list(self.controller.config.monitored_pids)
            hidden_set = set(self.controller.config.hidden_pids)
        for pid in pids:
            try:
                proc = psutil.Process(pid)
                proc_name = proc.name()
                exe_path = proc.exe()
            except:
                proc_name = "未知进程"
                exe_path = None
            status = "已隐藏" if pid in hidden_set else "可见"
            icon = self.controller.icon_cache.get_icon(exe_path) if exe_path and os.path.isfile(exe_path) else None
            if icon:
                self.tree.insert('', 'end', text=proc_name, values=(pid, status), image=icon, tags=('monitor',))
            else:
                self.tree.insert('', 'end', text=proc_name, values=(pid, status), tags=('monitor',))

    def remove_from_monitor(self, event):
        self.remove_selected_from_monitor()

    def remove_selected_from_monitor(self):
        selection = self.tree.selection()
        if not selection:
            return
        for item in selection:
            values = self.tree.item(item, 'values')
            pid = int(values[0])
            logger.info(f"从监控列表移除 PID {pid}")
            self.controller.remove_pid_from_monitor(pid)

    def view_selected_details(self):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        values = self.tree.item(item, 'values')
        pid = int(values[0])
        self.show_process_details(pid)

    def show_process_details(self, pid):
        try:
            proc = psutil.Process(pid)
            with proc.oneshot():
                name = proc.name()
                status = proc.status()
                cpu_percent = proc.cpu_percent(interval=0.1)
                memory_percent = proc.memory_percent()
                memory_rss = proc.memory_info().rss // 1024 // 1024
                create_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(proc.create_time()))
                exe_path = proc.exe()
                cmdline = ' '.join(proc.cmdline()) if proc.cmdline() else 'N/A'
                username = proc.username()
                num_threads = proc.num_threads()
                details = f"""
进程详情:
---------------
PID: {pid}
名称: {name}
状态: {status}
CPU占用率: {cpu_percent:.2f}%
内存占用率: {memory_percent:.2f}%
内存使用量: {memory_rss} MB
创建时间: {create_time}
用户名: {username}
线程数: {num_threads}
执行路径: {exe_path}
命令行参数: {cmdline}
"""
            messagebox.showinfo("进程详情", details)
        except psutil.AccessDenied:
            messagebox.showerror("访问被拒绝", f"无法访问进程 {pid}。需要管理员权限。")
        except psutil.NoSuchProcess:
            messagebox.showwarning("进程不存在", f"进程 {pid} 不存在。")
        except Exception as e:
            messagebox.showerror("错误", f"无法获取进程详情: {e}")

    def kill_selected_process(self):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        values = self.tree.item(item, 'values')
        pid = int(values[0])
        name = self.tree.item(item, 'text')
        logger.info(f"用户请求终止监控进程: {name} (PID: {pid})")
        if not messagebox.askyesno("确认", f"确定要终止进程 {name} (PID: {pid}) 吗？"):
            return
        try:
            if pid in self.controller.config.hidden_pids:
                self.controller.show_process_windows(pid)
            proc = psutil.Process(pid)
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except:
                pass
            self.controller.remove_pid_from_monitor(pid)
            messagebox.showinfo("成功", f"进程 {name} (PID: {pid}) 终止成功")
        except psutil.AccessDenied:
            messagebox.showerror("访问被拒绝", f"无法访问进程 {pid}。需要管理员权限。")
        except psutil.NoSuchProcess:
            messagebox.showwarning("进程不存在", f"进程 {pid} 不存在。")
            self.controller.remove_pid_from_monitor(pid)
        except Exception as e:
            messagebox.showerror("错误", f"终止进程失败: {e}")

    def copy_selected_pid(self):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        values = self.tree.item(item, 'values')
        if not values:
            return
        pid = values[0]
        self.controller.root.clipboard_clear()
        self.controller.root.clipboard_append(str(pid))
        self.controller.root.update()

    def copy_selected_name(self):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        name = self.tree.item(item, 'text')
        self.controller.root.clipboard_clear()
        self.controller.root.clipboard_append(name)
        self.controller.root.update()

    def set_controls_state(self, state):
        pass
