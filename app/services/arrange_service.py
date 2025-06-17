from app.models.arrange import Arrange
from loguru import logger
from fastapi import HTTPException
from collections import defaultdict

class ArrangeService:
    """排班服务类：处理排班相关的业务逻辑"""
    
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
                    # 创建排班记录
                    arrange = Arrange(
                        arrange_id=Arrange.generate_arrange_id(),
                        name=arrange_data["name"],
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