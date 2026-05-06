"""
窗口底层操作模块
提供隐藏、显示、置顶、透明等基本窗口操作
"""
import win32gui
import win32con
import win32process

def hide_window(hwnd):
    """隐藏窗口并从任务栏移除"""
    win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style | win32con.WS_EX_TOOLWINDOW)

def show_window(hwnd, restore_style=True):
    """显示窗口，可选恢复原样式"""
    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
    if restore_style:
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style & ~win32con.WS_EX_TOOLWINDOW)

def set_topmost(hwnd, topmost=True):
    """设置窗口置顶"""
    flags = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST if topmost else win32con.HWND_NOTOPMOST,
                          0, 0, 0, 0, flags)

def set_transparent(hwnd, alpha=180):
    """设置窗口透明度"""
    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    if alpha < 255:
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style | win32con.WS_EX_LAYERED)
        win32gui.SetLayeredWindowAttributes(hwnd, 0, alpha, win32con.LWA_ALPHA)
    else:
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style & ~win32con.WS_EX_LAYERED)

def enum_windows_for_pid(pid, callback):
    """枚举指定PID的所有窗口，对每个窗口调用callback(hwnd)"""
    def enum_callback(hwnd, _):
        try:
            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
            if found_pid == pid:
                callback(hwnd)
        except:
            pass
        return True
    win32gui.EnumWindows(enum_callback, None)
