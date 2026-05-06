"""
程序入口模块
负责：检查依赖、请求管理员权限、设置全局异常钩子、启动主控制器
"""
import ctypes
import sys
import os
import traceback
from datetime import datetime

def resource_path(relative_path):
    """获取资源文件的绝对路径，兼容开发环境和 PyInstaller 打包"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def global_exception_handler(exc_type, exc_value, exc_tb):
    """全局异常处理器：记录日志到文件并退出"""
    # 确保 logs 目录存在
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "crash.log")
    
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"崩溃时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"异常类型: {exc_type.__name__}\n")
        f.write(f"异常信息: {exc_value}\n")
        f.write("堆栈跟踪:\n")
        traceback.print_tb(exc_tb, file=f)
        f.write(f"{'='*60}\n")
    
    # 尝试记录到日志系统
    try:
        from core.logger import get_logger
        logger = get_logger()
        logger.critical("未捕获的异常", exc_info=(exc_type, exc_value, exc_tb))
    except:
        pass
    
    # 弹窗提示
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        tk.messagebox.showerror("程序崩溃", f"发生致命错误，已保存日志到：\n{log_path}\n程序将退出。")
        root.destroy()
    except:
        pass
    
    sys.exit(1)

# 设置全局异常钩子
sys.excepthook = global_exception_handler

def main():
    """主函数"""
    if os.name != 'nt':
        print("该程序仅支持Windows系统")
        return

    # 检查所有依赖模块
    try:
        import psutil
        import keyboard
        import win32gui
        import win32con
        import win32api
        import win32ui
        from PIL import Image, ImageTk
        import flask
        import qrcode
        import requests
    except ImportError as e:
        print(f"缺少必要的模块: {e}")
        print("请安装: pip install psutil keyboard pywin32 pillow flask qrcode[pil] requests")
        return

    # 自动请求管理员权限（如果不是管理员）
    if ctypes.windll.shell32.IsUserAnAdmin() == 0:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        return

    # 启动主控制器
    from core.app_controller import AppController
    app = AppController()
    app.run()

if __name__ == "__main__":
    main()
