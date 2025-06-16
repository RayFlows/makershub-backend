"""
任务路由模块 (Task Router Module)
"""

from fastapi import APIRouter, HTTPException, Depends, Path, Body
from loguru import logger
from app.services.task_service import TaskService
from app.core.auth import require_permission_level
from pydantic import BaseModel
from app.core import utils  # 导入utils模块

router = APIRouter()
task_service = TaskService()

class TaskCreateRequest(BaseModel):
    """任务创建请求模型"""
    department: str
    task_name: str
    name: str  # 负责人姓名
    content: str
    deadline: str  # ISO 8601格式时间字符串

@router.post("/post/{maker_id}")
async def create_task(
    maker_id: str = Path(..., description="负责人协会ID"),
    task_request: TaskCreateRequest = Body(...),
    current_user: dict = Depends(require_permission_level(2))  # 权限依赖
):
    """
    创建新任务 (POST /tasks/post/{maker_id})
    
    权限要求: 部长及以上(2)
    
    Args:
        maker_id: 负责人协会ID (路径参数)
        task_request: 任务创建请求数据 (请求体)
        
    Returns:
        dict: 包含任务ID的响应
    """
    try:
        # 验证截止时间格式
        deadline_str = task_request.deadline
        if not deadline_str:
            return {
                "code": 400,
                "message": "缺少截止时间字段"
            }
        
        # 使用utils中的parse_datetime函数验证时间格式
        if utils.parse_datetime(deadline_str) is None:
            return {
                "code": 400,
                "message": "无效的截止时间格式"
            }
        
        # 调用服务创建任务
        result = task_service.create_task(
            maker_id=maker_id,
            task_data=task_request.dict()
        )
        
        if result.get("success"):
            return {
                "code": 200,
                "message": "successfully post a new task",
                "data": {
                    "task_id": result["task_id"]
                }
            }
        else:
            error_code = result.get("code", 500)
            error_message = result.get("error", "创建任务失败")
            raise HTTPException(
                status_code=error_code,
                detail={
                    "code": error_code,
                    "message": error_message
                }
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"创建任务失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "服务器内部错误"
            }
        )

@router.post("/cancel/{task_id}")
async def cancel_task(
    task_id: str = Path(..., description="任务ID"),
    current_user: dict = Depends(require_permission_level(2))  # 权限依赖
):
    """
    取消已发布的任务 (POST /tasks/cancel/{task_id})
    
    权限要求: 部长及以上(2)
    
    Args:
        task_id: 任务ID (路径参数)
        
    Returns:
        dict: 包含取消操作结果的响应
    """
    try:
        # 调用服务取消任务
        result = task_service.cancel_task(task_id)
        
        if result.get("success"):
            return {
                "code": 200,
                "message": "successfully canceled a task",
                "data": {
                    "task_id": result["task_id"],
                    "state": result["state"]
                }
            }
        else:
            error_code = result.get("code", 500)
            error_message = result.get("error", "取消任务失败")
            raise HTTPException(
                status_code=error_code,
                detail={
                    "code": error_code,
                    "message": error_message
                }
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"取消任务失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "服务器内部错误"
            }
        )