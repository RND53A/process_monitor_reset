"""
进程工具模块
提供进程树终止、黑名单检查等功能
"""
import psutil
import subprocess
import time
from typing import List
from core.logger import get_logger

logger = get_logger()

def get_child_processes(pid: int) -> List[int]:
    """获取指定进程的所有子进程 PID"""
    try:
        process = psutil.Process(pid)
        children = process.children(recursive=True)
        return [p.pid for p in children]
    except psutil.NoSuchProcess:
        return []
    except Exception as e:
        logger.debug(f"获取子进程失败 PID {pid}: {e}")
        return []

def terminate_process_tree(pid: int) -> bool:
    """终止进程树（先优雅终止，后强制结束）"""
    logger.info(f"开始终止进程树 PID: {pid}")
    try:
        child_pids = get_child_processes(pid)
        all_pids = [pid] + child_pids
        logger.debug(f"进程树包含: {all_pids}")

        for p in all_pids:
            try:
                psutil.Process(p).terminate()
            except:
                pass

        time.sleep(3)

        still_alive = [p for p in all_pids if psutil.pid_exists(p)]
        if still_alive:
            logger.warning(f"以下进程未响应终止，使用强制结束: {still_alive}")
            try:
                subprocess.run(['taskkill', '/f', '/t', '/pid', str(pid)], capture_output=True, timeout=5)
            except Exception as e:
                logger.error(f"taskkill 失败: {e}")
                for p in still_alive:
                    try:
                        psutil.Process(p).kill()
                    except:
                        pass

        success = not psutil.pid_exists(pid)
        if success:
            logger.info(f"进程树终止成功 PID: {pid}")
        else:
            logger.error(f"进程树终止失败 PID: {pid}")
        return success
    except Exception as e:
        logger.error(f"终止进程树异常: {e}", exc_info=True)
        return False

def check_blacklist(blacklist: List[str]):
    """检查黑名单，自动终止匹配的进程"""
    if not blacklist:
        return
    blacklist_lower = [b.lower() for b in blacklist]
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            name = proc.info['name']
            if name and name.lower() in blacklist_lower:
                logger.warning(f"黑名单进程 {name} (PID: {proc.info['pid']}) 被终止")
                terminate_process_tree(proc.info['pid'])
        except:
            pass
