"""
系统工具模块
提供临时文件清理、CPU/内存获取等辅助功能
"""
import os
import subprocess
import psutil

def clean_temp_files():
    """清理临时文件（未使用）"""
    temp_path = os.environ.get('TEMP', '')
    if temp_path:
        try:
            subprocess.run(f'del /f /s /q "{temp_path}\\*.*"', shell=True, capture_output=True)
        except:
            pass

def get_process_cpu_memory(pid):
    """获取进程的 CPU 和内存使用情况"""
    try:
        proc = psutil.Process(pid)
        with proc.oneshot():
            cpu = proc.cpu_percent(interval=0)
            mem = proc.memory_info().rss / (1024 * 1024)
            return round(cpu, 1), round(mem, 1)
    except:
        return None, None
