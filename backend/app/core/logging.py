"""
简化的日志配置模块
使用loguru最简单的方式处理日志
"""

import sys
import os
from pathlib import Path
from loguru import logger


def setup_logging(log_level: str = "INFO", log_file: str = None) -> None:
    """
    设置简单的日志配置
    
    Args:
        log_level: 日志级别，默认INFO
        log_file: 日志文件路径，可选
    """
    # 移除默认处理器
    logger.remove()
    
    # 添加控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> | <level>{message}</level> | <blue>{extra}</blue>",
        level=log_level.upper(),
        colorize=True
    )
    
    # 如果指定了日志文件，添加文件输出
    if log_file:
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Windows-friendly logging configuration
        import platform
        if platform.system() == "Windows":
            # 使用带时间戳的唯一日志文件名，避免文件锁定问题
            import time
            timestamp = int(time.time())
            log_filename = Path(log_file)
            unique_log_file = os.path.join(
                str(log_filename.parent), 
                f"{log_filename.stem}_{timestamp}{log_filename.suffix}"
            )
            
            logger.add(
                unique_log_file,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message} | {extra}",
                level=log_level.upper(),
                rotation="1 day",  # 每天轮换
                retention="7 days",
                enqueue=True,      # 使用单独线程写入
                diagnose=True,     # 记录诊断信息
                backtrace=True,    # 记录回溯信息
                catch=True,        # 捕获异常
                delay=True         # 延迟创建文件，直到第一条日志
            )
        else:
            # Unix/Linux can handle size-based rotation better
            logger.add(
                log_file,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message} | {extra}",
                level=log_level.upper(),
                rotation="10 MB",
                retention="7 days"
            )


def get_logger(name: str = None):
    """获取logger实例"""
    if name:
        return logger.bind(name=name)
    return logger