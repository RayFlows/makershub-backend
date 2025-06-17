from fastapi import APIRouter, HTTPException, Depends
from app.services.site_borrow_service import SiteBorrowService
from app.core.auth import require_permission_level#, get_current_user
from loguru import logger
from pydantic import BaseModel
from typing import Optional

router = APIRouter()
# site_borrow_service = SiteBorrowService()

# 提交场地申请
@router.post("/post")
async def create_site_borrow_application(
    application_data: dict,
    user: dict = Depends(require_permission_level(0)),  # 允许权限0,1,2
    site_borrow_service: SiteBorrowService = Depends(SiteBorrowService) 
):
    """
    提交场地借用申请
    
    用户不能借用已经借用的场地（场地表中的is_occupied为true）
    """
    try:
        # 验证必要字段
        required_fields = [
            "name", "student_id", "phone_num", "email", "purpose", 
            "mentor_name", "mentor_phone_num", "site_id", "site", 
            "number", "end_time", "start_time", "project_id"
        ]
        
        for field in required_fields:
            if field not in application_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"缺少必要字段: {field}"
                )
        
        # 获取当前用户ID
        userid = user.userid  # 假设用户对象中有userid字段
        
        # 调用服务层创建申请
        apply_id = await site_borrow_service.create_borrow_application(application_data, userid)
        
        return {
            "code": 200,
            "message": "successfully create new site-application",
            "data": {
                "apply_id": apply_id
            }
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"提交场地申请失败: {str(e)}")
        raise HTTPException(status_code=500, detail="提交场地申请失败")

# 获取场地借用详情
@router.get("/detail/{apply_id}")
async def get_site_borrow_detail(
    apply_id: str,
    user: dict = Depends(require_permission_level(0)),  # 允许权限0,1,2
    site_borrow_service: SiteBorrowService = Depends(SiteBorrowService)
):
    """
    获取场地借用申请详情
    
    在"我的场地"页面中查看特定记录的详细信息
    """
    try:
        logger.info(f"获取场地借用详情 | 申请ID: {apply_id} | 用户: {user.userid}")
        
        # 调用服务层获取申请详情
        application_detail = await site_borrow_service.get_application_detail(apply_id)
        
        return {
            "code": 200,
            "message": "successfully get site-application detail",
            "data": application_detail
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"获取场地借用详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取场地借用详情失败")


# 获取全部场地申请
@router.get("/view-all")
async def get_all_site_borrow_applications(
    user: dict = Depends(require_permission_level(1)),  # 需要权限1或2
    site_borrow_service: SiteBorrowService = Depends(SiteBorrowService)
):
    """
    获取所有场地借用申请
    
    在场地借用审批页面显示所有申请记录
    """
    try:
        logger.info(f"获取全部场地申请 | 请求用户: {user.userid}")
        
        # 调用服务层获取申请列表
        applications = await site_borrow_service.get_all_applications()
        
        return {
            "code": 200,
            "message": "successfully get application list",
            "data": applications
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"获取全部场地申请失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取全部场地申请失败")

# 获取用户所有场地申请
@router.get("/view")
async def get_user_site_borrow_applications(
    user: dict = Depends(require_permission_level(0)),  # 允许权限0,1,2
    site_borrow_service: SiteBorrowService = Depends(SiteBorrowService)
):
    """
    获取当前用户的所有场地借用申请
    
    在"我的借物"页面显示用户的申请记录
    """
    try:
        logger.info(f"获取用户场地申请 | 用户: {user.userid}")
        
        # 获取当前用户ID
        userid = user.userid
        
        # 调用服务层获取用户申请列表
        applications = await site_borrow_service.get_user_applications(userid)
        
        return {
            "code": 200,
            "message": "successfully get application list",
            "data": applications
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"获取用户场地申请失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户场地申请失败")

# 取消场地申请
@router.post("/cancel/{apply_id}")
async def cancel_site_borrow_application(
    apply_id: str,  # 从路径获取申请ID
    user: dict = Depends(require_permission_level(0)),  # 允许权限0,1,2
    site_borrow_service: SiteBorrowService = Depends(SiteBorrowService)
):
    """
    取消场地借用申请
    
    用户只能取消自己状态为0（未审核）或1（打回）的申请。
    """
    try:
        logger.info(f"取消场地申请 | 申请ID: {apply_id} | 用户: {user.userid}")
        
        # 调用服务层取消申请
        canceled_apply_id = await site_borrow_service.cancel_application(apply_id, user.userid)
        
        return {
            "code": 200,
            "message": "successfully cancel site-application",
            "data": {
                "apply_id": canceled_apply_id
            }
        }
    except HTTPException as he:
        # 处理400错误的特殊返回格式
        if he.status_code == 400 and hasattr(he, 'data'):
            return JSONResponse(
                status_code=400,
                content={
                    "code": 400,
                    "message": he.detail,
                    "data": he.data
                }
            )
        # 处理其他HTTP异常
        raise he
    except Exception as e:
        logger.error(f"取消场地申请失败: {str(e)}")
        raise HTTPException(status_code=500, detail="cancel site-application failed")

# 定义审核请求模型
class ReviewRequest(BaseModel):
    state: int
    review: str = ""

# 发布审核结果
@router.patch("/review/{apply_id}")
async def review_site_borrow_application(
    apply_id: str,
    review_data: ReviewRequest,
    user: dict = Depends(require_permission_level(1)),  # 需要权限1或2
    site_borrow_service: SiteBorrowService = Depends(SiteBorrowService)
):
    """
    发布场地借用审核结果
    
    审核员在审核后更新申请状态：
    - 审核通过：state=2
    - 审核未通过：state=1，必须提供review
    
    只有状态为0（未审核）的申请才能被审核。
    """
    try:
        logger.info(f"发布审核结果 | 申请ID: {apply_id} | 审核员: {user.userid}")
        
        # 调用服务层审核申请
        result = await site_borrow_service.review_application(
            apply_id, 
            review_data.state, 
            review_data.review
        )
        
        return {
            "code": 200,
            "message": "successfully update application state",
            "data": {
                "apply_id": result[0],
                "state": result[1],
                "review": result[2]
            }
        }
    except HTTPException as he:
        # 处理400错误的特殊返回格式
        if he.status_code == 400 and hasattr(he, 'data'):
            return JSONResponse(
                status_code=400,
                content={
                    "code": 400,
                    "message": he.detail,
                    "data": he.data
                }
            )
        # 处理其他HTTP异常
        raise he
    except Exception as e:
        logger.error(f"发布审核结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail="review site-application failed")

# 定义更新请求模型
class UpdateRequest(BaseModel):
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
    start_time: Optional[str] = None
    student_id: Optional[str] = None

# 更新用户场地申请
@router.patch("/update/{apply_id}")
async def update_site_borrow_application(
    apply_id: str,
    update_data: UpdateRequest,
    user: dict = Depends(require_permission_level(0)),  # 允许权限0,1,2
    site_borrow_service: SiteBorrowService = Depends(SiteBorrowService)
):
    """
    更新场地借用申请
    
    用户只能更新自己状态为0（未审核）或1（打回）的申请。
    支持部分字段更新。
    """
    try:
        logger.info(f"更新场地申请 | 申请ID: {apply_id} | 用户: {user.userid}")
        
        # 转换为字典并移除空值
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        if not update_dict:
            logger.warning("没有提供更新字段")
            raise HTTPException(
                status_code=400,
                detail="no fields provided for update"
            )
        
        # 调用服务层更新申请
        result = await site_borrow_service.update_application(
            apply_id, 
            user.userid,
            update_dict
        )
        
        # 提取实际更新的字段名
        changed_fields = {k: v["new"] for k, v in result[1].items()}
        
        return {
            "code": 200,
            "message": "successfully update new application",
            "data": {
                "apply_id": result[0],
                "changed": changed_fields
            }
        }
    except HTTPException as he:
        # 处理400错误的特殊返回格式
        if he.status_code == 400 and hasattr(he, 'data'):
            return JSONResponse(
                status_code=400,
                content={
                    "code": 400,
                    "message": he.detail,
                    "data": he.data
                }
            )
        # 处理其他HTTP异常
        raise he
    except Exception as e:
        logger.error(f"更新场地申请失败: {str(e)}")
        raise HTTPException(status_code=500, detail="update site-application failed")

@router.patch("/return/{apply_id}")
async def return_borrow_application(
    apply_id: str,  # 从路径获取申请ID
    user: dict = Depends(require_permission_level(0)),  # 允许权限0,1,2
    site_borrow_service: SiteBorrowService = Depends(SiteBorrowService)
):
    """
    归还已借用的场地
    
    用户归还已借用的场地，将状态更新为已归还（3）
    只有状态为2（通过未归还）的申请才能被归还
    """
    try:
        logger.info(f"归还场地 | 申请ID: {apply_id} | 用户: {user.userid}")
        
        # 调用服务层归还场地
        result = await site_borrow_service.return_borrow_application(apply_id, user.userid)
        
        return {
            "code": 200,
            "message": "successfully return site",
            "data": {
                "apply_id": result[0],
                "state": result[1]
            }
        }
    except HTTPException as he:
        # 处理400错误的特殊返回格式
        if he.status_code == 400 and hasattr(he, 'data'):
            return JSONResponse(
                status_code=400,
                content={
                    "code": 400,
                    "message": he.detail,
                    "data": he.data
                }
            )
        # 处理其他HTTP异常
        raise he
    except Exception as e:
        logger.error(f"归还场地失败: {str(e)}")
        raise HTTPException(status_code=500, detail="return site failed")