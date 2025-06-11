from .base_model import BaseModel
from mongoengine import fields

class Event(BaseModel):
    # 活动ID格式 EV + 年月日 + 序号 (由服务层生成)
    event_id = fields.StringField(required=True, unique=True)  
    # 基础信息
    event_name = fields.StringField(required=True)
    description = fields.StringField(required=True)
    location = fields.StringField(required=True)
    link = fields.URLField()  # 二课链接，可选
    # 时间信息
    start_time = fields.DateTimeField(required=True)
    end_time = fields.DateTimeField(required=True)
    registration_deadline = fields.DateTimeField(required=True)
    # 图片信息（将由另一个接口处理）
    poster_url = fields.URLField()  # 海报URL

    # 作者信息
    created_by = fields.ReferenceField('User')  # 引用User模型
    last_modified_by = fields.ReferenceField('User')

    meta = {
        'collection': 'events',
        'indexes': ['start_time', 'registration_deadline']
    }
