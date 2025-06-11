"""
值班申请模型模块 (Duty Apply Model Module)

该模块定义了值班申请数据模型，用于存储用户的值班申请信息。
基于BaseModel，提供了自动时间戳和序列化功能。
"""

from mongoengine import StringField, IntField
from .base_model import BaseModel
import datetime

class DutyApply(BaseModel):
    """
    值班申请数据模型
    
    存储用户的值班申请信息，包括申请编号、申请人信息和三个时间段的值班安排。
    每个申请包含三个可选的值班时段，每个时段包含星期和具体时间段。
    
    Attributes:
        apply_id: 申请编号，格式为DA+日期
        name: 申请人姓名
        userid: 用户唯一标识符，使用微信openid
        day1: 第一个值班日（星期一到星期日）
        time_section1: 第一个时间段（1-6对应不同时间）
        day2: 第二个值班日（星期一到星期日）
        time_section2: 第二个时间段（1-6对应不同时间）
        day3: 第三个值班日（星期一到星期日）
        time_section3: 第三个时间段（1-6对应不同时间）
    """
    
    # 申请编号，格式：DA + 年月日，如DA20250506
    apply_id = StringField(required=True, unique=True)
    
    # 申请人姓名，必填
    name = StringField(required=True)
    
    # 用户唯一标识符，使用微信openid
    userid = StringField(required=True)
    
    # 第一个值班时段
    day1 = StringField(required=True, choices=[
        '星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'
    ])
    time_section1 = IntField(required=True, min_value=1, max_value=6)
    
    # 第二个值班时段
    day2 = StringField(required=True, choices=[
        '星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'
    ])
    time_section2 = IntField(required=True, min_value=1, max_value=6)
    
    # 第三个值班时段
    day3 = StringField(required=True, choices=[
        '星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'
    ])
    time_section3 = IntField(required=True, min_value=1, max_value=6)

    # MongoDB集合配置和索引定义
    meta = {
        'collection': 'duty_applies',  # 指定MongoDB集合名称
        'indexes': [
            'apply_id',     # 索引申请编号
            'userid',       # 索引用户ID
            'name',         # 索引申请人姓名
            'day1',         # 索引第一个值班日
            'day2',         # 索引第二个值班日
            'day3',         # 索引第三个值班日
            'created_at'    # 索引创建时间，便于按时间查询
        ]
    }
    
    @staticmethod
    def generate_apply_id():
        """
        生成申请编号
        
        格式：DA + 年月日，如DA20250506
        
        Returns:
            str: 申请编号
        """
        today = datetime.datetime.now()
        return f"DA{today.strftime('%Y%m%d')}"
    
    @staticmethod
    def get_time_section_desc(section):
        """
        获取时间段描述
        
        Args:
            section (int): 时间段编号（1-6）
            
        Returns:
            str: 时间段描述
        """
        time_sections = {
            1: "08:10 - 10:05",
            2: "10:15 - 12:20", 
            3: "12:30 - 14:30",
            4: "14:30 - 16:30",
            5: "16:30 - 18:30",
            6: "18:30 - 20:30"
        }
        return time_sections.get(section, "未知时间段")
    
    def to_dict(self):
        """
        将值班申请对象转换为字典格式
        
        重写基类方法，专门处理DutyApply模型的字段。
        用于API响应序列化和数据传输。
        
        Returns:
            dict: 包含值班申请所有字段的字典
        """
        return {
            "apply_id": self.apply_id,
            "name": self.name,
            "userid": self.userid,
            "day1": self.day1,
            "time_section1": self.time_section1,
            "time_section1_desc": self.get_time_section_desc(self.time_section1),
            "day2": self.day2,
            "time_section2": self.time_section2,
            "time_section2_desc": self.get_time_section_desc(self.time_section2),
            "day3": self.day3,
            "time_section3": self.time_section3,
            "time_section3_desc": self.get_time_section_desc(self.time_section3),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    def get_schedule_summary(self):
        """
        获取值班安排摘要
        
        Returns:
            list: 包含三个时段详细信息的列表
        """
        return [
            {
                "day": self.day1,
                "time_section": self.time_section1,
                "time_desc": self.get_time_section_desc(self.time_section1)
            },
            {
                "day": self.day2,
                "time_section": self.time_section2,
                "time_desc": self.get_time_section_desc(self.time_section2)
            },
            {
                "day": self.day3,  
                "time_section": self.time_section3,
                "time_desc": self.get_time_section_desc(self.time_section3)
            }
        ]