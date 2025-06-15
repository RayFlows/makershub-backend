from fastapi import APIRouter, HTTPException, Depends, Path
from app.core.auth import require_permission_level
from app.services.stuff_borrow_service import StuffBorrowService
from pydantic import BaseModel
from typing import List, Optional
import traceback

router = APIRouter()

class StuffBorrowApplication(BaseModel):
    name: str
    student_id: str
    phone: str
    email: str
    grade: str
    major: str
    content: str
    deadline: str
    materials: List[str]
    type: int = 0
    project_num: Optional[str] = None
    mentor_name: Optional[str] = None
    mentor_phone_num: Optional[str] = None

@router.post("/apply")
def submit_stuff_borrow_application(
    application: StuffBorrowApplication,
    user = Depends(require_permission_level(0))
):
    """提交借物申请"""
    print("=== 开始处理借物申请 ===")
    try:
        # 使用 dict() 而不是 model_dump()
        application_dict = application.dict()
        print(f"接收到申请: {application_dict}")
        print(f"用户信息: {user}")
        
        # 从用户对象中获取 user_id，user 是 User 对象，不是字典
        user_id = getattr(user, 'user_id', None) or getattr(user, 'id', None) or str(user.id) if hasattr(user, 'id') else None
        print(f"提取的用户ID: {user_id}")
        
        if not user_id:
            print("错误: 无法获取用户ID")
            raise HTTPException(status_code=400, detail="无法获取用户ID")
        
        # 准备申请数据
        application_dict["user_id"] = str(user_id)
        print(f"准备调用服务层，数据: {application_dict}")
        
        # 调用服务层
        result = StuffBorrowService.create_stuff_borrow_application(application_dict)
        print(f"服务层返回结果: {result}")
        
        return result
        
    except HTTPException as he:
        print(f"HTTP异常: {he.detail}")
        raise he
    except Exception as e:
        print(f"路由层错误: {str(e)}")
        print("异常堆栈:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"提交申请失败: {str(e)}")

@router.get("/view")
def view_user_stuff_borrow(user = Depends(require_permission_level(0))):
    """获取用户所有借物列表"""
    try:
        user_id = getattr(user, 'user_id', None) or getattr(user, 'id', None) or str(user.id) if hasattr(user, 'id') else None
        if not user_id:
            raise HTTPException(status_code=400, detail="无法获取用户ID")
        
        result = StuffBorrowService.get_user_stuff_borrow_list(str(user_id))
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detail/{sb_id}")
def get_stuff_borrow_detail(
    sb_id: str = Path(..., description="借物申请ID"),
    user = Depends(require_permission_level(0))
):
    """获取借物申请详情"""
    try:
        result = StuffBorrowService.get_stuff_borrow_detail(sb_id)
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/view-all")
def view_all_stuff_borrow(user = Depends(require_permission_level(1))):
    """获取数据库全部的借物申请"""
    try:
        result = StuffBorrowService.get_all_stuff_borrow_list()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))