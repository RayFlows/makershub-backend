from mongoengine import StringField, IntField, DateTimeField
from .base_model import BaseModel
from datetime import datetime
import random

class PublicityLink(BaseModel):
    """
    秀米链接模型
    
    存储秀米链接相关信息。
    """
    link_id = StringField(required=True, unique=True)  # 链接编号
    title = StringField(required=True)  # 推文标题
    name = StringField(required=True)  # 发布人姓名
    userid = StringField(required=True)  # 用户ID
    link = StringField(required=True)  # 链接地址
    state = IntField(default=0)  # 审核状态 (0:待审核, 1:审核通过, 2:已打回)
    review = StringField(default="")  # 审核反馈信息
    create_time = DateTimeField(default=datetime.utcnow)  # 创建时间
    
    # MongoDB集合配置
    meta = {
        'collection': 'publicity_links',
        'indexes': [
            'link_id',
            'userid',
            'state',
            'create_time'
        ]
    }
    
    @staticmethod
    def generate_link_id():
        """生成链接ID: PL + 当前时间戳(精确到毫秒) + 3位随机数"""
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%d%H%M%S%f")[:-3]
        random_suffix = f"{random.randint(0,999):03d}"
        return f"PL{timestamp}_{random_suffix}"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "link_id": self.link_id,
            "title": self.title,
            "name": self.name,
            "userid": self.userid,
            "link": self.link,
            "state": self.state,
            "review": self.review,
            "create_time": self.create_time.isoformat() + "Z",
            "created_at": self.created_at.isoformat() + "Z",
            "updated_at": self.updated_at.isoformat() + "Z"
        }