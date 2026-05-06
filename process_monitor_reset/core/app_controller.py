"""
应用程序核心控制器
负责：协调所有模块、处理UI线程安全、管理监控列表和窗口隐藏、文件传输、热键同步
"""
import tkinter as tk
from tkinter import messagebox
import threading
import time
import sys
import win32gui
import win32con
import os
import requests
from core.config import Config
from core.window_manager import WindowManager
from core.monitor_thread import MonitorThread
from core.hotkey_manager import HotkeyManager
from core.icon_cache import IconCache
from core.process_utils import terminate_process_tree
from core.http_api import register_callback, start_http_server, stop_http_server, set_receive_dir
from core.logger import setup_logger, get_logger
from core.utils import resource_path
from ui.main_window import MainWindow
from ui.debug_window import DebugWindow
from ui.device_discovery import DeviceDiscoveryWindow

setup_logger()
logger = get_logger()

class AppController:
    def __init__(self):
        """初始化所有组件"""
        logger.info("应用程序启动")
        self.config = Config()
        # 设置文件接收目录（从配置读取）
        receive_dir = self.config.config.get('receive_dir', '')
        if not receive_dir:
            receive_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'received_files')
        os.makedirs(receive_dir, exist_ok=True)
        set_receive_dir(receive_dir)
        
        self.window_manager = WindowManager()
        self.icon_cache = IconCache(maxsize=200)
        self.monitor_thread = None
        self.hotkey_manager = None
        self.root = None
        self.main_window = None
        self.process_tree = None
        self.monitor_tree = None
        self.stop_event = threading.Event()
        self.running = True
        self.debug_window = None
        self.device_window = None
        self.http_server_running = False

        self.http_api_enabled = self.config.config.get('http_api_enabled', False)
        self.http_api_port = self.config.config.get('http_api_port', 5000)
        self.discovery_port = self.config.config.get('discovery_port', 5001)

    def run(self):
        """启动GUI主循环"""
        self.root = tk.Tk()
        # 设置高分辨率任务栏图标（使用 PNG）
        try:
            png_path = resource_path("app_icon.png")
            if os.path.exists(png_path):
                img = Image.open(png_path)
                # 可以传递多个尺寸，tkinter 会选择最合适的
                photo = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, photo)
                # 注意要保存引用，否则会被垃圾回收
                self.root._icon_photo = photo
        except Exception as e:
            logger.debug(f"设置 iconphoto 失败: {e}")
        
        # 设置传统的 .ico 图标
        try:
            ico_path = resource_path("icon.ico")
            if os.path.exists(ico_path):
                self.root.iconbitmap(ico_path)
        except Exception as e:
            logger.debug(f"设置 iconbitmap 失败: {e}")
        self.debug_window = DebugWindow(self.root)
        self.main_window = MainWindow(self.root, self)
        self.hotkey_manager = HotkeyManager(self.config, self)
        self.root.update_idletasks()
        self.root.after(100, self._start_background_components)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        logger.info("主窗口已显示")
        self.root.mainloop()

    def _start_background_components(self):
        """在主循环启动后启动监控线程和HTTP API"""
        self.monitor_thread = MonitorThread(self.config, self, self.stop_event)
        self.monitor_thread.start()
        self.start_http_api_if_enabled()

    # ---------- 线程安全的UI更新 ----------
    def refresh_processes(self):
        """请求刷新进程列表（线程安全）"""
        if self.root:
            self.root.after(0, self._do_refresh_processes)

    def _do_refresh_processes(self):
        try:
            if self.process_tree:
                self.process_tree.refresh()
        except Exception as e:
            logger.error(f"刷新进程列表异常: {e}", exc_info=True)

    def update_monitor_list(self):
        """请求刷新监控列表（线程安全）"""
        if self.root:
            self.root.after(0, self._do_update_monitor_list)

    def _do_update_monitor_list(self):
        try:
            if self.monitor_tree:
                self.monitor_tree.refresh()
        except Exception as e:
            logger.error(f"刷新监控列表异常: {e}", exc_info=True)

    # ---------- 调试窗口 ----------
    def toggle_debug_window(self):
        if self.debug_window:
            self.debug_window.toggle()

    # ---------- 设备发现窗口 ----------
    def show_device_discovery_window(self):
        if self.device_window and hasattr(self.device_window, 'window') and self.device_window.window.winfo_exists():
            self.device_window.window.lift()
            return
        self.device_window = DeviceDiscoveryWindow(self.root, self, self.http_api_port)

    # ---------- 监控操作 ----------
    def add_pid_to_monitor(self, pid, silent=False):
        try:
            import psutil
            proc = psutil.Process(pid)
            proc.name()
            with self.config.lock:
                if pid in self.config.monitored_pids:
                    if not silent:
                        messagebox.showinfo("提示", "此PID已在监控列表中")
                    return False
                self.config.monitored_pids.add(pid)
                self.config.save_monitored_paths()
            # 强制刷新界面
            self.root.after_idle(self._do_update_monitor_list)
            self.root.after_idle(self._do_refresh_processes)
            logger.info(f"已添加监控 PID: {pid}")
            return True
        except psutil.NoSuchProcess:
            if not silent:
                messagebox.showwarning("进程不存在", f"进程 {pid} 不存在。")
        except psutil.AccessDenied:
            if not silent:
                messagebox.showerror("访问被拒绝", f"无法访问进程 {pid}。需要管理员权限。")
        except Exception as e:
            if not silent:
                messagebox.showerror("错误", f"无法添加进程 {pid}: {e}")
            logger.error(f"添加监控失败 {pid}: {e}")
        return False

    def add_pid_to_monitor_silent(self, pid):
        self.add_pid_to_monitor(pid, silent=True)

    def remove_pid_from_monitor(self, pid):
        with self.config.lock:
            if pid in self.config.hidden_pids:
                self.window_manager.show_process_windows(pid)
            self.config.monitored_pids.discard(pid)
            self.config.hidden_pids.discard(pid)
            to_del = [hwnd for hwnd, info in self.window_manager.hidden_windows.items() if info['pid'] == pid]
            for hwnd in to_del:
                del self.window_manager.hidden_windows[hwnd]
        self.config.save_monitored_paths()
        self.root.after_idle(self._do_update_monitor_list)
        self.root.after_idle(self._do_refresh_processes)
        logger.info(f"从监控列表移除 PID {pid}")

    def hide_process_windows(self, pid, silent=False):
        with self.config.lock:
            if pid not in self.config.monitored_pids:
                if not silent:
                    messagebox.showwarning("提示", f"进程 {pid} 不在监控列表中，无法隐藏。请先添加到监控。")
                logger.warning(f"尝试隐藏未监控进程 {pid}")
                return False
        self.window_manager.hide_process_windows(pid)
        with self.config.lock:
            self.config.hidden_pids.add(pid)
        self.root.after_idle(self._do_update_monitor_list)
        return True

    def show_process_windows(self, pid, silent=False):
        with self.config.lock:
            if pid not in self.config.monitored_pids:
                if not silent:
                    messagebox.showwarning("提示", f"进程 {pid} 不在监控列表中，无法显示。请先添加到监控。")
                logger.warning(f"尝试显示未监控进程 {pid}")
                return False
        self.window_manager.show_process_windows(pid)
        with self.config.lock:
            self.config.hidden_pids.discard(pid)
        self.root.after_idle(self._do_update_monitor_list)
        return True

    def toggle_hide_process(self, pid, silent=False):
        with self.config.lock:
            if pid not in self.config.monitored_pids:
                if not silent:
                    messagebox.showwarning("提示", f"进程 {pid} 不在监控列表中，无法切换隐藏/显示。请先添加到监控。")
                logger.warning(f"尝试切换未监控进程 {pid}")
                return False
            if pid in self.config.hidden_pids:
                return self.show_process_windows(pid, silent)
            else:
                return self.hide_process_windows(pid, silent)

    def hide_all_and_minimize(self):
        with self.config.lock:
            pids = list(self.config.monitored_pids)
        if not pids:
            messagebox.showinfo("提示", "监控列表为空，无法隐藏任何应用。")
            return
        for pid in pids:
            self.hide_process_windows(pid)
        time.sleep(0.1)
        if self.main_window and self.main_window.is_visible:
            self.main_window.minimize()

    def show_all_and_restore(self):
        with self.config.lock:
            pids = list(self.config.hidden_pids)
        if not pids:
            messagebox.showinfo("提示", "没有已隐藏的应用，无需显示。")
            return
        for pid in pids:
            self.show_process_windows(pid)
        if self.main_window and self.main_window.is_visible:
            self.main_window.restore()

    def kill_process_by_pid(self, pid):
        return terminate_process_tree(pid)

    def kill_selected_process_tree(self, pid, name):
        if not messagebox.askyesno("确认", f"确定要结束进程 {name} (PID: {pid}) 及其所有子进程吗？\n此操作不可撤销。"):
            return False
        success = terminate_process_tree(pid)
        if success:
            messagebox.showinfo("成功", f"进程 {name} (PID: {pid}) 及其子进程已成功结束。")
        else:
            messagebox.showerror("失败", f"无法结束进程 {name} (PID: {pid})，可能需要管理员权限。")
        self.refresh_processes()
        return success

    def show_message_popup(self, message):
        if self.root:
            self.root.after(0, lambda: messagebox.showinfo("收到消息", message))

    # ---------- 文件传输 ----------
    def send_file_to_device(self, ip, port, file_path):
        """向指定设备的 HTTP API 发送文件"""
        url = f"http://{ip}:{port}/api/upload"
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f)}
                response = requests.post(url, files=files, timeout=30)
            if response.status_code == 200:
                return True, "文件发送成功"
            else:
                return False, f"服务器错误: {response.text}"
        except Exception as e:
            return False, str(e)

    def on_file_received(self, filename, save_path):
        """文件接收后的回调，弹出提示"""
        if self.root:
            self.root.after(0, lambda: messagebox.showinfo("收到文件", f"已收到文件: {filename}\n保存位置: {save_path}"))

    # ---------- 蓝屏程序管理 ----------
    def launch_bluescreen(self):
        import os, sys, subprocess
        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        exe_path = os.path.join(base_dir, "BlueScreen.exe")
        if os.path.isfile(exe_path):
            try:
                subprocess.Popen([exe_path], shell=False)
                logger.info("启动蓝屏程序 (exe)")
                return
            except Exception as e:
                logger.error(f"启动 BlueScreen.exe 失败: {e}")
        script_path = os.path.join(os.path.dirname(sys.argv[0]), "bluescreen.py")
        if not os.path.isfile(script_path):
            script_path = "bluescreen.py"
        if os.path.isfile(script_path):
            try:
                subprocess.Popen([sys.executable, script_path], shell=False)
                logger.info("启动蓝屏程序 (py)")
            except Exception as e:
                messagebox.showerror("错误", f"启动 bluescreen.py 失败:\n{e}")
        else:
            messagebox.showerror("错误", "未找到 BlueScreen.exe 或 bluescreen.py，请确保它们位于程序目录下。")

    def start_bluescreen(self):
        if self.is_bluescreen_running():
            return "蓝屏程序已在运行"
        import os, sys, subprocess
        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        exe_path = os.path.join(base_dir, "BlueScreen.exe")
        if os.path.isfile(exe_path):
            try:
                subprocess.Popen([exe_path], shell=False)
                logger.info("启动蓝屏程序 (exe)")
                return "蓝屏程序已启动"
            except Exception as e:
                logger.error(f"启动 BlueScreen.exe 失败: {e}")
                return f"启动失败: {e}"
        script_path = os.path.join(os.path.dirname(sys.argv[0]), "bluescreen.py")
        if os.path.isfile(script_path):
            try:
                subprocess.Popen([sys.executable, script_path], shell=False)
                logger.info("启动蓝屏程序 (py)")
                return "蓝屏程序已启动"
            except Exception as e:
                logger.error(f"启动 bluescreen.py 失败: {e}")
                return f"启动失败: {e}"
        return "未找到 BlueScreen.exe 或 bluescreen.py"

    def stop_bluescreen(self):
        import psutil
        killed = False
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() in ('bluescreen.exe', 'bluescreen.py'):
                    proc.terminate()
                    proc.wait(timeout=3)
                    killed = True
                    logger.info(f"已终止蓝屏进程 PID: {proc.info['pid']}")
            except:
                pass
        if killed:
            return "蓝屏程序已关闭"
        else:
            return "未找到运行中的蓝屏程序"

    def is_bluescreen_running(self):
        import psutil
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'].lower() in ('bluescreen.exe', 'bluescreen.py'):
                    return True
            except:
                pass
        return False

    def open_settings(self):
        from ui.dialogs import SettingsDialog
        def save_callback(new_config):
            old_interval = self.config.config.get('refresh_interval', 5)
            self.config.update_config(new_config)
            self.config.save_config()
            self.hotkey_manager.setup_hotkeys()

            # 更新主窗口按钮上的热键提示
            if self.main_window:
                self.main_window.update_hotkey_labels(new_config.get('hotkeys', {}))

            old_api_enabled = self.http_api_enabled
            self.http_api_enabled = self.config.config.get('http_api_enabled', False)
            self.http_api_port = self.config.config.get('http_api_port', 5000)
            self.discovery_port = self.config.config.get('discovery_port', 5001)
            # 更新文件接收目录
            receive_dir = self.config.config.get('receive_dir', '')
            if receive_dir:
                os.makedirs(receive_dir, exist_ok=True)
                set_receive_dir(receive_dir)
            if self.config.config['http_api_enabled'] and not old_api_enabled:
                self.start_http_api_if_enabled()
            elif not self.config.config['http_api_enabled'] and old_api_enabled:
                self.stop_http_api()
            new_interval = self.config.config['refresh_interval']
            if new_interval != old_interval:
                self.stop_event.set()
                time.sleep(0.1)
                self.stop_event.clear()
        SettingsDialog(self.root, self.config.config, save_callback)

    def start_http_api_if_enabled(self):
        if self.http_api_enabled and not self.http_server_running:
            try:
                register_callback('hide_all', self.hide_all_and_minimize)
                register_callback('show_all', self.show_all_and_restore)
                register_callback('kill_process', self.kill_process_by_pid)
                register_callback('list_processes', self.get_filtered_process_list)
                register_callback('hide_process', lambda pid: self.hide_process_windows(pid, silent=True))
                register_callback('show_process', lambda pid: self.show_process_windows(pid, silent=True))
                register_callback('toggle_process', lambda pid: self.toggle_hide_process(pid, silent=True))
                register_callback('add_pid', self.add_pid_to_monitor_silent)
                register_callback('show_message', self.show_message_popup)
                register_callback('start_bluescreen', self.start_bluescreen)
                register_callback('stop_bluescreen', self.stop_bluescreen)
                register_callback('on_file_received', self.on_file_received)
                start_http_server(self.http_api_port, self.discovery_port)
                self.http_server_running = True
                logger.info(f"HTTP API 已启动，端口 {self.http_api_port}，局域网访问地址: http://{self.get_local_ip()}:{self.http_api_port}")
            except Exception as e:
                logger.error(f"启动 HTTP API 失败: {e}")
                messagebox.showerror("错误", f"无法启动 HTTP API：{e}")

    def stop_http_api(self):
        if self.http_server_running:
            stop_http_server()
            self.http_server_running = False
            logger.info("HTTP API 已停止")

    def get_local_ip(self):
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def get_filtered_process_list(self):
        import psutil
        import win32gui
        import win32process
        import os

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

        result = []
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'username']):
            try:
                pid = proc.info['pid']
                name = proc.info['name']
                exe = proc.info['exe']
                username = proc.info['username']
                has_window = pid in window_pids

                if username in ("SYSTEM", "LOCAL SERVICE", "NETWORK SERVICE", "NT AUTHORITY\\SYSTEM", "", None):
                    continue
                if exe:
                    system_root = os.environ.get('SystemRoot', 'C:\\Windows')
                    if exe.lower().startswith(system_root.lower()):
                        continue

                category = "应用" if has_window else "后台"
                result.append({
                    'pid': pid,
                    'name': name,
                    'category': category
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return result

    def on_closing(self):
        if messagebox.askyesno("确认退出", "确定要退出程序吗？\n退出前将恢复所有被隐藏的窗口。"):
            self.stop_http_api()
            with self.config.lock:
                pids = list(self.config.hidden_pids)
            for pid in pids:
                self.window_manager.show_process_windows(pid)
            with self.config.lock:
                for hwnd, info in list(self.window_manager.hidden_windows.items()):
                    try:
                        if win32gui.IsWindow(hwnd):
                            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, info['style'])
                            if info['visible']:
                                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                    except:
                        pass
                self.window_manager.hidden_windows.clear()
                self.config.hidden_pids.clear()
            if self.hotkey_manager:
                self.hotkey_manager.unhook()
            self.stop_event.set()
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=3)
            self.config.save_monitored_paths()
            self.root.destroy()
            sys.exit(0)
