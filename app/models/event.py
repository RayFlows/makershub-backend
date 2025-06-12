from mongoengine import StringField, IntField
from .base_model import BaseModel
from datetime import datetime
import random

class Event(BaseModel):
    """
    活动事件模型
    
    存储活动相关信息，包括名称、海报、描述等。
    """
    
    event_id = StringField(required=True, unique=True)  # 事件ID
    event_name = StringField()  # 活动名称
    poster = StringField()  # 海报URL
    description = StringField()  # 活动描述
    participant = StringField()  # 参与对象
    location = StringField()  # 活动地点
    link = StringField()  # 相关链接
    start_time = StringField()  # 开始时间
    end_time = StringField()  # 结束时间
    registration_deadline = StringField()  # 报名截止时间
    is_completed = IntField(default=0)  # 是否完成上传 (0:未完成, 1:已完成)
    
    # MongoDB集合配置
    meta = {
        'collection': 'events',
        'indexes': [
            'event_id',
            'start_time',
            'end_time'
        ]
    }
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "event_id": self.event_id,
            "event_name": self.event_name,
            "poster": self.poster,
            "description": self.description,
            "participant": self.participant,
            "location": self.location,
            "link": self.link,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "registration_deadline": self.registration_deadline,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @staticmethod
    def generate_event_id():
        """生成事件ID: EV + 当前时间戳(精确到毫秒) + 3位随机数"""
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d%H%M%S%f")[:-3]
        random_suffix = f"{random.randint(0,999):03d}"
        return f"EV{timestamp}_{random_suffix}"