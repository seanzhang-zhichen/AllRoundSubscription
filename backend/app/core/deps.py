"""
依赖注入模块
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from app.db.database import get_db
from app.db.redis import cache_service
from app.core.exceptions import AuthenticationException
from app.services.auth import auth_service
from app.models.user import User

logger = logging.getLogger(__name__)

# HTTP Bearer认证
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """获取当前用户依赖"""
    if not credentials:
        raise AuthenticationException("缺少认证令牌")
    
    token = credentials.credentials
    
    try:
        user = await auth_service.verify_access_token(token, db)
        logger.debug(f"用户认证成功，用户ID: {user.id}")
        return user
    except AuthenticationException:
        raise
    except Exception as e:
        logger.error(f"令牌验证失败: {str(e)}")
        raise AuthenticationException("无效的认证令牌")


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """获取当前用户依赖（可选）"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except AuthenticationException:
        return None


async def get_cache():
    """获取缓存服务依赖"""
    return cache_service


class CommonQueryParams:
    """通用查询参数"""
    
    def __init__(self, page: int = 1, size: int = 20):
        self.page = max(1, page)
        self.size = min(100, max(1, size))  # 限制每页最大100条
        self.offset = (self.page - 1) * self.size