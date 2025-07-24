"""
订阅管理服务
"""
from app.core.logging import get_logger
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc, delete
from sqlalchemy.orm import selectinload, joinedload

from app.models.user import User, MembershipLevel
from app.models.account import Account, Platform
from app.models.subscription import Subscription
from app.models.article import Article
from app.schemas.subscription import (
    SubscriptionCreate, SubscriptionResponse, SubscriptionWithAccount,
    SubscriptionList, SubscriptionStats, BatchSubscriptionCreate,
    BatchSubscriptionResponse
)
from app.services.limits import limits_service
from app.core.exceptions import (
    NotFoundException,
    BusinessException,
    ErrorCode,
    SubscriptionLimitException,
    DuplicateException
)
import traceback
from app.db.redis import cache_service

logger = get_logger(__name__)


class SubscriptionService:
    """订阅管理服务类"""
    
    async def create_subscription(
        self, 
        subscription_data: SubscriptionCreate, 
        db: AsyncSession
    ) -> SubscriptionResponse:
        """
        创建订阅关系
        
        Args:
            subscription_data: 订阅创建数据
            db: 数据库会话
            
        Returns:
            创建的订阅信息
            
        Raises:
            NotFoundException: 用户或账号不存在
            SubscriptionLimitException: 订阅数量超限
            DuplicateException: 重复订阅
        """
        try:
            user_id = subscription_data.user_id
            account_id = subscription_data.account_id
            
            # 检查用户是否存在
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise NotFoundException("用户不存在")
            
            # 检查账号是否存在
            account = await self._get_account_by_id(db, account_id)
            if not account:
                raise NotFoundException("账号不存在")
            
            # 检查是否已经订阅
            existing_subscription = await self._get_subscription_by_user_account(
                db, user_id, account_id
            )
            if existing_subscription:
                raise DuplicateException("已经订阅该账号")
            
            # 检查订阅数量限制
            await limits_service.check_subscription_limit(
                user_id, db, raise_exception=True
            )
            
            # 创建订阅记录
            subscription = Subscription(
                user_id=user_id,
                account_id=account_id
            )
            
            db.add(subscription)
            await db.commit()
            await db.refresh(subscription)
            
            # 清除相关缓存
            await self._clear_user_subscription_cache(user_id)
            
            logger.info(
                f"创建订阅成功 - 用户ID: {user_id}, 账号ID: {account_id}, "
                f"订阅ID: {subscription.id}"
            )
            
            return SubscriptionResponse.from_orm(subscription)
            
        except (NotFoundException, SubscriptionLimitException, DuplicateException):
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"创建订阅失败: {str(e)}", exc_info=True)
            raise BusinessException(
                error_code=ErrorCode.DATABASE_ERROR,
                message="创建订阅失败"
            )
    
    async def delete_subscription(
        self, 
        user_id: int, 
        account_id: int, 
        db: AsyncSession
    ) -> bool:
        """
        删除订阅关系
        
        Args:
            user_id: 用户ID
            account_id: 账号ID
            db: 数据库会话
            
        Returns:
            是否删除成功
            
        Raises:
            NotFoundException: 订阅关系不存在
        """
        try:
            # 查找订阅记录
            subscription = await self._get_subscription_by_user_account(
                db, user_id, account_id
            )
            if not subscription:
                raise NotFoundException("订阅关系不存在")
            
            # 删除订阅记录
            await db.delete(subscription)
            await db.commit()
            
            # 清除相关缓存
            await self._clear_user_subscription_cache(user_id)
            
            logger.info(
                f"删除订阅成功 - 用户ID: {user_id}, 账号ID: {account_id}, "
                f"订阅ID: {subscription.id}"
            )
            
            return True
            
        except NotFoundException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"删除订阅失败: {str(e)}", exc_info=True)
            raise BusinessException(
                error_code=ErrorCode.DATABASE_ERROR,
                message="删除订阅失败"
            )
    
    async def get_user_subscriptions(
        self, 
        query_params: SubscriptionList, 
        db: AsyncSession
    ) -> Tuple[List[SubscriptionWithAccount], int]:
        """
        获取用户订阅列表
        
        Args:
            query_params: 查询参数
            db: 数据库会话
            
        Returns:
            订阅列表和总数
        """
        try:
            user_id = query_params.user_id
            
            # 检查用户是否存在
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise NotFoundException("用户不存在")
            
            # 构建基础查询
            base_query = (
                select(Subscription)
                .options(
                    joinedload(Subscription.account),
                    joinedload(Subscription.user)
                )
                .where(Subscription.user_id == user_id)
            )
            
            # 平台筛选
            if query_params.platform:
                # 直接使用字符串比较，因为数据库中存储的是字符串
                base_query = base_query.where(Account.platform == query_params.platform)
            
            # 获取总数
            count_query = select(func.count()).select_from(base_query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar()
            
            # 排序
            if query_params.order_by == "created_at":
                order_field = Subscription.created_at
            elif query_params.order_by == "account_name":
                order_field = Account.name
            elif query_params.order_by == "latest_article_time":
                # 这里需要子查询获取最新文章时间
                order_field = Subscription.created_at  # 暂时用创建时间
            else:
                order_field = Subscription.created_at
            
            if query_params.order_desc:
                base_query = base_query.order_by(desc(order_field))
            else:
                base_query = base_query.order_by(asc(order_field))
            
            # 分页
            offset = (query_params.page - 1) * query_params.page_size
            base_query = base_query.offset(offset).limit(query_params.page_size)
            
            # 执行查询
            result = await db.execute(base_query)
            subscriptions = result.scalars().all()
            
            # 转换为响应格式
            subscription_list = []
            for subscription in subscriptions:
                account = subscription.account
                
                # 获取最新文章时间和文章数量
                latest_article_time, article_count = await self._get_account_article_stats(
                    db, account.id
                )
                
                subscription_with_account = SubscriptionWithAccount(
                    id=subscription.id,
                    user_id=subscription.user_id,
                    account_id=subscription.account_id,
                    created_at=subscription.created_at,
                    account_name=account.name,
                    account_platform=account.platform,
                    account_avatar_url=account.avatar_url,
                    account_description=account.description,
                    account_follower_count=account.follower_count,
                    platform_display_name=self._get_platform_display_name(account.platform),
                    latest_article_time=latest_article_time,
                    article_count=article_count
                )
                subscription_list.append(subscription_with_account)
            
            logger.debug(
                f"获取用户订阅列表成功 - 用户ID: {user_id}, "
                f"返回: {len(subscription_list)}/{total}"
            )
            
            return subscription_list, total
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"获取用户订阅列表失败: {str(e)}", exc_info=True)
            traceback.print_exc()
            raise BusinessException(
                error_code=ErrorCode.DATABASE_ERROR,
                message="获取订阅列表失败"
            )
    
    async def get_subscription_stats(
        self, 
        user_id: int, 
        db: AsyncSession
    ) -> SubscriptionStats:
        """
        获取用户订阅统计信息
        
        Args:
            user_id: 用户ID
            db: 数据库会话
            
        Returns:
            订阅统计信息
        """
        try:
            # 检查用户是否存在
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise NotFoundException("用户不存在")
            
            # 获取订阅限制信息
            limit_info = await limits_service.check_subscription_limit(user_id, db)
            
            # 获取平台统计
            platform_stats_query = (
                select(Account.platform, func.count(Subscription.id))
                .select_from(Subscription)
                .join(Account, Subscription.account_id == Account.id)
                .where(Subscription.user_id == user_id)
                .group_by(Account.platform)
            )
            platform_result = await db.execute(platform_stats_query)
            platform_stats = {
                platform: count 
                for platform, count in platform_result.fetchall()
            }
            
            # 获取最近订阅（最近5个）
            recent_query = (
                select(Subscription)
                .options(joinedload(Subscription.account))
                .where(Subscription.user_id == user_id)
                .order_by(desc(Subscription.created_at))
                .limit(5)
            )
            recent_result = await db.execute(recent_query)
            recent_subscriptions_raw = recent_result.scalars().all()
            
            recent_subscriptions = []
            for subscription in recent_subscriptions_raw:
                account = subscription.account
                latest_article_time, article_count = await self._get_account_article_stats(
                    db, account.id
                )
                
                recent_subscription = SubscriptionWithAccount(
                    id=subscription.id,
                    user_id=subscription.user_id,
                    account_id=subscription.account_id,
                    created_at=subscription.created_at,
                    account_name=account.name,
                    account_platform=account.platform,
                    account_avatar_url=account.avatar_url,
                    account_description=account.description,
                    account_follower_count=account.follower_count,
                    platform_display_name=self._get_platform_display_name(account.platform),
                    latest_article_time=latest_article_time,
                    article_count=article_count
                )
                recent_subscriptions.append(recent_subscription)
            
            stats = SubscriptionStats(
                total_subscriptions=limit_info["subscription_used"],
                subscription_limit=limit_info["subscription_limit"],
                remaining_subscriptions=limit_info["subscription_remaining"],
                platform_stats=platform_stats,
                recent_subscriptions=recent_subscriptions
            )
            
            logger.debug(f"获取订阅统计成功 - 用户ID: {user_id}")
            return stats
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"获取订阅统计失败: {str(e)}", exc_info=True)
            raise BusinessException(
                error_code=ErrorCode.DATABASE_ERROR,
                message="获取订阅统计失败"
            )
    
    async def batch_create_subscriptions(
        self, 
        batch_data: BatchSubscriptionCreate, 
        db: AsyncSession
    ) -> BatchSubscriptionResponse:
        """
        批量创建订阅
        
        Args:
            batch_data: 批量订阅数据
            db: 数据库会话
            
        Returns:
            批量操作结果
        """
        try:
            user_id = batch_data.user_id
            account_ids = batch_data.account_ids
            
            # 检查用户是否存在
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise NotFoundException("用户不存在")
            
            success_accounts = []
            failed_accounts = []
            
            for account_id in account_ids:
                try:
                    # 创建单个订阅
                    subscription_data = SubscriptionCreate(
                        user_id=user_id,
                        account_id=account_id
                    )
                    await self.create_subscription(subscription_data, db)
                    success_accounts.append(account_id)
                    
                except Exception as e:
                    failed_accounts.append({
                        "account_id": account_id,
                        "error": str(e)
                    })
            
            success_count = len(success_accounts)
            failed_count = len(failed_accounts)
            
            if success_count > 0:
                message = f"成功订阅 {success_count} 个账号"
                if failed_count > 0:
                    message += f"，失败 {failed_count} 个"
            else:
                message = "所有订阅都失败了"
            
            response = BatchSubscriptionResponse(
                success_count=success_count,
                failed_count=failed_count,
                success_accounts=success_accounts,
                failed_accounts=failed_accounts,
                message=message
            )
            
            logger.info(
                f"批量订阅完成 - 用户ID: {user_id}, "
                f"成功: {success_count}, 失败: {failed_count}"
            )
            
            return response
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"批量订阅失败: {str(e)}", exc_info=True)
            raise BusinessException(
                error_code=ErrorCode.DATABASE_ERROR,
                message="批量订阅失败"
            )
    
    async def check_subscription_status(
        self, 
        user_id: int, 
        account_id: int, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        检查订阅状态
        
        Args:
            user_id: 用户ID
            account_id: 账号ID
            db: 数据库会话
            
        Returns:
            订阅状态信息
        """
        try:
            # 检查是否已订阅
            subscription = await self._get_subscription_by_user_account(
                db, user_id, account_id
            )
            
            is_subscribed = subscription is not None
            subscription_id = subscription.id if subscription else None
            subscription_time = subscription.created_at if subscription else None
            
            # 检查是否可以订阅（如果未订阅）
            can_subscribe = True
            limit_info = None
            
            if not is_subscribed:
                try:
                    limit_info = await limits_service.check_subscription_limit(
                        user_id, db, raise_exception=False
                    )
                    can_subscribe = limit_info["can_subscribe"]
                except Exception as e:
                    logger.warning(f"检查订阅限制失败，用户ID: {user_id}, 错误: {str(e)}")
                    can_subscribe = False
            
            status = {
                "user_id": user_id,
                "account_id": account_id,
                "is_subscribed": is_subscribed,
                "subscription_id": subscription_id,
                "subscription_time": subscription_time,
                "can_subscribe": can_subscribe,
                "limit_info": limit_info
            }
            
            logger.debug(
                f"检查订阅状态完成 - 用户ID: {user_id}, 账号ID: {account_id}, "
                f"已订阅: {is_subscribed}"
            )
            
            return status
            
        except Exception as e:
            logger.error(f"检查订阅状态失败: {str(e)}", exc_info=True)
            raise BusinessException(
                error_code=ErrorCode.DATABASE_ERROR,
                message="检查订阅状态失败"
            )
    
    def _get_platform_display_name(self, platform: str) -> str:
        """获取平台显示名称"""
        display_names = {
            "wechat": "微信公众号",
            "weixin": "微信公众号",
            "weibo": "微博",
            "twitter": "推特",
            "bilibili": "哔哩哔哩",
            "douyin": "抖音",
            "zhihu": "知乎",
            "xiaohongshu": "小红书"
        }
        return display_names.get(platform, platform)
    
    async def _get_user_by_id(self, db: AsyncSession, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_account_by_id(self, db: AsyncSession, account_id: int) -> Optional[Account]:
        """根据ID获取账号"""
        stmt = select(Account).where(Account.id == account_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_subscription_by_user_account(
        self, 
        db: AsyncSession, 
        user_id: int, 
        account_id: int
    ) -> Optional[Subscription]:
        """根据用户ID和账号ID获取订阅记录"""
        stmt = (
            select(Subscription)
            .where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.account_id == account_id
                )
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_account_article_stats(
        self, 
        db: AsyncSession, 
        account_id: int
    ) -> Tuple[Optional[datetime], int]:
        """获取账号的文章统计信息"""
        try:
            # 获取最新文章时间
            latest_query = (
                select(Article.publish_time)
                .where(Article.account_id == account_id)
                .order_by(desc(Article.publish_time))
                .limit(1)
            )
            latest_result = await db.execute(latest_query)
            latest_time = latest_result.scalar_one_or_none()
            
            # 获取文章总数
            count_query = (
                select(func.count(Article.id))
                .where(Article.account_id == account_id)
            )
            count_result = await db.execute(count_query)
            article_count = count_result.scalar() or 0
            
            return latest_time, article_count
            
        except Exception as e:
            logger.warning(f"获取账号文章统计失败: {str(e)}")
            return None, 0
    
    async def _clear_user_subscription_cache(self, user_id: int):
        """清除用户订阅相关缓存"""
        try:
            cache_keys = [
                f"user_subscriptions:{user_id}",
                f"subscription_stats:{user_id}",
                f"subscription_limits:{user_id}"
            ]
            
            for key in cache_keys:
                await cache_service.delete(key)
                
        except Exception as e:
            logger.warning(f"清除缓存失败: {str(e)}")


# 全局订阅服务实例
subscription_service = SubscriptionService()