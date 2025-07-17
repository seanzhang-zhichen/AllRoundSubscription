"""
用户管理服务
"""
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from datetime import datetime, timedelta

from app.models.user import User, MembershipLevel
from app.models.subscription import Subscription
from app.models.push_record import PushRecord, PushStatus
from app.core.exceptions import NotFoundException, BusinessException, ErrorCode
from app.db.redis import cache_service

logger = logging.getLogger(__name__)


class UserService:
    """用户管理服务类"""
    
    async def get_user_profile(self, user_id: int, db: AsyncSession) -> Dict[str, Any]:
        """
        获取用户档案信息
        
        Args:
            user_id: 用户ID
            db: 数据库会话
            
        Returns:
            用户档案信息字典
        """
        try:
            # 获取用户基本信息
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise NotFoundException("用户不存在")
            
            # 获取订阅统计
            subscription_count = await self._get_user_subscription_count(db, user_id)
            
            # 获取今日推送统计
            daily_push_count = await self._get_daily_push_count(db, user_id)
            
            # 构建用户档案
            profile = {
                "id": user.id,
                "openid": user.openid,
                "nickname": user.nickname,
                "avatar_url": user.avatar_url,
                "membership_level": user.membership_level.value,
                "membership_expire_at": user.membership_expire_at,
                "is_membership_active": user.is_membership_active,
                "subscription_count": subscription_count,
                "subscription_limit": user.get_subscription_limit(),
                "daily_push_count": daily_push_count,
                "daily_push_limit": user.get_daily_push_limit(),
                "can_subscribe": subscription_count < user.get_subscription_limit() or user.get_subscription_limit() == -1,
                "can_receive_push": daily_push_count < user.get_daily_push_limit() or user.get_daily_push_limit() == -1,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            }
            
            logger.info(f"获取用户档案成功，用户ID: {user_id}")
            return profile
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"获取用户档案失败: {str(e)}", exc_info=True)
            raise BusinessException(
                error_code=ErrorCode.DATABASE_ERROR,
                message="获取用户信息失败"
            )
    
    async def update_user_profile(
        self, 
        user_id: int, 
        update_data: Dict[str, Any], 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        更新用户档案信息
        
        Args:
            user_id: 用户ID
            update_data: 更新数据
            db: 数据库会话
            
        Returns:
            更新后的用户信息
        """
        try:
            # 获取用户
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise NotFoundException("用户不存在")
            
            # 允许更新的字段
            allowed_fields = {"nickname", "avatar_url"}
            update_fields = {k: v for k, v in update_data.items() if k in allowed_fields}
            
            if not update_fields:
                logger.warning(f"没有有效的更新字段，用户ID: {user_id}")
                return await self.get_user_profile(user_id, db)
            
            # 更新用户信息
            update_fields["updated_at"] = datetime.utcnow()
            
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(**update_fields)
            )
            await db.execute(stmt)
            await db.commit()
            
            # 清除缓存
            await self._clear_user_cache(user_id)
            
            logger.info(f"用户信息更新成功，用户ID: {user_id}, 更新字段: {list(update_fields.keys())}")
            
            # 返回更新后的用户档案
            return await self.get_user_profile(user_id, db)
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"更新用户信息失败: {str(e)}", exc_info=True)
            await db.rollback()
            raise BusinessException(
                error_code=ErrorCode.DATABASE_ERROR,
                message="更新用户信息失败"
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
            
            membership_info = {
                "level": user.membership_level.value,
                "expire_at": user.membership_expire_at,
                "is_active": user.is_membership_active,
                "subscription_limit": user.get_subscription_limit(),
                "daily_push_limit": user.get_daily_push_limit(),
                "benefits": self._get_membership_benefits(user.membership_level)
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
    
    async def upgrade_membership(
        self, 
        user_id: int, 
        level: MembershipLevel, 
        duration_months: int, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        升级用户会员
        
        Args:
            user_id: 用户ID
            level: 目标会员等级
            duration_months: 购买月数
            db: 数据库会话
            
        Returns:
            升级后的会员信息
        """
        try:
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise NotFoundException("用户不存在")
            
            if level == MembershipLevel.FREE:
                raise BusinessException(
                    error_code=ErrorCode.INVALID_PARAMS,
                    message="不能升级到免费等级"
                )
            
            # 计算到期时间
            current_time = datetime.utcnow()
            if user.membership_expire_at and user.membership_expire_at > current_time:
                # 如果当前会员未过期，从当前到期时间开始计算
                expire_at = user.membership_expire_at + timedelta(days=duration_months * 30)
            else:
                # 如果当前会员已过期或是免费用户，从现在开始计算
                expire_at = current_time + timedelta(days=duration_months * 30)
            
            # 更新会员信息
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(
                    membership_level=level,
                    membership_expire_at=expire_at,
                    updated_at=current_time
                )
            )
            await db.execute(stmt)
            await db.commit()
            
            # 清除缓存
            await self._clear_user_cache(user_id)
            
            logger.info(f"用户会员升级成功，用户ID: {user_id}, 等级: {level.value}, 到期时间: {expire_at}")
            
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
    
    async def get_user_limits(self, user_id: int, db: AsyncSession) -> Dict[str, Any]:
        """
        获取用户限制信息
        
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
            
            # 获取当前使用情况
            subscription_used = await self._get_user_subscription_count(db, user_id)
            daily_push_used = await self._get_daily_push_count(db, user_id)
            
            # 获取限制
            subscription_limit = user.get_subscription_limit()
            daily_push_limit = user.get_daily_push_limit()
            
            limits = {
                "subscription_limit": subscription_limit,
                "subscription_used": subscription_used,
                "daily_push_limit": daily_push_limit,
                "daily_push_used": daily_push_used,
                "can_subscribe": subscription_used < subscription_limit or subscription_limit == -1,
                "can_receive_push": daily_push_used < daily_push_limit or daily_push_limit == -1
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
    
    async def delete_user(self, user_id: int, db: AsyncSession) -> bool:
        """
        删除用户账户
        
        Args:
            user_id: 用户ID
            db: 数据库会话
            
        Returns:
            是否删除成功
        """
        try:
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise NotFoundException("用户不存在")
            
            # 删除用户（级联删除相关数据）
            stmt = delete(User).where(User.id == user_id)
            result = await db.execute(stmt)
            await db.commit()
            
            # 清除缓存
            await self._clear_user_cache(user_id)
            
            if result.rowcount > 0:
                logger.info(f"用户删除成功，用户ID: {user_id}")
                return True
            else:
                logger.warning(f"用户删除失败，用户不存在，用户ID: {user_id}")
                return False
                
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"删除用户失败: {str(e)}", exc_info=True)
            await db.rollback()
            raise BusinessException(
                error_code=ErrorCode.DATABASE_ERROR,
                message="删除用户失败"
            )
    
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
    
    def _get_membership_benefits(self, level: MembershipLevel) -> List[str]:
        """获取会员权益列表"""
        benefits_map = {
            MembershipLevel.FREE: [
                "订阅10个博主",
                "每日5次推送通知",
                "基础内容聚合"
            ],
            MembershipLevel.BASIC: [
                "订阅50个博主",
                "每日20次推送通知",
                "高级内容聚合",
                "优先客服支持"
            ],
            MembershipLevel.PREMIUM: [
                "无限订阅博主",
                "无限推送通知",
                "高级内容聚合",
                "优先客服支持",
                "专属功能体验",
                "数据导出功能"
            ]
        }
        return benefits_map.get(level, [])
    
    async def _clear_user_cache(self, user_id: int) -> None:
        """清除用户相关缓存"""
        try:
            cache_keys = [
                f"user_profile:{user_id}",
                f"user_limits:{user_id}",
                f"user_session:{user_id}"
            ]
            for key in cache_keys:
                await cache_service.delete(key)
        except Exception as e:
            logger.warning(f"清除用户缓存失败: {str(e)}")


# 全局用户服务实例
user_service = UserService()