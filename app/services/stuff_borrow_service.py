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
    @staticmethod
    def review_stuff_borrow_application(review_data):
        """审核借物申请"""
        print(f"=== 服务层开始审核借物申请 ===")
        print(f"审核数据: {review_data}")
        
        try:
            borrow_id = review_data["borrow_id"]
            action = review_data["action"]
            reason = review_data.get("reason", "")
            reviewer_id = review_data["reviewer_id"]
            
            # 确定新状态
            new_state = 1 if action == "approve" else 2  # 1=通过, 2=打回
            
            print(f"申请ID: {borrow_id}, 操作: {action}, 新状态: {new_state}")
            
            # 使用正确的字段名 sb_id 进行查询
            existing_application = StuffBorrow.objects(sb_id=borrow_id).first()
            if not existing_application:
                print(f"申请不存在: {borrow_id}")
                raise ValueError(f"借物申请不存在: {borrow_id}")
            
            print(f"找到申请记录，当前申请状态: {existing_application.state}")
            
            # 更新申请状态
            from datetime import datetime, timezone
            
            existing_application.state = new_state
            existing_application.save()
            
            print(f"更新成功，新状态: {new_state}")
            
            return {
                "code": 200,
                "message": "审核成功",
                "data": {
                    "borrow_id": borrow_id,
                    "new_state": new_state,
                    "action": action
                }
            }
            
        except ValueError as ve:
            print(f"参数错误: {str(ve)}")
            raise ve
        except Exception as e:
            print(f"服务层审核失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"审核操作失败: {str(e)}")
    @staticmethod
    def update_stuff_quantity_after_borrow(update_data):
        """借物后更新物资余量"""
        print(f"=== 服务层开始更新物资余量 ===")
        print(f"更新数据: {update_data}")
        
        try:
            from app.models.stuff import Stuff
            
            borrow_id = update_data["borrow_id"]
            stuff_updates = update_data["stuff_updates"]
            operator_id = update_data["operator_id"]
            
            updated_stuff = []
            failed_updates = []
            
            print(f"开始处理 {len(stuff_updates)} 个物资更新")
            
            for update in stuff_updates:
                stuff_id = update.get("stuff_id")
                quantity = update.get("quantity", 0)
                
                if not stuff_id or quantity <= 0:
                    failed_updates.append(f"无效的物资ID或数量: {update}")
                    continue
                
                print(f"更新物资: {stuff_id}, 减少数量: {quantity}")
                
                # 查找物资
                stuff_item = Stuff.objects(stuff_id=stuff_id).first()
                if not stuff_item:
                    failed_updates.append(f"物资不存在: {stuff_id}")
                    continue
                
                # 检查余量是否足够
                if stuff_item.number_remain < quantity:
                    failed_updates.append(f"物资 {stuff_id} 余量不足，当前余量: {stuff_item.number_remain}, 需要: {quantity}")
                    continue
                
                # 更新余量
                old_remain = stuff_item.number_remain
                stuff_item.number_remain -= quantity
                stuff_item.save()
                
                updated_stuff.append({
                    "stuff_id": stuff_id,
                    "stuff_name": stuff_item.stuff_name,
                    "old_remain": old_remain,
                    "new_remain": stuff_item.number_remain,
                    "borrowed_quantity": quantity
                })
                
                print(f"物资 {stuff_id} 更新成功: {old_remain} -> {stuff_item.number_remain}")
            
            # 更新借物申请状态为已借出
            borrow_application = StuffBorrow.objects(sb_id=borrow_id).first()
            if borrow_application:
                borrow_application.state = 3  # 3 = 已借出
                borrow_application.save()
                print(f"借物申请 {borrow_id} 状态更新为已借出")
            
            return {
                "code": 200,
                "message": "物资余量更新完成",
                "data": {
                    "borrow_id": borrow_id,
                    "updated_stuff": updated_stuff,
                    "failed_updates": failed_updates,
                    "total_updates": len(stuff_updates),
                    "successful_updates": len(updated_stuff),
                    "failed_count": len(failed_updates)
                }
            }
            
        except Exception as e:
            print(f"服务层更新物资余量失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"更新物资余量失败: {str(e)}")

    @staticmethod
    def auto_update_stuff_quantity_from_application(sb_id, operator_id):
        """根据借物申请自动更新物资余量"""
        print(f"=== 服务层开始自动更新物资余量 ===")
        print(f"申请ID: {sb_id}")
        
        try:
            from app.models.stuff import Stuff
            
            # 获取借物申请详情
            borrow_application = StuffBorrow.objects(sb_id=sb_id).first()
            if not borrow_application:
                raise ValueError(f"借物申请不存在: {sb_id}")
            
            if borrow_application.state != 1:
                raise ValueError(f"借物申请未通过审核，当前状态: {borrow_application.state}")
            
            print(f"找到借物申请，物资列表: {borrow_application.stuff_list}")
            
            updated_stuff = []
            failed_updates = []
            
            # 处理申请中的物资列表
            for stuff_item in borrow_application.stuff_list:
                stuff_name = stuff_item.get("stuff")
                quantity = stuff_item.get("quantity", 1)  # 默认数量为1
                
                print(f"处理物资: {stuff_name}, 数量: {quantity}")
                
                # 根据物资名称查找物资（如果有stuff_id字段则用stuff_id）
                stuff_id = stuff_item.get("stuff_id")
                if stuff_id:
                    stuff_record = Stuff.objects(stuff_id=stuff_id).first()
                else:
                    stuff_record = Stuff.objects(stuff_name=stuff_name).first()
                
                if not stuff_record:
                    failed_updates.append(f"物资不存在: {stuff_name}")
                    continue
                
                # 检查余量
                if stuff_record.number_remain < quantity:
                    failed_updates.append(f"物资 {stuff_name} 余量不足，当前余量: {stuff_record.number_remain}, 需要: {quantity}")
                    continue
                
                # 更新余量
                old_remain = stuff_record.number_remain
                stuff_record.number_remain -= quantity
                stuff_record.save()
                
                updated_stuff.append({
                    "stuff_id": stuff_record.stuff_id,
                    "stuff_name": stuff_record.stuff_name,
                    "old_remain": old_remain,
                    "new_remain": stuff_record.number_remain,
                    "borrowed_quantity": quantity
                })
                
                print(f"物资 {stuff_name} 更新成功: {old_remain} -> {stuff_record.number_remain}")
            
            # 更新借物申请状态为已借出
            borrow_application.state = 3  # 3 = 已借出
            borrow_application.save()
            print(f"借物申请 {sb_id} 状态更新为已借出")
            
            return {
                "code": 200,
                "message": "自动更新物资余量完成",
                "data": {
                    "borrow_id": sb_id,
                    "updated_stuff": updated_stuff,
                    "failed_updates": failed_updates,
                    "total_items": len(borrow_application.stuff_list),
                    "successful_updates": len(updated_stuff),
                    "failed_count": len(failed_updates)
                }
            }
            
        except ValueError as ve:
            print(f"参数错误: {str(ve)}")
            raise ve
        except Exception as e:
            print(f"服务层自动更新物资余量失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"自动更新物资余量失败: {str(e)}")
