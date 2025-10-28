# app/services/admin_user_service.py
"""
管理员用户服务层，处理管理员端用户管理的业务逻辑。
[v2.0 SQLAlchemy 迁移版]
"""
from typing import Dict, Any
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.user import User
from app.core.storage import minio_client

class AdminUserService:
    """管理员用户服务类：处理管理员端用户相关的业务逻辑。"""
    
    @staticmethod
    def _get_department_text(department: int) -> str:
        department_map = {0: "基地管理部", 1: "宣传部", 2: "运维部", 3: "项目部", 4: "副会长", 5: "会长", 999: "未分配"}
        return department_map.get(department, "未知")
    
    @staticmethod
    def _user_to_admin_dict(user: User) -> dict:
        """辅助函数：将User ORM对象转换为管理员视图的字典，并处理头像URL。"""
        user_data = {
            'userid': user.userid,
            'maker_id': user.maker_id,
            'real_name': user.real_name or "未设置",
            'phone_num': user.phone_num or "",
            'role': user.role,
            'role_text': ['普通用户', '干事', '部长及以上'][user.role] if user.role in [0, 1, 2] else '未知',
            'department': user.department,
            'department_text': AdminUserService._get_department_text(user.department),
            'state': user.state,
            'state_text': '正常' if user.state == 1 else '封禁',
            'motto': user.motto or "",
            'score': user.score,
            'total_dutytime': user.total_dutytime,
            'created_at': user.created_at.isoformat() + "Z" if user.created_at else None,
            'updated_at': user.updated_at.isoformat() + "Z" if user.updated_at else None,
            'profile_photo': "" # 默认空
        }
        if user.profile_photo:
            try:
                photo_result = minio_client.get_file(user.profile_photo, bucket_type="AVATARS")
                user_data['profile_photo'] = photo_result.get("url", "")
            except Exception as e:
                logger.warning(f"获取用户 {user.userid} 头像失败: {e}")
        return user_data

    @staticmethod
    async def get_all_users_admin(db: AsyncSession, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        获取所有用户（管理员视图），支持筛选和搜索。
        """
        try:
            stmt = select(User).order_by(User.created_at.desc())
            
            if filters:
                if filters.get('role') is not None:
                    stmt = stmt.where(User.role == int(filters['role']))
                if filters.get('state') is not None:
                    stmt = stmt.where(User.state == int(filters['state']))
                if filters.get('department') is not None:
                    stmt = stmt.where(User.department == int(filters['department']))
                if filters.get('search'):
                    search_term = f"%{filters['search']}%"
                    stmt = stmt.where(or_(User.real_name.ilike(search_term), User.phone_num.ilike(search_term)))

            result = await db.execute(stmt)
            all_users = result.scalars().all()
            
            users_list = [AdminUserService._user_to_admin_dict(user) for user in all_users]
            
            stats = {
                'total_users': len(users_list),
                'active_users': sum(1 for u in users_list if u['state'] == 1),
                'banned_users': sum(1 for u in users_list if u['state'] == 0),
                'normal_users': sum(1 for u in users_list if u['role'] == 0),
                'staff_users': sum(1 for u in users_list if u['role'] == 1),
                'manager_users': sum(1 for u in users_list if u['role'] == 2)
            }
            
            department_stats = {}
            for user_data in users_list:
                dept_text = user_data['department_text']
                department_stats[dept_text] = department_stats.get(dept_text, 0) + 1
            
            return {
                "code": 200, "message": "获取用户列表成功",
                "data": {"users_list": users_list, "stats": stats, "department_stats": department_stats}
            }
        except Exception as e:
            logger.error(f"获取管理员用户列表失败: {e}", exc_info=True)
            raise e

    @staticmethod
    async def update_user_info_by_admin(db: AsyncSession, userid: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        由管理员更新指定用户的多个信息。
        """
        try:
            stmt = select(User).where(User.userid == userid)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                raise ValueError(f"用户不存在: {userid}")

            changes = []
            for field, value in update_data.items():
                if hasattr(user, field):
                    old_value = getattr(user, field)
                    if old_value != value:
                        setattr(user, field, value)
                        changes.append(f"{field}: {old_value} -> {value}")
            
            if not changes:
                 return {"code": 200, "message": "没有需要更新的字段", "data": {"userid": userid, "changes": []}}

            db.add(user)
            await db.commit()
            
            logger.info(f"管理员更新用户信息成功 | userid: {userid} | 变更: {', '.join(changes)}")
            return {"code": 200, "message": "用户信息更新成功", "data": {"userid": userid, "changes": changes}}
        except Exception as e:
            await db.rollback()
            logger.error(f"管理员更新用户信息失败: {e}", exc_info=True)
            raise e

    @staticmethod
    async def get_user_detail_by_admin(db: AsyncSession, userid: str) -> Dict[str, Any]:
        """
        由管理员获取指定用户的详细信息。
        """
        try:
            stmt = select(User).where(User.userid == userid)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            if not user:
                raise ValueError(f"用户不存在: {userid}")
            
            detail_data = AdminUserService._user_to_admin_dict(user)
            return {"code": 200, "message": "获取用户详情成功", "data": detail_data}
        except Exception as e:
            logger.error(f"管理员获取用户详情失败: {e}", exc_info=True)
            raise e