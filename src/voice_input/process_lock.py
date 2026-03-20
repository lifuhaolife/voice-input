"""进程锁模块 - 确保单实例运行"""

import fcntl
import os
import sys
from pathlib import Path


class ProcessLock:
    def __init__(self, lock_file: str = "/tmp/voice-input.lock"):
        self.lock_file = Path(lock_file)
        self.lock_fd = None
    
    def acquire(self) -> bool:
        try:
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)
            self.lock_fd = open(self.lock_file, 'w')
            fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_fd.write(str(os.getpid()))
            self.lock_fd.flush()
            return True
        except (IOError, OSError):
            if self.lock_fd:
                self.lock_fd.close()
                self.lock_fd = None
            return False
    
    def release(self):
        if self.lock_fd:
            try:
                fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
                self.lock_fd.close()
                if self.lock_file.exists():
                    self.lock_file.unlink()
            except Exception:
                pass
            self.lock_fd = None
    
    def check_existing(self) -> int | None:
        if not self.lock_file.exists():
            return None
        try:
            with open(self.lock_file, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return pid
        except (ProcessLookupError, ValueError, FileNotFoundError):
            if self.lock_file.exists():
                self.lock_file.unlink()
            return None
