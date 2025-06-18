from app.models.arrange import Arrange
from app.models.user import User
from loguru import logger
from fastapi import HTTPException
from collections import defaultdict

class ArrangeService:
    """排班服务类：处理排班相关的业务逻辑"""
    
    async def switch_to_next_arranger(self, task_type: int) -> bool:
        """
        切换到下一个值班人员
        
        步骤：
        1. 找到当前值班人员（current=True）的记录
        2. 将当前值班人员的current设为False
        3. 找到下一个值班人员（按order顺序，循环查找）
        4. 将下一个值班人员的current设为True
        5. 保存到数据库
        
        Args:
            task_type: 任务类型 (1,2,3)
            
        Returns:
            bool: 切换是否成功
        """
        try:
            # 获取该任务类型的所有排班记录，按order排序
            arrangements = list(Arrange.objects(task_type=task_type).order_by("order"))
            if not arrangements:
                logger.warning(f"没有找到任务类型 {task_type} 的排班记录")
                return False
            
            # 查找当前值班人员
            current_index = -1
            for idx, arrange in enumerate(arrangements):
                if arrange.current:
                    current_index = idx
                    break
            
            if current_index == -1:
                logger.warning(f"未找到当前值班人员 | 任务类型: {task_type}")
                # 如果没有当前值班人员，则设置第一个为当前
                arrangements[0].current = True
                arrangements[0].save()
                return True
            
            # 将当前值班人员设为False
            arrangements[current_index].current = False
            arrangements[current_index].save()
            
            # 计算下一个索引（循环）
            next_index = (current_index + 1) % len(arrangements)
            
            # 将下一个设为当前
            arrangements[next_index].current = True
            arrangements[next_index].save()
            
            logger.info(f"排班切换成功 | 任务类型: {task_type} | 当前: {arrangements[current_index].name} -> 下一个: {arrangements[next_index].name}")
            return True
        except Exception as e:
            logger.error(f"排班切换失败: {str(e)}")
            return False

    async def get_all_arrangements(self):
        """
        获取所有排班安排
        
        Returns:
            dict: 按任务类型分组的排班安排
        """
        try:
            # 获取所有排班记录，按任务类型和顺序排序
            arrangements = Arrange.objects().order_by("task_type", "order")
            
            # 按任务类型分组
            grouped = defaultdict(list)
            for arrange in arrangements:
                # 只返回必要字段
                grouped[str(arrange.task_type)].append({
                    "name": arrange.name,
                    "maker_id": arrange.maker_id,  # 新增字段
                    "order": arrange.order,
                    "current": arrange.current
                })
            
            # 确保所有任务类型都存在（即使没有数据）
            result = {
                "1": grouped.get("1", []),  # 活动文案
                "2": grouped.get("2", []),  # 推文
                "3": grouped.get("3", [])   # 新闻稿
            }
            
            return result
        except Exception as e:
            logger.error(f"获取所有排班安排失败: {str(e)}")
            raise HTTPException(status_code=500, detail="获取排班安排失败")
    
    async def batch_create_arrangements(self, arrangements_data: dict):
        """
        批量创建排班安排
        
        Args:
            arrangements_data: 包含所有任务类型排班数据的字典
            
        Returns:
            dict: 包含创建总数和类型列表的结果
        """
        try:
            # 先删除所有现有排班记录
            Arrange.objects().delete()
            
            # 创建新排班记录
            total_created = 0
            created_types = []
            
            # 遍历每种任务类型
            for task_type_str, arrangement_list in arrangements_data.items():
                # 验证类型是否有效
                if task_type_str not in ["1", "2", "3"]:
                    logger.warning(f"跳过无效的任务类型: {task_type_str}")
                    continue
                
                # 转换为整数类型
                task_type = int(task_type_str)
                
                # 遍历该类型下的人员安排
                for arrange_data in arrangement_list:
                    # 验证maker_id是否存在
                    if "maker_id" not in arrange_data:
                        logger.warning(f"人员数据缺少maker_id: {arrange_data}")
                        continue
                    
                    # 创建排班记录
                    arrange = Arrange(
                        arrange_id=Arrange.generate_arrange_id(),
                        name=arrange_data["name"],
                        maker_id=arrange_data["maker_id"],
                        task_type=task_type,
                        order=arrange_data["order"],
                        current=arrange_data["current"]
                    )
                    arrange.save()
                    total_created += 1
                
                created_types.append(task_type_str)
            
            logger.info(f"批量创建排班成功 | 总数: {total_created} | 类型: {', '.join(created_types)}")
            return {
                "total_created": total_created,
                "types": created_types
            }
        except Exception as e:
            logger.error(f"批量创建排班失败: {str(e)}")
            raise HTTPException(status_code=500, detail="批量创建排班失败")
    
    async def get_current_arranger(self, task_type: int):
        """
        获取当前值班人员
        
        Args:
            task_type: 任务类型 (1,2,3)
            
        Returns:
            dict: 当前值班人员信息 (包含name和maker_id)
        """
        try:
            # 查询当前值班人员
            arrangement = Arrange.objects(
                task_type=task_type,
                current=True
            ).first()
            
            if not arrangement:
                logger.warning(f"未找到任务类型 {task_type} 的当前值班人员")
                return None
            
            return {
                "name": arrangement.name,
                "maker_id": arrangement.maker_id
            }
        except Exception as e:
            logger.error(f"获取当前值班人员失败: {str(e)}")
            return None

    async def get_current_makers(self) -> list:
        """
        获取本次宣传部三个任务对应的值班人员
        
        Returns:
            list: 包含三个任务当前值班人员信息的列表
        """
        try:
            result = []
            # 获取三种任务类型的当前值班人员
            for task_type in [1, 2, 3]:
                arrangement = Arrange.objects(
                    task_type=task_type,
                    current=True
                ).first()
                
                if arrangement:
                    result.append({
                        "task_type": task_type,
                        "name": arrangement.name,
                        "maker_id": arrangement.maker_id
                    })
                else:
                    # 如果没有找到当前值班人员，返回空信息
                    result.append({
                        "task_type": task_type,
                        "name": "",
                        "maker_id": ""
                    })
                    logger.warning(f"未找到任务类型 {task_type} 的当前值班人员")
            
            return result
        except Exception as e:
            logger.error(f"获取当前值班人员失败: {str(e)}")
            # 返回默认结构
            return [
                {"task_type": 1, "name": "", "maker_id": ""},
                {"task_type": 2, "name": "", "maker_id": ""},
                {"task_type": 3, "name": "", "maker_id": ""}
            ]