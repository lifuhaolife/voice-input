"""Voice Input 启动脚本 - 处理日志和单例"""

import os
import sys
import fcntl
from pathlib import Path

# 单例检查
LOCK_FILE = Path("/tmp/voice-input.lock")

def check_and_acquire_lock():
    """检查并获取锁"""
    try:
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(str(os.getpid()))
        lock_fd.flush()
        return lock_fd
    except (IOError, OSError):
        # 检查是否有已运行的进程
        if LOCK_FILE.exists():
            try:
                with open(LOCK_FILE, 'r') as f:
                    pid = int(f.read().strip())
                os.kill(pid, 0)
                print(f"❌ 语音输入已在运行 (PID: {pid})")
                print(f"   如需重启，请先运行：kill {pid}")
                sys.exit(1)
            except (ProcessLookupError, ValueError, FileNotFoundError):
                LOCK_FILE.unlink()
        return None

def release_lock(lock_fd):
    """释放锁"""
    if lock_fd:
        try:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            lock_fd.close()
            if LOCK_FILE.exists():
                LOCK_FILE.unlink()
        except Exception:
            pass

def main():
    """主函数"""
    # 获取锁
    lock_fd = check_and_acquire_lock()
    
    try:
        # 导入并运行
        from voice_input.logger_config import setup_logger, get_log_file
        from voice_input.main import main as voice_main
        
        # 设置日志
        log_file = get_log_file()
        logger = setup_logger("voice_input", log_file=str(log_file), level="info")
        
        logger.info("=" * 60)
        logger.info("Voice Input 启动")
        logger.info(f"日志文件：{log_file}")
        logger.info(f"进程 PID: {os.getpid()}")
        logger.info("=" * 60)
        
        # 运行主程序
        voice_main()
        
    finally:
        # 释放锁
        release_lock(lock_fd)
        print("✅ 语音输入已停止")

if __name__ == "__main__":
    main()
