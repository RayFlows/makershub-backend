from app.models.task import Task
from app.models.user import User
from loguru import logger
from app.core import utils
from app.services.arrange_service import ArrangeService

class TaskService:
    """
    任务服务类
    """

    def __init__(self):
        self.arrange_service = ArrangeService()  # 创建排班服务实例
    
    async def create_task(self, maker_id: str, task_data: dict) -> dict:
        """
        创建新任务
        
        Args:
            maker_id: 负责人协会ID
            task_data: 包含任务数据的字典
            
        Returns:
            dict: 包含创建结果和任务ID的字典
        """
        try:
            # 根据协会ID查找负责人
            user = User.objects(maker_id=maker_id).first()
            if not user:
                logger.error(f"未找到协会ID为 {maker_id} 的负责人")
                return {
                    "success": False,
                    "error": "负责人不存在",
                    "code": 404
                }
            
            # 验证请求体中的负责人姓名是否匹配
            if user.real_name != task_data["name"]:
                logger.error(f"姓名不匹配: 请求姓名={task_data['name']}, 实际姓名={user.real_name}")
                return {
                    "success": False,
                    "error": "负责人姓名与协会ID不匹配",
                    "code": 400
                }
            
            # 验证截止时间格式
            deadline_str = task_data.get("deadline")
            if not deadline_str:
                return {
                    "success": False,
                    "error": "缺少截止时间字段",
                    "code": 400
                }
            
            deadline = utils.parse_datetime(deadline_str)
            if deadline is None:
                logger.error(f"无效的截止时间格式: {deadline_str}")
                return {
                    "success": False,
                    "error": "无效的截止时间格式",
                    "code": 400
                }
            
            # 对于特定任务类型，自动分配当前值班人员
            task_type = task_data.get("task_type")
            if task_type in [1, 2, 3]:
                current_arranger = await self.arrange_service.get_current_arranger(task_type)
                if current_arranger:
                    # 使用排班系统中的当前值班人员
                    task_data["name"] = current_arranger["name"]
                    maker_id = current_arranger["maker_id"]
                    logger.info(f"自动分配任务给值班人员 | 类型: {task_type} | 姓名: {current_arranger['name']} | ID: {maker_id}")
                    
                    # 切换到下一个值班人员
                    switch_success = await self.arrange_service.switch_to_next_arranger(task_type)
                    if not switch_success:
                        logger.error(f"任务创建成功，但排班切换失败 | 类型: {task_type}")
                else:
                    logger.warning(f"未找到任务类型 {task_type} 的当前值班人员，使用原始分配")
            
            # 生成唯一任务ID
            task_id = Task.generate_task_id()
            
            # 创建任务对象
            task = Task(
                task_id=task_id,
                department=task_data["department"],
                task_type=task_type,
                maker_id=maker_id,
                name=task_data["name"],
                content=task_data["content"],
                deadline=deadline,
                state=0  # 初始状态为未完成
            )
            
            # 保存到数据库
            task.save()
            
            logger.info(f"任务创建成功: {task_id}")
            return {
                "success": True,
                "task_id": task_id
            }
            
        except Exception as e:
            logger.error(f"创建任务失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "code": 500
            }

    async def cancel_task(self, task_id: str) -> dict:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            dict: 包含取消操作结果的字典
        """
        try:
            # 查询任务
            task = Task.objects(task_id=task_id).first()
            if not task:
                logger.error(f"未找到任务ID: {task_id}")
                return {
                    "success": False,
                    "error": "任务不存在",
                    "code": 404
                }
            
            # 检查任务状态
            if task.state == 1:  # 已完成
                logger.error(f"不能取消已完成的任务: {task_id}")
                return {
                    "success": False,
                    "error": "已完成的任务不能被取消",
                    "code": 400
                }
            elif task.state == 2:  # 已取消
                logger.warning(f"任务已取消，无需重复操作: {task_id}")
                return {
                    "success": True,
                    "task_id": task_id,
                    "state": 2
                }

            # 更新任务状态为已取消
            task.state = 2
            task.save()
            
            logger.info(f"任务已取消: {task_id}")
            return {
                "success": True,
                "task_id": task_id,
                "state": 2
            }
            
        except Exception as e:
            logger.error(f"取消任务失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "code": 500
            }
    
    async def finish_task(self, task_id: str) -> dict:
        """
        完成任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            dict: 包含完成操作结果的字典
        """
        try:
            # 查询任务
            task = Task.objects(task_id=task_id).first()
            if not task:
                logger.error(f"未找到任务ID: {task_id}")
                return {
                    "success": False,
                    "error": "任务不存在",
                    "code": 404
                }
            
            # 检查任务状态
            if task.state == 2:  # 已取消
                logger.error(f"不能完成已取消的任务: {task_id}")
                return {
                    "success": False,
                    "error": "已取消的任务不能被完成",
                    "code": 400
                }
            elif task.state == 1:  # 已完成
                logger.warning(f"任务已完成，无需重复操作: {task_id}")
                return {
                    "success": True,
                    "task_id": task_id,
                    "state": 1
                }

            # 更新任务状态为已完成
            task.state = 1
            task.save()
            
            logger.info(f"任务已完成: {task_id}")
            return {
                "success": True,
                "task_id": task_id,
                "state": 1
            }
            
        except Exception as e:
            logger.error(f"完成任务失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "code": 500
            }
    
    async def update_task(self, task_id: str, update_data: dict) -> dict:
        """
        更新任务
        
        Args:
            task_id: 任务ID
            update_data: 更新数据
            
        Returns:
            dict: 包含更新操作结果的字典
        """
        try:
            # 查询任务
            task = Task.objects(task_id=task_id).first()
            if not task:
                logger.error(f"未找到任务ID: {task_id}")
                return {
                    "success": False,
                    "error": "任务不存在",
                    "code": 404
                }
            
            # 检查任务状态
            if task.state in [0, 1]:  # 已完成或已取消
                logger.error(f"不能更新未完成或已完成的任务: {task_id} | 当前状态: {task.state}")
                return {
                    "success": False,
                    "error": "未完成或已完成的任务不能被更新",
                    "code": 400
                }   

            # 如果有更新负责人信息
            if "maker_id" in update_data or "name" in update_data:
                maker_id = update_data.get("maker_id", task.maker_id)
                name = update_data.get("name", task.name)
                
                # 根据协会ID查找负责人
                user = User.objects(maker_id=maker_id).first()
                if not user:
                    logger.error(f"未找到协会ID为 {maker_id} 的负责人")
                    return {
                        "success": False,
                        "error": "负责人不存在",
                        "code": 404
                    }
                
                # 验证姓名是否匹配
                if user.real_name != name:
                    logger.error(f"姓名不匹配: 请求姓名={name}, 实际姓名={user.real_name}")
                    return {
                        "success": False,
                        "error": "负责人姓名与协会ID不匹配",
                        "code": 400
                    }
                
                # 更新负责人信息
                task.maker_id = maker_id
                task.name = name
            
            # 更新其他字段
            if "department" in update_data:
                task.department = update_data["department"]
            if "task_type" in update_data:
                task.task_type = update_data["task_type"]
            if "content" in update_data:
                task.content = update_data["content"]
            if "deadline" in update_data:
                deadline = utils.parse_datetime(update_data["deadline"])
                if deadline:
                    task.deadline = deadline
            
            # 重置状态为未完成（根据需求文档）
            task.state = 0
            
            task.save()

            # 记录状态变更
            if original_state == 2:  # 原状态是已取消
                logger.info(f"已取消的任务被重新激活: {task_id}")
            
            logger.info(f"任务已更新: {task_id}")
            return {
                "success": True,
                "task_id": task_id
            }
            
        except Exception as e:
            logger.error(f"更新任务失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "code": 500
            }
    
    async def get_task_detail(self, task_id: str) -> dict:
        """
        获取任务详情
        
        Args:
            task_id: 任务ID
            
        Returns:
            dict: 任务详情
        """
        try:
            task = Task.objects(task_id=task_id).first()
            if not task:
                logger.error(f"未找到任务ID: {task_id}")
                return {
                    "success": False,
                    "error": "任务不存在",
                    "code": 404
                }
            
            return {
                "success": True,
                "task": task.to_dict()
            }
            
        except Exception as e:
            logger.error(f"获取任务详情失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "code": 500
            }
    
    async def get_all_tasks(self) -> list:
        """
        获取所有任务
        
        Returns:
            list: 任务列表
        """
        try:
            tasks = Task.objects().order_by("-created_at")
            return [task.to_dict() for task in tasks]
            
        except Exception as e:
            logger.error(f"获取所有任务失败: {str(e)}")
            return []
    
    async def get_user_tasks(self, user: dict) -> list:
        """
        获取用户的所有任务
        
        Args:
            user: 当前用户信息
            
        Returns:
            list: 任务列表
        """
        try:
            # 根据用户ID查找所有该用户负责的任务
            tasks = Task.objects(maker_id=user.maker_id).order_by("-created_at")
            return [task.to_dict() for task in tasks]
            
        except Exception as e:
            logger.error(f"获取用户任务失败: {str(e)}")
            return []