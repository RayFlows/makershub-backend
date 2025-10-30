# app/routes/site_borrow_router.py
"""
场地借用路由模块（小程序端）
提供面向小程序用户的场地借用申请、查询、更新和取消等API接口。
[v2.0 SQLAlchemy 迁移版 - 新业务流程]
"""
from fastapi import APIRouter, HTTPException, Depends, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from pydantic import BaseModel
from typing import Optional, List

from app.core.auth import require_permission_level
from app.services.site_borrow_service import SiteBorrowService
from app.core.database import get_db
from app.models.user import User

router = APIRouter()
site_borrow_service = SiteBorrowService()

# --- Pydantic 模型定义 ---

class SiteBorrowCreateRequest(BaseModel):
    """提交场地借用申请的请求体模型。"""
    name: str
    student_id: str
    phone_num: str
    email: str
    purpose: str
    mentor_name: str
    mentor_phone_num: str
    site_id: str
    site: str
    number: int
    start_time: str # 前端发送ISO格式字符串, e.g., "2025-10-30T10:00:00"
    end_time: str
    project_id: Optional[str] = None

class SiteBorrowUpdateRequest(BaseModel):
    """更新场地借用申请的请求体模型。所有字段均为可选。"""
    email: Optional[str] = None
    end_time: Optional[str] = None
    mentor_name: Optional[str] = None
    mentor_phone_num: Optional[str] = None
    name: Optional[str] = None
    number: Optional[int] = None
    phone_num: Optional[str] = None
    project_id: Optional[str] = None
    purpose: Optional[str] = None
    site: Optional[str] = None
    site_id: Optional[str] = None # 允许更新场地
    start_time: Optional[str] = None
    student_id: Optional[str] = None

class ReviewRequest(BaseModel):
    """审核请求的模型"""
    state: int
    review: str = ""

# --- API 路由 ---

@router.post("/post", summary="提交场地借用申请")
async def create_site_borrow_application(
    application_data: SiteBorrowCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission_level(0)),
):
    """
    用户提交一个新的场地借用申请。
    后端将验证数据，并创建一个状态为“未审核”的申请记录。
    """
    try:
        logger.info(f"用户 {user.userid} 正在提交场地申请...")
        
        # 调用服务层创建申请
        apply_id = await site_borrow_service.create_borrow_application(db,application_data.dict(), user.userid)
        
        logger.success(f"用户 {user.userid} 的场地申请 {apply_id} 已成功创建。")
        return {
            "code": 200, "message": "成功创建新的场地借用申请",
            "data": {"apply_id": apply_id}
        }
    except ValueError as e:
        logger.warning(f"提交场地申请失败 - 业务逻辑错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"提交场地申请时发生未知错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="提交场地申请失败")

@router.get("/detail/{apply_id}", summary="获取场地借用申请详情")
async def get_site_borrow_detail(
    apply_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission_level(0)),
):
    """
    获取单个场地借用申请的详细信息。
    普通用户只能查看自己的申请，管理员可以查看所有。
    """
    try:
        logger.info(f"用户 {user.userid} 正在请求查看场地申请详情: {apply_id}")
        
        application_detail = await site_borrow_service.get_application_detail(db, apply_id)
        
        # 权限检查：确保普通用户不能查看不属于自己的申请
        if user.role == 0 and application_detail.get("userid") != user.userid:
            logger.warning(f"权限不足: 用户 {user.userid} 尝试查看属于 {application_detail.get('userid')} 的申请 {apply_id}")
            raise HTTPException(status_code=403, detail="无权查看此申请")

        return {
            "code": 200, "message": "成功获取场地申请详情",
            "data": application_detail
        }
    except ValueError as e: # Service层抛出的 "申请不存在"
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取场地借用详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取场地借用详情失败")

@router.get("/view-all", summary="获取所有场地申请（管理员）")
async def get_all_site_borrow_applications(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission_level(1)),
):
    """
    获取所有场地借用申请的简化列表，供管理员概览。
    """
    try:
        logger.info(f"管理员 {user.userid} 正在请求所有场地申请列表。")
        applications = await site_borrow_service.get_all_applications(db)
        return {
            "code": 200, "message": "成功获取所有场地申请列表",
            "data": applications
        }
    except Exception as e:
        logger.error(f"获取全部场地申请失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取全部场地申请失败")

@router.get("/view", summary="获取当前用户的所有场地申请")
async def get_user_site_borrow_applications(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission_level(0)),
):
    """
    获取当前登录用户的所有场地借用申请的简化列表。
    """
    try:
        logger.info(f"用户 {user.userid} 正在请求自己的场地申请列表。")
        applications = await site_borrow_service.get_user_applications(db, user.userid)
        return {
            "code": 200, "message": "成功获取用户的场地申请列表",
            "data": applications
        }
    except Exception as e:
        logger.error(f"获取用户场地申请失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取用户场地申请失败")

@router.post("/cancel/{apply_id}", summary="用户取消场地申请")
async def cancel_site_borrow_application(
    apply_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission_level(0)),
):
    """
    用户取消自己提交的、处于可取消状态的场地借用申请。
    """
    try:
        logger.info(f"用户 {user.userid} 正在尝试取消场地申请: {apply_id}")
        
        canceled_apply_id = await site_borrow_service.cancel_application(db, apply_id, user.userid)
        
        logger.success(f"用户 {user.userid} 成功取消了申请 {canceled_apply_id}")
        return {
            "code": 200, "message": "成功取消场地申请",
            "data": {"apply_id": canceled_apply_id}
        }
    except ValueError as e:
        logger.warning(f"取消场地申请失败 - 业务错误: {e}")
        if "不存在" in str(e): raise HTTPException(status_code=404, detail=str(e))
        if "无权限" in str(e): raise HTTPException(status_code=403, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"取消场地申请时发生未知错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="取消场地申请失败")

@router.patch("/update/{apply_id}", summary="用户更新场地申请")
async def update_site_borrow_application(
    apply_id: str,
    update_data: SiteBorrowUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission_level(0)),
):
    """
    用户更新自己提交的、处于“未审核”或“已打回”状态的申请。
    """
    try:
        logger.info(f"用户 {user.userid} 正在尝试更新场地申请: {apply_id}")
        
        update_dict = update_data.dict(exclude_unset=True)
        if not update_dict:
            raise ValueError("没有提供任何用于更新的字段")
        
        result = await site_borrow_service.update_application(db, apply_id, user.userid, update_dict)
        
        return {
            "code": 200, "message": "成功更新场地申请",
            "data": {"apply_id": result[0], "changed": result[1]}
        }
    except ValueError as e:
        logger.warning(f"更新场地申请失败 - 业务错误: {e}")
        if "不存在" in str(e): raise HTTPException(status_code=404, detail=str(e))
        if "无权限" in str(e) or "不允许" in str(e): raise HTTPException(status_code=403, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新场地申请时发生未知错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新场地申请失败")

@router.patch("/review/{apply_id}", summary="发布审核结果（管理员在小程序端操作）")
async def review_site_borrow_application(
    apply_id: str,
    review_data: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission_level(1)), # 权限要求为管理员
):
    """
    （在小程序端）发布场地借用审核结果 (批准或打回)。
    此接口功能与后台管理端的审核接口相同。
    """
    try:
        logger.info(f"管理员 {user.userid} 在小程序端审核场地申请 | 申请ID: {apply_id}")
        
        # 复用我们已经写好的、健壮的 service 方法
        result_tuple = await site_borrow_service.review_application(
            db, 
            apply_id, 
            review_data.state, 
            review_data.review
        )
        
        return {
            "code": 200,
            "message": "审核成功",
            "data": {
                "apply_id": result_tuple[0],
                "state": result_tuple[1],
                "review": result_tuple[2]
            }
        }
    except ValueError as e:
        # Service 层抛出的业务错误
        logger.warning(f"审核场地申请 {apply_id} 失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"审核场地申请时发生未知错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="审核场地申请失败")

@router.patch("/return/{apply_id}", summary="用户确认场地归还")
async def return_borrow_application(
    apply_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission_level(0)), # 允许申请人自己归还
):
    """
    用户（或管理员）确认归还已借用的场地。
    """
    try:
        logger.info(f"用户 {user.userid} 正在归还场地，申请ID: {apply_id}")
        
        # 调用服务层归还场地，操作员ID为当前用户
        result = await site_borrow_service.return_borrow_application(db, apply_id, user.userid)
        
        return {
            "code": 200, "message": "成功归还场地",
            "data": {"apply_id": result[0], "state": result[1]}
        }
    except ValueError as e:
        logger.warning(f"归还场地失败 - 业务错误: {e}")
        if "不存在" in str(e): raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"归还场地失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="归还场地失败")