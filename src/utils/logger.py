import os
import sys
from loguru import logger
from pathlib import Path


def setup_logger(log_level: str = "INFO", log_file: str = None):
    logger.remove()
    
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    logger.add(sys.stdout, format=log_format, level=log_level, colorize=True)
    
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_file,
            format=log_format,
            level=log_level,
            rotation="10 MB",
            retention="7 days",
            encoding="utf-8"
        )
    
    logger.info(f"ログシステムを初期化しました。レベル: {log_level}")
    if log_file:
        logger.info(f"ログファイル: {log_file}")
    
    return logger


def get_logger(name: str = None):
    if name:
        return logger.bind(name=name)
    return logger