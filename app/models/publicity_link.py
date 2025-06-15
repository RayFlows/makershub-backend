from mongoengine import StringField, DateTimeField, IntField, ReferenceField
from .user import User  # 假设 User 模型在同目录或已正确导入
from .base_model import BaseModel
from datetime import datetime

class PublicityLink(BaseModel):
    """
    秀米链接模型
    - 关联提交用户、记录审核状态、提交时间等
    """
    # 关联提交用户（必选）
    submitter = ReferenceField(User, required=True, reverse_delete_rule=2)
    # 秀米链接地址（需包含 HTTPS，必选）
    link_url = StringField(required=True, validation=lambda x: "https://" in x)
    # 审核状态：0=待审核, 1=已通过, 2=未通过（默认待审核）
    audit_status = IntField(default=0)
    # 审核意见（可选，最多 500 字）
    audit_comment = StringField(max_length=500)
    # 提交时间（自动生成）
    submit_time = DateTimeField(default=datetime.now)
    # 审核人（可选，关联 User）
    auditor = ReferenceField(User)
    # 审核时间（可选）
    audit_time = DateTimeField()

    meta = {
        'collection': 'publicity_links',  # MongoDB 集合名
        'indexes': [
            'submitter',     # 按提交人索引
            'audit_status',  # 按审核状态索引
            'submit_time'    # 按提交时间索引
        ]
    }

    def to_dict(self):
        """序列化为字典，用于 API 响应"""
        return {
            "id": str(self.id),
            "submitter": self.submitter.to_dict() if self.submitter else None,
            "link_url": self.link_url,
            "audit_status": self.audit_status,
            "audit_comment": self.audit_comment,
            "submit_time": self.submit_time.strftime("%Y-%m-%d %H:%M:%S"),
            "auditor": self.auditor.to_dict() if self.auditor else None,
            "audit_time": self.audit_time.strftime("%Y-%m-%d %H:%M:%S") if self.audit_time else None,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        }