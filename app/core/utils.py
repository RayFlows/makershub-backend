#utils.py
from datetime import datetime, timedelta
from typing import Optional
import pytz

CHINA_TZ = pytz.timezone('Asia/Shanghai')  # 定义中国时区

def get_current_time() -> datetime:
    """获取当前北京时间"""
    return datetime.now(CHINA_TZ)  # 返回当前的北京时间

def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化日期时间"""
    if dt.tzinfo is None:
        dt = CHINA_TZ.localize(dt)  # 如果没有时区信息，添加中国时区
    return dt.strftime(format_str)  # 按指定格式返回日期时间字符串

def parse_datetime(date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """解析日期时间字符串"""
    try:
        dt = datetime.strptime(date_str, format_str)  # 解析字符串为datetime对象
        return CHINA_TZ.localize(dt)  # 添加中国时区
    except ValueError:
        return None  # 解析失败返回None

def get_week_start_end(dt: datetime = None) -> tuple[datetime, datetime]:
    """获取指定日期所在周的起止时间"""
    if dt is None:
        dt = get_current_time()  # 如果没有提供日期，使用当前时间
    start = dt - timedelta(days=dt.weekday())  # 计算周开始日期
    end = start + timedelta(days=6)  # 计算周结束日期
    return start.replace(hour=0, minute=0, second=0), end.replace(hour=23, minute=59, second=59)  # 返回周开始和结束时间

# 这里可以添加其他通用工具函数
