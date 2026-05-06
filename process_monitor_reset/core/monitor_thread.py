"""
监控线程模块
定期刷新进程列表、检查黑名单、清理失效监控、确保隐藏窗口保持隐藏
"""
import threading
import time
import psutil
from core.process_utils import check_blacklist
from core.logger import get_logger

logger = get_logger()

class MonitorThread(threading.Thread):
    def __init__(self, config, controller, stop_event):
        super().__init__(daemon=False)
        self.config = config
        self.controller = controller
        self.stop_event = stop_event

    def run(self):
        logger.info("监控线程启动")
        while not self.stop_event.is_set():
            try:
                # 刷新进程列表（线程安全）
                self.controller.refresh_processes()
                # 检查黑名单
                check_blacklist(self.config.config.get('blacklist', []))

                # 清理失效的监控 PID
                with self.config.lock:
                    monitored_copy = list(self.config.monitored_pids)
                dead_pids = []
                for pid in monitored_copy:
                    if not psutil.pid_exists(pid):
                        dead_pids.append(pid)
                if dead_pids:
                    logger.info(f"检测到失效监控进程: {dead_pids}")
                    with self.config.lock:
                        for pid in dead_pids:
                            self.config.monitored_pids.discard(pid)
                            self.config.hidden_pids.discard(pid)
                            to_del = [hwnd for hwnd, info in self.controller.window_manager.hidden_windows.items() if info['pid'] == pid]
                            for hwnd in to_del:
                                del self.controller.window_manager.hidden_windows[hwnd]
                    self.controller.update_monitor_list()

                # 确保被隐藏的进程窗口保持隐藏
                with self.config.lock:
                    hidden_copy = list(self.config.hidden_pids)
                for pid in hidden_copy:
                    if psutil.pid_exists(pid):
                        self.controller.window_manager.ensure_windows_hidden(pid)

            except Exception as e:
                logger.error(f"监控线程错误: {e}", exc_info=True)

            self.stop_event.wait(self.config.config.get('refresh_interval', 5))
        logger.info("监控线程结束")
