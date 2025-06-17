from fastapi import APIRouter, HTTPException, Depends, Path, Body
from loguru import logger
from app.services.task_service import TaskService
from app.core.auth import require_permission_level
from pydantic import BaseModel
from typing import Optional
from app.core import utils

router = APIRouter()
task_service = TaskService()

class TaskCreateRequest(BaseModel):
    """任务创建请求模型"""
    task_type: int
    name: str
    department: str
    maker_id: str 
    content: str
    deadline: str

class TaskUpdateRequest(BaseModel):
    """任务更新请求模型"""
    task_type: Optional[int] = None
    name: Optional[str] = None
    department: Optional[str] = None
    content: Optional[str] = None
    deadline: Optional[str] = None
    maker_id: Optional[str] = None

@router.post("/post")
async def create_task(
    task_request: TaskCreateRequest = Body(...),
    user: dict = Depends(require_permission_level(2))  # 需要权限2
):
    """创建新任务"""
    try:
        # 调用服务创建任务
        result = await task_service.create_task(task_request.maker_id, task_request.dict())
        
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
        raise HTTPException(status_code=500, detail="创建任务失败")
@router.patch("/cancel/{task_id}")
async def cancel_task(
    task_id: str = Path(..., description="任务ID"),
    user: dict = Depends(require_permission_level(2))  # 需要权限2
):
    """取消任务"""
    try:
        # 调用服务取消任务
        result = await task_service.cancel_task(task_id)
        
        if result.get("success"):
            return {
                "code": 200,
                "message": "successfully cancel task",
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
        raise HTTPException(status_code=500, detail="取消任务失败")

@router.patch("/finish/{task_id}")
async def finish_task(
    task_id: str = Path(..., description="任务ID"),
    user: dict = Depends(require_permission_level(1))  # 需要权限1或2
):
    """完成任务"""
    try:
        # 调用服务完成任务
        result = await task_service.finish_task(task_id)
        
        if result.get("success"):
            return {
                "code": 200,
                "message": "successfully finish a task",
                "data": {
                    "task_id": result["task_id"],
                    "state": result["state"]
                }
            }
        else:
            error_code = result.get("code", 500)
            error_message = result.get("error", "完成任务失败")
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
        logger.error(f"完成任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail="完成任务失败")

@router.patch("/update/{task_id}")
async def update_task(
    task_id: str = Path(..., description="任务ID"),
    update_data: TaskUpdateRequest = Body(...),
    user: dict = Depends(require_permission_level(2))  # 需要权限2
):
    """更新任务"""
    try:
        # 转换为字典并移除空值
        update_dict = update_data.dict(exclude_unset=True)
        
        # 调用服务更新任务
        result = await task_service.update_task(task_id, update_dict)
        
        if result.get("success"):
            # 重新获取任务详情
            detail_result = await task_service.get_task_detail(task_id)
            if detail_result.get("success"):
                return {
                    "code": 200,
                    "message": "successfully update task",
                    "data": detail_result["task"]
                }
            else:
                return {
                    "code": 200,
                    "message": "successfully update task",
                    "data": {"task_id": task_id}
                }
        else:
            error_code = result.get("code", 500)
            error_message = result.get("error", "更新任务失败")
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
        logger.error(f"更新任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新任务失败")

@router.get("/detail/{task_id}")
async def get_task_detail(
    task_id: str = Path(..., description="任务ID"),
    user: dict = Depends(require_permission_level(1))  # 需要权限1或2
):
    """获取任务详情"""
    try:
        # 调用服务获取任务详情
        result = await task_service.get_task_detail(task_id)
        
        if result.get("success"):
            return {
                "code": 200,
                "message": "successfully get task detail",
                "data": result["task"]
            }
        else:
            error_code = result.get("code", 500)
            error_message = result.get("error", "获取任务详情失败")
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
        logger.error(f"获取任务详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取任务详情失败")

@router.get("/view-all")
async def get_all_tasks(
    user: dict = Depends(require_permission_level(2))  # 需要权限2
):
    """获取所有任务"""
    try:
        # 调用服务获取所有任务
        tasks = await task_service.get_all_tasks()
        
        return {
            "code": 200,
            "message": "successfully get all tasks",
            "data": {
                "total": len(tasks),
                "list": tasks
            }
        }
            
    except Exception as e:
        logger.error(f"获取所有任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取所有任务失败")

@router.get("/view-my")
async def get_user_tasks(
    user: dict = Depends(require_permission_level(1))  # 需要权限1或2
):
    """获取用户的任务"""
    try:
        # 调用服务获取用户任务
        tasks = await task_service.get_user_tasks(user)
        
        return {
            "code": 200,
            "message": "successfully get my tasks",
            "data": {
                "total": len(tasks),
                "list": tasks
            }
        }
            
    except Exception as e:
        logger.error(f"获取用户任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户任务失败")