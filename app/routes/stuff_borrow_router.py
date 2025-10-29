# app/routes/stuff_borrow_router.py
# [v2.0 SQLAlchemy 迁移版 - 最终业务逻辑匹配完整版]

from fastapi import APIRouter, HTTPException, Depends, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional
from loguru import logger

from app.core.auth import require_permission_level
from app.services.stuff_borrow_service import StuffBorrowService
from app.core.database import get_db
from app.models.user import User

router = APIRouter()
stuff_borrow_service = StuffBorrowService()

# --- Pydantic 模型定义 (与原始文件完全一致) ---

class StuffBorrowApplication(BaseModel):
    name: str
    student_id: str
    phone: str
    email: str
    grade: str
    major: str
    reason: str
    deadline: str
    materials: List[str]
    type: int = 0
    project_number: Optional[str] = None
    supervisor_name: Optional[str] = None
    supervisor_phone: Optional[str] = None

class ReviewRequest(BaseModel):
    borrow_id: str
    action: str
    reason: Optional[str] = ""

class UpdateStuffQuantityRequest(BaseModel): # 确保这个模型存在
    borrow_id: str
    stuff_updates: List[dict]

class ReturnRequest(BaseModel):
    borrow_id: str
    return_notes: Optional[str] = ""

class StuffBorrowUpdateRequest(BaseModel):
    name: Optional[str] = None
    student_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    grade: Optional[str] = None
    major: Optional[str] = None
    reason: Optional[str] = None
    materials: Optional[List[str]] = None
    deadline: Optional[str] = None
    # 'type' 和 'start_time' 不允许用户更新

# --- API 路由 ---

@router.post("/apply", summary="提交物资借用申请")
async def submit_stuff_borrow_application(
    application: StuffBorrowApplication,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission_level(0))
):
    """用户提交物资借用申请。"""
    logger.info(f"用户 {user.userid} 开始提交借物申请")
    try:
        application_dict = application.dict()
        application_dict["user_id"] = user.userid
        logger.debug(f"准备调用服务层，数据: {application_dict}")
        result = await stuff_borrow_service.create_stuff_borrow_application(db, application_dict)
        logger.info(f"用户 {user.userid} 提交申请 {result['data']['sb_id']} 成功")
        return result
    except ValueError as e:
        logger.warning(f"提交借物申请失败 - 参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"提交借物申请失败 - 服务器错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"提交申请失败: {str(e)}")

@router.get("/view", summary="查看当前用户的借物列表")
async def view_user_stuff_borrow(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission_level(0))
):
    """获取当前登录用户的所有借物申请列表。"""
    try:
        logger.info(f"用户 {user.userid} 请求获取其借物列表。")
        return await stuff_borrow_service.get_user_stuff_borrow_list(db, user.userid)
    except Exception as e:
        logger.error(f"获取用户借物列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/detail/{sb_id}", summary="查看借物申请详情")
async def get_stuff_borrow_detail(
    sb_id: str = Path(..., description="借物申请ID"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission_level(0))
):
    """获取指定ID的借物申请详情。"""
    try:
        logger.info(f"用户 {user.userid} 请求查看申请详情: {sb_id}")
        result = await stuff_borrow_service.get_stuff_borrow_detail(db, sb_id)
        if user.role == 0 and result["data"]["user_id"] != user.userid:
             logger.warning(f"权限不足：用户 {user.userid} 尝试查看不属于自己的申请 {sb_id}")
             raise HTTPException(status_code=403, detail="无权限查看此申请")
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/view-all", summary="获取所有借物申请（管理员）")
async def view_all_stuff_borrow(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission_level(1))
):
    """获取数据库全部的借物申请，仅限管理员访问。"""
    try:
        logger.info(f"管理员 {user.userid} 请求获取所有借物申请列表。")
        return await stuff_borrow_service.get_all_stuff_borrow_list(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/review", summary="【原子操作】审核借物申请（管理员）")
async def review_stuff_borrow_application(
    review_data: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission_level(1))
):
    """
    审核借物申请（批准或打回）。
    这是一个原子性接口：
    - 批准操作会同步完成库存检查和扣减。
    - 如果库存不足，申请会自动变为“已打回”，并返回400错误。
    """
    logger.info(f"管理员 {user.userid} 请求审核申请 {review_data.borrow_id}，操作: {review_data.action}")
    try:
        if review_data.action not in ["approve", "reject"]:
            raise HTTPException(status_code=400, detail="无效的操作类型，必须是 'approve' 或 'reject'")
        if review_data.action == "reject" and not review_data.reason.strip():
            raise HTTPException(status_code=400, detail="打回申请必须提供理由")
        
        # 调用统一的、事务性的 service 方法
        result = await stuff_borrow_service.handle_review_process(
            db=db,
            sb_id=review_data.borrow_id,
            action=review_data.action,
            reason=review_data.reason,
            reviewer_id=user.userid
        )
        
        # 根据 service 返回的 code 决定 HTTP 响应状态
        if result.get("code") != 200:
            raise HTTPException(status_code=result["code"], detail=result.get("message"), headers={"X-Error-Data": str(result.get("data"))})
            
        return result
        
    except ValueError as e:
        # 捕获 service 内部抛出的业务逻辑错误
        logger.warning(f"审核操作失败 (ValueError): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"审核操作发生未知异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.post("/return", summary="确认物资归还（管理员）")
async def return_stuff_borrow_application(
    return_data: ReturnRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission_level(1))
):
    """物资归还流程：先确认归还状态，再恢复库存。"""
    logger.info(f"管理员 {user.userid} 开始确认物资归还: {return_data.borrow_id}")
    try:
        return_dict = return_data.dict()
        return_dict["operator_id"] = user.userid
        
        return_result = await stuff_borrow_service.confirm_stuff_return(db, return_dict)
        
        if return_result.get("code") == 200:
            logger.info("归还状态确认成功，开始恢复物资数量...")
            try:
                restore_result = await stuff_borrow_service.restore_stuff_quantity_from_return(db, return_data.borrow_id, user.userid)
                return {"code": 200, "message": "归还确认成功，物资数量已恢复", "data": {"return_result": return_result, "restore_result": restore_result}}
            except Exception as restore_error:
                logger.error(f"物资数量恢复失败: {restore_error}", exc_info=True)
                return {"code": 202, "message": "归还状态已确认，但自动恢复库存失败，请手动检查库存！", "error": str(restore_error)}
        else:
            return return_result
    except (ValueError, HTTPException) as e:
        raise e if isinstance(e, HTTPException) else HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"归还确认失败: {str(e)}")

@router.post("/cancel/{sb_id}", summary="用户取消借物申请")
async def cancel_stuff_borrow_application(
    sb_id: str = Path(..., description="借物申请ID"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission_level(0))
):
    """用户取消自己提交的、尚未被批准的借物申请。"""
    logger.info(f"用户 {user.userid} 请求取消借物申请: {sb_id}")
    try:
        return await stuff_borrow_service.cancel_stuff_borrow_application(db, sb_id, user.userid)
    except ValueError as e:
        if "不存在" in str(e): raise HTTPException(status_code=404, detail=str(e))
        if "无权限" in str(e): raise HTTPException(status_code=403, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消申请操作失败: {str(e)}")

@router.patch("/update/{sb_id}", summary="用户更新借物申请")
async def update_stuff_borrow_application(
    sb_id: str = Path(..., description="借物申请ID"),
    update_data: StuffBorrowUpdateRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission_level(0))
):
    """用户更新自己提交的、处于“未审核”或“已打回”状态的申请。"""
    logger.info(f"用户 {user.userid} 请求更新借物申请 {sb_id}")
    try:
        data_to_update = update_data.dict(exclude_unset=True)
        if not data_to_update: raise ValueError("没有提供任何更新数据")
        return await stuff_borrow_service.update_stuff_borrow_application(db, sb_id, data_to_update, user.userid)
    except ValueError as e:
        if "不存在" in str(e): raise HTTPException(status_code=404, detail=str(e))
        if "无权限" in str(e) or "才能修改" in str(e): raise HTTPException(status_code=403, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")