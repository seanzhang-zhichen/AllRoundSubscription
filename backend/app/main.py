"""
FastAPI应用主入口
"""
import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.exceptions import BusinessException
from app.core.middleware import RateLimitMiddleware, LoggingMiddleware, SecurityHeadersMiddleware
from app.core.monitoring import metrics_collector
from app.core.alerts import system_monitor
from app.api.v1.router import api_router
from app.api.v1.monitoring import router as monitoring_router
from app.db.database import engine, Base

# 设置日志
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file=os.getenv("LOG_FILE", "/app/logs/app.log"),
    enable_json=os.getenv("ENABLE_JSON_LOGS", "true").lower() == "true",
    enable_prometheus=os.getenv("ENABLE_PROMETHEUS", "true").lower() == "true"
)
logger = get_logger(__name__)

# 创建数据库表
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    logger.info("应用启动中...")
    
    # 创建数据库表
    await create_tables()
    logger.info("数据库表创建完成")
    
    # 启动系统监控
    monitoring_task = None
    if os.getenv("ENABLE_MONITORING", "true").lower() == "true":
        monitoring_task = asyncio.create_task(system_monitor.start_monitoring())
        logger.info("系统监控已启动")
    
    # 启动指标收集
    metrics_task = None
    if os.getenv("ENABLE_METRICS", "true").lower() == "true":
        async def collect_metrics_periodically():
            while True:
                try:
                    await metrics_collector.collect_all_metrics()
                    await asyncio.sleep(30)  # 每30秒收集一次指标
                except Exception as e:
                    logger.error(f"指标收集失败: {str(e)}")
                    await asyncio.sleep(30)
        
        metrics_task = asyncio.create_task(collect_metrics_periodically())
        logger.info("指标收集已启动")
    
    logger.info("应用启动完成")
    
    yield
    
    # 关闭时执行
    logger.info("应用关闭中...")
    
    # 停止监控任务
    if monitoring_task:
        system_monitor.stop_monitoring()
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
        logger.info("系统监控已停止")
    
    # 停止指标收集任务
    if metrics_task:
        metrics_task.cancel()
        try:
            await metrics_task
        except asyncio.CancelledError:
            pass
        logger.info("指标收集已停止")
    
    logger.info("应用关闭完成")

# 使用新的生命周期管理
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="多平台内容聚合API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# 添加中间件
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware, calls=100, period=60)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常处理
@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    logger.error(f"Business exception: {exc.message}", extra={
        "error_code": exc.error_code,
        "path": request.url.path
    })
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.error_code,
            "message": exc.message,
            "timestamp": int(exc.timestamp.timestamp())
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", extra={
        "path": request.url.path,
        "method": request.method
    }, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "服务器内部错误",
            "timestamp": int(__import__('time').time())
        }
    )

# 健康检查（保持简单版本用于负载均衡器）
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "服务运行正常"}

# 注册API路由
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(monitoring_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None  # 使用自定义日志配置
    )