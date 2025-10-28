#main.py
"""
MakerHub API 主应用入口文件

本文件定义了FastAPI应用实例，配置中间件、异常处理、数据库连接、
路由注册以及运行应用的入口点。采用了模块化架构，将各个功能分散到
不同的组件中，便于维护和扩展。

主要功能:
1. 应用初始化与配置
2. 中间件设置（日志、CORS、认证）
3. 异常处理
4. 数据库连接管理
5. API路由注册
6. 应用运行配置
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware  # 用于处理跨域资源共享
from fastapi.responses import JSONResponse  # 用于返回JSON格式响应
from fastapi.exceptions import RequestValidationError  # 请求参数验证错误类型
from loguru import logger  # 高级日志记录工具
from app.core.database import engine, Base  # 数据库连接管理
from app.core.config import settings  # 应用配置
from app.core.logging import setup_logging  # 日志配置
from app.core.auth import AuthMiddleware  # 自定义认证中间件
# from app.services.event_service import EventService
from app.models import ( 
    user, 
    stuff, 
    stuff_borrow, 
    borrow_item
) 
# 导入所有模型以确保SQLAlchemy能识别它们
import json
from app.routes import (
    # clean_router,
    # duty_apply_router,
    # duty_record_router,
    # event_router,
    # publicity_link_router,
    # site_borrow_router,
    site_router,
    stuff_router, 
    # stuff_borrow_router,
    # task_router,
    # arrange_router,
    user_router,
    admin_router,
    admin_stuff_router,
    admin_site_router,
    admin_user_router
)
import asyncio
# 初始化FastAPI应用

app = FastAPI(
    title="MakerHub API",  # API文档标题
    description="MakerHub后端API",  # API文档描述
    version="1.0.0",  # API版本号
    docs_url="/docs",  # Swagger UI文档地址
    redoc_url="/redoc",  # ReDoc文档地址
    openapi_url="/openapi.json"  # OpenAPI规范文档地址
)

# 请求日志中间件：记录所有请求和响应的详细信息
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    请求日志中间件
    
    记录所有HTTP请求和响应的详细信息，包括:
    - 请求方法和路径
    - 查询参数
    - 请求体（仅用于POST/PUT/PATCH请求）
    - 响应状态码
    
    Args:
        request: 当前HTTP请求
        call_next: 调用链中的下一个处理函数
        
    Returns:
        响应对象
    
    注意:
        读取请求体后确保重新设置request._receive，以便后续处理程序能够再次读取请求体
    """
    # 安全读取请求体
    request_body = None
    body = b""

    # 获取Content-Type
    content_type = request.headers.get("content-type", "")

    if request.method in ["POST", "PUT", "PATCH"] and "application/json" in content_type:
        try:
            # 读取原始请求体
            body = await request.body()
            if body:
                # 解析JSON但不消费流
                request_body = json.loads(body.decode('utf-8'))
                
                # 重要：重新设置请求体，让后续处理程序可以再次读取
                # 这是FastAPI/Starlette内部机制的一部分，确保请求体可被多次读取
                async def receive():
                    return {"type": "http.request", "body": body}
                request._receive = receive
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            request_body = {"error": f"Invalid JSON: {str(e)}"}
            logger.warning(f"Invalid JSON body for {request.method} {request.url.path}: {e}")
    # 对于文件上传请求，只记录是文件上传，不尝试解析内容
    elif "multipart/form-data" in content_type:
        # request_body = {"message": "File upload request (body not logged)"}
        try:
            # 1. 读取并保留原始请求体
            body = await request.body()
            
            # 2. 重置接收函数 (关键修复)
            async def receive():
                return {"type": "http.request", "body": body}
            request._receive = receive
            
            # 3. 记录元数据而非实际内容
            request_body = {
                "content_type": content_type,
                "file_size": len(body),
                "message": "File upload request (content not logged)"
            }
            logger.debug(f"文件上传请求 | 大小: {len(body)}字节")  # 新增调试日志
        except Exception as e:
            request_body = {"error": f"File read error: {str(e)}"}
            logger.error(f"文件读取失败: {str(e)}")

    # 记录请求信息
    logger.info(
        f"Request: {request.method} {request.url.path} - Query: {request.query_params} - Body: {request_body}"
    )
    
    # 调用下一个处理函数并获取响应
    response = await call_next(request)
    
    # 记录响应信息
    logger.info(
        f"Response: {response.status_code} {request.url.path}"
    )
    return response

# CORS配置：允许跨域资源共享
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # 允许的源列表，从配置中读取
    allow_credentials=True,  # 允许携带凭据
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
)

# 认证中间件：验证API请求的认证状态
# app.middleware("http")(AuthMiddleware())

# 异常处理：自定义请求验证错误的响应格式
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    请求验证错误处理器
    
    当请求参数验证失败时返回详细的错误信息
    
    Args:
        request: 当前HTTP请求
        exc: 验证错误异常
        
    Returns:
        包含详细错误信息的JSON响应
    """
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,  # 未处理的实体
        content={"detail": exc.errors(), "body": exc.body}  # 返回详细错误信息和原始请求体
    )

# 数据库连接管理：应用启动时连接数据库，关闭时断开连接
@app.on_event("startup")
async def startup_event():
    """
    应用启动事件处理

    在应用启动时执行初始化任务，包括：
    1. 配置日志系统。
    2. 初始化数据库，根据ORM模型创建所有尚不存在的表。
    3. 启动后台定时任务。
    """
    setup_logging()

    # --- 新的数据库初始化逻辑 ---
    # 使用异步上下文管理器 `engine.begin()` 来获取一个连接和事务。
    # 在这个块内，我们可以执行DDL（数据定义语言）命令，如创建表。
    async with engine.begin() as conn:
        # `Base.metadata.create_all`会检查数据库中是否存在所有继承自`Base`的模型所对应的表。
        # 如果表不存在，它会自动生成并执行`CREATE TABLE`语句来创建它们。
        # 注意：这不会处理表的修改或删除。在生产环境中，我们应使用Alembic这样的迁移工具
        # 来管理数据库模式的演变，而不是依赖`create_all`。
        await conn.run_sync(Base.metadata.create_all)

    # 启动后台清理任务
    # asyncio.create_task(cleanup_incomplete_events_task())
    # logger.info("应用启动 - 数据库表已初始化，清理任务已启动")

@app.on_event("shutdown")
async def shutdown_event():
    """
    应用关闭事件处理

    在应用关闭时执行清理任务，主要是安全地关闭数据库连接池。
    """
    # --- 新的数据库关闭逻辑 ---
    # `engine.dispose()`会关闭并丢弃引擎连接池中的所有连接。
    # 这是一个优雅关闭的步骤，确保没有挂起的连接。
    await engine.dispose()
    logger.info("应用关闭 - 数据库连接池已关闭")

# API路由注册：将各个模块的路由挂载到应用上

# 注册管理员路由
app.include_router(
    admin_router.router,  # 管理员相关API路由
    prefix="/admin/api",  # 使用独立的前缀避免冲突
    tags=["管理员后台"]    # API文档分类标签
)

app.include_router(
    admin_stuff_router.router,
    prefix="/admin/api/stuff",
    tags=["管理员物资管理"]
)

app.include_router(
    admin_site_router.router,
    prefix="/admin/api/site",
    tags=["管理员场地管理"]
)

app.include_router(
    admin_user_router.router,
    prefix="/admin/api/user",
    tags=["管理员用户管理"]
)

app.include_router(
    user_router.router,  # 用户相关API路由
    prefix="/users",     # 路由前缀
    tags=["用户管理"]    # API文档分类标签
)
# # 添加值班申请路由
# app.include_router(
#     duty_apply_router.router,  # 值班申请相关API路由
#     prefix="/duty-apply",      # 路由前缀
#     tags=["值班申请"]          # API文档分类标签
# )

# # 注册Event路由
# app.include_router(
#     event_router.router,  # event相关API路由
#     prefix="/events",     # 路由前缀
#     tags=["活动管理"]    # API文档分类标签
# )

# # 注册借物申请路由
# app.include_router(
#     stuff_borrow_router.router, 
#     prefix="/stuff-borrow", 
#     tags=["借物申请"]
# )

# 注册场地路由
app.include_router(
    site_router.router,
    prefix="/site",
    tags=["场地管理"]
)

# # 注册场地借用申请路由
# app.include_router(
#     site_borrow_router.router,
#     prefix="/sites-borrow",
#     tags=["场地借用申请"]
# )

# # 注册任务相关路由
# app.include_router(
#     task_router.router,  # 任务相关API路由
#     prefix="/tasks",     # 路由前缀
#     tags=["任务管理"]    # API文档分类标签
# )


# app.include_router(
#     publicity_link_router.router,  
#     prefix="/publicity-link",  
#     tags=["秀米链接"]  
# )


app.include_router(
    stuff_router.router,  # 物资相关API路由
    prefix="/stuff",      # 路由前缀
    tags=["物资管理"]       # API文档分类标签
)

# app.include_router(
#     arrange_router.router,  # 排班相关API路由
#     prefix="/arrange",  # 路由前缀
#     tags=["学年工作安排"]        # API文档分类标签
# )

# #健康检查端点：用于监控系统确认API是否正常运行
@app.get("/health")
async def health_check():
    """
    健康检查接口
    
    返回应用的健康状态和版本信息，用于监控系统检测API是否正常运行
    
    Returns:
        dict: 包含状态和版本信息的字典
    """
    return {"status": "healthy", "version": app.version}

# 根路径端点：API欢迎页
@app.get("/")
async def root():
    """
    API根路径
    
    返回API欢迎信息
    
    Returns:
        dict: 包含欢迎信息的字典
    """
    return {"message": "Welcome to MakerHub API!"}

# 应用入口点：直接运行此文件时启动应用
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",                # 应用实例的导入路径
        host=settings.HOST,        # 主机地址，从配置中读取
        port=settings.PORT,        # 端口，从配置中读取
        reload=settings.DEBUG,     # 是否启用热重载，生产环境应禁用
        workers=settings.WORKERS   # 工作进程数，影响并发处理能力
    )

# 添加后台任务函数
# async def cleanup_incomplete_events_task():
#     """定期清理未完成的事件任务"""
#     event_service = EventService()
#     while True:
#         try:
#             # 每5分钟执行一次清理
#             result = await event_service.cleanup_incomplete_events()
#             if "cleaned" in result:
#                 logger.info(f"清理未完成事件: {result['cleaned']}个")
#             elif "error" in result:
#                 logger.error(f"清理任务出错: {result['error']}")
#         except Exception as e:
#             logger.error(f"清理任务异常: {str(e)}")
        
#         # 等待5分钟
#         await asyncio.sleep(300)  # 300秒 = 5分钟