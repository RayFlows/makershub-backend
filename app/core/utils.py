#utils.py
from datetime import datetime, timedelta
from typing import Optional
import pytz
from loguru import logger # 确保导入 logger

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

# 添加时间解析函数
# def parse_datetime(date_str: str, format_str: str = "%Y-%m-%dT%H:%M:%SZ") -> Optional[datetime]:
#     """解析ISO 8601格式的时间字符串"""
#     try:
#         return datetime.strptime(date_str, format_str)
#     except (ValueError, TypeError):
#         return None
def parse_datetime(date_str: str) -> Optional[datetime]:
    """
    智能解析多种常见ISO 8601及相关格式的时间字符串。
    
    支持的格式示例:
    - "2024-02-13T10:00:00Z" (UTC 时区)
    - "2024-02-13T18:00:00+08:00" (带时区)
    - "2024-02-13T10:00:00" (无时区，将被视为北京时间)
    - "2024-02-13 10:00:00" (用空格分隔，将被视为北京时间)
    - "2024-02-13" (仅日期，将被视为当日零点零分，北京时间)
    """
    if not isinstance(date_str, str):
        return None
    
    try:
        # Python 3.7+ 的 fromisoformat 是处理标准ISO格式的首选
        # 它能自动处理 'YYYY-MM-DD' 和 'YYYY-MM-DDTHH:MM:SS'
        # 对于以 'Z' 结尾的UTC时间，需特殊处理
        if date_str.endswith('Z'):
            # fromisoformat 在某些版本不直接支持'Z'，替换为+00:00更通用
            dt_with_tz = datetime.fromisoformat(date_str[:-1] + '+00:00')
        else:
            dt_with_tz = datetime.fromisoformat(date_str)
        
        # 如果解析出的对象有时区信息，则统一转换为北京时间
        if dt_with_tz.tzinfo:
            return dt_with_tz.astimezone(CHINA_TZ)
        else:
            # 如果没有时区信息，则假定为北京时间
            return CHINA_TZ.localize(dt_with_tz)
            
    except ValueError:
        # 如果 fromisoformat 失败 (例如 "2024-02-13 10:00:00" 这种带空格的格式)
        # 我们尝试使用 strptime 作为后备
        try:
            dt_naive = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            return CHINA_TZ.localize(dt_naive)
        except ValueError:
            logger.error(f"所有方法都无法解析日期时间字符串: '{date_str}'")
            return None
    except Exception as e:
        logger.error(f"解析日期 '{date_str}' 时发生未知错误: {e}")
        return None



# 这里可以添加其他通用工具函数
