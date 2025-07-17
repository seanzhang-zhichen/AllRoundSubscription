"""
API v1 主路由
"""
from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as user_router
from app.api.v1.membership import router as membership_router
from app.api.v1.subscriptions import router as subscription_router
from app.api.v1.content import router as content_router
from app.api.v1.content_detection import router as content_detection_router

# 创建主路由
api_router = APIRouter()

# 健康检查路由
@api_router.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "message": "API服务运行正常",
        "version": "1.0.0"
    }

# 注册认证路由
api_router.include_router(auth_router, prefix="/auth", tags=["认证"])

# 注册用户路由
api_router.include_router(user_router, prefix="/users", tags=["用户"])

# 注册会员路由
api_router.include_router(membership_router, prefix="/membership", tags=["会员"])

# 注册订阅路由
api_router.include_router(subscription_router, prefix="/subscriptions", tags=["订阅"])

# 注册内容路由
api_router.include_router(content_router, prefix="/content", tags=["内容"])

# 注册内容检测路由
api_router.include_router(content_detection_router, prefix="/content-detection", tags=["内容检测"])

# 注册推送通知路由
from app.api.v1.push_notifications import router as push_notifications_router
api_router.include_router(push_notifications_router, prefix="/push-notifications", tags=["推送通知"])

# 注册搜索路由
from app.api.v1.search import router as search_router
api_router.include_router(search_router, prefix="/search", tags=["搜索"])

# 注册监控路由
from app.api.v1.monitoring import router as monitoring_router
api_router.include_router(monitoring_router, prefix="/monitoring", tags=["监控"])