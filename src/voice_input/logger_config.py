"""日志配置模块 - 统一管理日志"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(name: str = "voice_input", log_file: str = None, level: str = "info") -> logging.Logger:
    """设置日志
    
    日志规范：
    - DEBUG: 详细的调试信息（音频块、事件详情等）
    - INFO: 关键操作信息（启动、停止、识别结果）
    - WARNING: 警告信息（配置问题、降级处理）
    - ERROR: 错误信息（失败操作、异常）
    """
    log_levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
    }
    log_level = log_levels.get(level.lower(), logging.INFO)
    
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    if logger.handlers:
        return logger
    
    # 简化日志格式，只在 DEBUG 模式显示详细信息
    if log_level == logging.DEBUG:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%H:%M:%S"
        )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=3, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_log_file() -> Path:
    """获取日志文件路径
    
    优先级：
    1. ~/.local/share/voice-input/voice-input.log (用户目录)
    2. /tmp/voice-input.log (降级方案)
    """
    # 优先使用用户目录
    user_log_dir = Path.home() / ".local" / "share" / "voice-input"
    try:
        user_log_dir.mkdir(parents=True, exist_ok=True)
        log_file = user_log_dir / "voice-input.log"
        # 测试是否可写
        log_file.touch(exist_ok=True)
        return log_file
    except (PermissionError, OSError):
        # 降级到 /tmp
        return Path("/tmp/voice-input.log")
