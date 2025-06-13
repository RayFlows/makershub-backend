from .base_model import BaseModel
from mongoengine import StringField, IntField
from datetime import datetime
import random

class SiteBorrow(BaseModel):
    """
    场地借用模型
    
    存储场地借用申请相关信息。
    """
    apply_id = StringField(required=True, unique=True)  # 申请编号
    userid = StringField(required=True)  # 用户ID
    name = StringField(required=True)  # 借用人姓名
    student_id = StringField(required=True)  # 学号
    phone_num = StringField(required=True)  # 电话号码
    email = StringField(required=True)  # 邮箱地址
    purpose = StringField(required=True)  # 借用目的
    project_id = StringField()  # 项目编号
    mentor_name = StringField(required=True)  # 指导老师姓名
    mentor_phone_num = StringField(required=True)  # 指导老师电话
    site_id = StringField(required=True)  # 场地ID
    site = StringField(required=True)  # 场地位置
    number = IntField(required=True)  # 场地编号
    start_time = StringField(required=True)  # 开始时间
    end_time = StringField(required=True)  # 结束时间
    state = IntField(default=0)  # 状态 (0:未审核, 1:打回, 2:通过未归还, 3:已归还, 4:取消)
    review = StringField(default="")  # 审核反馈
    
    # MongoDB集合配置
    meta = {
        'collection': 'site_borrows',
        'indexes': [
            'apply_id',
            'userid',
            'site_id',
            'number',
            'start_time',
            'end_time'
        ]
    }
    
    @staticmethod
    def generate_apply_id():
        """生成申请ID: SB + 当前时间戳(精确到毫秒) + 3位随机数"""
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%d%H%M%S%f")[:-3]
        random_suffix = f"{random.randint(0,999):03d}"
        return f"SB{timestamp}_{random_suffix}"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "apply_id": self.apply_id,
            "userid": self.userid,
            "name": self.name,
            "student_id": self.student_id,
            "phone_num": self.phone_num,
            "email": self.email,
            "purpose": self.purpose,
            "project_id": self.project_id,
            "mentor_name": self.mentor_name,
            "mentor_phone_num": self.mentor_phone_num,
            "site_id": self.site_id,
            "site": self.site,
            "number": self.number,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "state": self.state,
            "review": self.review,
            "created_at": self.created_at.isoformat() + "Z",
            "updated_at": self.updated_at.isoformat() + "Z"
        }