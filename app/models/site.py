from .base_model import BaseModel
from mongoengine import Document, StringField, BooleanField, DateTimeField, IntField
from datetime import datetime
import random


class Site(BaseModel):
    """
    场地模型
    
    存储场地相关信息，包括位置、工位状态等。
    """
    site_id = StringField(required=True)  # 场地编号
    site = StringField(required=True)  # 场地位置
    number = IntField(required=True)  # 工位号
    is_occupied = BooleanField(default=False)  # 是否被占用
    
    # MongoDB集合配置
    meta = {
        'collection': 'sites',
        'indexes': [
            'site_id',
            'site',
            'number'
        ]
    }
    
    @staticmethod
    def generate_site_id():
        """生成场地ID: ST + 当前时间戳(精确到毫秒) + 3位随机数"""
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%d%H%M%S%f")[:-3]
        random_suffix = f"{random.randint(0,999):03d}"
        return f"ST{timestamp}_{random_suffix}"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "site_id": self.site_id,
            "site": self.site,
            "number": self.number,
            "is_occupied": self.is_occupied,
            "created_at": self.created_at.isoformat() + "Z",
            "updated_at": self.updated_at.isoformat() + "Z"
        }