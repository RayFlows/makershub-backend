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
            
            # 基本字段
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
            
            # 处理团队借物的额外字段
            borrow_type = int(application_data.get('type', 0))
            if borrow_type == 1:  # 团队借物
                print("S5.1. 处理团队借物额外字段...")
                
                # 获取团队借物的额外字段
                project_number = application_data.get('project_number')
                supervisor_name = application_data.get('supervisor_name')
                supervisor_phone = application_data.get('supervisor_phone')
                
                print(f"S5.2. 团队借物字段: project_number={project_number}, supervisor_name={supervisor_name}, supervisor_phone={supervisor_phone}")
                
                # 设置团队借物的额外字段
                if project_number:
                    new_application.project_number = str(project_number)
                if supervisor_name:
                    new_application.supervisor_name = str(supervisor_name)
                if supervisor_phone:
                    new_application.supervisor_phone = str(supervisor_phone)
                    
                print("S5.3. 团队借物字段设置完成")
            
            print("S6. 模型对象创建完成，准备保存...")
            new_application.save()
            print(f"S7. 保存成功: {sb_id}")
            
            # 验证保存结果
            saved_record = StuffBorrow.objects(sb_id=sb_id).first()
            if saved_record and borrow_type == 1:
                print(f"S8. 验证团队借物字段保存情况:")
                print(f"  - project_number: {saved_record.project_number}")
                print(f"  - supervisor_name: {saved_record.supervisor_name}")
                print(f"  - supervisor_phone: {saved_record.supervisor_phone}")
            
            return {
                "code": 200,
                "message": "申请提交成功",
                "data": {
                    "sb_id": sb_id,
                    "type": borrow_type
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
                    "name": record.name,
                    "grade": record.grade,
                    "major": record.major,
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
                "sb_id": borrow_record.sb_id,  # 添加申请ID
                "type": borrow_record.type,
                "name": borrow_record.name,
                "student_id": borrow_record.student_id,
                "phone_num": borrow_record.phone_num,
                "email": borrow_record.email,
                "grade": borrow_record.grade,
                "major": borrow_record.major,
                "review": borrow_record.review,
                "start_time": borrow_record.start_time.isoformat() + "Z" if borrow_record.start_time else None,
                "deadline": borrow_record.deadline.isoformat() + "Z" if borrow_record.deadline else None,
                "reason": borrow_record.reason,
                "state": borrow_record.state,
                "stuff_list": borrow_record.stuff_list or []
            }
            
            # 如果是团队借物，添加额外字段
            if borrow_record.type == 1:
                detail_data.update({
                    "project_number": borrow_record.project_number,
                    "supervisor_name": borrow_record.supervisor_name,
                    "supervisor_phone": borrow_record.supervisor_phone
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
                    "name": record.name,
                    "major": record.major,
                    "grade": record.grade,
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
            
            # ✅ 根据新定义映射审核操作到状态值
            if action == "approve":
                new_state = 2  # 已通过
            elif action == "reject":
                new_state = 1  # 已打回
            else:
                raise ValueError(f"无效的操作类型: {action}")
            
            print(f"申请ID: {borrow_id}, 操作: {action}, 新状态: {new_state}")
            
            # 查询申请记录
            existing_application = StuffBorrow.objects(sb_id=borrow_id).first()
            if not existing_application:
                print(f"申请不存在: {borrow_id}")
                raise ValueError(f"借物申请不存在: {borrow_id}")
            
            print(f"[INFO] 找到申请记录，当前状态: {existing_application.state}")
            
            # ✅ 设置新状态
            existing_application.state = new_state
            existing_application.save()
            print(f"[DEBUG] 状态保存完毕: {new_state}")
            
            # 可选：保存审核理由
            if reason:
                existing_application.review = reason  # 确保模型中有该字段
                existing_application.save()
                print(f"[DEBUG] 审核理由保存完毕: {reason}")
            
            # 验证保存成功
            updated_application = StuffBorrow.objects(sb_id=borrow_id).first()
            if updated_application.state != new_state:
                raise Exception(f"状态更新失败！期望: {new_state}, 实际: {updated_application.state}")
            
            print(f"[SUCCESS] 审核成功，新状态: {new_state}")
            
            return {
                "code": 200,
                "message": "审核成功",
                "data": {
                    "borrow_id": borrow_id,
                    "new_state": new_state,
                    "action": action,
                    "reason": reason,
                    "current_state": updated_application.state
                }
            }
            
        except ValueError as ve:
            print(f"[ERROR] 参数错误: {str(ve)}")
            raise ve
        except Exception as e:
            print(f"[ERROR] 服务层审核失败: {str(e)}")
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
            import time
            import re

            # 等待一秒确保审核状态已保存
            time.sleep(1)

            # 获取借物申请详情
            borrow_application = StuffBorrow.objects(sb_id=sb_id).first()
            if not borrow_application:
                raise ValueError(f"借物申请不存在: {sb_id}")

            print(f"[DEBUG] 当前申请状态: {borrow_application.state}")

            if borrow_application.state != 2:  # 2 = 已通过
                raise ValueError(f"借物申请未通过审核，当前状态: {borrow_application.state}")

            print(f"找到借物申请，物资列表: {borrow_application.stuff_list}")

            # 获取所有物资
            all_stuff = Stuff.objects()
            print(f"[DEBUG] 数据库中共有 {len(all_stuff)} 个物资:")
            for stuff in all_stuff:
                print(f"  - Type: {stuff.type}, 名称: '{stuff.stuff_name}', 余量: {stuff.number_remain}")

            updated_stuff = []
            failed_updates = []
            insufficient_items = []

            # === 第一步：预校验每一项是否满足余量 ===
            for stuff_item in borrow_application.stuff_list:
                print("stuff_item: ", stuff_item)

                match = re.match(r'^\s*(.+?)\s*-\s*(.+?)\s*-\s*(\d+)\s*$', stuff_item['stuff'])
                if match:
                    category = match.group(1)
                    name = match.group(2)
                    quantity = int(match.group(3))
                else:
                    insufficient_items.append("物资格式不匹配")
                    continue

                matched = False
                for stuff in all_stuff:
                    if stuff.type == category and stuff.stuff_name == name:
                        matched = True
                        if stuff.number_remain < quantity:
                            msg = f"物资 '{name}' 余量不足，当前: {stuff.number_remain}，需要: {quantity}"
                            insufficient_items.append(msg)
                        break

                if not matched:
                    insufficient_items.append(f"未找到匹配物资: {name}")

            # === 如果有任何不满足的，强制状态改为未审核，并返回错误 ===
            if insufficient_items:
                print(f"[CHECK FAILED] 以下物资余量不足，取消扣减操作: {insufficient_items}")

                borrow_application.state = 0
                borrow_application.save()
                print("[ROLLBACK] 余量不足，已将申请状态重置为待审核 (state=0)")

                return {
                    "code": 400,
                    "message": "部分物资余量不足，申请状态已重置为待审核",
                    "data": {
                        "borrow_id": sb_id,
                        "errors": insufficient_items
                    }
                }

            # === 第二步：正式执行余量扣减 ===
            for stuff_item in borrow_application.stuff_list:
                match = re.match(r'^\s*(.+?)\s*-\s*(.+?)\s*-\s*(\d+)\s*$', stuff_item['stuff'])
                if not match:
                    continue

                category = match.group(1)
                name = match.group(2)
                quantity = int(match.group(3))

                for stuff in all_stuff:
                    if stuff.type == category and stuff.stuff_name == name:
                        old_remain = stuff.number_remain
                        stuff.number_remain -= quantity
                        stuff.save()

                        updated_stuff.append({
                            "stuff_id": stuff.stuff_id,
                            "stuff_name": name,
                            "old_remain": old_remain,
                            "new_remain": stuff.number_remain,
                            "borrowed_quantity": quantity
                        })

                        print(f"[SUCCESS] 物资 {name} 更新成功: {old_remain} -> {stuff.number_remain}")
                        break

            # === 状态保持不变 ===
            print(f"[INFO] 物资余量更新完成，申请状态保持为: {borrow_application.state}")

            print(f"[SUMMARY] 总物资: {len(borrow_application.stuff_list)}, 成功更新: {len(updated_stuff)}, 失败: {len(failed_updates)}")
            if failed_updates:
                print(f"[FAILED_DETAILS] 失败原因: {failed_updates}")

            return {
                "code": 200,
                "message": "自动更新物资余量完成",
                "data": {
                    "borrow_id": sb_id,
                    "updated_stuff": updated_stuff,
                    "failed_updates": failed_updates,
                    "total_items": len(borrow_application.stuff_list),
                    "successful_updates": len(updated_stuff),
                    "failed_count": len(failed_updates),
                    "final_state": borrow_application.state
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

    @staticmethod
    def confirm_stuff_return(return_data):
        """确认物资归还"""
        print(f"=== 服务层开始确认物资归还 ===")
        print(f"归还数据: {return_data}")
        
        try:
            borrow_id = return_data["borrow_id"]
            return_notes = return_data.get("return_notes", "")
            operator_id = return_data["operator_id"]
            
            print(f"申请ID: {borrow_id}, 操作员ID: {operator_id}")
            
            # 使用正确的字段名 sb_id 进行查询
            existing_application = StuffBorrow.objects(sb_id=borrow_id).first()
            if not existing_application:
                print(f"借物申请不存在: {borrow_id}")
                raise ValueError(f"借物申请不存在: {borrow_id}")
            
            print(f"[INFO] 找到申请记录，当前状态: {existing_application.state}")
            
            # 检查当前状态，只有已通过的申请才能归还
            if existing_application.state not in [2]:
                status_map = {0: "未审核", 1: "已打回", 2: "已通过", 3: "已归还"}
                current_status = status_map.get(existing_application.state, "未知状态")
                raise ValueError(f"当前状态不允许归还操作，当前状态: {current_status}")
            
            # 更新申请状态为已归还
            old_state = existing_application.state
            existing_application.state = 3  # 3 = 已归还
            
            # 可以添加归还时间和备注字段（如果模型支持的话）
            from datetime import datetime, timezone
            # existing_application.return_time = datetime.now(timezone.utc)
            # existing_application.return_notes = return_notes
            
            print(f"[DEBUG] 即将保存新状态到数据库: state = 3 (已归还)")
            existing_application.save()
            print(f"[DEBUG] save() 执行完毕")
            
            # 重新查询确认状态已更新
            updated_application = StuffBorrow.objects(sb_id=borrow_id).first()
            print(f"[DEBUG] 重新查询后的状态值: {updated_application.state}")
            
            if updated_application.state != 3:
                print(f"[ERROR] 状态更新失败！期望: 3, 实际: {updated_application.state}")
                raise Exception("状态更新失败")
            
            print(f"归还确认成功，状态从 {old_state} 更新为 3")
            
            return {
                "code": 200,
                "message": "物资归还确认成功",
                "data": {
                    "borrow_id": borrow_id,
                    "old_state": old_state,
                    "new_state": 3,
                    "return_notes": return_notes,
                    "operator_id": operator_id
                }
            }
            
        except ValueError as ve:
            print(f"参数错误: {str(ve)}")
            raise ve
        except Exception as e:
            print(f"服务层归还确认失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"归还确认操作失败: {str(e)}")
    @staticmethod
    def restore_stuff_quantity_from_return(sb_id, operator_id):
        """归还时恢复物资数量"""
        print(f"=== 服务层开始恢复物资数量 ===")
        print(f"申请ID: {sb_id}")
        
        try:
            from app.models.stuff import Stuff
            
            # 获取借物申请详情
            borrow_application = StuffBorrow.objects(sb_id=sb_id).first()
            if not borrow_application:
                raise ValueError(f"借物申请不存在: {sb_id}")
            
            print(f"[DEBUG] 当前申请状态: {borrow_application.state}")
            print(f"找到借物申请，物资列表: {borrow_application.stuff_list}")
            
            # 调试：查看数据库中所有物资
            all_stuff = Stuff.objects()
            print(f"[DEBUG] 数据库中共有 {len(all_stuff)} 个物资:")
            for stuff in all_stuff:
                print(f"  - ID: {stuff.stuff_id}, 类型: {stuff.type}, 名称: '{stuff.stuff_name}', 余量: {stuff.number_remain}")
            
            restored_stuff = []
            failed_restores = []
            
            # 处理申请中的物资列表
            for stuff_item in borrow_application.stuff_list:
                print("stuff_item: ", stuff_item)
                import re

                # stuff_item = {'category': 0, 'stuff': '开发板 - ESP-32-WROOM - 2'}
                match = re.match(r'^\s*(.+?)\s*-\s*(.+?)\s*-\s*(\d+)\s*$', stuff_item['stuff'])

                if match:
                    category = match.group(1).strip()   # '开发板'
                    name = match.group(2).strip()       # 'ESP-32-WROOM'
                    quantity = int(match.group(3))      # '2' 转为整数
                    print(f"解析物资: 类型='{category}', 名称='{name}', 数量={quantity}")
                else:
                    print("格式不匹配，跳过此物资")
                    failed_restores.append(f"物资格式不匹配: {stuff_item['stuff']}")
                    continue

                print(f"处理物资归还: '{name}', 数量: {quantity}")
                
                if not name:
                    failed_restores.append("物资名称为空")
                    continue
                
                # 查找匹配的物资并恢复数量
                found = False
                for stuff in all_stuff:
                    if stuff.type == category and stuff.stuff_name == name:
                        # 恢复数量（增加）
                        old_remain = stuff.number_remain
                        stuff.number_remain += quantity  # 注意这里是加法，不是减法
                        stuff.save()

                        print(f"stuff.stuff_id: {stuff.stuff_id}")
                        print(f"stuff.number_remain (new): {stuff.number_remain}")
                        print(f"stuff.stuff_name: {name}")
                        print(f"old_remain: {old_remain}")
                        print(f"quantity (restored): {quantity}")

                        restored_stuff.append({
                            "stuff_id": stuff.stuff_id,
                            "stuff_name": name,
                            "old_remain": old_remain,
                            "new_remain": stuff.number_remain,
                            "restored_quantity": quantity
                        })
                
                        print(f"[SUCCESS] 物资 {name} 数量恢复成功: {old_remain} -> {stuff.number_remain}")
                        found = True
                        break
                
                if not found:
                    failed_restores.append(f"未找到匹配的物资: 类型={category}, 名称={name}")
                    print(f"[WARNING] 未找到匹配的物资: {category} - {name}")
            
            # 打印详细的执行结果
            print(f"[SUMMARY] 总物资: {len(borrow_application.stuff_list)}, 成功恢复: {len(restored_stuff)}, 失败: {len(failed_restores)}")
            if failed_restores:
                print(f"[FAILED_DETAILS] 失败原因: {failed_restores}")
            
            return {
                "code": 200,
                "message": "物资数量恢复完成",
                "data": {
                    "borrow_id": sb_id,
                    "restored_stuff": restored_stuff,
                    "failed_restores": failed_restores,
                    "total_items": len(borrow_application.stuff_list),
                    "successful_restores": len(restored_stuff),
                    "failed_count": len(failed_restores)
                }
            }
            
        except ValueError as ve:
            print(f"参数错误: {str(ve)}")
            raise ve
        except Exception as e:
            print(f"服务层恢复物资数量失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"恢复物资数量失败: {str(e)}")
    @staticmethod
    def cancel_stuff_borrow_application(sb_id: str, user_id: str) -> Dict[str, Any]:
        """取消借物申请"""
        print(f"=== 服务层开始取消借物申请 ===")
        print(f"申请ID: {sb_id}, 用户ID: {user_id}")
        
        try:
            # 查找借物申请
            borrow_application = StuffBorrow.objects(sb_id=sb_id).first()
            if not borrow_application:
                print(f"借物申请不存在: {sb_id}")
                raise ValueError(f"借物申请不存在: {sb_id}")
            
            print(f"[INFO] 找到申请记录，当前状态: {borrow_application.state}")
            print(f"[INFO] 申请用户ID: {borrow_application.user_id}, 请求用户ID: {user_id}")
            
            # 验证申请是否属于当前用户
            if str(borrow_application.user_id) != str(user_id):
                print(f"[ERROR] 权限验证失败")
                raise ValueError("无权限取消此申请")
            
            # 检查申请状态，只有未审核(0)和已打回(2)的申请可以取消
            if borrow_application.state not in [0, 2]:
                status_map = {0: "未审核", 1: "已通过", 2: "已打回", 3: "已归还"}
                current_status = status_map.get(borrow_application.state, "未知状态")
                print(f"[ERROR] 当前状态不允许取消: {current_status}")
                raise ValueError(f"当前状态不允许取消操作，当前状态: {current_status}")
            
            # 记录要删除的申请信息
            deleted_info = {
                "sb_id": borrow_application.sb_id,
                "user_id": borrow_application.user_id,
                "name": borrow_application.name,
                "state": borrow_application.state,
                "start_time": borrow_application.start_time.isoformat() + "Z" if borrow_application.start_time else None,
                "stuff_count": len(borrow_application.stuff_list) if borrow_application.stuff_list else 0
            }
            
            print(f"[INFO] 准备删除申请: {deleted_info}")
            
            # 删除申请记录
            borrow_application.delete()
            print(f"[SUCCESS] 申请 {sb_id} 已成功删除")
            
            # 验证删除结果
            check_deleted = StuffBorrow.objects(sb_id=sb_id).first()
            if check_deleted:
                print(f"[ERROR] 删除验证失败，记录仍存在")
                raise Exception("删除操作未成功执行")
            
            print(f"[SUCCESS] 删除验证通过，记录已完全移除")
            
            return {
                "code": 200,
                "message": "借物申请已成功取消",
                "data": {
                    "cancelled_application": deleted_info,
                    "cancel_time": datetime.utcnow().isoformat() + "Z"
                }
            }
            
        except ValueError as ve:
            print(f"参数错误: {str(ve)}")
            raise ve
        except Exception as e:
            print(f"服务层取消申请失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"取消申请操作失败: {str(e)}")