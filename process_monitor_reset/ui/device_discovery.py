"""
设备发现窗口
显示局域网内其他运行本程序的设备，双击打开Web终端，支持发送文件
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import webbrowser
from core.http_api import discovered_devices
import threading
import time

class DeviceDiscoveryWindow:
    def __init__(self, parent, controller, http_port):
        self.parent = parent
        self.controller = controller
        self.http_port = http_port
        self.window = tk.Toplevel(parent)
        self.window.title("局域网设备")
        self.window.geometry("450x350")
        self.window.transient(parent)
        self.window.grab_set()

        # 记录当前选中的设备 IP
        self.selected_ip = None

        # 设备列表
        self.tree = ttk.Treeview(self.window, columns=('ip',), show='headings')
        self.tree.heading('ip', text='IP 地址')
        self.tree.column('ip', width=200)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tree.bind('<Double-1>', self.on_double_click)
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

        # 按钮区域
        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(btn_frame, text="刷新 (F5)", command=self.refresh_list).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="发送文件", command=self.send_file_to_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="关闭", command=self.on_close).pack(side=tk.RIGHT, padx=2)

        # 绑定 F5 键
        self.window.bind('<F5>', lambda e: self.refresh_list())

        self.refresh_list()
        self.running = True
        self.refresh_thread = threading.Thread(target=self.auto_refresh, daemon=True)
        self.refresh_thread.start()

        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def is_alive(self):
        return self.window.winfo_exists()

    def on_select(self, event):
        """记录选中的设备 IP"""
        selected = self.tree.selection()
        if selected:
            self.selected_ip = self.tree.item(selected[0], 'values')[0]
        else:
            self.selected_ip = None

    def refresh_list(self):
        """刷新设备列表，并恢复之前选中项的高亮"""
        # 记录当前选中的 IP（优先使用当前选中项，确保最新）
        current_selection = self.tree.selection()
        if current_selection:
            self.selected_ip = self.tree.item(current_selection[0], 'values')[0]

        # 清空树
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 重新填充
        for ip, info in discovered_devices.items():
            item = self.tree.insert('', 'end', values=(ip,))
            # 如果是之前选中的 IP，则重新选中
            if self.selected_ip == ip:
                self.tree.selection_set(item)
                self.tree.see(item)

        # 如果之前选中的设备已离线，清除记录
        if self.selected_ip and self.selected_ip not in discovered_devices:
            self.selected_ip = None

    def auto_refresh(self):
        """自动刷新设备列表（每2秒）"""
        while self.running:
            if self.is_alive():
                self.window.after(0, self.refresh_list)
            time.sleep(2)

    def on_double_click(self, event):
        """双击打开 Web 终端"""
        selected = self.tree.selection()
        if selected:
            ip = self.tree.item(selected[0], 'values')[0]
            port = discovered_devices.get(ip, {}).get('port')
            if port:
                url = f"http://{ip}:{port}"
                webbrowser.open(url)
            else:
                messagebox.showerror("错误", "无法获取设备端口")

    def send_file_to_selected(self):
        """向选中的设备发送文件"""
        selected = self.tree.selection()
        if not selected:
            # 如果没有选中，尝试使用 self.selected_ip 的节点
            if self.selected_ip:
                for item in self.tree.get_children():
                    if self.tree.item(item, 'values')[0] == self.selected_ip:
                        selected = (item,)
                        break
        if not selected:
            messagebox.showwarning("提示", "请先选中一个设备")
            return
        ip = self.tree.item(selected[0], 'values')[0]
        port = discovered_devices.get(ip, {}).get('port')
        if not port:
            messagebox.showerror("错误", "无法获取设备端口，设备可能已离线")
            return
        file_path = filedialog.askopenfilename(title="选择要发送的文件")
        if not file_path:
            return
        success, msg = self.controller.send_file_to_device(ip, port, file_path)
        if success:
            messagebox.showinfo("成功", msg)
        else:
            messagebox.showerror("失败", f"发送失败: {msg}")

    def on_close(self):
        self.running = False
        self.window.destroy()
