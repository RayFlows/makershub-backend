from typing import List, Dict, Any, Optional
from app.models.stuff_borrow import StuffBorrow
from mongoengine.errors import ValidationError, NotUniqueError
from datetime import datetime
import time
import random
import traceback

class StuffBorrowService:
    
    @staticmethod
    def create_stuff_borrow_application(application_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建借物申请"""
        print("=== 服务层开始处理 ===")
        try:
            print(f"S1. 收到申请数据: {application_data}")
            
            # 生成申请ID
            timestamp = int(time.time() * 1000)
            random_num = random.randint(100, 999)
            sb_id = f"SB{timestamp}{random_num}"
            print(f"S2. 生成申请ID: {sb_id}")
            
            # 解析截止时间
            deadline_str = application_data.get('deadline')
            deadline = None
            if deadline_str:
                try:
                    deadline = datetime.strptime(deadline_str, '%Y-%m-%d %H:%M:%S')
                    print(f"S3. 解析截止时间成功: {deadline}")
                except ValueError as e:
                    print(f"S3. 时间解析失败: {e}")
                    raise ValueError(f"时间格式错误: {deadline_str}")
            
            # 处理物资列表
            materials = application_data.get('materials', [])
            stuff_list = []
            for i, material in enumerate(materials):
                stuff_list.append({
                    "category": i,
                    "stuff": str(material)
                })
            print(f"S4. 物资列表处理完成: {stuff_list}")
            
            # 创建记录
            print("S5. 开始创建数据库记录...")
            
            new_application = StuffBorrow(
                sb_id=sb_id,
                user_id=str(application_data.get('user_id')),
                type=int(application_data.get('type', 0)),
                name=str(application_data.get('name')),
                student_id=str(application_data.get('student_id')),
                phone_num=str(application_data.get('phone')),
                email=str(application_data.get('email')),
                grade=str(application_data.get('grade')),
                major=str(application_data.get('major')),
                start_time=datetime.utcnow(),
                deadline=deadline,
                reason=str(application_data.get('content', '')),
                state=0,
                stuff_list=stuff_list
            )
            
            print("S6. 模型对象创建完成，准备保存...")
            new_application.save()
            print(f"S7. 保存成功: {sb_id}")
            
            return {
                "code": 200,
                "message": "申请提交成功",
                "data": {
                    "sb_id": sb_id
                }
            }
            
        except Exception as e:
            print(f"S8. 服务层异常: {str(e)}")
            print("S9. 异常堆栈:")
            traceback.print_exc()
            raise Exception(f"提交申请失败: {str(e)}")

    @staticmethod
    def get_user_stuff_borrow_list(user_id: str) -> Dict[str, Any]:
        """获取特定用户的所有借物记录"""
        try:
            borrow_records = StuffBorrow.objects(user_id=user_id)
            
            records_list = []
            for record in borrow_records:
                records_list.append({
                    "sb_id": record.sb_id,
                    "start_time": record.start_time.isoformat() + "Z" if record.start_time else None,
                    "deadline": record.deadline.isoformat() + "Z" if record.deadline else None,
                    "state": record.state
                })
            
            return {
                "code": 200,
                "message": "successfully get user stuff-borrow list",
                "data": {
                    "total": len(records_list),
                    "records": records_list
                }
            }
            
        except Exception as e:
            raise Exception(f"获取用户借物记录失败: {str(e)}")

    @staticmethod
    def get_stuff_borrow_detail(sb_id: str) -> Dict[str, Any]:
        """获取借物申请详情"""
        try:
            borrow_record = StuffBorrow.objects(sb_id=sb_id).first()
            
            if not borrow_record:
                raise ValueError("借物申请不存在")
            
            detail_data = {
                "type": borrow_record.type,
                "name": borrow_record.name,
                "student_id": borrow_record.student_id,
                "phone_num": borrow_record.phone_num,
                "email": borrow_record.email,
                "grade": borrow_record.grade,
                "major": borrow_record.major,
                "start_time": borrow_record.start_time.isoformat() + "Z" if borrow_record.start_time else None,
                "deadline": borrow_record.deadline.isoformat() + "Z" if borrow_record.deadline else None,
                "reason": borrow_record.reason,
                "state": borrow_record.state,
                "stuff_list": borrow_record.stuff_list or []
            }
            
            if borrow_record.type == 1:
                detail_data.update({
                    "project_num": borrow_record.project_num,
                    "mentor_name": borrow_record.mentor_name,
                    "mentor_phone_num": borrow_record.mentor_phone_num
                })
            
            return {
                "code": 200,
                "message": "successfully get stuff-borrow detail",
                "data": detail_data
            }
            
        except ValueError as e:
            raise e
        except Exception as e:
            raise Exception(f"获取借物详情失败: {str(e)}")

    @staticmethod
    def get_all_stuff_borrow_list() -> Dict[str, Any]:
        """获取所有借物申请记录"""
        try:
            all_records = StuffBorrow.objects()
            
            records_list = []
            for record in all_records:
                records_list.append({
                    "sb_id": record.sb_id,
                    "type": record.type,
                    "start_time": record.start_time.isoformat() + "Z" if record.start_time else None,
                    "state": record.state
                })
            
            return {
                "code": 200,
                "message": "successfully get all stuff-borrow list",
                "data": {
                    "total": len(records_list),
                    "records": records_list
                }
            }
            
        except Exception as e:
            raise Exception(f"获取所有借物记录失败: {str(e)}")