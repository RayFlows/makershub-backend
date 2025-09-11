from app.models.base_model import BaseModel
from mongoengine import StringField, IntField
from mongoengine.errors import ValidationError

class Stuff(BaseModel):
    """
    物资模型
    
    用于存储物资的基本信息，包括物资类型、名称、数量等。
    支持数量验证和数据转换功能。
    """
    meta = {'collection': 'stuff'}
    
    type_id = StringField(max_length=50)
    stuff_id = StringField(max_length=50, unique=True, required=True)
    type = StringField(max_length=100, required=True)
    stuff_name = StringField(max_length=200, required=True)
    number_total = IntField(required=True, min_value=0)
    number_remain = IntField(required=True, min_value=0)
    description = StringField(max_length=500, required=True)
    
    def clean(self):
        """
        数据验证方法
        
        验证剩余数量不能超过总数量
        
        Raises:
            ValidationError: 当剩余数量超过总数量时抛出异常
        """
        super().clean()
        if self.number_remain > self.number_total:
            raise ValidationError('剩余数量不能超过总数量')
    
    def to_dict(self):
        """
        将模型实例转换为字典格式
        
        Returns:
            Dict: 包含所有字段的字典，时间字段转换为ISO格式字符串
        """
        return {
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
    
    @classmethod
    def from_dict(cls, data):
        """
        从字典创建模型实例
        
        Args:
            data: 包含物资信息的字典
            
        Returns:
            Stuff: 新创建的物资模型实例
        """
        return cls(
            type_id=data.get('type_id'),
            stuff_id=data.get('stuff_id'),
            type=data.get('type'),
            stuff_name=data.get('stuff_name'),
            number_total=data.get('number_total'),
            number_remain=data.get('number_remain'),
            description=data.get('description')
        )