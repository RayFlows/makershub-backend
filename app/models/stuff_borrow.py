from app.models.base_model import BaseModel
from mongoengine import StringField, IntField, DateTimeField, ListField, DictField
from datetime import datetime

class StuffBorrow(BaseModel):
    meta = {'collection': 'stuff_borrow'}
    
    sb_id = StringField(max_length=50, unique=True, required=True)
    user_id = StringField(max_length=100, required=True)
    type = IntField(required=True, default=0)  # 0为个人借物，1为团队借物
    name = StringField(max_length=100, required=True)
    student_id = StringField(max_length=50, required=True)
    phone_num = StringField(max_length=20, required=True)
    email = StringField(max_length=100, required=True)
    grade = StringField(max_length=20, required=True)
    major = StringField(max_length=100, required=True)
    start_time = DateTimeField(required=True)
    deadline = DateTimeField(required=True)
    reason = StringField(max_length=500, required=True)
    state = IntField(required=True, default=0)  # 0-未审核, 1-被打回, 2-通过未归还, 3-已归还
    stuff_list = ListField(DictField(), required=True)
    
    # 团队借物相关字段（可选）
    project_num = StringField(max_length=50)
    mentor_name = StringField(max_length=100)
    mentor_phone_num = StringField(max_length=20)
    
    def to_dict(self):
        return {
            'sb_id': self.sb_id,
            'user_id': self.user_id,
            'type': self.type,
            'name': self.name,
            'student_id': self.student_id,
            'phone_num': self.phone_num,
            'email': self.email,
            'grade': self.grade,
            'major': self.major,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'reason': self.reason,
            'state': self.state,
            'stuff_list': self.stuff_list,
            'project_num': self.project_num,
            'mentor_name': self.mentor_name,
            'mentor_phone_num': self.mentor_phone_num,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }