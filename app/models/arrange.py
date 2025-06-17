from mongoengine import StringField, IntField, BooleanField
from .base_model import BaseModel
from datetime import datetime
import random

class Arrange(BaseModel):
    """
    排班安排模型
    
    存储各类排班任务的人员安排信息
    """
    arrange_id = StringField(required=True, unique=True)  # 排班编号
    name = StringField(required=True)  # 排班人员姓名
    maker_id = StringField(required=True)  # 新增: 负责人协会ID
    task_type = IntField(required=True)  # 任务类型 (1:活动文案, 2:推文, 3:新闻稿)
    order = IntField(required=True)  # 排班顺序
    current = BooleanField(default=False)  # 当前是否值班
    
    # MongoDB集合配置
    meta = {
        'collection': 'arrangements',
        'indexes': [
            'task_type',
            'order',
            'current',
            'maker_id'  # 新增索引
        ]
    }
    
    @staticmethod
    def generate_arrange_id():
        """生成排班ID: AR + 当前时间戳(精确到毫秒) + 3位随机数"""
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%d%H%M%S%f")[:-3]
        random_suffix = f"{random.randint(0,999):03d}"
        return f"AR{timestamp}_{random_suffix}"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "arrange_id": self.arrange_id,
            "name": self.name,
            "maker_id": self.maker_id,  # 新增字段
            "task_type": self.task_type,
            "order": self.order,
            "current": self.current,
            "created_at": self.created_at.isoformat() + "Z",
            "updated_at": self.updated_at.isoformat() + "Z"
        }