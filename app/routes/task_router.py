# app/routes/task_router.py
"""
任务路由模块 (Task Router Module)
本模块负责处理所有与任务相关的API路由，包括任务的创建、更新、状态变更和查询。
[v0.2 SQLAlchemy 重构版]
"""
from fastapi import APIRouter, HTTPException, Depends, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional
from loguru import logger

from app.services.task_service import TaskService
from app.core.auth import require_permission_level
from app.models.user import User
from app.core.database import get_db

router = APIRouter()

# --- Pydantic Schemas for Request Validation ---

class TaskCreateRequest(BaseModel):
    """任务创建请求模型"""
    task_type: int
    # [v0.2 移除] name 不再由前端提供，将通过 maker_id 从数据库获取
    # name: str
    department: int
    maker_id: str 
    content: str
    deadline: str # 接收 ISO 8601 格式的字符串

class TaskUpdateRequest(BaseModel):
    """任务更新请求模型"""
    task_type: Optional[int] = None
    # [v0.2 移除] name 不再可被直接更新，它与 maker_id 绑定
    # name: Optional[str] = None
    department: Optional[int] = None
    content: Optional[str] = None
    deadline: Optional[str] = None
    maker_id: Optional[str] = None

# --- API Endpoints ---

@router.post("/post", summary="创建新任务", dependencies=[Depends(require_permission_level(2))])
async def create_task(
    task_request: TaskCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    (管理员权限) 创建一个新任务并分配给指定负责人。
    如果任务类型匹配，会自动使用排班系统进行分配。
    """
    logger.info(f"路由层: 接收到创建任务请求，类型: {task_request.task_type}")
    try:
        service = TaskService()
        # [v0.2 适配] 不再传入 task_request.dict()，而是明确传入需要的参数
        new_task = await service.create_task(db, task_request.maker_id, task_request.dict())
        logger.success(f"路由层: 任务创建成功, TaskID: {new_task.task_id}")
        return {
            "code": 200,
            "message": "successfully post a new task",
            "data": {"task_id": new_task.task_id}
        }
    except ValueError as e:
        logger.warning(f"创建任务失败 (值错误): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建任务时发生未知错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建任务失败")

@router.patch("/cancel/{task_id}", summary="取消任务", dependencies=[Depends(require_permission_level(2))])
async def cancel_task(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """(管理员权限) 取消一个任务，将其状态置为2。"""
    logger.info(f"路由层: 接收到取消任务请求, TaskID: {task_id}")
    try:
        service = TaskService()
        updated_task = await service.update_task_state(db, task_id, new_state=2)
        logger.success(f"路由层: 任务取消成功, TaskID: {task_id}")
        return {
            "code": 200,
            "message": "successfully cancel task",
            "data": {
                "task_id": updated_task.task_id,
                "state": updated_task.state
            }
        }
    except ValueError as e:
        logger.warning(f"取消任务失败 (值错误): {e} | TaskID: {task_id}")
        status_code = 404 if "不存在" in str(e) else 400
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        logger.error(f"取消任务时发生未知错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="取消任务失败")

@router.patch("/finish/{task_id}", summary="完成任务", dependencies=[Depends(require_permission_level(1))])
async def finish_task(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """(成员权限) 将一个任务标记为已完成，将其状态置为1。"""
    logger.info(f"路由层: 接收到完成任务请求, TaskID: {task_id}")
    try:
        service = TaskService()
        updated_task = await service.update_task_state(db, task_id, new_state=1)
        logger.success(f"路由层: 任务完成成功, TaskID: {task_id}")
        return {
            "code": 200,
            "message": "successfully finish a task",
            "data": {
                "task_id": updated_task.task_id,
                "state": updated_task.state
            }
        }
    except ValueError as e:
        logger.warning(f"完成任务失败 (值错误): {e} | TaskID: {task_id}")
        status_code = 404 if "不存在" in str(e) else 400
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        logger.error(f"完成任务时发生未知错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="完成任务失败")

@router.patch("/update/{task_id}", summary="更新任务详情", dependencies=[Depends(require_permission_level(2))])
async def update_task(
    task_id: str,
    update_data: TaskUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """(管理员权限) 更新一个任务的详细信息。如果任务已取消，会被重新激活。"""
    logger.info(f"路由层: 接收到更新任务详情请求, TaskID: {task_id}")
    try:
        service = TaskService()
        update_dict = update_data.dict(exclude_unset=True)
        if not update_dict:
            raise HTTPException(status_code=400, detail="No fields provided for update")

        updated_task = await service.update_task_details(db, task_id, update_dict)
        logger.success(f"路由层: 任务详情更新成功, TaskID: {task_id}")
        return {
            "code": 200,
            "message": "successfully update task",
            "data": service._task_to_dict(updated_task)
        }
    except ValueError as e:
        logger.warning(f"更新任务失败 (值错误): {e} | TaskID: {task_id}")
        status_code = 404 if "不存在" in str(e) else 400
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        logger.error(f"更新任务时发生未知错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新任务失败")

@router.get("/detail/{task_id}", summary="获取任务详情", dependencies=[Depends(require_permission_level(1))])
async def get_task_detail(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取指定任务的详细信息。"""
    logger.info(f"路由层: 接收到获取任务详情请求, TaskID: {task_id}")
    try:
        service = TaskService()
        task = await service.get_task_by_id(db, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return {
            "code": 200,
            "message": "successfully get task detail",
            "data": service._task_to_dict(task)
        }
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取任务详情失败")

@router.get("/view-all", summary="获取所有任务 (管理员)", dependencies=[Depends(require_permission_level(2))])
async def get_all_tasks(db: AsyncSession = Depends(get_db)):
    """获取系统中的所有任务。"""
    logger.info("路由层: 接收到获取所有任务请求。")
    try:
        service = TaskService()
        tasks = await service.get_all_tasks(db)
        return {
            "code": 200,
            "message": "successfully get all tasks",
            "data": {
                "total": len(tasks),
                "list": tasks
            }
        }
    except Exception as e:
        logger.error(f"获取所有任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取所有任务失败")

@router.get("/view-my", summary="获取我的任务", dependencies=[Depends(require_permission_level(1))])
async def get_user_tasks(
    current_user: User = Depends(require_permission_level(1)),
    db: AsyncSession = Depends(get_db)
):
    """获取分配给当前用户的任务列表。"""
    logger.info(f"路由层: 接收到获取用户任务请求, User: {current_user.userid}")
    try:
        service = TaskService()
        tasks = await service.get_user_tasks(db, current_user.maker_id)
        return {
            "code": 200,
            "message": "successfully get my tasks",
            "data": {
                "total": len(tasks),
                "list": tasks
            }
        }
    except Exception as e:
        logger.error(f"获取我的任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取我的任务失败")