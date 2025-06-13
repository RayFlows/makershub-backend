from fastapi import APIRouter, HTTPException, Depends
from app.services.site_borrow_service import SiteBorrowService
from app.core.auth import require_permission_level#, get_current_user
from loguru import logger

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