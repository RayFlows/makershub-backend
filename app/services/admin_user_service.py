# app/services/admin_user_service.py
"""
管理员用户服务层
处理管理员端用户管理的业务逻辑
"""

from typing import List, Dict, Any, Optional
from app.models.user import User
from mongoengine.errors import NotUniqueError, ValidationError
from app.core.logging import logger
from datetime import datetime
from app.core.db import minio_client

class AdminUserService:
    """管理员用户服务类：处理管理员端用户相关的业务逻辑"""
    
    @staticmethod
    def get_all_users_admin(filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        获取所有用户（管理员视图）
        
        Args:
            filters: 筛选条件
                - role: 用户角色 (0=普通用户, 1=干事, 2=部长及以上)
                - state: 用户状态 (0=封禁, 1=正常)
                - department: 部门 (0-5, 999)
                - search: 搜索关键字（姓名、手机号）
        
        Returns:
            Dict: 包含用户列表和统计信息
        """
        try:
            logger.info(f"[AdminUserService] 开始获取用户列表，筛选条件: {filters}")
            
            # 构建查询条件
            query = {}
            if filters:
                if filters.get('role') is not None:
                    query['role'] = int(filters['role'])
                    logger.debug(f"添加角色筛选: {filters['role']}")
                
                if filters.get('state') is not None:
                    query['state'] = int(filters['state'])
                    logger.debug(f"添加状态筛选: {filters['state']}")
                
                if filters.get('department') is not None:
                    query['department'] = int(filters['department'])
                    logger.debug(f"添加部门筛选: {filters['department']}")
                
                if filters.get('search'):
                    # 模糊搜索真实姓名或手机号
                    from mongoengine.queryset.visitor import Q
                    search_term = filters['search']
                    query_obj = Q(real_name__icontains=search_term) | Q(phone_num__icontains=search_term)
                    users_query = User.objects(query_obj, **query)
                else:
                    users_query = User.objects(**query)
            else:
                users_query = User.objects()
            
            # 执行查询
            all_users = users_query.order_by('-created_at')
            logger.info(f"查询到 {len(all_users)} 个用户")
            
            # 转换为字典列表
            users_list = []
            for user in all_users:
                user_data = {
                    'userid': user.userid,
                    'maker_id': user.maker_id,
                    'real_name': user.real_name or "未设置",
                    'phone_num': user.phone_num or "",
                    'role': user.role,
                    'role_text': ['普通用户', '干事', '部长及以上'][user.role] if user.role <= 2 else '未知',
                    'department': user.department,
                    'department_text': AdminUserService._get_department_text(user.department),
                    'state': user.state,
                    'state_text': '正常' if user.state == 1 else '封禁',
                    'motto': user.motto or "",
                    'score': user.score,
                    'total_dutytime': user.total_dutytime,
                    'created_at': user.created_at.isoformat() + "Z" if user.created_at else None,
                    'updated_at': user.updated_at.isoformat() + "Z" if user.updated_at else None
                }
                
                # 处理头像URL
                if user.profile_photo:
                    try:
                        photo_result = minio_client.get_file(
                            user.profile_photo,
                            expire_seconds=3600,
                            bucket_type="AVATARS"
                        )
                        user_data['profile_photo'] = photo_result.get("url", "")
                    except Exception as e:
                        logger.warning(f"获取用户头像失败: {e}")
                        user_data['profile_photo'] = ""
                else:
                    user_data['profile_photo'] = ""
                
                users_list.append(user_data)
            
            # 统计信息
            stats = {
                'total_users': len(users_list),
                'active_users': sum(1 for u in users_list if u['state'] == 1),
                'banned_users': sum(1 for u in users_list if u['state'] == 0),
                'normal_users': sum(1 for u in users_list if u['role'] == 0),
                'staff_users': sum(1 for u in users_list if u['role'] == 1),
                'manager_users': sum(1 for u in users_list if u['role'] == 2)
            }
            
            # 部门分布统计
            department_stats = {}
            for user in users_list:
                dept = user['department_text']
                department_stats[dept] = department_stats.get(dept, 0) + 1
            
            logger.info(f"[AdminUserService] 用户列表获取成功，返回 {len(users_list)} 个用户")
            
            return {
                "code": 200,
                "message": "获取用户列表成功",
                "data": {
                    "users_list": users_list,
                    "stats": stats,
                    "department_stats": department_stats
                }
            }
            
        except Exception as e:
            logger.error(f"[AdminUserService] 获取用户列表失败: {str(e)}", exc_info=True)
            raise Exception(f"获取用户列表失败: {str(e)}")
    
    @staticmethod
    def update_user_role(userid: str, role: int) -> Dict[str, Any]:
        """
        更新用户角色
        
        Args:
            userid: 用户ID（openid）
            role: 新角色 (0=普通用户, 1=干事, 2=部长及以上)
        
        Returns:
            Dict: 更新结果
        """
        try:
            logger.info(f"[AdminUserService] 开始更新用户角色: userid={userid}, role={role}")
            
            # 验证角色值
            if role not in [0, 1, 2]:
                raise ValueError("无效的角色值，必须为 0, 1 或 2")
            
            # 查找用户
            user = User.objects(userid=userid).first()
            if not user:
                logger.warning(f"[AdminUserService] 用户不存在: {userid}")
                raise ValueError(f"用户不存在: {userid}")
            
            # 记录原始角色
            old_role = user.role
            old_role_text = ['普通用户', '干事', '部长及以上'][old_role] if old_role <= 2 else '未知'
            new_role_text = ['普通用户', '干事', '部长及以上'][role]
            
            # 更新角色
            user.role = role
            user.save()
            
            logger.info(f"[AdminUserService] 用户角色更新成功 | userid: {userid} | "
                       f"角色: {old_role_text} -> {new_role_text}")
            
            return {
                "code": 200,
                "message": "用户角色更新成功",
                "data": {
                    "userid": userid,
                    "old_role": old_role,
                    "new_role": role,
                    "role_text": new_role_text
                }
            }
            
        except ValueError as e:
            raise e
        except Exception as e:
            logger.error(f"[AdminUserService] 更新用户角色失败: {str(e)}", exc_info=True)
            raise Exception(f"更新用户角色失败: {str(e)}")
    
    @staticmethod
    def update_user_state(userid: str, state: int) -> Dict[str, Any]:
        """
        更新用户状态（封禁/解封）
        
        Args:
            userid: 用户ID（openid）
            state: 新状态 (0=封禁, 1=正常)
        
        Returns:
            Dict: 更新结果
        """
        try:
            logger.info(f"[AdminUserService] 开始更新用户状态: userid={userid}, state={state}")
            
            # 验证状态值
            if state not in [0, 1]:
                raise ValueError("无效的状态值，必须为 0 或 1")
            
            # 查找用户
            user = User.objects(userid=userid).first()
            if not user:
                logger.warning(f"[AdminUserService] 用户不存在: {userid}")
                raise ValueError(f"用户不存在: {userid}")
            
            # 记录原始状态
            old_state = user.state
            old_state_text = '正常' if old_state == 1 else '封禁'
            new_state_text = '正常' if state == 1 else '封禁'
            
            # 更新状态
            user.state = state
            user.save()
            
            logger.info(f"[AdminUserService] 用户状态更新成功 | userid: {userid} | "
                       f"状态: {old_state_text} -> {new_state_text}")
            
            return {
                "code": 200,
                "message": f"用户已{'解封' if state == 1 else '封禁'}",
                "data": {
                    "userid": userid,
                    "old_state": old_state,
                    "new_state": state,
                    "state_text": new_state_text
                }
            }
            
        except ValueError as e:
            raise e
        except Exception as e:
            logger.error(f"[AdminUserService] 更新用户状态失败: {str(e)}", exc_info=True)
            raise Exception(f"更新用户状态失败: {str(e)}")
    
    @staticmethod
    def update_user_info(userid: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新用户信息（管理员）
        
        Args:
            userid: 用户ID
            update_data: 更新数据（可包含role, state, department, score等）
        
        Returns:
            Dict: 更新结果
        """
        try:
            logger.info(f"[AdminUserService] 开始更新用户信息: userid={userid}")
            logger.debug(f"更新数据: {update_data}")
            
            # 查找用户
            user = User.objects(userid=userid).first()
            if not user:
                logger.warning(f"[AdminUserService] 用户不存在: {userid}")
                raise ValueError(f"用户不存在: {userid}")
            
            # 记录变更
            changes = []
            
            # 更新各字段
            if 'role' in update_data:
                old_role = user.role
                user.role = int(update_data['role'])
                changes.append(f"角色: {old_role} -> {user.role}")
            
            if 'state' in update_data:
                old_state = user.state
                user.state = int(update_data['state'])
                changes.append(f"状态: {old_state} -> {user.state}")
            
            if 'department' in update_data:
                old_dept = user.department
                user.department = int(update_data['department'])
                changes.append(f"部门: {old_dept} -> {user.department}")
            
            if 'score' in update_data:
                old_score = user.score
                user.score = int(update_data['score'])
                changes.append(f"积分: {old_score} -> {user.score}")
            
            if 'total_dutytime' in update_data:
                old_time = user.total_dutytime
                user.total_dutytime = int(update_data['total_dutytime'])
                changes.append(f"值班时长: {old_time} -> {user.total_dutytime}")
            
            # 保存更新
            user.save()
            
            if changes:
                logger.info(f"[AdminUserService] 用户信息更新成功 | userid: {userid} | 变更: {', '.join(changes)}")
            
            return {
                "code": 200,
                "message": "用户信息更新成功",
                "data": {
                    "userid": userid,
                    "changes": changes
                }
            }
            
        except ValueError as e:
            raise e
        except Exception as e:
            logger.error(f"[AdminUserService] 更新用户信息失败: {str(e)}", exc_info=True)
            raise Exception(f"更新用户信息失败: {str(e)}")
    
    @staticmethod
    def get_user_detail(userid: str) -> Dict[str, Any]:
        """
        获取用户详细信息
        
        Args:
            userid: 用户ID
        
        Returns:
            Dict: 用户详细信息
        """
        try:
            logger.info(f"[AdminUserService] 获取用户详细信息: {userid}")
            
            user = User.objects(userid=userid).first()
            if not user:
                raise ValueError(f"用户不存在: {userid}")
            
            # 构建详细信息
            detail = {
                'userid': user.userid,
                'maker_id': user.maker_id,
                'real_name': user.real_name or "未设置",
                'phone_num': user.phone_num or "",
                'role': user.role,
                'role_text': ['普通用户', '干事', '部长及以上'][user.role] if user.role <= 2 else '未知',
                'department': user.department,
                'department_text': AdminUserService._get_department_text(user.department),
                'state': user.state,
                'state_text': '正常' if user.state == 1 else '封禁',
                'motto': user.motto or "",
                'score': user.score,
                'total_dutytime': user.total_dutytime,
                'created_at': user.created_at.isoformat() + "Z" if user.created_at else None,
                'updated_at': user.updated_at.isoformat() + "Z" if user.updated_at else None
            }
            
            # 处理头像
            if user.profile_photo:
                try:
                    photo_result = minio_client.get_file(
                        user.profile_photo,
                        expire_seconds=3600,
                        bucket_type="AVATARS"
                    )
                    detail['profile_photo'] = photo_result.get("url", "")
                except Exception as e:
                    logger.warning(f"获取用户头像失败: {e}")
                    detail['profile_photo'] = ""
            else:
                detail['profile_photo'] = ""
            
            return {
                "code": 200,
                "message": "获取用户详情成功",
                "data": detail
            }
            
        except ValueError as e:
            raise e
        except Exception as e:
            logger.error(f"[AdminUserService] 获取用户详情失败: {str(e)}", exc_info=True)
            raise Exception(f"获取用户详情失败: {str(e)}")
    
    @staticmethod
    def _get_department_text(department: int) -> str:
        """
        获取部门文本
        
        Args:
            department: 部门编号
        
        Returns:
            str: 部门名称
        """
        department_map = {
            0: "基地管理部",
            1: "宣传部",
            2: "运维部",
            3: "项目部",
            4: "副会长",
            5: "会长",
            999: "未分配"
        }
        return department_map.get(department, "未知")