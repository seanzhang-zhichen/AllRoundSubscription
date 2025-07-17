"""
服务层模块
"""
from app.services.membership import membership_service, MembershipConfig
from app.services.limits import limits_service
from app.services.subscription import subscription_service
from app.services.search import search_service
from app.services.content import content_service
from app.services.image import image_service
from app.services.platform import platform_service
from app.services.refresh import refresh_service

# 导入注册器以自动注册所有适配器
from app.services.search import registry

__all__ = [
    "membership_service",
    "MembershipConfig",
    "limits_service",
    "subscription_service",
    "search_service",
    "content_service",
    "image_service",
    "platform_service",
    "refresh_service"
]