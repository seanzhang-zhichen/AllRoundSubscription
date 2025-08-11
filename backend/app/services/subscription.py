"""
订阅管理服务
"""
from app.core.logging import get_logger
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import time
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
from app.services.search.service import search_service

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
            platform = subscription_data.platform
            source = subscription_data.source

            print("====="*10)
            print(f"订阅参数： {subscription_data}")
            print("====="*10)
            
            # 检查用户是否存在
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise NotFoundException("用户不存在")
            
            # 优先通过平台和账号ID查找账号
            if source == 'included':
                account = await search_service.get_account_by_platform_id(platform, account_id)
            elif source == 'search':
                logger.info(f"开始添加账号: {subscription_data}")
                account = await search_service.add_account(platform, mp_name=subscription_data.mp_name, avatar=subscription_data.avatar, mp_id=subscription_data.account_id, mp_intro=subscription_data.mp_intro)
            else:
                raise ValueError(f"无效的订阅来源: {source}")
            
            if not account:
                raise NotFoundException(f"在平台 {platform} 上未找到账号 {account_id}")
            
            # 检查是否已经订阅
            existing_subscription = await self._get_subscription_by_user_account(
                db, user_id, account.id, platform
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
                account_id=account.id,
                platform=platform
            )
            
            db.add(subscription)
            await db.commit()
            await db.refresh(subscription)
            
            # 清除相关缓存
            await self._clear_user_subscription_cache(user_id)
            
            logger.info(
                f"创建订阅成功 - 用户ID: {user_id}, 账号ID: {account.id}, "
                f"平台: {platform}, 订阅ID: {subscription.id}"
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
        account_id: str, 
        platform: str,
        source: str,
        db: AsyncSession
    ) -> bool:
        """
        删除订阅关系
        
        Args:
            user_id: 用户ID
            account_id: 账号ID
            platform: 平台类型
            db: 数据库会话
            
        Returns:
            是否删除成功
            
        Raises:
            NotFoundException: 订阅关系不存在
        """
        try:
            print("====="*10)
            print(f"删除订阅: {user_id}, {account_id}, {platform}, {source}")
            print("====="*10)
            

            if source == "search":
                account_id = await search_service.get_id_by_faker_id(account_id, platform)

            subscription_query = (
                select(Subscription)
                .where(
                    and_(
                        Subscription.user_id == user_id,
                        Subscription.account_id == account_id,
                        Subscription.platform == platform
                    )
                )
            )
            
            result = await db.execute(subscription_query)
            subscription = result.scalar_one_or_none()
            if not subscription:
                raise NotFoundException("订阅关系不存在")
            
            # 删除订阅记录
            await db.delete(subscription)
            await db.commit()
            
            # 清除相关缓存
            await self._clear_user_subscription_cache(user_id)
            
            logger.info(
                f"删除订阅成功 - 用户ID: {user_id}, 账号ID: {subscription.account_id}, "
                f"平台: {subscription.platform}, 订阅ID: {subscription.id}"
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
            
            logger.info(f"开始获取用户订阅列表 - 用户ID: {user_id}")
            
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
                base_query = base_query.where(Subscription.platform == query_params.platform)
            
            # 获取总数
            count_query = select(func.count()).select_from(base_query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar()
            
            # 排序和分页
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
            
            # 转换为响应模型
            subscription_list = []
            
            # 遍历所有订阅并获取额外信息
            for subscription in enumerate(subscriptions):
                # 获取实际的订阅对象（enumerate返回的是元组）
                _, subscription = subscription
                
                # 获取账号信息
                account_id = subscription.account_id
                platform = subscription.platform
                account = await search_service.get_account_by_platform_id(platform, account_id)
                
                # 获取最新文章时间和文章数量
                latest_article_time, article_count = await self._get_account_article_stats(
                    db, platform, account_id
                )
                
                # 构建响应模型
                subscription_with_account = SubscriptionWithAccount(
                    id=subscription.id,
                    user_id=subscription.user_id,
                    account_id=subscription.account_id,
                    platform=subscription.platform,
                    created_at=subscription.created_at,
                    account_name=account.name,
                    account_platform=account.platform,
                    account_avatar_url=account.avatar_url,
                    account_description=account.description,
                    account_follower_count=account.follower_count,
                    platform_display_name=self._get_platform_display_name(subscription.platform),
                    latest_article_time=latest_article_time,
                    article_count=article_count
                )
                subscription_list.append(subscription_with_account)
            
            logger.info(f"获取用户订阅列表完成 - 用户ID: {user_id}, 返回: {len(subscription_list)}/{total}")
            
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
            
            # 获取平台统计 - 使用订阅表中的platform字段
            platform_stats_query = (
                select(Subscription.platform, func.count(Subscription.id))
                .where(Subscription.user_id == user_id)
                .group_by(Subscription.platform)
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
                    platform=subscription.platform,
                    created_at=subscription.created_at,
                    account_name=account.name,
                    account_platform=account.platform,
                    account_avatar_url=account.avatar_url,
                    account_description=account.description,
                    account_follower_count=account.follower_count,
                    platform_display_name=self._get_platform_display_name(subscription.platform),
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
            platform = batch_data.platform
            
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
                        account_id=str(account_id),
                        platform=platform
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
                f"批量订阅完成 - 用户ID: {user_id}, 平台: {platform}, "
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
        account_id: str, 
        platform: str,
        source: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        检查订阅状态
        
        Args:
            user_id: 用户ID
            account_id: 账号ID
            platform: 平台类型
            db: 数据库会话
            
        Returns:
            订阅状态信息
        """
        try:

            print("====="*10)
            print(f"检查订阅状态: {user_id}, {account_id}, {platform}, {source}")
            print("====="*10)

            if source == "search":
                real_account_id = await search_service.get_id_by_faker_id(account_id, platform)
                print("====="*10)
                print(f"根据faker_id查询账号的id: {real_account_id}")
                print("====="*10)
                if real_account_id is None:
                    # 检查是否可以订阅（如果未订阅）
                    can_subscribe = True
                    limit_info = None

                    try:
                        limit_info = await limits_service.check_subscription_limit(
                            user_id, db, raise_exception=False
                        )
                        can_subscribe = limit_info["can_subscribe"]
                    except Exception as e:
                        logger.warning(f"检查订阅限制失败，用户ID: {user_id}, 错误: {str(e)}")
                        can_subscribe = False
                    return {
                        "user_id": user_id,
                        "account_id": account_id,
                        "platform": platform,
                        "is_subscribed": False,
                        "subscription_id": None,
                        "subscription_time": None,
                        "can_subscribe": can_subscribe,
                        "limit_info": limit_info
                    }
                else:
                    account_id = real_account_id

            # 查找订阅记录
            subscription = None

            # 如果找到了账号，使用账号ID查找订阅
            subscription_query = (
                select(Subscription)
                .where(
                    and_(
                        Subscription.user_id == user_id,
                        Subscription.account_id == account_id,
                        Subscription.platform == platform
                    )
                )
            )
            
            result = await db.execute(subscription_query)
            subscription = result.scalar_one_or_none()
            
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
                "platform": platform,
                "is_subscribed": is_subscribed,
                "subscription_id": subscription_id,
                "subscription_time": subscription_time,
                "can_subscribe": can_subscribe,
                "limit_info": limit_info
            }
            
            logger.debug(
                f"检查订阅状态完成 - 用户ID: {user_id}, 账号ID: {account_id}, "
                f"平台: {platform}, 已订阅: {is_subscribed}"
            )
            
            return status

        except Exception as e:
            traceback.print_exc()
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
    
    async def _get_account_by_platform_id(self, db: AsyncSession, platform: str, account_id: str) -> Optional[Account]:
        """根据平台和平台账号ID获取账号"""
        stmt = (
            select(Account)
            .where(
                and_(
                    Account.platform == platform,
                    Account.account_id == account_id
                )
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_subscription_by_user_account(
        self, 
        db: AsyncSession, 
        user_id: int, 
        account_id: int,
        platform: str
    ) -> Optional[Subscription]:
        """
        根据用户ID和账号ID获取订阅记录
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            account_id: 账号ID
            platform: 平台类型
            
        Returns:
            订阅记录，如果不存在则返回None
        """
        query = (
            select(Subscription)
            .where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.account_id == account_id,
                    Subscription.platform == platform
                )
            )
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_account_article_stats(
        self, 
        db: AsyncSession, 
        platform: str,
        account_id: str
    ) -> Tuple[Optional[datetime], int]:
        """
        获取账号的文章统计信息（最新文章时间和文章数量）
        
        Args:
            db: 数据库会话
            platform: 平台
            account_id: 账号ID
            
        Returns:
            (最新文章时间, 文章数量)元组
        """

        
        try:
            # 获取最新文章时间
            start_time = time.time()
            logger.debug(f"开始获取文章统计 - 平台:{platform}, 账号ID:{account_id}")
            stats = await search_service.get_account_article_stats(account_id, platform)
            end_time = time.time()
            logger.debug(f"获取文章统计完成 - 平台:{platform}, 账号ID:{account_id}, 耗时:{end_time - start_time:.3f}秒")
            if stats:
                latest_time = stats.get("latest_article_time")
                article_count = stats.get("article_count")
                return latest_time, article_count
            else:
                return None, 0
            
        except Exception as e:
            logger.error(f"获取文章统计失败 - 平台:{platform}, 账号ID:{account_id}, 错误:{str(e)}")
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