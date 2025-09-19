# app/models/stuff.py
"""
物资模型（扩展版本）
支持管理员后台的额外字段，同时保持与小程序的兼容性
"""

from app.models.base_model import BaseModel
from mongoengine import StringField, IntField, ListField
from mongoengine.errors import ValidationError

class Stuff(BaseModel):
    """
    物资模型
    
    用于存储物资的基本信息，包括物资类型、名称、数量等。
    扩展字段用于管理员后台的物资定位管理。
    """
    meta = {'collection': 'stuff'}
    
    # ========== 基础字段（小程序使用） ==========
    type_id = StringField(max_length=50)
    stuff_id = StringField(max_length=50, unique=True, required=True)
    type = StringField(max_length=100, required=True)  # 物资类型
    stuff_name = StringField(max_length=200, required=True)  # 物资名称
    number_total = IntField(required=True, min_value=0)  # 总数量
    number_remain = IntField(required=True, min_value=0)  # 剩余数量
    description = StringField(max_length=500, required=True)  # 描述
    
    # ========== 扩展字段（管理员后台专用） ==========
    # 这些字段为可选，确保向后兼容
    location = StringField(max_length=50, default="")  # 所在场地：i创街、101、208+
    cabinet = StringField(max_length=10, default="")   # 展柜位置：A-Z, AA-AZ等
    layer = IntField(min_value=1, max_value=10, default=1)  # 层数：1-10
    
    # 可用场地列表（动态从Site集合获取）
    available_locations = ListField(StringField(), default=lambda: ["i创街", "101", "208+"])
    
    def clean(self):
        """
        数据验证方法
        
        验证剩余数量不能超过总数量，以及位置信息的合法性
        
        Raises:
            ValidationError: 当数据不符合要求时抛出异常
        """
        super().clean()
        
        # 验证数量关系
        if self.number_remain > self.number_total:
            raise ValidationError('剩余数量不能超过总数量')
        
        # 验证展柜编号（如果提供）
        if self.cabinet:
            # 支持A-Z, AA-ZZ的格式
            import re
            if not re.match(r'^[A-Z]{1,2}$', self.cabinet):
                raise ValidationError('展柜编号必须为A-Z或AA-ZZ格式')
        
        # 验证层数范围
        if self.layer and (self.layer < 1 or self.layer > 10):
            raise ValidationError('层数必须在1-10之间')
    
    def to_dict(self, include_admin_fields=False):
        """
        将模型实例转换为字典格式
        
        Args:
            include_admin_fields: 是否包含管理员专用字段
            
        Returns:
            Dict: 包含字段的字典，时间字段转换为ISO格式字符串
        """
        base_dict = {
            'type_id': self.type_id,
            'stuff_id': self.stuff_id,
            'type': self.type,
            'stuff_name': self.stuff_name,
            'number_total': self.number_total,
            'number_remain': self.number_remain,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        # 仅在管理员请求时包含扩展字段
        if include_admin_fields:
            base_dict.update({
                'location': self.location or "",
                'cabinet': self.cabinet or "",
                'layer': self.layer or 1
            })
        
        return base_dict
    
    @classmethod
    def from_dict(cls, data, is_admin=False):
        """
        从字典创建模型实例
        
        Args:
            data: 包含物资信息的字典
            is_admin: 是否为管理员操作（决定是否处理扩展字段）
            
        Returns:
            Stuff: 新创建的物资模型实例
        """
        instance = cls(
            type_id=data.get('type_id'),
            stuff_id=data.get('stuff_id'),
            type=data.get('type'),
            stuff_name=data.get('stuff_name'),
            number_total=data.get('number_total'),
            number_remain=data.get('number_remain'),
            description=data.get('description')
        )
        
        # 如果是管理员操作，设置扩展字段
        if is_admin:
            instance.location = data.get('location', '')
            instance.cabinet = data.get('cabinet', '')
            instance.layer = data.get('layer', 1)
        
        return instance