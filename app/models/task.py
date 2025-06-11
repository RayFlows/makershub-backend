"""
任务模型模块 (Task Model Module)

该模块定义了任务数据模型，用于存储用户的任务信息。
基于BaseModel，提供了自动时间戳和序列化功能。
"""

from mongoengine import StringField, DateTimeField, IntField
from .base_model import BaseModel
from datetime import datetime
import re

class Task(BaseModel):
    """
    任务数据模型
    
    存储用户的任务信息，包括任务名称、负责人、内容描述和截止时间。
    每个任务都关联到特定用户，实现用户间数据隔离。
    
    Attributes:
        task_id: 任务唯一标识符
        task_name: 任务名称
        name: 负责人姓名
        content: 任务内容描述
        deadline: 任务截止时间
        userid: 创建任务的用户ID
        status: 任务状态
        priority: 任务优先级
    """
    
    # 任务唯一标识符，格式：TASK + 时间戳
    task_id = StringField(required=True, unique=True)
    
    # 任务名称
    task_name = StringField(required=True, max_length=200)
    
    # 负责人姓名
    name = StringField(required=True, max_length=100)
    
    # 任务内容描述
    content = StringField(required=True, max_length=1000)
    
    # 任务截止时间
    deadline = DateTimeField(required=True)
    
    # 创建任务的用户ID，用于用户间数据隔离
    userid = StringField(required=True)
    
    # 任务状态: 0=待处理, 1=进行中, 2=已完成, 3=已取消
    status = IntField(default=0, min_value=0, max_value=3)
    
    # 任务优先级: 1=低, 2=中, 3=高
    priority = IntField(default=2, min_value=1, max_value=3)

    # MongoDB集合配置（简化索引配置）
    meta = {
        'collection': 'tasks',
        'indexes': [
            'task_id',
            'userid',
            'status',
            'deadline',
            ('userid', 'status')  # 只保留最重要的组合索引
        ]
    }
    
    @staticmethod
    def generate_task_id():
        """
        生成任务ID
        
        格式：TASK + 年月日时分秒，如TASK20250611001530
        
        Returns:
            str: 任务ID
        """
        now = datetime.now()
        return f"TASK{now.strftime('%Y%m%d%H%M%S')}"
    
    @staticmethod
    def parse_deadline(deadline_str: str):
        """
        解析截止时间字符串
        
        支持多种格式：
        - "2024年-1月-1日 1时:1分"
        - "2024-01-01 01:01"
        - "2024/01/01 01:01"
        
        Args:
            deadline_str: 截止时间字符串
            
        Returns:
            datetime: 解析后的datetime对象
            
        Raises:
            ValueError: 如果时间格式不正确
        """
        if not deadline_str:
            raise ValueError("时间字符串不能为空")
        
        try:
            # 处理中文格式：2024年-1月-1日 1时:1分
            if '年' in deadline_str and '月' in deadline_str and '日' in deadline_str:
                # 提取数字
                pattern = r'(\d+)年-?(\d+)月-?(\d+)日\s*(\d+)时:?(\d+)分?'
                match = re.match(pattern, deadline_str)
                if match:
                    year, month, day, hour, minute = map(int, match.groups())
                    return datetime(year, month, day, hour, minute)
            
            # 处理标准格式
            formats = [
                '%Y-%m-%d %H:%M',
                '%Y/%m/%d %H:%M',
                '%Y-%m-%d %H:%M:%S',
                '%Y/%m/%d %H:%M:%S',
                '%Y-%m-%d',
                '%Y/%m/%d'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(deadline_str, fmt)
                except ValueError:
                    continue
            
            raise ValueError(f"无法解析时间格式: {deadline_str}")
            
        except Exception as e:
            raise ValueError(f"时间解析错误: {str(e)}")
    
    @staticmethod
    def get_status_desc(status):
        """
        获取状态描述
        
        Args:
            status (int): 状态编号
            
        Returns:
            str: 状态描述
        """
        status_map = {
            0: "待处理",
            1: "进行中", 
            2: "已完成",
            3: "已取消"
        }
        return status_map.get(status, "未知状态")
    
    @staticmethod
    def get_priority_desc(priority):
        """
        获取优先级描述
        
        Args:
            priority (int): 优先级编号
            
        Returns:
            str: 优先级描述
        """
        priority_map = {
            1: "低",
            2: "中",
            3: "高"
        }
        return priority_map.get(priority, "未知优先级")
    
    def to_dict(self):
        """
        将任务对象转换为字典格式
        
        重写基类方法，专门处理Task模型的字段。
        用于API响应序列化和数据传输。
        
        Returns:
            dict: 包含任务所有字段的字典
        """
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "name": self.name,
            "content": self.content,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "userid": self.userid,
            "status": self.status,
            "status_desc": self.get_status_desc(self.status),
            "priority": self.priority,
            "priority_desc": self.get_priority_desc(self.priority),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def is_overdue(self):
        """
        检查任务是否已过期
        
        Returns:
            bool: 如果任务已过期返回True，否则返回False
        """
        if not self.deadline:
            return False
        return self.deadline < datetime.now() and self.status not in [2, 3]
    
    def get_remaining_time(self):
        """
        获取剩余时间
        
        Returns:
            str: 剩余时间描述
        """
        if self.status in [2, 3]:  # 已完成或已取消
            return "任务已结束"
        
        if not self.deadline:
            return "未设置截止时间"
        
        now = datetime.now()
        if self.deadline < now:
            return "已过期"
        
        delta = self.deadline - now
        days = delta.days
        hours = delta.seconds // 3600
        
        if days > 0:
            return f"剩余{days}天{hours}小时"
        elif hours > 0:
            return f"剩余{hours}小时"
        else:
            return "即将到期"