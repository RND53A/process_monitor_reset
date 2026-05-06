"""
进程树控件
显示应用进程和后台进程，支持图标、分组、右键菜单
"""
import tkinter as tk
from tkinter import ttk, messagebox
import psutil
import win32gui
import win32process
import os
import re
import time
from core.system_utils import get_process_cpu_memory
from core.process_utils import terminate_process_tree
from core.logger import get_logger

logger = get_logger()

def natural_sort_key(s):
    """自然排序键函数（处理数字）"""
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

class ProcessTree:
    def __init__(self, parent_frame, controller):
        self.controller = controller
        self.process_frame = ttk.LabelFrame(parent_frame, text="进程列表")
        self.process_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0,5))
        self.process_frame.columnconfigure(0, weight=1)
        self.process_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(self.process_frame, columns=('pid', 'memory', 'status'),
                                 show='tree headings', selectmode='extended')
        self.tree.heading('#0', text="程序")
        self.tree.heading('pid', text="PID")
        self.tree.heading('memory', text="内存(MB)")
        self.tree.heading('status', text="状态")
        self.tree.column('#0', width=250)
        self.tree.column('pid', width=70)
        self.tree.column('memory', width=80)
        self.tree.column('status', width=80)

        scrollbar = ttk.Scrollbar(self.process_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        self.tree.bind('<Double-1>', self.add_to_monitor)
        self.tree.bind('<Button-3>', self.show_menu)

        self.top_app = self.tree.insert('', 'end', text="应用进程", values=('', '', ''), tags=('top',))
        self.top_background = self.tree.insert('', 'end', text="后台进程", values=('', '', ''), tags=('top',))

        self.setup_context_menu()
        self.refresh()

    def setup_context_menu(self):
        """创建右键菜单"""
        self.menu = tk.Menu(self.tree, tearoff=0)
        self.menu.add_command(label="添加到监控", command=self.add_selected_to_monitor)
        self.menu.add_command(label="查看详情", command=self.view_selected_details)
        self.menu.add_separator()
        self.menu.add_command(label="结束进程树", command=self.kill_selected_process_tree)
        self.menu.add_command(label="结束进程组", command=self.kill_selected_group)
        self.menu.add_separator()
        self.menu.add_command(label="复制PID", command=self.copy_selected_pid)
        self.menu.add_command(label="复制名称", command=self.copy_selected_name)

    def show_menu(self, event):
        """显示右键菜单（根据选中项动态启用/禁用）"""
        item = self.tree.identify_row(event.y)
        if item:
            tags = self.tree.item(item, 'tags')
            if 'top' in tags:
                for entry in ["添加到监控", "查看详情", "结束进程树", "结束进程组", "复制PID", "复制名称"]:
                    self.menu.entryconfig(entry, state=tk.DISABLED)
            elif 'group' in tags:
                for entry in ["添加到监控", "查看详情", "结束进程树", "复制PID", "复制名称"]:
                    self.menu.entryconfig(entry, state=tk.DISABLED)
                self.menu.entryconfig("结束进程组", state=tk.NORMAL)
            else:
                for entry in ["添加到监控", "查看详情", "结束进程树", "复制PID", "复制名称"]:
                    self.menu.entryconfig(entry, state=tk.NORMAL)
                self.menu.entryconfig("结束进程组", state=tk.DISABLED)
            self.tree.selection_set(item)
            self.menu.post(event.x_root, event.y_root)

    def refresh(self):
        """刷新进程列表（在UI线程调用）"""
        # 保存展开状态
        app_expanded = self.tree.item(self.top_app, 'open')
        bg_expanded = self.tree.item(self.top_background, 'open')
        bg_group_expanded = {}
        for group in self.tree.get_children(self.top_background):
            tags = self.tree.item(group, 'tags')
            if len(tags) >= 2 and tags[0] == 'group':
                key = tags[1]
                bg_group_expanded[key] = self.tree.item(group, 'open')

        # 清空
        for child in self.tree.get_children(self.top_app):
            self.tree.delete(child)
        for child in self.tree.get_children(self.top_background):
            self.tree.delete(child)

        # 获取有窗口的PID集合
        window_pids = set()
        def enum_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    window_pids.add(pid)
                except:
                    pass
            return True
        win32gui.EnumWindows(enum_callback, None)

        app_items = []
        bg_items = []
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'username']):
            try:
                pid = proc.info['pid']
                name = proc.info['name']
                exe = proc.info['exe']
                username = proc.info['username']
                has_window = pid in window_pids
                category = self.get_process_category(pid, exe, username, has_window)
                if category is None:
                    continue
                cpu, mem = get_process_cpu_memory(pid)
                mem_str = f"{mem:.1f}" if mem is not None else "?"
                with self.controller.config.lock:
                    status = "已监控" if pid in self.controller.config.monitored_pids else "未监控"
                if category == "应用":
                    app_items.append((name, pid, mem_str, status, exe))
                else:
                    bg_items.append((name, pid, mem_str, status, exe))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # 应用进程
        app_items.sort(key=lambda x: natural_sort_key(x[0]))
        for name, pid, mem_str, status, exe in app_items:
            icon = self.controller.icon_cache.get_icon(exe) if exe and os.path.isfile(exe) else None
            if icon:
                self.tree.insert(self.top_app, 'end', text=name, values=(pid, mem_str, status), image=icon, tags=('process',))
            else:
                self.tree.insert(self.top_app, 'end', text=name, values=(pid, mem_str, status), tags=('process',))

        # 后台进程分组
        groups = {}
        for name, pid, mem_str, status, exe in bg_items:
            key = exe if exe else name
            if key not in groups:
                groups[key] = []
            groups[key].append((name, pid, mem_str, status, exe))
        sorted_groups = sorted(groups.items(), key=lambda x: natural_sort_key(x[0] if x[0] else ''))
        for key, procs in sorted_groups:
            display_name = os.path.basename(key) if key else "未知程序"
            if not display_name or display_name == "":
                display_name = "未知程序"
            icon = self.controller.icon_cache.get_icon(key) if key and os.path.isfile(key) else None
            if icon:
                group_node = self.tree.insert(self.top_background, 'end', text=display_name,
                                               values=('', '', f'{len(procs)}个进程'),
                                               tags=('group', key), image=icon)
            else:
                group_node = self.tree.insert(self.top_background, 'end', text=display_name,
                                               values=('', '', f'{len(procs)}个进程'),
                                               tags=('group', key))
            if key in bg_group_expanded:
                self.tree.item(group_node, open=bg_group_expanded[key])
            else:
                self.tree.item(group_node, open=False)
            procs.sort(key=lambda x: natural_sort_key(x[0]))
            for name, pid, mem_str, status, exe in procs:
                self.tree.insert(group_node, 'end', text=name, values=(pid, mem_str, status), tags=('process',))

        self.tree.item(self.top_app, open=app_expanded)
        self.tree.item(self.top_background, open=bg_expanded)

    def get_process_category(self, pid, exe, username, has_window):
        """判断进程类别：应用/后台/过滤"""
        if username in ("SYSTEM", "LOCAL SERVICE", "NETWORK SERVICE", "NT AUTHORITY\\SYSTEM", "", None):
            return None
        if exe:
            system_root = os.environ.get('SystemRoot', 'C:\\Windows')
            if exe.lower().startswith(system_root.lower()):
                return None
        if has_window:
            return "应用"
        else:
            return "后台"

    def search_name(self, name):
        """按名称搜索并选中"""
        found = False
        for top in (self.top_app, self.top_background):
            for child in self.tree.get_children(top):
                proc_name = self.tree.item(child, 'text').lower()
                if name in proc_name:
                    self.tree.selection_add(child)
                    self.tree.see(child)
                    self.tree.item(top, open=True)
                    found = True
            for group in self.tree.get_children(top):
                if self.tree.item(group, 'tags')[0] == 'group':
                    for proc in self.tree.get_children(group):
                        proc_name = self.tree.item(proc, 'text').lower()
                        if name in proc_name:
                            self.tree.selection_add(proc)
                            self.tree.see(proc)
                            self.tree.item(top, open=True)
                            self.tree.item(group, open=True)
                            found = True
        return found

    def add_to_monitor(self, event):
        self.add_selected_to_monitor()

    def add_selected_to_monitor(self):
        selection = self.tree.selection()
        if not selection:
            return
        for item in selection:
            tags = self.tree.item(item, 'tags')
            if 'process' not in tags:
                messagebox.showinfo("提示", "请选择具体进程")
                continue
            values = self.tree.item(item, 'values')
            pid = int(values[0])
            logger.info(f"用户添加监控: PID {pid}")
            self.controller.add_pid_to_monitor(pid)

    def view_selected_details(self):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        tags = self.tree.item(item, 'tags')
        if 'process' not in tags:
            messagebox.showinfo("提示", "请选择具体进程")
            return
        values = self.tree.item(item, 'values')
        pid = int(values[0])
        self.show_process_details(pid)

    def show_process_details(self, pid):
        """显示进程详细信息对话框"""
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

    def kill_selected_process_tree(self):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        tags = self.tree.item(item, 'tags')
        if 'process' not in tags:
            messagebox.showinfo("提示", "请选择具体进程")
            return
        values = self.tree.item(item, 'values')
        pid = int(values[0])
        name = self.tree.item(item, 'text')
        logger.info(f"用户请求结束进程树: {name} (PID: {pid})")
        self.controller.kill_selected_process_tree(pid, name)

    def kill_selected_group(self):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        tags = self.tree.item(item, 'tags')
        if 'group' not in tags:
            messagebox.showinfo("提示", "请选择一个进程组")
            return
        group_name = self.tree.item(item, 'text')
        children = self.tree.get_children(item)
        if not children:
            return
        if not messagebox.askyesno("确认", f"确定要结束进程组 [{group_name}] 下的所有进程吗？\n此操作不可撤销。"):
            return
        pids = []
        for child in children:
            values = self.tree.item(child, 'values')
            if values and values[0]:
                try:
                    pids.append(int(values[0]))
                except:
                    pass
        if not pids:
            return
        self.controller.info_label.config(text=f"正在结束进程组 {group_name} ...")
        self.controller.root.update()
        success = 0
        for pid in pids:
            if terminate_process_tree(pid):
                success += 1
        self.controller.info_label.config(text="Process Monitor")
        messagebox.showinfo("完成", f"已尝试结束 {len(pids)} 个进程，成功 {success} 个。")
        self.refresh()

    def copy_selected_pid(self):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        tags = self.tree.item(item, 'tags')
        if 'process' not in tags:
            messagebox.showinfo("提示", "请选择具体进程")
            return
        values = self.tree.item(item, 'values')
        pid = values[0]
        self.controller.root.clipboard_clear()
        self.controller.root.clipboard_append(pid)
        self.controller.root.update()

    def copy_selected_name(self):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        tags = self.tree.item(item, 'tags')
        if 'process' not in tags:
            messagebox.showinfo("提示", "请选择具体进程")
            return
        name = self.tree.item(item, 'text')
        self.controller.root.clipboard_clear()
        self.controller.root.clipboard_append(name)
        self.controller.root.update()

    def set_controls_state(self, state):
        pass
