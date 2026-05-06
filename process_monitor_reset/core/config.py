"""
配置管理模块
负责：加载/保存JSON配置、管理监控PID集合、固定配置文件路径
"""
import json
import os
import threading
import sys

def get_config_path():
    """获取配置文件路径（程序所在目录）"""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(base, "process_monitor_config.json")

CONFIG_FILE = get_config_path()

DEFAULT_CONFIG = {
    "monitored_paths": [],
    "hotkeys": {
        "refresh": "f5",
        "show_all": "f10",
        "hide_all": "f11",
        "toggle_ui": "f12",
        "kill_selected": "k"
    },
    "blacklist": [],
    "http_api_enabled": False,
    "http_api_port": 5000,
    "refresh_interval": 10,
    "discovery_port": 5001,
    "receive_dir": ""
}

class Config:
    def __init__(self):
        self.lock = threading.Lock()
        self.config = self.load_config()
        self.monitored_pids = set()
        self.hidden_pids = set()
        self.load_monitored_paths()

    def load_config(self):
        """加载配置文件，若不存在则创建默认配置"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                # 确保新字段存在
                if "discovery_port" not in cfg:
                    cfg["discovery_port"] = DEFAULT_CONFIG["discovery_port"]
                return cfg
            except:
                pass
        return DEFAULT_CONFIG.copy()

    def save_config(self):
        """保存配置到文件"""
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def update_config(self, new_config):
        """更新配置字典"""
        self.config.update(new_config)

    def load_monitored_paths(self):
        """根据配置中的 monitored_paths 加载 PID 集合"""
        import psutil
        paths = self.config.get('monitored_paths', [])
        for path in paths:
            pids = self.get_process_by_path(path)
            for pid in pids:
                self.monitored_pids.add(pid)

    def save_monitored_paths(self):
        """将当前 monitored_pids 转换为路径并保存到配置"""
        import psutil
        paths = set()
        for pid in self.monitored_pids:
            try:
                exe = psutil.Process(pid).exe()
                if exe:
                    paths.add(exe)
            except:
                pass
        self.config['monitored_paths'] = list(paths)
        self.save_config()

    @staticmethod
    def get_process_by_path(exe_path):
        """根据可执行文件路径获取所有 PID"""
        import psutil
        import os
        pids = []
        for proc in psutil.process_iter(['pid', 'exe']):
            try:
                if proc.info['exe'] and os.path.samefile(proc.info['exe'], exe_path):
                    pids.append(proc.info['pid'])
            except:
                pass
        return pids
