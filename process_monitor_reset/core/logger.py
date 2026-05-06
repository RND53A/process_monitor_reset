"""
日志管理模块
支持文件、控制台和调试窗口回调
"""
import logging
import sys
import os
from datetime import datetime

_log_callback = None

def set_log_callback(callback):
    """设置日志回调函数，参数为 (level, message)"""
    global _log_callback
    _log_callback = callback

class TkinterLogHandler(logging.Handler):
    """将日志记录发送到调试窗口的回调"""
    def emit(self, record):
        if _log_callback:
            msg = self.format(record)
            _log_callback(record.levelname, msg)

class ImmediateFileHandler(logging.FileHandler):
    """每次日志记录后立即刷新到磁盘，确保崩溃时不丢失"""
    def emit(self, record):
        super().emit(record)
        self.flush()

def setup_logger(log_file="process_monitor.log"):
    """配置全局日志记录器，日志输出到 logs 子目录"""
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)

    logger = logging.getLogger("ProcessMonitor")
    logger.setLevel(logging.DEBUG)

    # 立即刷新的文件处理器
    file_handler = ImmediateFileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Tkinter 回调处理器
    tk_handler = TkinterLogHandler()
    tk_handler.setLevel(logging.DEBUG)
    tk_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(tk_handler)

    return logger

def get_logger():
    return logging.getLogger("ProcessMonitor")
