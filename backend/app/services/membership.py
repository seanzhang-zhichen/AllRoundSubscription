"""
会员等级管理服务
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload

from app.models.user import User, MembershipLevel
from app.models.subscription import Subscription
from app.models.push_record import PushRecord, PushStatus
from app.core.exceptions import (
    NotFoundException, 
    BusinessException, 
    ErrorCode,
    SubscriptionLimitException,
    PushLimitException
)
from app.db.redis import cache_service

logger = logging.getLogger(__name__)


class MembershipConfig:
    """会员等级配置"""
    
    # 会员等级权限配置
    MEMBERSHIP_LIMITS = {
        MembershipLevel.FREE: {
            "subscription_limit": 10,
            "daily_push_limit": 5,
            "features": ["basic_aggregation"]
        },
        MembershipLevel.BASIC: {
            "subscription_limit": 50,
            "daily_push_limit": 20,
            "features": ["basic_aggregation", "advanced_search", "priority_support"]
        },
        MembershipLevel.PREMIUM: {
            "subscription_limit": -1,  # 无限制
            "daily_push_limit": -1,    # 无限制
            "features": [
                "basic_aggregation", 
                "advanced_search", 
                "priority_support",
                "exclusive_features",
                "data_export"
            ]
        }
    }
    
    # 会员等级权益描述
    MEMBERSHIP_BENEFITS = {
        MembershipLevel.FREE: [
            "订阅10个博主",
            "每日5次推送通知",
            "基础内容聚合"
        ],
        MembershipLevel.BASIC: [
            "订阅50个博主",
            "每日20次推送通知",
            "高级内容聚合",
            "高级搜索功能",
            "优先客服支持"
        ],
        MembershipLevel.PREMIUM: [
            "无限订阅博主",
            "无限推送通知",
            "高级内容聚合",
            "高级搜索功能",
            "优先客服支持",
            "专属功能体验",
            "数据导出功能"
        ]
    }
    
    @classmethod
    def get_subscription_limit(cls, level: MembershipLevel) -> int:
        """获取订阅数量限制"""
        return cls.MEMBERSHIP_LIMITS.get(level, {}).get("subscription_limit", 10)
    
    @classmethod
    def get_daily_push_limit(cls, level: MembershipLevel) -> int:
        """获取每日推送限制"""
        return cls.MEMBERSHIP_LIMITS.get(level, {}).get("daily_push_limit", 5)
    
    @classmethod
    def get_features(cls, level: MembershipLevel) -> List[str]:
        """获取会员功能列表"""
        return cls.MEMBERSHIP_LIMITS.get(level, {}).get("features", [])
    
    @classmethod
    def get_benefits(cls, level: MembershipLevel) -> List[str]:
        """获取会员权益描述"""
        return cls.MEMBERSHIP_BENEFITS.get(level, [])


class MembershipService:
    """会员等级管理服务类"""
    
    async def upgrade_membership(
        self, 
        user_id: int, 
        target_level: MembershipLevel, 
        duration_months: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        升级用户会员等级
        
        Args:
            user_id: 用户ID
            target_level: 目标会员等级
            duration_months: 购买月数
            db: 数据库会话
            
        Returns:
            升级后的会员信息
        """
        try:
            # 获取用户信息
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise NotFoundException("用户不存在")
            
            # 验证升级参数
            if target_level == MembershipLevel.FREE:
                raise BusinessException(
                    error_code=ErrorCode.INVALID_PARAMS,
                    message="不能升级到免费等级"
                )
            
            if duration_months < 1 or duration_months > 12:
                raise BusinessException(
                    error_code=ErrorCode.INVALID_PARAMS,
                    message="购买月数必须在1-12个月之间"
                )
            
            # 计算新的到期时间
            current_time = datetime.utcnow()
            if (user.membership_expire_at and 
                user.membership_expire_at > current_time and 
                user.membership_level != MembershipLevel.FREE):
                # 如果当前会员未过期，从当前到期时间开始计算
                new_expire_at = user.membership_expire_at + timedelta(days=duration_months * 30)
            else:
                # 如果当前会员已过期或是免费用户，从现在开始计算
                new_expire_at = current_time + timedelta(days=duration_months * 30)
            
            # 更新用户会员信息
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(
                    membership_level=target_level,
                    membership_expire_at=new_expire_at,
                    updated_at=current_time
                )
            )
            await db.execute(stmt)
            await db.commit()
            
            # 清除用户相关缓存
            await self._clear_user_cache(user_id)
            
            logger.info(
                f"用户会员升级成功 - 用户ID: {user_id}, "
                f"等级: {user.membership_level.value} -> {target_level.value}, "
                f"到期时间: {new_expire_at}"
            )
            
            # 返回升级后的会员信息
            return await self.get_membership_info(user_id, db)
            
        except (NotFoundException, BusinessException):
            raise
        except Exception as e:
            logger.error(f"升级会员失败: {str(e)}", exc_info=True)
            await db.rollback()
            raise BusinessException(
                error_code=ErrorCode.DATABASE_ERROR,
                message="升级会员失败"
            )
    
    async def check_membership_expiry(self, db: AsyncSession) -> List[int]:
        """
        检查并处理会员到期
        
        Args:
            db: 数据库会话
            
        Returns:
            已过期的用户ID列表
        """
        try:
            current_time = datetime.utcnow()
            
            # 查找已过期的付费会员
            stmt = (
                select(User.id)
                .where(
                    User.membership_level != MembershipLevel.FREE,
                    User.membership_expire_at <= current_time
                )
            )
            result = await db.execute(stmt)
            expired_user_ids = [row[0] for row in result.fetchall()]
            
            if expired_user_ids:
                # 批量降级为免费用户
                stmt = (
                    update(User)
                    .where(User.id.in_(expired_user_ids))
                    .values(
                        membership_level=MembershipLevel.FREE,
                        membership_expire_at=None,
                        updated_at=current_time
                    )
                )
                await db.execute(stmt)
                await db.commit()
                
                # 清除相关缓存
                for user_id in expired_user_ids:
                    await self._clear_user_cache(user_id)
                
                logger.info(f"处理会员到期，降级用户数量: {len(expired_user_ids)}")
            
            return expired_user_ids
            
        except Exception as e:
            logger.error(f"检查会员到期失败: {str(e)}", exc_info=True)
            await db.rollback()
            raise BusinessException(
                error_code=ErrorCode.DATABASE_ERROR,
                message="检查会员到期失败"
            )
    
    async def get_membership_info(self, user_id: int, db: AsyncSession) -> Dict[str, Any]:
        """
        获取用户会员信息
        
        Args:
            user_id: 用户ID
            db: 数据库会话
            
        Returns:
            会员信息字典
        """
        try:
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise NotFoundException("用户不存在")
            
            # 检查会员是否有效
            is_active = self._is_membership_active(user)
            effective_level = user.membership_level if is_active else MembershipLevel.FREE
            
            membership_info = {
                "level": user.membership_level.value,
                "effective_level": effective_level.value,
                "expire_at": user.membership_expire_at,
                "is_active": is_active,
                "subscription_limit": MembershipConfig.get_subscription_limit(effective_level),
                "daily_push_limit": MembershipConfig.get_daily_push_limit(effective_level),
                "features": MembershipConfig.get_features(effective_level),
                "benefits": MembershipConfig.get_benefits(effective_level)
            }
            
            logger.debug(f"获取会员信息成功，用户ID: {user_id}")
            return membership_info
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"获取会员信息失败: {str(e)}", exc_info=True)
            raise BusinessException(
                error_code=ErrorCode.DATABASE_ERROR,
                message="获取会员信息失败"
            )
    
    async def check_subscription_limit(self, user_id: int, db: AsyncSession) -> bool:
        """
        检查用户是否可以继续订阅
        
        Args:
            user_id: 用户ID
            db: 数据库会话
            
        Returns:
            是否可以继续订阅
        """
        try:
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise NotFoundException("用户不存在")
            
            # 获取有效会员等级
            effective_level = self._get_effective_membership_level(user)
            subscription_limit = MembershipConfig.get_subscription_limit(effective_level)
            
            # 无限制的情况
            if subscription_limit == -1:
                return True
            
            # 获取当前订阅数量
            current_count = await self._get_user_subscription_count(db, user_id)
            
            can_subscribe = current_count < subscription_limit
            
            if not can_subscribe:
                logger.info(f"用户订阅数量已达上限 - 用户ID: {user_id}, 当前: {current_count}, 限制: {subscription_limit}")
            
            return can_subscribe
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"检查订阅限制失败: {str(e)}", exc_info=True)
            raise BusinessException(
                error_code=ErrorCode.DATABASE_ERROR,
                message="检查订阅限制失败"
            )
    
    async def check_push_limit(self, user_id: int, db: AsyncSession) -> bool:
        """
        检查用户是否可以接收推送
        
        Args:
            user_id: 用户ID
            db: 数据库会话
            
        Returns:
            是否可以接收推送
        """
        try:
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise NotFoundException("用户不存在")
            
            # 获取有效会员等级
            effective_level = self._get_effective_membership_level(user)
            push_limit = MembershipConfig.get_daily_push_limit(effective_level)
            
            # 无限制的情况
            if push_limit == -1:
                return True
            
            # 获取今日推送数量
            today_count = await self._get_daily_push_count(db, user_id)
            
            can_push = today_count < push_limit
            
            if not can_push:
                logger.info(f"用户推送次数已达上限 - 用户ID: {user_id}, 今日: {today_count}, 限制: {push_limit}")
            
            return can_push
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"检查推送限制失败: {str(e)}", exc_info=True)
            raise BusinessException(
                error_code=ErrorCode.DATABASE_ERROR,
                message="检查推送限制失败"
            )
    
    async def get_user_limits(self, user_id: int, db: AsyncSession) -> Dict[str, Any]:
        """
        获取用户权限限制信息
        
        Args:
            user_id: 用户ID
            db: 数据库会话
            
        Returns:
            用户限制信息字典
        """
        try:
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise NotFoundException("用户不存在")
            
            # 获取有效会员等级
            effective_level = self._get_effective_membership_level(user)
            
            # 获取限制配置
            subscription_limit = MembershipConfig.get_subscription_limit(effective_level)
            daily_push_limit = MembershipConfig.get_daily_push_limit(effective_level)
            
            # 获取当前使用情况
            subscription_used = await self._get_user_subscription_count(db, user_id)
            daily_push_used = await self._get_daily_push_count(db, user_id)
            
            limits = {
                "membership_level": user.membership_level.value,
                "effective_level": effective_level.value,
                "is_membership_active": self._is_membership_active(user),
                "subscription_limit": subscription_limit,
                "subscription_used": subscription_used,
                "daily_push_limit": daily_push_limit,
                "daily_push_used": daily_push_used,
                "can_subscribe": subscription_used < subscription_limit or subscription_limit == -1,
                "can_receive_push": daily_push_used < daily_push_limit or daily_push_limit == -1,
                "features": MembershipConfig.get_features(effective_level)
            }
            
            logger.debug(f"获取用户限制信息成功，用户ID: {user_id}")
            return limits
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"获取用户限制信息失败: {str(e)}", exc_info=True)
            raise BusinessException(
                error_code=ErrorCode.DATABASE_ERROR,
                message="获取用户限制信息失败"
            )
    
    def _is_membership_active(self, user: User) -> bool:
        """检查会员是否有效"""
        if user.membership_level == MembershipLevel.FREE:
            return True
        if user.membership_expire_at is None:
            return False
        return user.membership_expire_at > datetime.utcnow()
    
    def _get_effective_membership_level(self, user: User) -> MembershipLevel:
        """获取有效的会员等级"""
        if self._is_membership_active(user):
            return user.membership_level
        return MembershipLevel.FREE
    
    async def _get_user_by_id(self, db: AsyncSession, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_user_subscription_count(self, db: AsyncSession, user_id: int) -> int:
        """获取用户订阅数量"""
        stmt = select(func.count(Subscription.id)).where(Subscription.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar() or 0
    
    async def _get_daily_push_count(self, db: AsyncSession, user_id: int) -> int:
        """获取用户今日推送数量"""
        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)
        
        stmt = (
            select(func.count(PushRecord.id))
            .where(
                PushRecord.user_id == user_id,
                PushRecord.push_time >= today,
                PushRecord.push_time < tomorrow,
                PushRecord.status == PushStatus.SUCCESS
            )
        )
        result = await db.execute(stmt)
        return result.scalar() or 0
    
    async def _clear_user_cache(self, user_id: int) -> None:
        """清除用户相关缓存"""
        try:
            cache_keys = [
                f"user_profile:{user_id}",
                f"user_limits:{user_id}",
                f"membership_info:{user_id}",
                f"user_session:{user_id}"
            ]
            for key in cache_keys:
                await cache_service.delete(key)
        except Exception as e:
            logger.warning(f"清除用户缓存失败: {str(e)}")


# 全局会员服务实例
membership_service = MembershipService()