# app/core/database.py
"""
数据库核心模块 (Database Core Module)

该模块负责初始化与MySQL数据库的异步连接，并提供数据库会话管理的依赖注入功能。
它使用SQLAlchemy 2.0的异步API，为整个应用提供统一的、高效的数据库访问入口。
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from loguru import logger

# 从环境变量中获取数据库连接URL，这是连接数据库的唯一凭证
DATABASE_URL = os.getenv("DATABASE_URL")

# --- 数据库引擎 (Engine) ---
# 创建一个全局的异步数据库引擎实例。
# 引擎是SQLAlchemy与DBAPI（如aiomysql）交互的核心接口。
# echo=True: 会在控制台打印所有执行的SQL语句，非常适合在开发和调试阶段使用。
#            生产环境中应设置为False，以避免泄露敏感信息和性能开销。
# pool_pre_ping=True: 在每次从连接池中获取连接时，会先发送一个简单的 "ping" 查询来检查连接是否仍然有效。
#                    这能有效防止因数据库服务器断开空闲连接而导致的 "MySQL server has gone away" 错误。
engine = create_async_engine(DATABASE_URL, echo=True, pool_pre_ping=True)


# --- 数据库会话工厂 (Session Factory) ---
# 创建一个异步会话的工厂/构造器。
# 我们不直接实例化AsyncSession，而是通过这个工厂来按需创建新的会话。
# class_=AsyncSession: 指定使用SQLAlchemy的异步会话类。
# expire_on_commit=False: 这是一个关键设置。默认情况下，一旦事务被提交(commit)，
#                        所有从该会话加载的ORM对象都会过期。设置为False后，即使在提交后，
#                        这些对象依然可以被访问和使用，这在FastAPI的依赖注入模式中非常方便。
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# --- 声明式基类 (Declarative Base) ---
# 创建一个所有ORM模型都必须继承的基类。
# 当模型类继承自Base时，SQLAlchemy的声明式系统会自动将类定义映射到数据库的表结构。
# 我们所有的表元数据(metadata)都会被收集在这个Base.metadata对象中。
Base = declarative_base()


# --- 依赖注入 (Dependency Injection) ---
async def get_db() -> AsyncSession:
    """
    FastAPI依赖项，为每个API请求提供一个独立的数据库会话。

    该函数是一个异步生成器，它通过`AsyncSessionLocal`工厂创建一个新的数据库会话，
    使用`yield`关键字将该会话提供给路径操作函数（API接口），并在请求处理完毕后，
    无论成功或失败，都能确保会话被正确关闭。

    Yields:
        AsyncSession: 一个可用的、独立的SQLAlchemy异步数据库会话实例。
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # 如果路由函数执行完毕没有抛出任何HTTPException之外的异常，
            # 我们在这里显式地提交由该会话管理的主事务。
            logger.debug("[DB] Request finished successfully, committing transaction.")
            await session.commit()
            logger.success("[DB] Transaction committed.")
        except Exception as e:
            # 如果在请求处理过程中发生任何错误，回滚事务。
            logger.error(f"[DB] An error occurred during request, rolling back transaction: {e}")
            await session.rollback()
            logger.warning("[DB] Transaction rolled back.")
            # 重新抛出异常，以便FastAPI可以正确处理它
            raise