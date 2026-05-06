"""
全局热键管理模块
负责：注册热键、检测冲突并弹窗警告
"""
import keyboard
from core.logger import get_logger

logger = get_logger()

class HotkeyManager:
    def __init__(self, config, controller):
        self.config = config
        self.controller = controller
        self.setup_hotkeys()

    def setup_hotkeys(self):
        """注册所有配置的热键"""
        try:
            keyboard.unhook_all()
            hk = self.config.config['hotkeys']
            self._safe_add_hotkey(hk['refresh'], lambda: self.controller.refresh_processes())
            self._safe_add_hotkey(hk['hide_all'], lambda: self.controller.root.after(0, self.controller.hide_all_and_minimize))
            self._safe_add_hotkey(hk['show_all'], lambda: self.controller.root.after(0, self.controller.show_all_and_restore))
            self._safe_add_hotkey(hk['toggle_ui'], lambda: self.controller.root.after(0, self.controller.main_window.toggle_visible))
            self._safe_add_hotkey(hk['kill_selected'], lambda: self.controller.main_window.kill_selected_from_any())
            self._safe_add_hotkey('ctrl+b', lambda: self.controller.launch_bluescreen())
            self._safe_add_hotkey('f3', lambda: self.controller.toggle_debug_window())
            logger.info("热键注册成功")
        except Exception as e:
            logger.error(f"热键注册失败: {e}")

    def _safe_add_hotkey(self, hotkey, callback):
        """安全注册单个热键，捕获冲突异常并弹窗"""
        try:
            keyboard.add_hotkey(hotkey, callback)
        except Exception as e:
            error_msg = f"热键 {hotkey} 注册失败: {e}"
            logger.error(error_msg)
            if self.controller.root:
                self.controller.root.after(0, lambda: self._show_hotkey_warning(error_msg))

    def _show_hotkey_warning(self, msg):
        """弹窗警告热键冲突"""
        from tkinter import messagebox
        messagebox.showwarning("热键冲突", f"{msg}\n请修改设置中的热键。")

    def unhook(self):
        """卸载所有热键"""
        try:
            keyboard.unhook_all()
        except:
            pass
