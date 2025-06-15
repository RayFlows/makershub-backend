"""
借物申请模型模块 (Stuff Borrow Model Module)

该模块定义了借物申请数据模型，用于存储用户的借物申请信息。
基于BaseModel，提供了自动时间戳和序列化功能。
"""

from mongoengine import StringField, DateTimeField, IntField, ListField
from .base_model import BaseModel
from datetime import datetime
import re

class StuffBorrow(BaseModel):
    """
    借物申请数据模型
    
    存储用户的借物申请信息，包括个人信息、申请内容和借用物品清单。
    每个申请都关联到特定用户，实现用户间数据隔离。
    
    Attributes:
        borrow_id: 借物申请唯一标识符
        task_name: 任务名称/申请标题
        name: 申请人姓名
        student_id: 学生ID 
        phone: 联系电话
        email: 邮箱地址
        grade: 年级
        major: 专业
        content: 申请内容/用途说明
        deadline: 归还截止时间
        materials: 借用物品清单
        userid: 创建申请的用户ID
        type: 借物类型 (0=个人借物, 1=团队借物)
        supervisor_name: 指导老师姓名 (仅团队借物)
        supervisor_phone: 指导老师电话 (仅团队借物)
        project_number: 项目编号 (仅团队借物)
        status: 申请状态
        approval_note: 审批备注
        approval_time: 审批时间
        actual_return_time: 实际归还时间
    """
    
    # 借物申请唯一标识符，格式：BR + 时间戳
    borrow_id = StringField(required=True, unique=True)
    
    # # 任务名称/申请标题
    # task_name = StringField(required=True, max_length=200)
    
    # 申请人姓名
    name = StringField(required=True, max_length=100)

    # 学生ID，通常为学号
    student_id = StringField(max_length=50, default="")
    
    # 联系电话
    phone = StringField(required=True, max_length=20)
    
    # 邮箱地址
    email = StringField(required=True, max_length=100)
    
    # 年级
    grade = StringField(required=True, max_length=50)
    
    # 专业
    major = StringField(required=True, max_length=100)
    
    # 申请内容/用途说明
    content = StringField(required=True, max_length=1000)
    
    # 归还截止时间
    deadline = DateTimeField(required=True)
    
    # 借用物品清单，存储字符串列表
    materials = ListField(StringField(max_length=200), required=True)
    
    # 创建申请的用户ID，用于用户间数据隔离
    userid = StringField(required=True)

    # 借物类型: 0=个人借物, 1=团队借物
    type = IntField(default=0, min_value=0, max_value=1)
    
    # 指导老师姓名 (仅团队借物时使用)
    supervisor_name = StringField(max_length=100, default="")
    
    # 指导老师电话 (仅团队借物时使用)
    supervisor_phone = StringField(max_length=20, default="")
    
    # 项目编号 (仅团队借物时使用)
    project_number = StringField(max_length=100, default="")
    
    # 申请状态: 0=待审批, 1=已批准, 2=已借出, 3=已归还, 4=已拒绝, 5=已过期
    status = IntField(default=0, min_value=0, max_value=5)
    
    # 审批备注
    approval_note = StringField(max_length=500, default="")
    
    # 审批时间
    approval_time = DateTimeField()
    
    # 实际归还时间
    actual_return_time = DateTimeField()

    # MongoDB集合配置和索引定义
    meta = {
        'collection': 'stuff_borrows',
        'indexes': [
            'borrow_id',
            'userid',
            'status',
            'type',  # 添加type字段索引
            'deadline',
            'name',
            'student_id',  
            'phone',
            'email',
            'supervisor_name',  # 添加指导老师姓名索引
            'project_number',   # 添加项目编号索引
            'created_at',
            ('userid', 'status'),
            ('userid', 'type'),  # 添加复合索引
            ('userid', 'deadline'),
            ('status', 'deadline'),
            ('type', 'status'),  # 添加复合索引
            ('type', 'supervisor_name'),  # 团队借物按指导老师索引
            ('supervisor_name', 'project_number')  # 指导老师和项目编号复合索引
        ]
    }
    
    @staticmethod
    def get_type_desc(type_value):
        """
        获取借物类型描述
        
        Args:
            type_value (int): 类型编号
            
        Returns:
            str: 类型描述
        """
        type_map = {
            0: "个人借物",
            1: "团队借物"
        }
        return type_map.get(type_value, "未知类型")
    
    @staticmethod
    def generate_borrow_id():
        """
        生成借物申请ID
        
        格式：BR + 年月日时分秒，如BR20250611142307
        
        Returns:
            str: 借物申请ID
        """
        now = datetime.now()
        return f"BR{now.strftime('%Y%m%d%H%M%S')}"
    
    @staticmethod
    def parse_deadline(deadline_str: str):
        """
        解析截止时间字符串
        
        支持多种格式：
        - "2025-01-01"
        - "2025/01/01"
        - "2025-01-01 12:00"
        - "2025年1月1日"
        
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
            # 处理中文格式
            if '年' in deadline_str and '月' in deadline_str and '日' in deadline_str:
                pattern = r'(\d+)年(\d+)月(\d+)日'
                match = re.match(pattern, deadline_str)
                if match:
                    year, month, day = map(int, match.groups())
                    return datetime(year, month, day, 23, 59, 59)  # 默认到当天最后一秒
            
            # 处理标准格式
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y-%m-%d',
                '%Y/%m/%d %H:%M:%S',
                '%Y/%m/%d %H:%M',
                '%Y/%m/%d'
            ]
            
            for fmt in formats:
                try:
                    parsed_time = datetime.strptime(deadline_str, fmt)
                    # 如果只有日期没有时间，设置为当天最后一秒
                    if fmt in ['%Y-%m-%d', '%Y/%m/%d']:
                        parsed_time = parsed_time.replace(hour=23, minute=59, second=59)
                    return parsed_time
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
            0: "待审批",
            1: "已批准",
            2: "已借出",
            3: "已归还",
            4: "已拒绝",
            5: "已过期"
        }
        return status_map.get(status, "未知状态")
    
    def clean(self):
        """
        数据清理和验证
        根据借物类型处理相关字段
        """
        super().clean()
        
        # 个人借物时，清空团队相关字段
        if self.type == 0:
            self.supervisor_name = ""
            self.supervisor_phone = ""
            self.project_number = ""
        # 团队借物时，验证必填字段
        elif self.type == 1:
            if not self.supervisor_name or not self.supervisor_name.strip():
                from mongoengine import ValidationError
                raise ValidationError("团队借物必须填写指导老师姓名")
            if not self.supervisor_phone or not self.supervisor_phone.strip():
                from mongoengine import ValidationError
                raise ValidationError("团队借物必须填写指导老师电话")
            if not self.project_number or not self.project_number.strip():
                from mongoengine import ValidationError
                raise ValidationError("团队借物必须填写项目编号")
    
    def to_dict(self):
        """
        将借物申请对象转换为字典格式
        
        Returns:
            dict: 包含借物申请所有字段的字典
        """
        result = {
            "borrow_id": self.borrow_id,
            # "task_name": self.task_name,
            "name": self.name,
            "student_id": self.student_id,
            "phone": self.phone,
            "email": self.email,
            "grade": self.grade,
            "major": self.major,
            "content": self.content,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "materials": self.materials,
            "userid": self.userid,
            "type": self.type,
            "type_desc": self.get_type_desc(self.type),
            "status": self.status,
            "status_desc": self.get_status_desc(self.status),
            "approval_note": self.approval_note,
            "approval_time": self.approval_time.isoformat() if self.approval_time else None,
            "actual_return_time": self.actual_return_time.isoformat() if self.actual_return_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        
        # 根据借物类型添加相应字段
        if self.type == 1:  # 团队借物
            result.update({
                "supervisor_name": self.supervisor_name,
                "supervisor_phone": self.supervisor_phone,
                "project_number": self.project_number
            })
        else:  # 个人借物
            result.update({
                "supervisor_name": "",
                "supervisor_phone": "",
                "project_number": ""
            })
        
        return result
    
    def is_overdue(self):
        """
        检查借物申请是否已过期
        
        Returns:
            bool: 如果申请已过期返回True，否则返回False
        """
        if not self.deadline:
            return False
        # 只有已借出状态的申请才检查是否过期
        return self.deadline < datetime.now() and self.status == 2
    
    def get_remaining_time(self):
        """
        获取剩余时间
        
        Returns:
            str: 剩余时间描述
        """
        if self.status == 3:  # 已归还
            return "已归还"
        elif self.status == 4:  # 已拒绝
            return "申请被拒绝"
        elif self.status in [0, 1]:  # 待审批或已批准
            return "尚未借出"
        
        if not self.deadline:
            return "未设置归还时间"
        
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
    
    def get_materials_count(self):
        """
        获取借用物品总数
        
        Returns:
            int: 物品总数
        """
        return len(self.materials) if self.materials else 0
    
    def get_materials_summary(self):
        """
        获取借用物品摘要
        
        Returns:
            str: 物品摘要描述
        """
        if not self.materials:
            return "无借用物品"
        
        if len(self.materials) == 1:
            return self.materials[0]
        elif len(self.materials) <= 3:
            return "、".join(self.materials)
        else:
            return f"{self.materials[0]}等{len(self.materials)}项物品"
    
    def get_team_info_summary(self):
        """
        获取团队信息摘要
        
        Returns:
            str: 团队信息摘要，如果是个人借物返回空字符串
        """
        if self.type == 0:  # 个人借物
            return ""
        
        team_info = []
        if self.supervisor_name:
            team_info.append(f"指导老师：{self.supervisor_name}")
        if self.project_number:
            team_info.append(f"项目编号：{self.project_number}")
        
        return " | ".join(team_info) if team_info else ""
    
    def is_team_borrow(self):
        """
        判断是否为团队借物
        
        Returns:
            bool: 如果是团队借物返回True，否则返回False
        """
        return self.type == 1
    
    def validate_team_fields(self):
        """
        验证团队借物必填字段
        
        Returns:
            tuple: (is_valid: bool, error_messages: list)
        """
        if self.type != 1:  # 非团队借物不需要验证
            return True, []
        
        errors = []
        
        if not self.supervisor_name or not self.supervisor_name.strip():
            errors.append("团队借物必须填写指导老师姓名")
        
        if not self.supervisor_phone or not self.supervisor_phone.strip():
            errors.append("团队借物必须填写指导老师电话")
        
        if not self.project_number or not self.project_number.strip():
            errors.append("团队借物必须填写项目编号")
        
        return len(errors) == 0, errors