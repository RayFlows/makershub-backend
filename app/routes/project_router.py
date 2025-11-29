# app/routes/project_router.py
"""
项目路由模块 (Project Router Module)
处理项目立项、管理、结项等API路由。
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Security
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from loguru import logger

from app.core.database import get_db
from app.core.auth import AuthMiddleware
from app.models.user import User
from app.services.project_service import ProjectService

router = APIRouter()
security = HTTPBearer()
project_service = ProjectService()

# --- Pydantic Schemas (DTOs) ---

class ProjectCreateRequest(BaseModel):
    """创建项目请求体"""
    project_name: str = Field(..., description="项目名称")
    project_type: int = Field(..., description="项目类型: 0=个人, 1=比赛")
    description: str = Field(..., description="项目详细描述")
    
    # 接收字符串格式的时间，Pydantic 会自动尝试解析 ISO 格式
    # 前端传: "2025-09-01 00:00:00"
    start_time: datetime = Field(..., description="预计开始时间")
    end_time: datetime = Field(..., description="预计结束时间")
    
    mentor_name: Optional[str] = Field(None, description="指导老师姓名")
    mentor_phone: Optional[str] = Field(None, description="指导老师电话")
    is_recruiting: bool = Field(False, description="是否开放招募")
    
    member_phones: List[str] = Field(default=[], description="初始成员手机号列表")

    class Config:
        json_schema_extra = {
            "example": {
                "project_name": "基于视觉识别的自动喂猫机",
                "project_type": 0,
                "description": "本项目旨在利用树莓派...",
                "start_time": "2025-09-01 00:00:00",
                "end_time": "2025-12-30 00:00:00",
                "mentor_name": "张教授",
                "mentor_phone": "13800138000",
                "is_recruiting": False,
                "member_phones": ["13800138001", "13900139002"]
            }
        }

# --- Routes ---

@router.post("/create", dependencies=[Security(security)])
async def create_project(
    request: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """
    创建新项目
    
    - Header: 需要 Authorization Token
    - Logic: 自动绑定当前用户为负责人(leader)，根据手机号查找并添加成员。
    - State: 初始状态默认为 0 (待审核)。
    """
    try:
        # 提取基础数据，剔除 member_phones 单独处理
        project_data = request.dict(exclude={"member_phones"})
        member_phones = request.member_phones
        
        return await project_service.create_project(
            db=db,
            project_data=project_data,
            leader=current_user,
            member_phones=member_phones
        )
    except Exception as e:
        logger.error(f"创建项目接口异常: {e}", exc_info=True)
        # 区分已知错误和未知错误，这里暂统一报 500，Service层如果有特定逻辑可抛 HTTPException
        raise HTTPException(status_code=500, detail="创建项目失败，请联系管理员")