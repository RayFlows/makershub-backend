#user.py
"""
用户模型模块 (User Model Module)

该模块定义了用户数据模型，用于存储与微信小程序用户相关的信息。
基于BaseModel，提供了自动时间戳和序列化功能。
"""

from mongoengine import StringField, IntField, BinaryField
from .base_model import BaseModel

class User(BaseModel):
    """
    用户数据模型
    
    存储用户基本信息、权限级别、状态和积分等数据。
    主要用于微信小程序用户的身份验证和信息管理。
    
    Attributes:
        userid: 用户唯一标识符，使用微信openid
        role: 用户权限级别
        real_name: 用户真实姓名
        phone_num: 用户手机号
        motto: 用户个性签名
        state: 用户账号状态
        profile_photo: 用户头像(链接Minio存储)
        score: 用户积分
        total_dutytime: 用户总值班时长，单位分钟
    """
    
    # 使用微信openid作为用户唯一标识
    userid = StringField(required=True, unique=True)

    # 协会ID，分配给用户的协会标识符
    maker_id = StringField()  
    
    # 用户权限级别: 0=普通用户, 1=干事(默认), 2=部长及以上
    role = IntField(default=1)

    # 用户所属部门，默认为999
    department = IntField(default=999)
    
    # 用户真实姓名(可选)
    real_name = StringField(default="猫猫")
    
    # 用户手机号(可选)
    phone_num = StringField()

    # 用户个性签名(可选)
    motto = StringField(default="这个人很懒，什么都没写~") 
    
    # 用户账号状态: 0=封禁, 1=正常(默认)
    state = IntField(default=1)
    
    # 用户头像，链接Minio
    profile_photo = StringField()
    
    # 用户积分，默认为0
    score = IntField(default=0)

    # 总值班时长，单位分钟
    total_dutytime = IntField(default=0) 




    # MongoDB集合配置和索引定义
    meta = {
        'collection': 'users',  # 指定MongoDB集合名称
        'indexes': [
            'userid',     # 索引用户ID加快查询
            'phone_num',  # 索引电话号码
            'real_name',  # 索引真实姓名
            'role',      # 索引用户级别，便于权限筛选
            'state',       # 索引用户状态，便于状态筛选
            'department',  # 索引部门，便于部门筛选
            "maker_id" 
        ]
    }
    
    def to_dict(self):
        """
        将用户对象转换为字典格式
        
        重写基类方法，专门处理User模型的字段。
        用于API响应序列化和数据传输。
        
        Returns:
            dict: 包含用户所有字段的字典
        """
        return {
            "userid": self.userid,
            "maker_id": self.maker_id,
            "role": self.role,
            "department": self.department,
            "real_name": self.real_name,
            "phone_num": self.phone_num,
            "motto": self.motto,
            "state": self.state,
            "profile_photo": self.profile_photo,
            "score": self.score,
            "total_dutytime": self.total_dutytime,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
