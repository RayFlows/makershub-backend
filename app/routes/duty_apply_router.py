from fastapi import APIRouter, HTTPException, Depends
from loguru import logger
from app.models.duty_apply import DutyApply
from app.models.user import User
from app.core.auth import AuthMiddleware
from pydantic import BaseModel, Field
from typing import List
import datetime

router = APIRouter()

class TimeSlot(BaseModel):
    """时间槽数据模型"""
    slot: int = Field(..., ge=1, le=3, description="时间槽编号(1-3)")
    week: str = Field(..., description="星期")
    time: str = Field(..., description="时间段描述")
    selected: bool = Field(..., description="是否选中")

class DutyApplyRequest(BaseModel):
    """值班申请请求数据模型"""
    timeSlots: List[TimeSlot] = Field(..., description="时间槽列表")
    submitTime: int = Field(..., description="提交时间戳")

@router.post("/post")
async def receive_duty_apply(
    data: DutyApplyRequest,
    current_user: User = Depends(AuthMiddleware.get_current_user)
):
    """
    接收值班申请数据并存储到数据库
    支持多次申请，后续申请会覆盖之前的内容
    
    Args:
        data: 包含时间槽信息的值班申请数据
        current_user: 从JWT token解析出的当前用户
        
    Returns:
        dict: 处理结果
    """
    try:
        logger.info(f"用户 {current_user.real_name}({current_user.userid}) 提交值班申请")
        logger.info(f"收到值班申请数据: {data.dict()}")
        
        # 过滤出被选中的时间槽（selected=True）
        selected_slots = [slot for slot in data.timeSlots if slot.selected]
        
        if len(selected_slots) == 0:
            raise HTTPException(
                status_code=400, 
                detail="必须至少选择1个时间段"
            )
        
        logger.info(f"用户选择了 {len(selected_slots)} 个时间段")
        
        # 检查用户是否已经提交过申请
        today = datetime.datetime.now().strftime('%Y%m%d')
        existing_apply = DutyApply.objects(
            userid=current_user.userid,
            apply_id__startswith=f"DA{today}"
        ).first()
        
        # 转换时间段描述为数字编号
        def get_time_section_number(time_desc: str) -> int:
            """根据时间描述获取时间段编号"""
            if not time_desc or time_desc.strip() == '':
                return 1  # 空字符串返回默认值
            
            time_mapping = {
                "08:10 - 10:05": 1,
                "10:15 - 12:20": 2,
                "12:30 - 14:30": 3,
                "14:30 - 16:30": 4,
                "16:30 - 18:30": 5,
                "18:30 - 20:30": 6
            }
            return time_mapping.get(time_desc, 1)
        
        # 准备存储的数据
        slots_to_store = selected_slots[:3]  # 只取前3个
        
        # 补齐到3个槽位（如果用户选择不足3个）
        while len(slots_to_store) < 3:
            default_slot = TimeSlot(
                slot=len(slots_to_store) + 1,
                week='星期一',
                time='08:10 - 10:05',
                selected=False
            )
            slots_to_store.append(default_slot)
        
        logger.info(f"准备存储的时间段数据:")
        for i, slot in enumerate(slots_to_store):
            logger.info(f"  槽位{i+1}: {slot.week} {slot.time} (选中:{slot.selected})")
        
        if existing_apply:
            # 如果存在已有申请，覆盖更新
            logger.info(f"发现已有申请 {existing_apply.apply_id}，将覆盖更新")
            
            # 更新现有申请的所有字段
            existing_apply.name = current_user.real_name  # 更新用户姓名（可能变更）
            existing_apply.day1 = slots_to_store[0].week
            existing_apply.time_section1 = get_time_section_number(slots_to_store[0].time)
            existing_apply.day2 = slots_to_store[1].week
            existing_apply.time_section2 = get_time_section_number(slots_to_store[1].time)
            existing_apply.day3 = slots_to_store[2].week
            existing_apply.time_section3 = get_time_section_number(slots_to_store[2].time)
            
            # 保存更新（updated_at会自动更新）
            existing_apply.save()
            
            apply_id = existing_apply.apply_id
            duty_apply = existing_apply
            action = "覆盖更新"
            
            logger.info(f"申请已覆盖更新，申请编号: {apply_id}")
            
        else:
            # 第一次申请，创建新记录
            apply_id = DutyApply.generate_apply_id()
            counter = 1
            base_apply_id = apply_id
            while DutyApply.objects(apply_id=apply_id).first():
                apply_id = f"{base_apply_id}_{counter:02d}"
                counter += 1
            
            # 创建新的申请记录
            duty_apply = DutyApply(
                apply_id=apply_id,
                name=current_user.real_name,
                userid=current_user.userid,
                day1=slots_to_store[0].week,
                time_section1=get_time_section_number(slots_to_store[0].time),
                day2=slots_to_store[1].week,
                time_section2=get_time_section_number(slots_to_store[1].time),
                day3=slots_to_store[2].week,
                time_section3=get_time_section_number(slots_to_store[2].time)
            )
            
            duty_apply.save()
            action = "新建"
            
            logger.info(f"新申请已创建，申请编号: {apply_id}")
        
        logger.info(f"值班申请已{action}到用户 {current_user.real_name}({current_user.userid}) 的数据库记录中")
        
        # 准备返回的选中时间段信息
        selected_time_info = []
        for slot in selected_slots:
            selected_time_info.append({
                "slot": slot.slot,
                "week": slot.week,
                "time": slot.time,
                "time_section_number": get_time_section_number(slot.time)
            })
        
        return {
            "message": f"值班申请{action}成功",
            "status": "ok",
            "apply_id": apply_id,
            "action": action,  # 告诉前端是新建还是覆盖更新
            "user_info": {
                "name": current_user.real_name,
                "userid": current_user.userid,
                "role": current_user.role
            },
            "selected_slots": {
                "count": len(selected_slots),
                "details": selected_time_info
            },
            "stored_data": duty_apply.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理值班申请时出错: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")
@router.get("/my-applies")
async def get_my_duty_applies(current_user: User = Depends(AuthMiddleware.get_current_user)):
    """获取当前用户的值班申请列表"""
    try:
        applies = DutyApply.objects(userid=current_user.userid).order_by('-created_at')
        return {
            "message": "获取成功",
            "status": "ok",
            "data": [apply.to_dict() for apply in applies]
        }
    except Exception as e:
        logger.error(f"获取用户值班申请列表时出错: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@router.get("/list")
async def get_duty_applies(current_user: User = Depends(AuthMiddleware.get_current_user)):
    """获取所有值班申请列表（需要管理员权限）"""
    try:
        # 检查用户权限（可选）
        if current_user.role < 2:  # 假设role>=2才能查看所有申请
            raise HTTPException(status_code=403, detail="权限不足")
        
        applies = DutyApply.objects().order_by('-created_at')
        return {
            "message": "获取成功",
            "status": "ok", 
            "data": [apply.to_dict() for apply in applies]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取值班申请列表时出错: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@router.get("/test")
async def test():
    """测试端点（不需要认证）"""
    return {"message": "duty_apply_router working", "status": "ok"}