#logging.py
import sys
from pathlib import Path
from loguru import logger
import datetime
import os
import time

def setup_logging():
    # 设置系统时区为北京时区(UTC+8)
    os.environ["TZ"] = "Asia/Shanghai"
    try:
        time.tzset()  # Unix-like系统时区更新
    except AttributeError:
        # Windows不支持tzset，需要额外处理
        from win32api import SetTimeZoneInformation
        import win32timezone
        win_tz = win32timezone.TimeZoneInfo("China Standard Time")
        SetTimeZoneInformation(win_tz.getUtcTZI())
        
    # 创建日志目录
    log_path = Path("logs")
    log_path.mkdir(exist_ok=True)  # 如果目录不存在则创建

    # 移除默认处理程序
    logger.remove()

    # 添加控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="DEBUG"
    )

    # 添加文件输出
    # logger.add(
    #     "logs/app_{time:YYYY-MM-DD}.log",
    #     rotation="00:00",  # 每天创建一个新日志文件
    #     retention="7 days",  # 保留30天的日志
    #     compression="zip",  # 压缩日志文件
    #     level="INFO",
    #     encoding="utf-8"
    # )
    # 替换原有的文件输出配置
    logger.add(
        "logs/app.log",  # 使用固定文件名
        rotation="00:00",  # 每天午夜轮转
        retention="7 days",  
        compression="zip",
        level="DEBUG",
        encoding="utf-8",
        enqueue=True,  # 避免文件锁问题
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
    )


    return logger  # 返回配置好的logger实例