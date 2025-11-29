# app/routes/project_router.py
"""
项目路由模块 (Project Router Module)
处理项目立项、管理、结项等API路由。
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Security, Query
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from loguru import logger

from app.core.database import get_db
from app.core.auth import AuthMiddleware, require_permission_level
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
    
    member_maker_ids: List[str] = Field(default=[], description="初始成员MakerID列表")

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
                "member_maker_ids": ["MK20231101_123", "MK20231101_456"]
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
    - Logic: 自动绑定当前用户为负责人(leader)，根据 member_maker_ids 查找并添加成员。
    - State: 初始状态默认为 0 (待审核)。
    """
    try:
        # 提取基础数据，剔除 member_maker_ids 单独处理
        project_data = request.dict(exclude={"member_maker_ids"})
        member_maker_ids = request.member_maker_ids
        
        return await project_service.create_project(
            db=db,
            project_data=project_data,
            leader=current_user,
            member_maker_ids=member_maker_ids
        )
    except ValueError as ve:
        # [新增] 专门捕获业务逻辑验证错误，返回 400 Bad Request
        logger.warning(f"创建项目参数错误: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"创建项目接口异常: {e}", exc_info=True)
        # 区分已知错误和未知错误，这里暂统一报 500，Service层如果有特定逻辑可抛 HTTPException
        raise HTTPException(status_code=500, detail="创建项目失败，请联系管理员")

@router.get("/list/view-my", dependencies=[Security(security)])
async def view_my_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """
    获取我的项目列表
    
    返回当前用户参与的所有项目（无论是作为负责人还是作为成员）。
    列表按创建时间倒序排列。
    """
    try:
        projects = await project_service.get_my_projects(db, current_user.id)
        
        return {
            "code": 200,
            "message": "获取项目列表成功",
            "data": projects
        }
    except Exception as e:
        logger.error(f"获取我的项目列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取项目列表失败")

@router.get("/detail/{project_id}", dependencies=[Security(security)])
async def get_project_detail(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    # 只需要鉴权，不需要用到 current_user 对象，但必须验证 token
    _ = Depends(AuthMiddleware.get_current_user)
):
    """
    获取项目详情
    
    - **project_id**: 业务唯一编号 (例如 PJ2025...)
    - **返回**: 项目基础信息 + 负责人详细信息 + 成员列表
    """
    try:
        project_detail = await project_service.get_project_detail(db, project_id)
        
        if not project_detail:
            raise HTTPException(status_code=404, detail="未找到指定项目")
            
        return {
            "code": 200,
            "message": "success",
            "data": project_detail
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"查询项目详情异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取项目详情失败")

class MemberIdItem(BaseModel):
    """单个成员ID对象"""
    maker_id: str

class AddProjectMemberRequest(BaseModel):
    """添加成员请求体"""
    new_members: List[MemberIdItem]

@router.post("/{project_id}/member/add", dependencies=[Security(security)])
async def add_project_members(
    project_id: str,
    request: AddProjectMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """
    添加项目成员
    
    - 鉴权: 仅项目负责人可操作
    - 逻辑: 自动去重，忽略已存在的成员和负责人自己
    """
    try:
        # 提取 maker_id 列表
        maker_ids = [item.maker_id for item in request.new_members]
        
        added_members = await project_service.add_members(
            db=db,
            project_id=project_id,
            leader_user=current_user,
            maker_ids=maker_ids
        )
        
        return {
            "code": 200,
            "msg": "成员添加成功",
            "data": added_members
        }
        
    except ValueError as ve:
        # 项目不存在
        raise HTTPException(status_code=404, detail=str(ve))
    except PermissionError as pe:
        # 权限不足 (不是负责人)
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        logger.error(f"添加成员接口异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="添加成员失败")    

class RemoveProjectMemberRequest(BaseModel):
    """移除成员请求体"""
    deleted_members: List[MemberIdItem]

@router.delete("/{project_id}/member", dependencies=[Security(security)])
async def remove_project_members(
    project_id: str,
    request: RemoveProjectMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """
    移除项目成员
    
    - 鉴权: 仅项目负责人可操作
    - 逻辑: 根据 maker_id 移除成员，忽略不在项目中的用户。
    """
    try:
        # 提取 maker_id 列表
        maker_ids = [item.maker_id for item in request.deleted_members]
        
        removed_members = await project_service.remove_members(
            db=db,
            project_id=project_id,
            leader_user=current_user,
            maker_ids=maker_ids
        )
        
        return {
            "code": 200,
            "msg": "成员移除成功",
            "data": removed_members
        }
        
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        logger.error(f"移除成员接口异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="移除成员失败")

@router.get("/list/review", dependencies=[Security(security)])
async def get_project_review_list(
    state: Optional[int] = Query(None, description="筛选特定状态 (如 0=待审核)"),
    db: AsyncSession = Depends(get_db),
    # [鉴权] 要求权限等级 >= 1 (干事及以上)
    # 这会自动验证 token 并检查 user.role
    current_user: User = Depends(require_permission_level(1))
):
    """
    获取审核列表
    
    - 权限: 仅限协会高级成员 (Role >= 1)
    - 筛选: 可通过 state 参数筛选，例如传 0 只看新申请。
    - 返回: 包含项目完整信息、负责人联系方式及成员名单。
    """
    try:
        projects = await project_service.get_review_list(db, state)
        
        return {
            "code": 200,
            "msg": "success",
            "data": projects
        }
    except Exception as e:
        logger.error(f"获取审核列表异常: {e}", exc_info=True)
        # 这里的 500 会被前端捕获
        raise HTTPException(status_code=500, detail="获取列表失败")

class AuditProjectRequest(BaseModel):
    """立项审核请求体"""
    state: int = Field(..., description="审核结果: 1=通过(进行中), 2=驳回")
    review: Optional[str] = Field(None, description="审核意见")

@router.put("/{project_id}/action/audit", dependencies=[Security(security)])
async def audit_project(
    project_id: str,
    request: AuditProjectRequest,
    db: AsyncSession = Depends(get_db),
    # [鉴权] 必须是干事及以上权限
    current_user: User = Depends(require_permission_level(1))
):
    """
    提交立项审核结果
    
    - **权限**: Role >= 1
    - **约束**: state 只能为 1 或 2
    """
    try:
        # 1. 参数校验
        if request.state not in [1, 2]:
            raise HTTPException(status_code=400, detail="审核状态无效，只能为 1(通过) 或 2(驳回)")

        # 2. 调用服务
        result = await project_service.audit_project(
            db=db,
            project_id=project_id,
            state=request.state,
            review=request.review
        )
        
        return {
            "code": 200,
            "msg": "审核操作成功",
            "data": result
        }
        
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"审核接口异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="审核操作失败")

class ToggleRecruitRequest(BaseModel):
    """切换招募状态请求体"""
    is_recruiting: bool = Field(..., description="是否开启招募: true=开启, false=关闭")

@router.put("/{project_id}/action/toggle-recruit", dependencies=[Security(security)])
async def toggle_recruit_status(
    project_id: str,
    request: ToggleRecruitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """
    切换项目招募状态
    
    - 权限: 项目负责人 OR 管理员(Role>=1)
    """
    try:
        result = await project_service.toggle_recruiting(
            db=db,
            project_id=project_id,
            user=current_user,
            is_recruiting=request.is_recruiting
        )
        
        return {
            "code": 200,
            "msg": "状态更新成功",
            "data": result
        }
        
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        logger.error(f"切换招募状态接口异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="状态更新失败")