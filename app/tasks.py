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

async def cleanup_incomplete_events_task():
    """
    后台定时任务：定期清理未完成的活动。

    该任务独立于API请求运行，因此需要手动创建和管理数据库会e话。
    它会无限循环，每隔5分钟执行一次清理操作。
    """
    event_service = EventService()
    logger.info("🚀 后台[活动清理]任务已初始化，将在首次延迟后开始执行...")
    
    # 首次启动时先延迟，避免应用刚启动就立即执行
    await asyncio.sleep(300)

    while True:
        logger.info("[BG_TASK] 开始执行未完成活动清理...")
        
        # 1. 手动创建独立的数据库会话
        #    使用 `async with` 语句确保会话在使用后无论成功或失败都会被正确关闭。
        async with AsyncSessionLocal() as session:
            try:
                # 2. 调用服务层方法，并显式传入我们创建的会话
                cleaned_count = await event_service.cleanup_incomplete_events(db=session)
                
                # 3. 手动提交事务
                await session.commit()
                logger.success(f"[BG_TASK] 清理任务成功完成，清除了 {cleaned_count} 个活动。")
            
            except Exception as e:
                # 4. 异常时手动回滚
                logger.error(f"[BG_TASK] 清理任务执行失败: {e}", exc_info=True)
                await session.rollback()
        
        # 在每次循环的末尾，等待下一个周期
        await asyncio.sleep(300)