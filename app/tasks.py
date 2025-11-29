# app/tasks.py
"""
应用后台任务模块 (Application Background Tasks)

该模块定义了所有独立于API请求运行的后台任务，例如定时清理、数据同步等。
这些任务在应用启动时由 `main.py` 中的 startup 事件进行初始化和调度。
"""

import asyncio
from loguru import logger

from app.core.database import AsyncSessionLocal
from app.services.event_service import EventService
from app.services.project_service import ProjectService

async def cleanup_incomplete_events_task():
    """
    后台综合清理任务
    
    每隔 5 分钟执行一次，清理系统中的过期/僵尸数据。
    该任务独立于API请求运行，因此需要手动创建和管理数据库会e话。
    它会无限循环，每隔5分钟执行一次清理操作。
    """
    event_service = EventService()
    project_service = ProjectService()

    logger.info("🚀 后台[综合清理]任务已初始化，将在首次延迟后开始执行...")
    
    # 首次启动时先延迟，避免应用刚启动就立即执行
    await asyncio.sleep(300)

    while True:
        logger.info("[BG_TASK] 开始执行定期维护...")
        
        # 创建独立的数据库会话
        # 使用 `async with` 语句确保会话在使用后无论成功或失败都会被正确关闭。
        async with AsyncSessionLocal() as session:
            try:
                # --- 任务 1: 清理未完成活动 ---
                event_count = await event_service.cleanup_incomplete_events(db=session)
                if event_count > 0:
                    logger.success(f"[BG_TASK] 清理活动: {event_count} 个")
                
                # --- 任务 2: 清理项目僵尸文件 ---
                material_count = await project_service.cleanup_zombie_materials(db=session)
                if material_count > 0:
                    logger.success(f"[BG_TASK] 清理僵尸材料: {material_count} 个")

                # 统一提交事务
                await session.commit()
            
            except Exception as e:
                # 4. 异常时手动回滚
                logger.error(f"[BG_TASK] 清理任务执行失败: {e}", exc_info=True)
                await session.rollback()
        
        # 在每次循环的末尾，等待下一个周期
        await asyncio.sleep(300)