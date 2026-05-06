"""
窗口管理模块
负责隐藏/显示指定进程的所有窗口，带线程锁保护
"""
import win32gui
import win32con
import win32process
import threading
from core.window_utils import hide_window, show_window, enum_windows_for_pid
from core.logger import get_logger

logger = get_logger()

class WindowManager:
    def __init__(self):
        self.hidden_windows = {}   # hwnd -> {pid, visible, style}
        self.lock = threading.Lock()

    def hide_process_windows(self, pid):
        """隐藏指定进程的所有窗口"""
        logger.debug(f"隐藏进程窗口 PID: {pid}")
        def callback(hwnd):
            with self.lock:
                if hwnd not in self.hidden_windows:
                    original_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                    was_visible = win32gui.IsWindowVisible(hwnd)
                    hide_window(hwnd)
                    self.hidden_windows[hwnd] = {
                        'pid': pid,
                        'visible': was_visible,
                        'style': original_style
                    }
                    logger.debug(f"隐藏窗口 {hwnd} (PID {pid})")
                else:
                    if win32gui.IsWindowVisible(hwnd):
                        hide_window(hwnd)
        enum_windows_for_pid(pid, callback)

    def show_process_windows(self, pid):
        """显示指定进程的所有窗口"""
        logger.debug(f"恢复进程窗口 PID: {pid}")
        to_show = []
        with self.lock:
            for hwnd, info in list(self.hidden_windows.items()):
                if info['pid'] == pid:
                    if win32gui.IsWindow(hwnd):
                        to_show.append((hwnd, info))
                    else:
                        del self.hidden_windows[hwnd]
        for hwnd, info in to_show:
            try:
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, info['style'])
                if info['visible']:
                    show_window(hwnd, restore_style=False)
                with self.lock:
                    if hwnd in self.hidden_windows:
                        del self.hidden_windows[hwnd]
                logger.debug(f"恢复窗口 {hwnd}")
            except:
                with self.lock:
                    if hwnd in self.hidden_windows:
                        del self.hidden_windows[hwnd]

    def ensure_windows_hidden(self, pid):
        """确保指定进程的窗口被隐藏（用于监控线程）"""
        def callback(hwnd):
            with self.lock:
                if hwnd not in self.hidden_windows:
                    original_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                    was_visible = win32gui.IsWindowVisible(hwnd)
                    hide_window(hwnd)
                    self.hidden_windows[hwnd] = {
                        'pid': pid,
                        'visible': was_visible,
                        'style': original_style
                    }
                    logger.debug(f"确保隐藏窗口 {hwnd} (PID {pid})")
                else:
                    if win32gui.IsWindowVisible(hwnd):
                        hide_window(hwnd)
        enum_windows_for_pid(pid, callback)
