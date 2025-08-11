"""
权限检查装饰器和工具
"""
from app.core.logging import get_logger
from functools import wraps
from typing import Callable, Any, Optional, List
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, MembershipLevel
from app.core.exceptions import (
    AuthorizationException, 
    SubscriptionLimitException,
    PushLimitException,
    BusinessException,
    ErrorCode
)
from app.services.membership import membership_service, MembershipConfig
from app.core.deps import get_current_user, get_db

logger = get_logger(__name__)


class PermissionChecker:
    """权限检查器"""
    
    @staticmethod
    async def check_membership_level(
        user: User,
        required_level: MembershipLevel,
        db: AsyncSession
    ) -> bool:
        """
        检查用户会员等级是否满足要求
        
        Args:
            user: 用户对象
            required_level: 所需会员等级
            db: 数据库会话
            
        Returns:
            是否满足等级要求
        """
        try:
            # 获取用户会员信息
            membership_info = await membership_service.get_membership_info(user.id, db)
            
            # 获取有效等级
            effective_level = MembershipLevel(membership_info["effective_level"])
            
            # 等级优先级：FREE < V1 < V2 < V3 < V4 < V5（兼容BASIC≈V2，PREMIUM≈V5）
            level_priority = {
                MembershipLevel.FREE: 0,
                MembershipLevel.V1: 1,
                MembershipLevel.V2: 2,
                MembershipLevel.V3: 3,
                MembershipLevel.V4: 4,
                MembershipLevel.V5: 5,
            }
            
            user_priority = level_priority.get(effective_level, 0)
            required_priority = level_priority.get(required_level, 0)
            
            return user_priority >= required_priority
            
        except Exception as e:
            logger.error(f"检查会员等级失败: {str(e)}")
            return False
    
    @staticmethod
    async def check_subscription_permission(user: User, db: AsyncSession) -> bool:
        """
        检查用户是否有订阅权限
        
        Args:
            user: 用户对象
            db: 数据库会话
            
        Returns:
            是否有订阅权限
        """
        try:
            return await membership_service.check_subscription_limit(user.id, db)
        except Exception as e:
            logger.error(f"检查订阅权限失败: {str(e)}")
            return False
    
    @staticmethod
    async def check_push_permission(user: User, db: AsyncSession) -> bool:
        """
        检查用户是否有推送权限
        
        Args:
            user: 用户对象
            db: 数据库会话
            
        Returns:
            是否有推送权限
        """
        try:
            return await membership_service.check_push_limit(user.id, db)
        except Exception as e:
            logger.error(f"检查推送权限失败: {str(e)}")
            return False
    
    @staticmethod
    async def check_feature_permission(
        user: User, 
        feature: str, 
        db: AsyncSession
    ) -> bool:
        """
        检查用户是否有特定功能权限
        
        Args:
            user: 用户对象
            feature: 功能名称
            db: 数据库会话
            
        Returns:
            是否有功能权限
        """
        try:
            membership_info = await membership_service.get_membership_info(user.id, db)
            features = membership_info.get("features", [])
            return feature in features
        except Exception as e:
            logger.error(f"检查功能权限失败: {str(e)}")
            return False


def require_membership(required_level: MembershipLevel):
    """
    要求特定会员等级的装饰器
    
    Args:
        required_level: 所需会员等级
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从kwargs中获取用户和数据库会话
            user = kwargs.get('current_user')
            db = kwargs.get('db')
            
            if not user or not db:
                # 如果没有在kwargs中找到，尝试从args中获取
                for arg in args:
                    if isinstance(arg, User):
                        user = arg
                    elif hasattr(arg, 'execute'):  # AsyncSession
                        db = arg
            
            if not user or not db:
                raise AuthorizationException("无法获取用户信息或数据库会话")
            
            # 检查会员等级
            has_permission = await PermissionChecker.check_membership_level(
                user, required_level, db
            )
            
            if not has_permission:
                logger.warning(
                    f"用户会员等级不足 - 用户ID: {user.id}, "
                    f"当前等级: {user.membership_level.value}, "
                    f"所需等级: {required_level.value}"
                )
                raise AuthorizationException(
                    f"需要{required_level.value}等级会员权限"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_subscription_permission():
    """
    要求订阅权限的装饰器
    
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从kwargs中获取用户和数据库会话
            user = kwargs.get('current_user')
            db = kwargs.get('db')
            
            if not user or not db:
                # 如果没有在kwargs中找到，尝试从args中获取
                for arg in args:
                    if isinstance(arg, User):
                        user = arg
                    elif hasattr(arg, 'execute'):  # AsyncSession
                        db = arg
            
            if not user or not db:
                raise AuthorizationException("无法获取用户信息或数据库会话")
            
            # 检查订阅权限
            has_permission = await PermissionChecker.check_subscription_permission(user, db)
            
            if not has_permission:
                logger.warning(f"用户订阅数量已达上限 - 用户ID: {user.id}")
                raise SubscriptionLimitException("订阅数量已达上限，请升级会员")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_push_permission():
    """
    要求推送权限的装饰器
    
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从kwargs中获取用户和数据库会话
            user = kwargs.get('current_user')
            db = kwargs.get('db')
            
            if not user or not db:
                # 如果没有在kwargs中找到，尝试从args中获取
                for arg in args:
                    if isinstance(arg, User):
                        user = arg
                    elif hasattr(arg, 'execute'):  # AsyncSession
                        db = arg
            
            if not user or not db:
                raise AuthorizationException("无法获取用户信息或数据库会话")
            
            # 检查推送权限
            has_permission = await PermissionChecker.check_push_permission(user, db)
            
            if not has_permission:
                logger.warning(f"用户推送次数已达上限 - 用户ID: {user.id}")
                raise PushLimitException("推送次数已达上限，请升级会员")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_feature(feature: str):
    """
    要求特定功能权限的装饰器
    
    Args:
        feature: 功能名称
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从kwargs中获取用户和数据库会话
            user = kwargs.get('current_user')
            db = kwargs.get('db')
            
            if not user or not db:
                # 如果没有在kwargs中找到，尝试从args中获取
                for arg in args:
                    if isinstance(arg, User):
                        user = arg
                    elif hasattr(arg, 'execute'):  # AsyncSession
                        db = arg
            
            if not user or not db:
                raise AuthorizationException("无法获取用户信息或数据库会话")
            
            # 检查功能权限
            has_permission = await PermissionChecker.check_feature_permission(user, feature, db)
            
            if not has_permission:
                logger.warning(
                    f"用户缺少功能权限 - 用户ID: {user.id}, 功能: {feature}"
                )
                raise AuthorizationException(f"需要{feature}功能权限")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# FastAPI依赖项形式的权限检查
def check_membership_dependency(required_level: MembershipLevel):
    """
    会员等级检查依赖项工厂
    
    Args:
        required_level: 所需会员等级
        
    Returns:
        依赖项函数
    """
    async def dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        has_permission = await PermissionChecker.check_membership_level(
            current_user, required_level, db
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要{required_level.value}等级会员权限"
            )
        
        return current_user
    
    return dependency


async def check_subscription_dependency(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    订阅权限检查依赖项
    
    Args:
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        用户对象
        
    Raises:
        HTTPException: 权限不足时抛出
    """
    has_permission = await PermissionChecker.check_subscription_permission(current_user, db)
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="订阅数量已达上限，请升级会员"
        )
    
    return current_user


async def check_push_dependency(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    推送权限检查依赖项
    
    Args:
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        用户对象
        
    Raises:
        HTTPException: 权限不足时抛出
    """
    has_permission = await PermissionChecker.check_push_permission(current_user, db)
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="推送次数已达上限，请升级会员"
        )
    
    return current_user


def check_feature_dependency(feature: str):
    """
    功能权限检查依赖项工厂
    
    Args:
        feature: 功能名称
        
    Returns:
        依赖项函数
    """
    async def dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        has_permission = await PermissionChecker.check_feature_permission(
            current_user, feature, db
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要{feature}功能权限"
            )
        
        return current_user
    
    return dependency