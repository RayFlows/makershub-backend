# app/services/project_service.py
"""
项目服务类：处理与项目部相关的所有业务逻辑
[v1.1] 创建项目返回结果增加负责人年级(grade)
"""
from typing import Optional, List
from datetime import datetime
import random
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.project import Project, ProjectMember
from app.models.user import User

class ProjectService:
    """
    项目服务类，封装项目立项、管理、结项等业务逻辑。
    """

    def _generate_project_id(self) -> str:
        """
        生成项目业务ID: PJ + 当前时间戳(精确到毫秒) + 3位随机数。
        示例: PJ20231123120000123_456
        """
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d%H%M%S%f")[:-3]
        random_suffix = f"{random.randint(0,999):03d}"
        return f"PJ{timestamp}_{random_suffix}"

    def _project_to_dict(self, project: Project) -> Optional[dict]:
        """
        将 SQLAlchemy Project ORM 对象转换为字典。
        """
        if not project:
            return None
        
        # 获取负责人的附加信息
        # 注意：需要确保 project.leader 已经被加载（在 create_project 中我们会手动赋值）
        leader_grade = None
        leader_name = None
        if project.leader:
            leader_grade = project.leader.grade
            leader_name = project.leader.real_name

        return {
            "id": project.id, # 内部ID
            "project_id": project.project_id, # 业务ID
            "project_name": project.project_name,
            "project_type": project.project_type,
            "description": project.description,
            "start_time": project.start_time.strftime("%Y-%m-%d %H:%M:%S") if project.start_time else None,
            "end_time": project.end_time.strftime("%Y-%m-%d %H:%M:%S") if project.end_time else None,
            
            # --- 负责人信息 ---
            "leader_id": project.leader_id,
            "leader_name": leader_name,   # [新增] 负责人姓名
            "leader_grade": leader_grade, # [新增] 负责人年级 (User表字段)
            
            "mentor_name": project.mentor_name,
            "mentor_phone": project.mentor_phone,
            "state": project.state,
            "is_recruiting": project.is_recruiting,
            "review": project.review,
            "finish_description": project.finish_description,
            "finish_review": project.finish_review,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None
        }

    async def create_project(self, db: AsyncSession, project_data: dict, leader: User, member_phones: List[str]) -> dict:
        """
        创建新项目
        
        Args:
            db: 数据库会话
            project_data: 包含项目基础信息的字典
            leader: 当前登录用户（项目负责人）
            member_phones: 初始成员的手机号列表
            
        Returns:
            创建成功的项目信息字典
        """
        try:
            # 1. 生成业务ID
            pj_id = self._generate_project_id()
            
            # 2. 创建项目主表记录
            new_project = Project(
                project_id=pj_id,
                leader_id=leader.id, # 自动关联负责人
                state=0, # 默认为待审核
                **project_data # 解包其余字段
            )
            db.add(new_project)
            # 先flush以获取 new_project.id，用于后续插入成员
            await db.flush() 
            
            # 3. 处理初始成员 (如果有)
            if member_phones:
                # 批量查询手机号对应的用户
                stmt = select(User).where(User.phone_num.in_(member_phones))
                result = await db.execute(stmt)
                users_found = result.scalars().all()
                
                members_to_add = []
                found_phones = []
                
                for user in users_found:
                    if user.id == leader.id:
                        continue 
                        
                    members_to_add.append(ProjectMember(
                        project_id=new_project.id,
                        user_id=user.id
                    ))
                    found_phones.append(user.phone_num)
                
                if members_to_add:
                    db.add_all(members_to_add)
                    logger.info(f"项目 {pj_id} 添加了 {len(members_to_add)} 名初始成员。手机号: {found_phones}")
                else:
                    logger.info(f"项目 {pj_id} 未找到匹配的成员手机号。")

            # 4. 提交事务
            await db.commit()
            await db.refresh(new_project)
            
            # [关键步骤] 手动将 leader 对象赋值给 new_project
            # 这样 _project_to_dict 就能直接读取到 grade，而不需要再次查询数据库
            new_project.leader = leader
            
            logger.info(f"新项目创建成功: {new_project.project_name} (ID: {pj_id}) by User {leader.userid}")
            
            return {
                "code": 200,
                "message": "项目创建成功",
                "data": self._project_to_dict(new_project)
            }
            
        except Exception as e:
            await db.rollback()
            logger.error(f"创建项目失败: {e}", exc_info=True)
            raise e