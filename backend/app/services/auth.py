"""
认证服务
"""
from app.core.logging import get_logger
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from datetime import timedelta
from app.models.user import User, MembershipLevel
from app.services.wechat import wechat_service
from app.core.security import jwt_manager
from app.core.exceptions import AuthenticationException, BusinessException
from app.db.redis import cache_service

logger = get_logger(__name__)


class AuthService:
    """认证服务类"""
    
    async def wechat_login(self, code: str, db: AsyncSession) -> Dict[str, Any]:
        """
        微信小程序登录
        
        Args:
            code: 微信小程序登录code
            db: 数据库会话
            
        Returns:
            包含用户信息和令牌的字典
        """
        try:
            # 1. 验证code格式
            if not code or len(code.strip()) == 0:
                raise BusinessException("登录凭证不能为空")
            
            code = code.strip()  # 清理可能的空白字符
            
            # 2. 通过code换取openid
            logger.info(f"开始微信登录流程，code: {code[:10]}...")
            wechat_data = await wechat_service.code_to_session(code)
            openid = wechat_data["openid"]
            
            # 2. 查找或创建用户
            user = await self._get_or_create_user(db, openid)
            
            # 3. 生成JWT令牌
            token_data = {"sub": str(user.id), "openid": openid}
            access_token = jwt_manager.create_access_token(token_data)
            refresh_token = jwt_manager.create_refresh_token(token_data)
            
            # 4. 缓存用户会话信息
            await self._cache_user_session(user.id, {
                "openid": openid,
                "login_time": datetime.utcnow().isoformat()
            })
            
            logger.info(f"用户登录成功，用户ID: {user.id}, openid: {openid[:10]}...")
            
            # 计算token过期时间
            expire_at = datetime.utcnow() + timedelta(minutes=jwt_manager.access_token_expire_minutes)
            
            return {
                "user": {
                    "id": user.id,
                    "openid": user.openid,
                    "nickname": user.nickname,
                    "avatar_url": user.avatar_url,
                    "membership_level": user.membership_level.value,
                    "membership_expire_at": user.membership_expire_at,
                    "is_membership_active": user.is_membership_active,
                    "subscription_limit": user.get_subscription_limit(),
                    "daily_push_limit": user.get_daily_push_limit()
                },
                "tokens": {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "bearer",
                    "expires_in": jwt_manager.access_token_expire_minutes * 60,
                    "expire_at": expire_at.isoformat()
                }
            }
            
        except BusinessException:
            # 重新抛出业务异常
            raise
        except Exception as e:
            logger.error(f"微信登录失败: {str(e)}", exc_info=True)
            raise AuthenticationException("登录失败，请稍后重试")
    
    async def refresh_token(self, refresh_token: str, db: AsyncSession) -> Dict[str, Any]:
        """
        刷新访问令牌
        
        Args:
            refresh_token: 刷新令牌
            db: 数据库会话
            
        Returns:
            新的令牌信息
        """
        try:
            # 1. 验证刷新令牌
            payload = jwt_manager.verify_token(refresh_token, "refresh")
            user_id = int(payload["sub"])
            openid = payload["openid"]
            
            # 2. 验证用户是否存在
            user = await self._get_user_by_id(db, user_id)
            if not user or user.openid != openid:
                raise AuthenticationException("用户不存在或令牌无效")
            
            # 3. 生成新的访问令牌
            token_data = {"sub": str(user.id), "openid": openid}
            new_access_token = jwt_manager.create_access_token(token_data)
            
            # 计算新token过期时间
            
            expire_at = datetime.utcnow() + timedelta(minutes=jwt_manager.access_token_expire_minutes)
            
            logger.info(f"令牌刷新成功，用户ID: {user_id}")
            
            return {
                "access_token": new_access_token,
                "token_type": "bearer",
                "expires_in": jwt_manager.access_token_expire_minutes * 60,
                "expire_at": expire_at.isoformat()
            }
            
        except AuthenticationException:
            raise
        except Exception as e:
            logger.error(f"令牌刷新失败: {str(e)}", exc_info=True)
            raise AuthenticationException("令牌刷新失败")
    
    async def verify_access_token(self, token: str, db: AsyncSession) -> User:
        """
        验证访问令牌并返回用户
        
        Args:
            token: 访问令牌
            db: 数据库会话
            
        Returns:
            用户对象
        """
        try:
            # 1. 验证令牌
            payload = jwt_manager.verify_token(token, "access")
            user_id = int(payload["sub"])
            
            # 2. 获取用户信息
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise AuthenticationException("用户不存在")
            
            # 3. 检查会员状态（如果会员过期，自动降级）
            if not user.is_membership_active and user.membership_level != MembershipLevel.FREE:
                await self._downgrade_expired_membership(db, user)
            
            return user
            
        except AuthenticationException:
            raise
        except Exception as e:
            logger.error(f"令牌验证失败: {str(e)}", exc_info=True)
            raise AuthenticationException("令牌验证失败")
    
    async def logout(self, user_id: int) -> bool:
        """
        用户登出
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否成功
        """
        try:
            # 清除缓存的会话信息
            await self._clear_user_session(user_id)
            logger.info(f"用户登出成功，用户ID: {user_id}")
            return True
        except Exception as e:
            logger.error(f"用户登出失败: {str(e)}", exc_info=True)
            return False
    
    async def _get_or_create_user(self, db: AsyncSession, openid: str) -> User:
        """获取或创建用户"""
        # 查找现有用户
        stmt = select(User).where(User.openid == openid)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            # 更新最后登录时间
            user.updated_at = datetime.utcnow()
            await db.commit()
            logger.info(f"找到现有用户，ID: {user.id}")
            return user
        
        # 创建新用户
        user = User(
            openid=openid,
            membership_level=MembershipLevel.FREE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"创建新用户成功，ID: {user.id}, openid: {openid[:10]}...")
        return user
    
    async def _get_user_by_id(self, db: AsyncSession, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _downgrade_expired_membership(self, db: AsyncSession, user: User) -> None:
        """降级过期会员"""
        logger.info(f"用户会员已过期，自动降级，用户ID: {user.id}")
        user.membership_level = MembershipLevel.FREE
        user.membership_expire_at = None
        user.updated_at = datetime.utcnow()
        await db.commit()
    
    async def _cache_user_session(self, user_id: int, session_data: Dict[str, Any]) -> None:
        """缓存用户会话信息"""
        try:
            cache_key = f"user_session:{user_id}"
            await cache_service.set(cache_key, session_data, expire=3600 * 24)  # 24小时
        except Exception as e:
            logger.warning(f"缓存用户会话失败: {str(e)}", exc_info=True)
    
    async def _clear_user_session(self, user_id: int) -> None:
        """清除用户会话缓存"""
        try:
            cache_key = f"user_session:{user_id}"
            await cache_service.delete(cache_key)
        except Exception as e:
            logger.warning(f"清除用户会话缓存失败: {str(e)}", exc_info=True)


# 全局认证服务实例
auth_service = AuthService()