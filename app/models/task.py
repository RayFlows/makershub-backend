from mongoengine import StringField, IntField, DateTimeField
from .base_model import BaseModel
from datetime import datetime
import random

class Task(BaseModel):
    """
    任务数据模型
    
    Attributes:
        task_id: 任务唯一标识符
        department: 负责部门
        task_type: 任务类型 (0:其他, 1:活动文案, 2:推文, 3:新闻稿)
        maker_id: 负责人协会ID
        name: 负责人姓名
        content: 任务内容
        state: 任务状态 (0-未完成, 1-已完成, 2-已取消)
        deadline: 截止时间
    """
    
    task_id = StringField(required=True, unique=True)
    department = StringField(required=True)
    task_type = IntField(required=True)
    maker_id = StringField(required=True)
    name = StringField(required=True)
    content = StringField(required=True)
    state = IntField(default=0)  # 0-未完成, 1-已完成, 2-已取消
    deadline = DateTimeField(required=True)

    # MongoDB集合配置和索引定义
    meta = {
        'collection': 'tasks',
        'indexes': [
            'task_id',
            'department',
            'task_type',
            'maker_id',
            'state',
            'deadline'
        ]
    }
    
    def to_dict(self):
        """
        将任务对象转换为字典格式
        """
        return {
            "task_id": self.task_id,
            "department": self.department,
            "task_type": self.task_type,
            "maker_id": self.maker_id,
            "name": self.name,
            "content": self.content,
            "state": self.state,
            "deadline": self.deadline.isoformat() + "Z",
            "created_at": self.created_at.isoformat() + "Z",
            "updated_at": self.updated_at.isoformat() + "Z"
        }
    
    @classmethod
    def generate_task_id(cls):
        """生成唯一任务ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]  # 精确到毫秒
        random_suffix = str(random.randint(100, 999))  # 3位随机数
        return f"TS{timestamp}_{random_suffix}"