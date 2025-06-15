from fastapi import APIRouter, HTTPException, Depends, Query
from loguru import logger
from app.models.stuff_borrow import StuffBorrow
from app.models.user import User
from app.core.auth import AuthMiddleware
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime

router = APIRouter()

class BorrowApplyRequest(BaseModel):
    # task_name: str = Field(..., description="任务名称", max_length=200)
    name: str = Field(..., description="申请人姓名", max_length=100)
    student_id: str = Field(..., description="学号", max_length=20)
    phone: str = Field(..., description="联系电话", max_length=20)
    email: str = Field(..., description="邮箱地址", max_length=100)
    grade: str = Field(..., description="年级", max_length=50)
    major: str = Field(..., description="专业", max_length=100)
    content: str = Field(..., description="申请内容", max_length=1000)
    deadline: str = Field(..., description="归还截止时间")
    materials: List[str] = Field(..., description="借用物品列表")
    type: Optional[int] = Field(0, description="借物类型: 0=个人借物, 1=团队借物", ge=0, le=1)
    
    # 团队借物专用字段（个人借物时可以不传或传空值）
    supervisor_name: Optional[str] = Field("", description="指导老师姓名", max_length=100)
    supervisor_phone: Optional[str] = Field("", description="指导老师电话", max_length=20)
    project_number: Optional[str] = Field("", description="项目编号", max_length=100)

class BorrowApplyUpdate(BaseModel):
    """更新借物申请请求数据模型"""
    # task_name: Optional[str] = Field(None, min_length=1, max_length=200, description="任务名称")
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="申请人姓名")
    student_id: Optional[str] = Field(None, min_length=1, max_length=20, description="学号")
    phone: Optional[str] = Field(None, min_length=1, max_length=20, description="联系电话")
    email: Optional[str] = Field(None, description="邮箱地址")
    grade: Optional[str] = Field(None, min_length=1, max_length=50, description="年级")
    major: Optional[str] = Field(None, min_length=1, max_length=100, description="专业")
    content: Optional[str] = Field(None, min_length=1, max_length=1000, description="申请内容")
    deadline: Optional[str] = Field(None, description="归还截止时间")
    materials: Optional[List[str]] = Field(None, min_items=1, description="借用物品清单")
    type: Optional[int] = Field(None, ge=0, le=1, description="借物类型: 0=个人借物, 1=团队借物")
    
    # 团队借物专用字段
    supervisor_name: Optional[str] = Field(None, max_length=100, description="指导老师姓名")
    supervisor_phone: Optional[str] = Field(None, max_length=20, description="指导老师电话")
    project_number: Optional[str] = Field(None, max_length=100, description="项目编号")
    
    status: Optional[int] = Field(None, ge=0, le=5, description="申请状态")
    approval_note: Optional[str] = Field(None, max_length=500, description="审批备注")

@router.post("/apply")
async def create_borrow_apply(
    borrow_data: BorrowApplyRequest,
    current_user: User = Depends(AuthMiddleware.get_current_user)
):
    try:
        logger.info(f"用户 {current_user.real_name}({current_user.userid}) 提交借物申请")
        logger.info(f"借物申请数据: {borrow_data.dict()}")
        
        # 解析归还截止时间
        try:
            deadline_dt = StuffBorrow.parse_deadline(borrow_data.deadline)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"时间格式错误: {str(e)}")
        
        # 验证借用物品列表
        if not borrow_data.materials or len(borrow_data.materials) == 0:
            raise HTTPException(status_code=400, detail="必须至少选择一项借用物品")
        
        # 获取借物类型
        borrow_type = getattr(borrow_data, 'type', 0)
        logger.info(f"借物类型: {borrow_type} ({StuffBorrow.get_type_desc(borrow_type)})")
        
        # 处理团队借物字段 - 修复这里
        supervisor_name = ""
        supervisor_phone = ""
        project_number = ""
        
        if borrow_type == 1:  # 团队借物
            # 直接从 borrow_data 获取字段值
            supervisor_name = borrow_data.supervisor_name or ""
            supervisor_phone = borrow_data.supervisor_phone or ""
            project_number = borrow_data.project_number or ""
            
            logger.info(f"团队借物信息 - 指导老师: '{supervisor_name}', 电话: '{supervisor_phone}', 项目编号: '{project_number}'")
            
            # 验证团队借物必填字段 - 暂时注释用于调试
            # if not supervisor_name.strip():
            #     raise HTTPException(status_code=400, detail="团队借物必须填写指导老师姓名")
            # if not supervisor_phone.strip():
            #     raise HTTPException(status_code=400, detail="团队借物必须填写指导老师电话")
            # if not project_number.strip():
            #     raise HTTPException(status_code=400, detail="团队借物必须填写项目编号")
            
            # 添加警告日志
            if not supervisor_name.strip() or not supervisor_phone.strip() or not project_number.strip():
                logger.warning(f"团队借物缺少必填字段 - 指导老师: '{supervisor_name}', 电话: '{supervisor_phone}', 项目编号: '{project_number}'")
        
        # 生成借物申请ID
        borrow_id = StuffBorrow.generate_borrow_id()
        
        # 确保申请ID唯一
        counter = 1
        base_borrow_id = borrow_id
        while StuffBorrow.objects(borrow_id=borrow_id).first():
            borrow_id = f"{base_borrow_id}_{counter:02d}"
            counter += 1
        
        # 创建借物申请记录 - 确保包含所有字段
        borrow_apply = StuffBorrow(
            borrow_id=borrow_id,
            # task_name=borrow_data.task_name,
            name=borrow_data.name,
            student_id=borrow_data.student_id,
            phone=borrow_data.phone,
            email=borrow_data.email,
            grade=borrow_data.grade,
            major=borrow_data.major,
            content=borrow_data.content,
            deadline=deadline_dt,
            materials=borrow_data.materials,
            userid=current_user.userid,
            type=borrow_type,
            supervisor_name=supervisor_name,      # 确保这些字段被设置
            supervisor_phone=supervisor_phone,    # 确保这些字段被设置
            project_number=project_number,        # 确保这些字段被设置
            status=0
        )
        
        logger.info(f"创建的借物申请对象信息:")
        logger.info(f"  - type: {borrow_apply.type}")
        logger.info(f"  - supervisor_name: '{borrow_apply.supervisor_name}'")
        logger.info(f"  - supervisor_phone: '{borrow_apply.supervisor_phone}'")
        logger.info(f"  - project_number: '{borrow_apply.project_number}'")
        
        # 保存到数据库
        borrow_apply.save()
        
        # 验证保存结果
        saved_apply = StuffBorrow.objects(borrow_id=borrow_id).first()
        if saved_apply:
            logger.info(f"数据库中保存的完整信息:")
            logger.info(f"  - type: {saved_apply.type}")
            logger.info(f"  - supervisor_name: '{saved_apply.supervisor_name}'")
            logger.info(f"  - supervisor_phone: '{saved_apply.supervisor_phone}'")
            logger.info(f"  - project_number: '{saved_apply.project_number}'")
            logger.info(f"  - to_dict结果: {saved_apply.to_dict()}")
        
        logger.info(f"借物申请已创建，申请ID: {borrow_id}")
        
        return {
            "message": "借物申请提交成功",
            "status": "ok",
            "borrow_id": borrow_id,
            "user_info": {
                "name": current_user.real_name,
                "userid": current_user.userid
            },
            "materials_count": len(borrow_data.materials),
            "data": borrow_apply.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建借物申请时出错: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")
@router.get("/my-applies")
async def get_user_borrow_applies(
    current_user: User = Depends(AuthMiddleware.get_current_user),
    status: Optional[int] = Query(None, description="申请状态筛选"),
    limit: int = Query(20, le=100, description="返回数量限制"),
    offset: int = Query(0, description="偏移量")
):
    """
    获取当前用户的借物申请列表
    
    Args:
        current_user: 当前用户
        status: 状态筛选
        limit: 返回数量限制
        offset: 偏移量
        
    Returns:
        dict: 借物申请列表
    """
    try:
        # 构建查询条件（只查询当前用户的申请）
        query_filter = {"userid": current_user.userid}
        
        if status is not None:
            query_filter["status"] = status
        
        # 查询借物申请
        applies_query = StuffBorrow.objects(**query_filter).order_by('-created_at')
        total_count = applies_query.count()
        applies = applies_query.skip(offset).limit(limit)
        
        # 统计信息
        stats = {
            "total": StuffBorrow.objects(userid=current_user.userid).count(),
            "pending": StuffBorrow.objects(userid=current_user.userid, status=0).count(),
            "approved": StuffBorrow.objects(userid=current_user.userid, status=1).count(),
            "borrowed": StuffBorrow.objects(userid=current_user.userid, status=2).count(),
            "returned": StuffBorrow.objects(userid=current_user.userid, status=3).count(),
            "rejected": StuffBorrow.objects(userid=current_user.userid, status=4).count(),
            "overdue": StuffBorrow.objects(userid=current_user.userid, status=5).count()
        }
        
        return {
            "message": "获取成功",
            "status": "ok",
            "total_count": total_count,
            "returned_count": len(applies),
            "stats": stats,
            "data": [apply.to_dict() for apply in applies]
        }
        
    except Exception as e:
        logger.error(f"获取用户借物申请列表时出错: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@router.put("/applies/{borrow_id}")
async def update_borrow_apply(
    borrow_id: str,
    borrow_data: BorrowApplyUpdate,
    current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """
    更新借物申请（仅限待审批状态）
    """
    try:
        # 只能更新自己的申请
        borrow_apply = StuffBorrow.objects(borrow_id=borrow_id, userid=current_user.userid).first()
        
        if not borrow_apply:
            raise HTTPException(status_code=404, detail="未找到该借物申请")
        
        # 只有待审批状态的申请才能修改
        if borrow_apply.status != 0:
            raise HTTPException(status_code=400, detail="只有待审批状态的申请才能修改")
        
        # 更新字段
        update_fields = []
        
        # # 基本字段更新逻辑...
        # if borrow_data.task_name is not None:
        #     borrow_apply.task_name = borrow_data.task_name
        #     update_fields.append("task_name")
        
        if borrow_data.name is not None:
            borrow_apply.name = borrow_data.name
            update_fields.append("name")

        if borrow_data.student_id is not None:
            borrow_apply.student_id = borrow_data.student_id
            update_fields.append("student_id")    
        
        if borrow_data.phone is not None:
            borrow_apply.phone = borrow_data.phone
            update_fields.append("phone")
        
        if borrow_data.email is not None:
            borrow_apply.email = borrow_data.email
            update_fields.append("email")
        
        if borrow_data.grade is not None:
            borrow_apply.grade = borrow_data.grade
            update_fields.append("grade")
        
        if borrow_data.major is not None:
            borrow_apply.major = borrow_data.major
            update_fields.append("major")
        
        if borrow_data.content is not None:
            borrow_apply.content = borrow_data.content
            update_fields.append("content")
        
        if borrow_data.deadline is not None:
            try:
                deadline_dt = StuffBorrow.parse_deadline(borrow_data.deadline)
                borrow_apply.deadline = deadline_dt
                update_fields.append("deadline")
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"时间格式错误: {str(e)}")
        
        if borrow_data.materials is not None:
            if not borrow_data.materials or len(borrow_data.materials) == 0:
                raise HTTPException(status_code=400, detail="必须至少选择一项借用物品")
            borrow_apply.materials = borrow_data.materials
            update_fields.append("materials")
        
        # 借物类型更新
        if borrow_data.type is not None:
            old_type = borrow_apply.type
            borrow_apply.type = borrow_data.type
            update_fields.append("type")
            
            # 如果类型从团队改为个人，清空团队相关字段
            if old_type == 1 and borrow_data.type == 0:
                borrow_apply.supervisor_name = ""
                borrow_apply.supervisor_phone = ""
                borrow_apply.project_number = ""
                update_fields.extend(["supervisor_name", "supervisor_phone", "project_number"])
        
        # 团队借物相关字段更新
        if borrow_data.supervisor_name is not None:
            borrow_apply.supervisor_name = borrow_data.supervisor_name
            update_fields.append("supervisor_name")
        
        if borrow_data.supervisor_phone is not None:
            borrow_apply.supervisor_phone = borrow_data.supervisor_phone
            update_fields.append("supervisor_phone")
        
        if borrow_data.project_number is not None:
            borrow_apply.project_number = borrow_data.project_number
            update_fields.append("project_number")
        
        # 如果是团队借物，验证必填字段
        if borrow_apply.type == 1:
            is_valid, errors = borrow_apply.validate_team_fields()
            if not is_valid:
                raise HTTPException(status_code=400, detail="; ".join(errors))
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="没有提供更新字段")
        
        # 保存更新
        borrow_apply.save()
        
        logger.info(f"用户 {current_user.userid} 更新了借物申请 {borrow_id}，更新字段: {update_fields}")
        
        return {
            "message": "借物申请更新成功",
            "status": "ok",
            "borrow_id": borrow_id,
            "updated_fields": update_fields,
            "data": borrow_apply.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新借物申请时出错: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@router.get("/test")
async def test_borrow():
    """测试借物申请路由"""
    return {
        "message": "借物申请模块工作正常",
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    }
@router.get("/applies/{borrow_id}")
async def get_borrow_apply_by_id(
    borrow_id: str,
    current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """
    根据借物申请ID获取详细信息
    
    Args:
        borrow_id: 借物申请ID
        current_user: 当前用户
        
    Returns:
        dict: 借物申请的完整信息
    """
    try:
        logger.info(f"用户 {current_user.userid} 查询借物申请详情: {borrow_id}")
        
        # 查找借物申请（只能查看自己的申请）
        borrow_apply = StuffBorrow.objects(
            borrow_id=borrow_id, 
            userid=current_user.userid
        ).first()
        
        if not borrow_apply:
            logger.warning(f"用户 {current_user.userid} 尝试访问不存在或无权限的申请: {borrow_id}")
            raise HTTPException(status_code=404, detail="未找到该借物申请或您无权访问")
        
        # 获取申请详情
        apply_data = borrow_apply.to_dict()
        
        # 添加额外的计算信息
        extra_info = {
            "is_overdue": borrow_apply.is_overdue(),
            "remaining_time": borrow_apply.get_remaining_time(),
            "materials_count": borrow_apply.get_materials_count(),
            "materials_summary": borrow_apply.get_materials_summary(),
            "can_edit": borrow_apply.status == 0,  # 只有待审批状态可编辑
            "can_cancel": borrow_apply.status in [0, 1],  # 待审批和已批准可取消
            "status_color": get_status_color(borrow_apply.status)  # 状态颜色
        }
        
        logger.info(f"成功获取借物申请 {borrow_id} 的详情")
        
        return {
            "message": "获取借物申请详情成功",
            "status": "ok",
            "borrow_id": borrow_id,
            "data": apply_data,
            "extra_info": extra_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取借物申请详情时出错: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

def get_status_color(status):
    """
    根据状态返回对应的颜色代码
    
    Args:
        status (int): 申请状态
        
    Returns:
        str: 颜色代码
    """
    color_map = {
        0: "#FFA500",  # 待审批 - 橙色
        1: "#4CAF50",  # 已批准 - 绿色
        2: "#2196F3",  # 已借出 - 蓝色
        3: "#9E9E9E",  # 已归还 - 灰色
        4: "#F44336",  # 已拒绝 - 红色
        5: "#FF5722"   # 已过期 - 深橙色
    }
    return color_map.get(status, "#000000")

@router.get("/applies/{borrow_id}/simple")
async def get_borrow_apply_simple(
    borrow_id: str,
    current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """
    获取借物申请的简化信息（仅基本字段）
    
    Args:
        borrow_id: 借物申请ID
        current_user: 当前用户
        
    Returns:
        dict: 借物申请的简化信息
    """
    try:
        # 查找借物申请
        borrow_apply = StuffBorrow.objects(
            borrow_id=borrow_id, 
            userid=current_user.userid
        ).first()
        
        if not borrow_apply:
            raise HTTPException(status_code=404, detail="未找到该借物申请")
        
        # 返回简化信息
        simple_data = {
            "borrow_id": borrow_apply.borrow_id,
            # "task_name": borrow_apply.task_name,
            "name": borrow_apply.name,
            "student_id": borrow_apply.student_id,
            "status": borrow_apply.status,
            "status_desc": borrow_apply.get_status_desc(borrow_apply.status),
            "materials_count": borrow_apply.get_materials_count(),
            "materials_summary": borrow_apply.get_materials_summary(),
            "deadline": borrow_apply.deadline.strftime('%Y-%m-%d') if borrow_apply.deadline else None,
            "created_at": borrow_apply.created_at.strftime('%Y-%m-%d %H:%M') if borrow_apply.created_at else None
        }
        
        return {
            "message": "获取成功",
            "status": "ok",
            "data": simple_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取借物申请简化信息时出错: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

# 管理员专用路由 - 可以查看任意申请
@router.get("/admin/applies/{borrow_id}")
async def get_any_borrow_apply(
    borrow_id: str,
    current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """
    管理员获取任意借物申请详情（不限制用户）
    
    Args:
        borrow_id: 借物申请ID
        current_user: 当前用户（需要管理员权限）
        
    Returns:
        dict: 借物申请的完整信息
    """
    try:
        # 检查管理员权限
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            raise HTTPException(status_code=403, detail="需要管理员权限")
        
        logger.info(f"管理员 {current_user.userid} 查询借物申请: {borrow_id}")
        
        # 查找借物申请（不限制用户）
        borrow_apply = StuffBorrow.objects(borrow_id=borrow_id).first()
        
        if not borrow_apply:
            raise HTTPException(status_code=404, detail="未找到该借物申请")
        
        # 获取申请用户信息
        from app.models.user import User as UserModel
        apply_user = UserModel.objects(userid=borrow_apply.userid).first()
        
        apply_data = borrow_apply.to_dict()
        
        # 添加申请用户信息
        if apply_user:
            apply_data["apply_user_info"] = {
                "real_name": apply_user.real_name,
                "userid": apply_user.userid,
                "role": getattr(apply_user, 'role', 'user')
            }
        
        # 添加管理信息
        admin_info = {
            "is_overdue": borrow_apply.is_overdue(),
            "remaining_time": borrow_apply.get_remaining_time(),
            "materials_count": borrow_apply.get_materials_count(),
            "can_approve": borrow_apply.status == 0,  # 可以审批
            "can_mark_borrowed": borrow_apply.status == 1,  # 可以标记为已借出
            "can_mark_returned": borrow_apply.status == 2,  # 可以标记为已归还
        }
        
        return {
            "message": "管理员获取借物申请详情成功",
            "status": "ok",
            "borrow_id": borrow_id,
            "data": apply_data,
            "admin_info": admin_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"管理员获取借物申请详情时出错: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

# 临时测试路由 - 不需要认证
@router.get("/test-applies/{borrow_id}")
async def get_borrow_apply_test(borrow_id: str):
    """
    测试路由 - 获取借物申请详情（不需要认证）
    """
    try:
        logger.info(f"测试获取借物申请详情: {borrow_id}")
        
        # 查找借物申请
        borrow_apply = StuffBorrow.objects(borrow_id=borrow_id).first()
        
        if not borrow_apply:
            return {
                "message": "未找到该借物申请",
                "status": "error",
                "borrow_id": borrow_id
            }
        
        return {
            "message": "测试获取成功",
            "status": "ok",
            "borrow_id": borrow_id,
            "data": borrow_apply.to_dict(),
            "test_mode": True
        }
        
    except Exception as e:
        logger.error(f"测试获取借物申请详情时出错: {e}")
        return {
            "message": f"获取失败: {str(e)}",
            "status": "error",
            "test_mode": True
        }
@router.get("/all-borrow-ids")
async def get_all_borrow_ids(
    current_user: User = Depends(AuthMiddleware.get_current_user),
    status: Optional[int] = Query(None, description="状态筛选"),
    limit: int = Query(100, le=500, description="返回数量限制"),
    offset: int = Query(0, description="偏移量")
):
    """
    获取当前用户所有借物申请的ID列表
    
    Args:
        current_user: 当前用户
        status: 状态筛选（可选）
        limit: 返回数量限制
        offset: 偏移量
        
    Returns:
        dict: 借物申请ID列表
    """
    try:
        logger.info(f"用户 {current_user.userid} 请求获取所有借物申请ID")
        
        # 构建查询条件（只查询当前用户的申请）
        query_filter = {"userid": current_user.userid}
        
        if status is not None:
            query_filter["status"] = status
            logger.info(f"按状态筛选: {status}")
        
        # 查询借物申请，只获取必要字段
        applies_query = StuffBorrow.objects(**query_filter).only(
            'borrow_id', 'status', 'created_at', 'deadline'
        ).order_by('-created_at')
        
        total_count = applies_query.count()
        applies = applies_query.skip(offset).limit(limit)
        
        # 构建ID列表，包含基本信息
        borrow_ids = []
        for apply in applies:
            borrow_ids.append({
                "borrow_id": apply.borrow_id,
                # "task_name": apply.task_name,
                "status": apply.status,
                "status_desc": StuffBorrow.get_status_desc(apply.status),
                "created_at": apply.created_at.strftime('%Y-%m-%d %H:%M') if apply.created_at else None,
                "deadline": apply.deadline.strftime('%Y-%m-%d') if apply.deadline else None
            })
        
        logger.info(f"返回 {len(borrow_ids)} 个借物申请ID")
        
        return {
            "message": "获取借物申请ID列表成功",
            "status": "ok", 
            "total_count": total_count,
            "returned_count": len(borrow_ids),
            "data": borrow_ids
        }
        
    except Exception as e:
        logger.error(f"获取借物申请ID列表时出错: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@router.get("/all-borrow-ids/simple")
async def get_all_borrow_ids_simple(
    current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """
    获取当前用户所有借物申请的ID（仅ID字符串列表）
    
    Args:
        current_user: 当前用户
        
    Returns:
        dict: 纯ID字符串列表
    """
    try:
        # 查询当前用户的所有申请，只获取ID
        applies = StuffBorrow.objects(userid=current_user.userid).only('borrow_id').order_by('-created_at')
        
        # 提取纯ID列表
        borrow_ids = [apply.borrow_id for apply in applies]
        
        return {
            "message": "获取成功",
            "status": "ok",
            "count": len(borrow_ids),
            "borrow_ids": borrow_ids
        }
        
    except Exception as e:
        logger.error(f"获取简单ID列表时出错: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@router.get("/admin/all-borrow-ids")
async def get_all_borrow_ids_admin(
    current_user: User = Depends(AuthMiddleware.get_current_user),
    userid: Optional[str] = Query(None, description="用户ID筛选"),
    status: Optional[int] = Query(None, description="状态筛选"),
    limit: int = Query(200, le=1000, description="返回数量限制"),
    offset: int = Query(0, description="偏移量")
):
    """
    管理员获取所有借物申请的ID列表（不限制用户）
    
    Args:
        current_user: 当前用户（需要管理员权限）
        userid: 用户ID筛选（可选）
        status: 状态筛选（可选）
        limit: 返回数量限制
        offset: 偏移量
        
    Returns:
        dict: 所有借物申请ID列表
    """
    try:
        # 检查管理员权限
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            raise HTTPException(status_code=403, detail="需要管理员权限")
        
        logger.info(f"管理员 {current_user.userid} 请求获取所有借物申请ID")
        
        # 构建查询条件
        query_filter = {}
        
        if userid:
            query_filter["userid"] = userid
            logger.info(f"按用户ID筛选: {userid}")
        
        if status is not None:
            query_filter["status"] = status
            logger.info(f"按状态筛选: {status}")
        
        # 查询借物申请
        applies_query = StuffBorrow.objects(**query_filter).only(
            'borrow_id', 'userid', 'status', 'created_at', 'deadline'
        ).order_by('-created_at')
        
        total_count = applies_query.count()
        applies = applies_query.skip(offset).limit(limit)
        
        # 构建详细信息列表
        borrow_data = []
        for apply in applies:
            borrow_data.append({
                "borrow_id": apply.borrow_id,
                # "task_name": apply.task_name,
                "userid": apply.userid,
                "status": apply.status,
                "status_desc": StuffBorrow.get_status_desc(apply.status),
                "created_at": apply.created_at.strftime('%Y-%m-%d %H:%M') if apply.created_at else None,
                "deadline": apply.deadline.strftime('%Y-%m-%d') if apply.deadline else None
            })
        
        # 统计信息
        stats = {
            "total_all": StuffBorrow.objects().count(),
            "pending": StuffBorrow.objects(status=0).count(),
            "approved": StuffBorrow.objects(status=1).count(),
            "borrowed": StuffBorrow.objects(status=2).count(),
            "returned": StuffBorrow.objects(status=3).count(),
            "rejected": StuffBorrow.objects(status=4).count(),
            "overdue": StuffBorrow.objects(status=5).count()
        }
        
        logger.info(f"管理员查询返回 {len(borrow_data)} 个借物申请")
        
        return {
            "message": "管理员获取所有借物申请ID成功",
            "status": "ok",
            "total_count": total_count,
            "returned_count": len(borrow_data),
            "stats": stats,
            "data": borrow_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"管理员获取所有借物申请ID时出错: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

# 临时测试路由 - 不需要认证
@router.get("/test-all-ids")
async def get_all_borrow_ids_test():
    """
    测试路由 - 获取所有借物申请ID（不需要认证）
    """
    try:
        logger.info("测试获取所有借物申请ID")
        
        # 查询最近20个申请
        applies = StuffBorrow.objects().only(
            'borrow_id', 'userid', 'status', 'created_at'
        ).order_by('-created_at').limit(20)
        
        test_data = []
        for apply in applies:
            test_data.append({
                "borrow_id": apply.borrow_id,
                # "task_name": apply.task_name,
                "userid": apply.userid,
                "status": apply.status,
                "status_desc": StuffBorrow.get_status_desc(apply.status),
                "created_at": apply.created_at.strftime('%Y-%m-%d %H:%M') if apply.created_at else None
            })
        
        return {
            "message": "测试获取成功",
            "status": "ok",
            "count": len(test_data),
            "data": test_data,
            "test_mode": True
        }
        
    except Exception as e:
        logger.error(f"测试获取所有ID时出错: {e}")
        return {
            "message": f"获取失败: {str(e)}",
            "status": "error",
            "test_mode": True
        }

@router.get("/borrow-ids/by-status/{status}")
async def get_borrow_ids_by_status(
    status: int,
    current_user: User = Depends(AuthMiddleware.get_current_user),
    limit: int = Query(50, le=200, description="返回数量限制")
):
    """
    根据状态获取借物申请ID列表
    
    Args:
        status: 申请状态 (0-5)
        current_user: 当前用户
        limit: 返回数量限制
        
    Returns:
        dict: 指定状态的借物申请ID列表
    """
    try:
        if status < 0 or status > 5:
            raise HTTPException(status_code=400, detail="状态值必须在0-5之间")
        
        logger.info(f"用户 {current_user.userid} 按状态 {status} 查询借物申请ID")
        
        # 查询指定状态的申请
        applies = StuffBorrow.objects(
            userid=current_user.userid, 
            status=status
        ).only(
            'borrow_id', 'created_at', 'deadline'
        ).order_by('-created_at').limit(limit)
        
        status_data = []
        for apply in applies:
            status_data.append({
                "borrow_id": apply.borrow_id,
                # "task_name": apply.task_name,
                "created_at": apply.created_at.strftime('%Y-%m-%d %H:%M') if apply.created_at else None,
                "deadline": apply.deadline.strftime('%Y-%m-%d') if apply.deadline else None
            })
        
        return {
            "message": f"获取{StuffBorrow.get_status_desc(status)}状态的申请成功",
            "status": "ok",
            "filter_status": status,
            "filter_status_desc": StuffBorrow.get_status_desc(status),
            "count": len(status_data),
            "data": status_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"按状态获取借物申请ID时出错: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")
@router.get("/applies/by-type/{type_value}")
async def get_applies_by_type(
    type_value: int,
    current_user: User = Depends(AuthMiddleware.get_current_user),
    limit: int = Query(50, le=200, description="返回数量限制")
):
    """
    根据借物类型获取申请列表
    
    Args:
        type_value: 借物类型 (0=个人, 1=团队)
        current_user: 当前用户
        limit: 返回数量限制
    """
    try:
        if type_value < 0 or type_value > 1:
            raise HTTPException(status_code=400, detail="类型值必须为0或1")
        
        applies = StuffBorrow.objects(
            userid=current_user.userid,
            type=type_value
        ).order_by('-created_at').limit(limit)
        
        result_data = []
        for apply in applies:
            result_data.append(apply.to_dict())
        
        return {
            "message": f"获取{StuffBorrow.get_type_desc(type_value)}申请成功",
            "status": "ok",
            "type": type_value,
            "type_desc": StuffBorrow.get_type_desc(type_value),
            "count": len(result_data),
            "data": result_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"按类型获取申请失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")