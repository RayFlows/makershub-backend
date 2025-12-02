# app/services/project_service.py
"""
项目服务类：处理与项目部相关的所有业务逻辑
[v1.1] 创建项目返回结果增加负责人年级(grade)
"""
from typing import Optional, List
from datetime import datetime, timedelta
import random
from sqlalchemy import select, select, or_, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload # 使用 selectinload 预加载关系
from loguru import logger

from app.models.project import Project, ProjectMember, ProjectMaterial
from app.models.user import User
from app.core.storage import minio_client

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

    async def create_project(self, db: AsyncSession, project_data: dict, leader: User, member_maker_ids: List[str]) -> dict:
        """
        创建新项目
        
        Args:
            db: 数据库会话
            project_data: 包含项目基础信息的字典
            leader: 当前登录用户（项目负责人）
            member_maker_ids: 初始成员的 maker_id 列表
            
        Returns:
            创建成功的项目信息字典
        """
        try:
            # [新增校验] 检查负责人是否把自己加进了成员列表
            if leader.maker_id in member_maker_ids:
                # 直接抛出错误，中断流程，防止后续的数据库查询导致 Session 冲突
                raise ValueError("项目负责人已自动包含在项目中，请勿将其添加到成员列表。")
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
            if member_maker_ids:
                # 使用 maker_id 查询用户
                stmt = select(User).where(User.maker_id.in_(member_maker_ids))
                result = await db.execute(stmt)
                users_found = result.scalars().all()
                
                members_to_add = []
                found_maker_ids = []
                found_phones = []
                
                for user in users_found:
                    if user.id == leader.id:
                        continue 
                        
                    members_to_add.append(ProjectMember(
                        project_id=new_project.id,
                        user_id=user.id
                    ))
                    found_maker_ids.append(user.maker_id)
                    found_phones.append(user.phone_num)
                
                if members_to_add:
                    db.add_all(members_to_add)
                    logger.info(f"项目 {pj_id} 添加了 {len(members_to_add)} 名初始成员。手机号: {found_phones}，IDs: {found_maker_ids}")
                else:
                    logger.info(f"项目 {pj_id} 未找到匹配的成员手机号或IDs。")

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
            
        except ValueError as ve:
            # 捕获业务逻辑错误，重新抛出给 Router 处理
            raise ve    
        except Exception as e:
            await db.rollback()
            logger.error(f"创建项目失败: {e}", exc_info=True)
            raise e
    
    async def get_my_projects(self, db: AsyncSession, user_id: int) -> List[dict]:
        """
        获取我参与的项目列表（我是负责人 OR 我是成员）
        """
        try:
            # 构造查询：
            # 1. 查询 Project 表
            # 2. 左连接 ProjectMember 表 (为了检查我是不是成员)
            # 3. 过滤条件: Project.leader_id == 我  OR  ProjectMember.user_id == 我
            # 4. 预加载 leader 关系 (为了 _project_to_dict 能拿到负责人姓名和年级)
            # 5. 去重 (distinct) 因为如果我又当负责人又把自己加进成员表，会查出两条
            stmt = select(Project).outerjoin(
                ProjectMember, Project.id == ProjectMember.project_id
            ).where(
                or_(
                    Project.leader_id == user_id,
                    ProjectMember.user_id == user_id
                )
            ).options(
                selectinload(Project.leader)
            ).distinct().order_by(Project.created_at.desc())

            result = await db.execute(stmt)
            projects = result.scalars().all()

            # 转换为字典列表
            return [self._project_to_dict(p) for p in projects]
            
        except Exception as e:
            logger.error(f"获取用户项目列表失败: {e}", exc_info=True)
            raise e

    async def get_project_detail(self, db: AsyncSession, project_id: str) -> Optional[dict]:
        """
        根据 project_id 获取项目详情（包含负责人详细信息和成员列表）
        """
        try:
            # 构造查询
            # 1. 根据 project_id 过滤
            # 2. 预加载 leader (User)
            # 3. 预加载 members -> user (ProjectMember -> User)
            stmt = select(Project).where(
                Project.project_id == project_id
            ).options(
                selectinload(Project.leader),
                selectinload(Project.members).selectinload(ProjectMember.user)
            )

            result = await db.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                return None

            # 构建符合接口文档要求的成员列表
            members_list = []
            for pm in project.members:
                if pm.user:
                    members_list.append({
                        "real_name": pm.user.real_name,
                        "phone_num": pm.user.phone_num,
                        "college": pm.user.college,
                        "grade": pm.user.grade,         
                        "student_id": pm.user.student_id,
                        "maker_id": pm.user.maker_id 
                    })

            # 构建返回字典 (扁平化负责人信息)
            return {
                "project_id": project.project_id,
                "project_name": project.project_name,
                "project_type": project.project_type,
                "description": project.description,
                
                "start_time": project.start_time.strftime("%Y-%m-%d %H:%M:%S") if project.start_time else None,
                "end_time": project.end_time.strftime("%Y-%m-%d %H:%M:%S") if project.end_time else None,
                
                # --- 负责人信息 (扁平化) ---
                "leader_name": project.leader.real_name if project.leader else "",
                "leader_phone": project.leader.phone_num if project.leader else "",
                "leader_qq": project.leader.qq if project.leader else "",
                "leader_grade": project.leader.grade if project.leader else "",
                "leader_student_id": project.leader.student_id if project.leader else "",
                "college": project.leader.college if project.leader else "", # 负责人的学院
                
                # --- 其他信息 ---
                "mentor_name": project.mentor_name,
                "mentor_phone": project.mentor_phone,
                "state": project.state,
                "is_recruiting": project.is_recruiting,
                "review": project.review,
                "finish_description": project.finish_description,
                "finish_review": project.finish_review,
                "created_at": project.created_at.strftime("%Y-%m-%d %H:%M:%S") if project.created_at else None,
                "updated_at": project.updated_at.strftime("%Y-%m-%d %H:%M:%S") if project.updated_at else None,
                
                # --- 成员列表 ---
                "members": members_list
            }

        except Exception as e:
            logger.error(f"获取项目详情失败: {e}", exc_info=True)
            raise e
    
    async def add_members(self, db: AsyncSession, project_id: str, leader_user: User, maker_ids: List[str]) -> List[dict]:
        """
        添加项目成员
        
        Args:
            project_id: 项目业务ID
            leader_user: 当前操作用户（必须是负责人）
            maker_ids: 待添加成员的 maker_id 列表
            
        Returns:
            List[dict]: 成功新添加的成员列表信息
        """
        try:
            # 1. 获取项目并校验权限
            stmt = select(Project).where(Project.project_id == project_id)
            result = await db.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                raise ValueError("项目不存在")
            
            if project.leader_id != leader_user.id:
                raise PermissionError("只有项目负责人可以添加成员")

            if not maker_ids:
                return []

            # 2. 查询待添加的用户对象
            stmt = select(User).where(User.maker_id.in_(maker_ids))
            result = await db.execute(stmt)
            candidate_users = result.scalars().all()
            
            if not candidate_users:
                return []

            candidate_user_ids = [u.id for u in candidate_users]

            # 3. 查询这些用户中，哪些已经是成员了 (避免重复插入)
            stmt_exist = select(ProjectMember.user_id).where(
                ProjectMember.project_id == project.id,
                ProjectMember.user_id.in_(candidate_user_ids)
            )
            result_exist = await db.execute(stmt_exist)
            existing_member_ids = set(result_exist.scalars().all())

            # 4. 过滤并构建插入列表
            members_to_add = []
            added_users_info = []

            for user in candidate_users:
                # 规则A: 排除负责人自己
                if user.id == project.leader_id:
                    continue
                # 规则B: 排除已经是成员的人
                if user.id in existing_member_ids:
                    continue

                members_to_add.append(ProjectMember(
                    project_id=project.id,
                    user_id=user.id
                ))
                
                # 收集返回数据
                added_users_info.append({
                    "real_name": user.real_name,
                    "college": user.college,
                    "phone_num": user.phone_num,
                    "maker_id": user.maker_id
                })

            # 5. 执行插入
            if members_to_add:
                db.add_all(members_to_add)
                await db.commit()
                logger.info(f"项目 {project_id} 新增成员: {[u['maker_id'] for u in added_users_info]}")
            
            return added_users_info

        except Exception as e:
            if not isinstance(e, (ValueError, PermissionError)):
                await db.rollback()
                logger.error(f"添加成员失败: {e}", exc_info=True)
            raise e

    async def remove_members(self, db: AsyncSession, project_id: str, leader_user: User, maker_ids: List[str]) -> List[dict]:
        """
        移除项目成员
        
        Args:
            project_id: 项目业务ID
            leader_user: 当前操作用户（必须是负责人）
            maker_ids: 待移除成员的 maker_id 列表
            
        Returns:
            List[dict]: 成功移除的成员列表信息
        """
        try:
            # 1. 获取项目并校验权限
            stmt = select(Project).where(Project.project_id == project_id)
            result = await db.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                raise ValueError("项目不存在")
            
            if project.leader_id != leader_user.id:
                raise PermissionError("只有项目负责人可以移除成员")

            if not maker_ids:
                return []

            # 2. 查询待移除的用户对象
            stmt_users = select(User).where(User.maker_id.in_(maker_ids))
            result_users = await db.execute(stmt_users)
            target_users = result_users.scalars().all()
            
            if not target_users:
                return []

            target_user_ids = [u.id for u in target_users]

            # 3. 确认这些用户确实在成员列表中 (为了准确返回被删除的人，也为了避免无效删除)
            # 我们先查出来“即将被删除的成员信息”，用于返回给前端
            stmt_exist = select(User).join(
                ProjectMember, User.id == ProjectMember.user_id
            ).where(
                ProjectMember.project_id == project.id,
                User.id.in_(target_user_ids)
            )
            result_exist = await db.execute(stmt_exist)
            users_to_remove = result_exist.scalars().all()
            
            if not users_to_remove:
                return []
                
            ids_to_remove = [u.id for u in users_to_remove]

            # 4. 执行删除操作
            stmt_delete = delete(ProjectMember).where(
                ProjectMember.project_id == project.id,
                ProjectMember.user_id.in_(ids_to_remove)
            )
            await db.execute(stmt_delete)
            await db.commit()
            
            # 5. 构造返回数据
            removed_info = [
                {
                    "real_name": u.real_name,
                    "college": u.college,
                    "phone_num": u.phone_num,
                    "maker_id": u.maker_id
                }
                for u in users_to_remove
            ]
            
            logger.info(f"项目 {project_id} 移除了成员: {[u['maker_id'] for u in removed_info]}")
            return removed_info

        except Exception as e:
            if not isinstance(e, (ValueError, PermissionError)):
                await db.rollback()
                logger.error(f"移除成员失败: {e}", exc_info=True)
            raise e

    async def get_review_list(self, db: AsyncSession, state: Optional[int]) -> List[dict]:
        """
        获取审核列表 (管理员/高级成员专用)
        
        Args:
            state: 筛选的项目状态 (可选)
        """
        try:
            # 构造查询
            stmt = select(Project)
            
            # 如果传了 state，则进行筛选
            if state is not None:
                stmt = stmt.where(Project.state == state)
            
            # [关键] 预加载 Leader 和 Members，防止 N+1
            stmt = stmt.options(
                selectinload(Project.leader),
                selectinload(Project.members).selectinload(ProjectMember.user)
            ).order_by(Project.created_at.desc()) # 按时间倒序

            result = await db.execute(stmt)
            projects = result.scalars().all()

            # 序列化结果
            results_list = []
            for p in projects:
                # 1. 处理成员列表
                members_data = []
                for pm in p.members:
                    if pm.user:
                        members_data.append({
                            "real_name": pm.user.real_name,
                            "phone_num": pm.user.phone_num,
                            "college": pm.user.college
                        })

                # 2. 构建详细字典 (匹配接口文档要求)
                project_data = {
                    "project_id": p.project_id,
                    "project_name": p.project_name,
                    "project_type": p.project_type,
                    "description": p.description,
                    
                    "start_time": p.start_time.strftime("%Y-%m-%d %H:%M:%S") if p.start_time else None,
                    "end_time": p.end_time.strftime("%Y-%m-%d %H:%M:%S") if p.end_time else None,
                    
                    # 负责人详细信息 (审核需要看联系方式)
                    "leader_name": p.leader.real_name if p.leader else "",
                    "leader_phone": p.leader.phone_num if p.leader else "",
                    "leader_qq": p.leader.qq if p.leader else "",
                    "college": p.leader.college if p.leader else "",
                    
                    "mentor_name": p.mentor_name,
                    "mentor_phone": p.mentor_phone,
                    "state": p.state,
                    "is_recruiting": p.is_recruiting,
                    "review": p.review,
                    "created_at": p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else None,
                    "updated_at": p.updated_at.strftime("%Y-%m-%d %H:%M:%S") if p.updated_at else None,
                    
                    # 包含成员列表
                    "members": members_data
                }
                results_list.append(project_data)

            return results_list
            
        except Exception as e:
            logger.error(f"获取审核列表失败: {e}", exc_info=True)
            raise e

    async def audit_project(self, db: AsyncSession, project_id: str, state: int, review: Optional[str]) -> dict:
        """
        提交立项审核结果
        
        Args:
            project_id: 项目业务ID
            state: 新状态 (1=通过, 2=驳回)
            review: 审核意见
        """
        try:
            # 1. 查找项目
            stmt = select(Project).where(Project.project_id == project_id)
            result = await db.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                raise ValueError("项目不存在")
            
            # 2. 更新状态和意见
            project.state = state
            project.review = review
            
            # 如果审核不通过，通常不需要设置时间；如果通过，保持原有的时间即可。
            # 这里逻辑很简单，直接更新字段
            
            db.add(project)
            await db.commit()
            await db.refresh(project)
            
            return {
                "project_id": project.project_id,
                "state": project.state,
                "review": project.review
            }
            
        except Exception as e:
            # 如果不是 ValueError，说明是数据库错误，回滚
            if not isinstance(e, ValueError):
                await db.rollback()
                logger.error(f"审核项目失败: {e}", exc_info=True)
            raise e

    async def toggle_recruiting(self, db: AsyncSession, project_id: str, user: User, is_recruiting: bool) -> dict:
        """
        切换招募状态
        
        Args:
            project_id: 项目业务ID
            user: 当前操作用户
            is_recruiting: 目标状态
        """
        try:
            # 1. 查找项目
            stmt = select(Project).where(Project.project_id == project_id)
            result = await db.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                raise ValueError("项目不存在")
            
            # 2. 权限校验: 或者是负责人，或者是管理员(Role>=1)
            is_leader = (project.leader_id == user.id)
            is_admin = (user.role >= 1)
            
            if not (is_leader or is_admin):
                raise PermissionError("权限不足: 仅限负责人或管理员操作")

            # 3. 更新状态
            project.is_recruiting = is_recruiting
            
            db.add(project)
            await db.commit()
            await db.refresh(project)
            
            logger.info(f"项目 {project_id} 招募状态更新为: {is_recruiting} (Operator: {user.userid})")
            
            return {
                "project_id": project.project_id,
                "is_recruiting": project.is_recruiting
            }
            
        except Exception as e:
            if not isinstance(e, (ValueError, PermissionError)):
                await db.rollback()
                logger.error(f"切换招募状态失败: {e}", exc_info=True)
            raise e
        
    def _generate_material_id(self) -> str:
        """
        生成材料业务ID: MAT + 时间戳 + 随机数
        """
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d%H%M%S%f")[:-3]
        random_suffix = f"{random.randint(0,999):03d}"
        return f"MAT{timestamp}_{random_suffix}"
    
    async def upload_material(self, db: AsyncSession, project_id: str, user: User, file_data: bytes, filename: str, content_type: str) -> dict:
        """
        上传结项材料
        """
        try:
            # 1. 校验项目
            stmt = select(Project).where(Project.project_id == project_id)
            result = await db.execute(stmt)
            project = result.scalar_one_or_none()
            
            if not project:
                raise ValueError("项目不存在")
            
            if project.leader_id != user.id:
                raise PermissionError("仅项目负责人可上传材料")
                
            # 状态检查：必须是 '进行中(1)' 或者 '驳回待修改(2)' (视具体业务而定，通常是进行中)
            if project.state != 1: 
                raise ValueError("当前项目状态不允许上传材料 (非进行中)")

            # 2. 上传到 MinIO (使用 MATERIALS 私有桶)
            # 命名策略: projects/{project_id}/{timestamp}_{filename}
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            safe_filename = f"projects/{project.project_id}/{timestamp}_{filename}"
            
            upload_success = minio_client.upload_file(
                file_data,
                safe_filename,
                content_type=content_type,
                bucket_type="MATERIALS" # [关键] 指定私有桶
            )
            
            if not upload_success:
                raise Exception("MinIO 上传失败")
            
            # 3. [验证环节] 立即生成一个预签名 URL 返回给前端，用于确认文件是否可访问
            # 有效期 1 小时
            url_res = minio_client.get_file(safe_filename, bucket_type="MATERIALS")
            preview_url = url_res.get("url", "")

            # 4. 写入数据库
            mat_id = self._generate_material_id() # 生成业务ID

            new_material = ProjectMaterial(
                project_id=project.id,
                material_id=mat_id,
                file_name=safe_filename,
                file_type=content_type,
                description=filename # 暂存原文件名
            )
            db.add(new_material)
            await db.commit()
            await db.refresh(new_material)
            
            return {
                "material_id": new_material.material_id,
                "file_name": new_material.file_name,
                "original_name": filename,
                "url": preview_url # [测试用] 此时你可以直接点击这个链接测试访问
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"上传材料失败: {e}", exc_info=True)
            raise e
        
    async def delete_material(self, db: AsyncSession, material_id: str, user: User) -> bool:
        """
        删除单条项目材料 (根据业务ID)
        """
        try:
            # 1. 根据 material_id 查找材料记录
            stmt = select(ProjectMaterial).where(ProjectMaterial.material_id == material_id)
            result = await db.execute(stmt)
            material = result.scalar_one_or_none()
            
            if not material:
                raise ValueError("文件记录不存在")
            
            # 2. 查找关联项目以验证权限
            stmt_proj = select(Project).where(Project.id == material.project_id)
            result_proj = await db.execute(stmt_proj)
            project = result_proj.scalar_one_or_none()
            
            if not project or project.leader_id != user.id:
                raise PermissionError("仅项目负责人可删除文件")
            if project.state != 1:
                raise ValueError("当前项目状态不允许删除文件")

            # 3. 从 MinIO 移除
            try:
                minio_client.client.remove_object(
                    "makershub-materials", 
                    material.file_name
                )
                logger.info(f"MinIO 文件删除成功: {material.file_name}")
            except Exception as minio_e:
                # 即使 MinIO 删失败（比如文件本来就不在），也要继续删数据库，保证数据一致性
                logger.warning(f"MinIO 文件删除异常（可能已丢失）: {minio_e}")

            # 4. 删 DB
            await db.delete(material)
            await db.commit()
            
            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"删除材料失败: {e}", exc_info=True)
            raise e

    async def clear_project_materials(self, db: AsyncSession, project_id: str, user: User) -> int:
        """
        清空项目的所有结项材料 (用于重新提交前的清理)
        """
        try:
            # 1. 校验项目
            stmt = select(Project).where(Project.project_id == project_id)
            result = await db.execute(stmt)
            project = result.scalar_one_or_none()
            
            if not project:
                raise ValueError("项目不存在")
            
            if project.leader_id != user.id:
                raise PermissionError("仅项目负责人可操作")
                
            # 只有 '进行中(1)' 的项目可以清理材料，'待审核(3)' 或 '已结束' 的不能动
            if project.state != 1:
                raise ValueError("当前项目状态不允许清空材料")

            # 2. 查询所有文件 (为了删 MinIO)
            stmt_files = select(ProjectMaterial).where(ProjectMaterial.project_id == project.id)
            result_files = await db.execute(stmt_files)
            materials = result_files.scalars().all()
            
            if not materials:
                return 0

            # 3. 物理删除 MinIO 文件
            # 即使某个文件删失败也不阻断流程，数据库一定要删干净
            for mat in materials:
                try:
                    minio_client.client.remove_object(
                        "makershub-materials", 
                        mat.file_name
                    )
                except Exception as e:
                    logger.warning(f"MinIO 删除残留文件失败: {mat.file_name}, error: {e}")

            # 4. 数据库删除
            stmt_del = delete(ProjectMaterial).where(ProjectMaterial.project_id == project.id)
            await db.execute(stmt_del)
            await db.commit()
            
            logger.info(f"项目 {project_id} 材料已清空，共删除 {len(materials)} 个文件")
            return len(materials)

        except Exception as e:
            await db.rollback()
            logger.error(f"清空材料失败: {e}", exc_info=True)
            raise e

    async def submit_closure(self, db: AsyncSession, project_id: str, user: User, finish_description: str) -> dict:
        """
        提交结项申请
        """
        try:
            # 1. 校验项目
            stmt = select(Project).where(Project.project_id == project_id)
            result = await db.execute(stmt)
            project = result.scalar_one_or_none()
            
            if not project:
                raise ValueError("项目不存在")
                
            if project.leader_id != user.id:
                raise PermissionError("仅项目负责人可提交结项")
            
            if project.state != 1:
                raise ValueError("当前项目状态无法提交结项")

            # 2. [关键检查] 检查数据库中是否已存在该项目的文件记录
            # 使用 func.count 进行统计
            stmt_count = select(func.count()).select_from(ProjectMaterial).where(ProjectMaterial.project_id == project.id)
            result_count = await db.execute(stmt_count)
            count = result_count.scalar()
            
            if count == 0:
                raise ValueError("请至少上传一份结项材料后再次提交")

            # 3. 更新状态
            project.state = 3 # 3=待结项审核
            project.finish_description = finish_description
            
            db.add(project)
            await db.commit()
            await db.refresh(project)
            
            return {
                "project_id": project.project_id,
                "state": project.state,
                "updated_at": project.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            if not isinstance(e, (ValueError, PermissionError)):
                await db.rollback()
                logger.error(f"提交结项失败: {e}", exc_info=True)
            raise e
        
    async def update_project(self, db: AsyncSession, project_id: str, user: User, update_data: dict) -> dict:
        """
        更新项目立项信息
        """
        try:
            # 1. 查找项目
            stmt = select(Project).where(Project.project_id == project_id)
            result = await db.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                raise ValueError("项目不存在")
            
            # 2. 权限校验
            if project.leader_id != user.id:
                raise PermissionError("仅项目负责人可修改申请")
            
            # 3. 状态校验: 只有 0(待审核) 或 2(已驳回) 可以改
            # 1(进行中), 3(待结项), 4(已结束) 都不允许改基础信息
            if project.state not in [0, 2]:
                raise ValueError("当前项目状态不允许修改立项信息")

            # 4. 执行更新
            for field, value in update_data.items():
                if hasattr(project, field):
                    setattr(project, field, value)
            
            # 5. [关键] 重置状态为 0 (待审核)
            # 无论是修改了草稿，还是修改了被驳回的项目，都需要管理员重新审核
            project.state = 0
            
            # 如果之前有审核意见，建议清空吗？通常保留历史意见给管理员参考比较好，这里暂时不自动清空 review
            
            db.add(project)
            await db.commit()
            await db.refresh(project)
            
            logger.info(f"项目 {project_id} 立项信息已更新并重置为待审核状态")
            
            # 返回用户修改的那些字段
            return update_data

        except Exception as e:
            if not isinstance(e, (ValueError, PermissionError)):
                await db.rollback()
                logger.error(f"更新项目失败: {e}", exc_info=True)
            raise e

    async def cleanup_zombie_materials(self, db: AsyncSession) -> int:
        """
        [后台任务专用] 清理僵尸材料
        
        逻辑：
        1. 筛选条件：
           - 项目状态 = 1 (进行中，说明还没提交结项)
           - 材料创建时间 < 当前时间 - 24小时 (说明用户上传后晾了一天没动)
        2. 执行操作：
           - 从 MinIO 物理删除
           - 从数据库删除记录
        """
        try:
            # 定义过期时间：24小时前
            deadline = datetime.now() - timedelta(hours=24)
            
            # 构造查询：关联 Project 表，筛选符合条件的材料
            stmt = select(ProjectMaterial).join(
                Project, ProjectMaterial.project_id == Project.id
            ).where(
                Project.state == 1,
                ProjectMaterial.created_at < deadline
            )
            
            result = await db.execute(stmt)
            zombies = result.scalars().all()
            
            if not zombies:
                return 0
                
            count = 0
            for mat in zombies:
                # 1. 删 MinIO (容错处理，即使文件不在了也不影响删库)
                try:
                    minio_client.client.remove_object(
                        "makershub-materials", # 对应的桶名
                        mat.file_name
                    )
                except Exception as e:
                    logger.warning(f"清理僵尸文件 MinIO 删除失败: {mat.file_name}, error: {e}")

                # 2. 删 DB
                await db.delete(mat)
                count += 1
            
            # 注意：这里不需要 commit，因为 tasks.py 会在最外层统一 commit
            # 但为了保险起见（防止 tasks 逻辑有变），service 层 flush 一下也可以
            await db.flush()
            
            if count > 0:
                logger.info(f"后台任务：已清理 {count} 个项目部僵尸文件")
            
            return count
            
        except Exception as e:
            logger.error(f"僵尸文件清理逻辑异常: {e}", exc_info=True)
            # 抛出异常由 tasks.py 捕获，避免中断整个循环
            raise e