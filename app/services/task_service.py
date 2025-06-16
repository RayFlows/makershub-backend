"""
任务服务模块 (Task Service Module)
"""

from app.models.task import Task
from app.models.user import User
from loguru import logger
from app.core import utils  # 导入utils模块

class TaskService:
    """
    任务服务类
    """
    
    def create_task(self, maker_id: str, task_data: dict) -> dict:
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
            
            # 解析截止时间
            deadline_str = task_data.get("deadline")
            if not deadline_str:
                return {
                    "success": False,
                    "error": "缺少截止时间字段",
                    "code": 400
                }
            
            # 使用utils中的parse_datetime函数解析时间
            deadline = utils.parse_datetime(deadline_str)
            if deadline is None:
                logger.error(f"无效的截止时间格式: {deadline_str}")
                return {
                    "success": False,
                    "error": "无效的截止时间格式",
                    "code": 400
                }
            
            # 生成唯一任务ID
            task_id = Task.generate_task_id()
            
            # 创建任务对象
            task = Task(
                task_id=task_id,
                department=task_data["department"],
                task_name=task_data["task_name"],
                userid=user.userid,
                maker_id=maker_id,
                name=task_data["name"],
                content=task_data["content"],
                deadline=deadline  # 使用解析后的datetime对象
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

    def cancel_task(self, task_id: str) -> dict:
        """
        取消已发布的任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            dict: 包含取消操作结果的字典
        """
        try:
            # 查询任务是否存在
            task = Task.objects(task_id=task_id).first()
            if not task:
                logger.error(f"未找到任务ID: {task_id}")
                return {
                    "success": False,
                    "error": "任务不存在",
                    "code": 404
                }
            
            # 检查任务状态，只能取消未完成的任务
            if task.state != 0:
                logger.warning(f"任务状态已为 {task.state}，无法取消")
                return {
                    "success": False,
                    "error": "任务已完成或已取消，无法再次取消",
                    "code": 400
                }
            
            # 更新任务状态为2（已取消）
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