#base_model.py
"""
基础模型类模块 (Base Model Module)

该模块定义了应用中所有MongoDB文档模型的基类，提供了自动时间戳和序列化功能。
所有业务模型都应继承此基类以获得统一的基础功能。
"""

from mongoengine import Document, DateTimeField  # 导入mongoengine的文档基类和日期时间字段
from datetime import datetime  # 导入datetime用于处理时间戳

class BaseModel(Document):
    """
    MongoDB文档模型的基类
    
    提供以下功能:
    1. 自动维护创建和更新时间戳
    2. 文档实例转字典方法
    
    所有业务模型应继承此类而非直接继承mongoengine.Document
    """
    # 将此类标记为抽象类，MongoDB不会为其创建集合
    # 只能被其他模型类继承使用
    meta = {'abstract': True}
    
    # 文档创建时间，自动设置为创建时的UTC时间
    created_at = DateTimeField(default=datetime.utcnow)
    
    # 文档更新时间，初始与创建时间相同，每次保存时更新
    updated_at = DateTimeField(default=datetime.utcnow)

    def save(self, *args, **kwargs):
        """
        重写保存方法，在每次保存文档时自动更新时间戳
        
        如果创建时间为空，则设置为当前时间
        每次调用save()时都会更新updated_at字段
        
        Args:
            *args: 传递给父类save方法的位置参数
            **kwargs: 传递给父类save方法的关键字参数
            
        Returns:
            Document: 保存后的文档实例
        """
        if not self.created_at:
            self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)
    
    def to_dict(self):
        """
        将文档实例转换为Python字典格式
        
        遍历所有字段并获取它们的值，适用于API响应和数据序列化
        
        Returns:
            dict: 包含所有字段名和值的字典
        """
        return {field: getattr(self, field) for field in self._fields}
