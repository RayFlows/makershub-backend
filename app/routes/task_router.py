from fastapi import APIRouter, HTTPException, Depends
from loguru import logger
from app.models.task import Task
from app.models.user import User
from app.core.auth import AuthMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

router = APIRouter()

class TaskCreate(BaseModel):
    """创建任务请求数据模型"""
    task_name: str = Field(..., description="任务名称")
    name: str = Field(..., description="负责人姓名")
    content: str = Field(..., description="任务内容")
    deadline: str = Field(..., description="截止时间")
    priority: int = Field(default=2, description="优先级(1-3)")

@router.post("/tasks")
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """
    创建新任务
    """
    try:
        logger.info(f"用户 {current_user.real_name}({current_user.userid}) 创建任务")
        
        # 解析截止时间
        try:
            deadline_dt = Task.parse_deadline(task_data.deadline)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"时间格式错误: {str(e)}")
        
        # 生成任务ID
        task_id = Task.generate_task_id()
        
        # 确保任务ID唯一
        counter = 1
        base_task_id = task_id
        while Task.objects(task_id=task_id).first():
            task_id = f"{base_task_id}_{counter:02d}"
            counter += 1
        
        # 创建任务记录
        task = Task(
            task_id=task_id,
            task_name=task_data.task_name,
            name=task_data.name,
            content=task_data.content,
            deadline=deadline_dt,
            userid=current_user.userid,
            priority=task_data.priority,
            status=0
        )
        
        # 保存到数据库
        task.save()
        
        logger.info(f"任务已创建，任务ID: {task_id}")
        
        return {
            "message": "任务创建成功",
            "status": "ok",
            "task_id": task_id,
            "data": task.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建任务时出错: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@router.get("/tasks")
async def get_user_tasks(
    current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """获取当前用户的任务列表"""
    try:
        tasks = Task.objects(userid=current_user.userid).order_by('-created_at')
        
        return {
            "message": "获取成功",
            "status": "ok",
            "total_count": len(tasks),
            "data": [task.to_dict() for task in tasks]
        }
        
    except Exception as e:
        logger.error(f"获取任务列表时出错: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@router.get("/tasks/test")
async def test_task():
    """测试任务路由"""
    return {"message": "任务模块工作正常", "status": "ok"}