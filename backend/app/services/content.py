"""
内容获取服务
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func, text
from sqlalchemy.orm import selectinload
from app.models.article import Article
from app.models.account import Account
from app.models.subscription import Subscription
from app.schemas.article import ArticleResponse, ArticleWithAccount, ArticleDetail, ArticleFeed, ArticleStats
from app.schemas.common import PaginatedResponse
from app.db.redis import get_redis
from app.core.exceptions import BusinessException
from app.services.image import image_service
from app.services.platform import platform_service
import json
import traceback
from app.core.logging import get_logger
from datetime import datetime, timedelta

logger = get_logger(__name__)


class ContentService:
    """内容获取服务"""
    
    def __init__(self):
        self.cache_prefix = "content:"
        self.feed_cache_ttl = 300  # 5分钟
        self.detail_cache_ttl = 600  # 10分钟
    
    async def get_user_feed(
        self, 
        db: AsyncSession, 
        user_id: int, 
        page: int = 1, 
        page_size: int = 20,
        refresh: bool = False
    ) -> PaginatedResponse[ArticleWithAccount]:
        """
        获取用户动态流
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            page: 页码
            page_size: 每页大小
            refresh: 是否刷新缓存
        
        Returns:
            分页的文章列表
        """
        try:
            # 构建缓存键
            cache_key = f"{self.cache_prefix}feed:{user_id}:{page}:{page_size}"
            
            # 如果不是刷新请求，先尝试从缓存获取
            if not refresh:
                cached_result = await self._get_cached_feed(cache_key)
                if cached_result:
                    logger.info(f"从缓存获取用户 {user_id} 的动态流")
                    return cached_result
            
            # 获取用户订阅的账号ID列表
            subscribed_accounts_query = select(Subscription.account_id).where(
                Subscription.user_id == user_id
            )
            subscribed_accounts_result = await db.execute(subscribed_accounts_query)
            subscribed_account_ids = [row[0] for row in subscribed_accounts_result.fetchall()]
            
            if not subscribed_account_ids:
                # 用户没有订阅任何账号
                return PaginatedResponse.create(
                    data=[],
                    total=0,
                    page=page,
                    page_size=page_size
                )
            
            # 构建查询
            offset = (page - 1) * page_size
            
            # 查询文章总数
            count_query = select(func.count(Article.id)).where(
                Article.account_id.in_(subscribed_account_ids)
            )
            total_result = await db.execute(count_query)
            total = total_result.scalar() or 0
            
            # 查询文章列表
            articles_query = (
                select(Article, Account)
                .join(Account, Article.account_id == Account.id)
                .where(Article.account_id.in_(subscribed_account_ids))
                .order_by(desc(Article.publish_timestamp))
                .offset(offset)
                .limit(page_size)
            )
            
            articles_result = await db.execute(articles_query)
            articles_data = articles_result.fetchall()
            
            # 转换为响应模型
            articles = []
            for article, account in articles_data:
                article_with_account = ArticleWithAccount(
                    id=article.id,
                    account_id=article.account_id,
                    title=article.title,
                    url=article.url,
                    content=article.content,
                    summary=article.summary,
                    publish_time=article.publish_time,
                    publish_timestamp=article.publish_timestamp,
                    images=article.images or [],
                    details=article.details or {},
                    created_at=article.created_at,
                    updated_at=article.updated_at,
                    image_count=article.image_count,
                    has_images=article.has_images,
                    thumbnail_url=article.get_thumbnail_url(),
                    account_name=account.name,
                    account_platform=account.platform.value,
                    account_avatar_url=account.avatar_url,
                    platform_display_name=platform_service.get_platform_display_name(account.platform.value)
                )
                articles.append(article_with_account)
            
            result = PaginatedResponse.create(
                data=articles,
                total=total,
                page=page,
                page_size=page_size
            )
            
            # 缓存结果
            await self._cache_feed(cache_key, result)
            
            logger.info(f"获取用户 {user_id} 的动态流，页码: {page}，总数: {total}")
            return result
            
        except Exception as e:
            logger.error(f"获取用户动态流失败: {str(e)}")
            raise BusinessException(message="获取动态流失败")
    
    async def get_article_detail(
        self, 
        db: AsyncSession, 
        article_id: int, 
        user_id: Optional[int] = None
    ) -> ArticleDetail:
        """
        获取文章详情
        
        Args:
            db: 数据库会话
            article_id: 文章ID
            user_id: 用户ID（可选，用于判断是否已订阅）
        
        Returns:
            文章详情
        """
        try:
            # 构建缓存键
            cache_key = f"{self.cache_prefix}detail:{article_id}:{user_id or 0}"
            
            # 尝试从缓存获取
            cached_result = await self._get_cached_detail(cache_key)
            if cached_result:
                logger.info(f"从缓存获取文章详情: {article_id}")
                return cached_result
            
            # 查询文章和账号信息
            article_query = (
                select(Article, Account)
                .join(Account, Article.account_id == Account.id)
                .where(Article.id == article_id)
            )
            
            article_result = await db.execute(article_query)
            article_data = article_result.first()
            
            if not article_data:
                raise BusinessException(message="文章不存在", status_code=404)
            
            article, account = article_data
            
            # 检查用户是否已订阅该账号
            is_subscribed = False
            if user_id:
                subscription_query = select(Subscription).where(
                    and_(
                        Subscription.user_id == user_id,
                        Subscription.account_id == article.account_id
                    )
                )
                subscription_result = await db.execute(subscription_query)
                is_subscribed = subscription_result.first() is not None
            
            # 获取相关文章（同一账号的其他文章）
            related_articles = await self._get_related_articles(db, article.account_id, article.id)
            
            # 构建详情响应
            article_detail = ArticleDetail(
                id=article.id,
                account_id=article.account_id,
                title=article.title,
                url=article.url,
                content=article.content,
                summary=article.summary,
                publish_time=article.publish_time,
                publish_timestamp=article.publish_timestamp,
                images=article.images or [],
                details=article.details or {},
                created_at=article.created_at,
                updated_at=article.updated_at,
                image_count=article.image_count,
                has_images=article.has_images,
                thumbnail_url=article.get_thumbnail_url(),
                account_name=account.name,
                account_platform=account.platform.value,
                account_avatar_url=account.avatar_url,
                platform_display_name=platform_service.get_platform_display_name(account.platform.value),
                is_subscribed=is_subscribed,
                related_articles=related_articles
            )
            
            # 缓存结果
            await self._cache_detail(cache_key, article_detail)
            
            logger.info(f"获取文章详情: {article_id}")
            return article_detail
            
        except BusinessException:
            raise
        except Exception as e:
            logger.error(f"获取文章详情失败: {str(e)}")
            raise BusinessException(message="获取文章详情失败")
    
    async def get_articles_by_account(
        self,
        db: AsyncSession,
        account_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> PaginatedResponse[ArticleResponse]:
        """
        获取指定账号的文章列表
        
        Args:
            db: 数据库会话
            account_id: 账号ID
            page: 页码
            page_size: 每页大小
        
        Returns:
            分页的文章列表
        """
        try:
            offset = (page - 1) * page_size
            
            # 查询文章总数
            count_query = select(func.count(Article.id)).where(
                Article.account_id == account_id
            )
            total_result = await db.execute(count_query)
            total = total_result.scalar() or 0
            
            # 查询文章列表
            articles_query = (
                select(Article)
                .where(Article.account_id == account_id)
                .order_by(desc(Article.publish_timestamp))
                .offset(offset)
                .limit(page_size)
            )
            
            articles_result = await db.execute(articles_query)
            articles_data = articles_result.fetchall()
            
            # 转换为响应模型
            articles = []
            for (article,) in articles_data:
                article_response = ArticleResponse(
                    id=article.id,
                    account_id=article.account_id,
                    title=article.title,
                    url=article.url,
                    content=article.content,
                    summary=article.summary,
                    publish_time=article.publish_time,
                    publish_timestamp=article.publish_timestamp,
                    images=article.images or [],
                    details=article.details or {},
                    created_at=article.created_at,
                    updated_at=article.updated_at,
                    image_count=article.image_count,
                    has_images=article.has_images,
                    thumbnail_url=article.get_thumbnail_url()
                )
                articles.append(article_response)
            
            result = PaginatedResponse.create(
                data=articles,
                total=total,
                page=page,
                page_size=page_size
            )
            
            logger.info(f"获取账号 {account_id} 的文章列表，页码: {page}，总数: {total}")
            return result
            
        except Exception as e:
            logger.error(f"获取账号文章列表失败: {str(e)}")
            raise BusinessException(message="获取文章列表失败")
    
    async def get_content_stats(self, db: AsyncSession, user_id: int) -> ArticleStats:
        """
        获取内容统计信息
        
        Args:
            db: 数据库会话
            user_id: 用户ID
        
        Returns:
            内容统计信息
        """
        try:
            # 获取用户订阅的账号ID列表
            subscribed_accounts_query = select(Subscription.account_id).where(
                Subscription.user_id == user_id
            )
            subscribed_accounts_result = await db.execute(subscribed_accounts_query)
            subscribed_account_ids = [row[0] for row in subscribed_accounts_result.fetchall()]
            
            if not subscribed_account_ids:
                return ArticleStats(
                    total_articles=0,
                    today_articles=0,
                    week_articles=0,
                    platform_stats={}
                )
            
            # 计算时间范围
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = today_start - timedelta(days=7)
            
            # 查询总文章数
            total_query = select(func.count(Article.id)).where(
                Article.account_id.in_(subscribed_account_ids)
            )
            total_result = await db.execute(total_query)
            total_articles = total_result.scalar() or 0
            
            # 查询今日文章数
            today_query = select(func.count(Article.id)).where(
                and_(
                    Article.account_id.in_(subscribed_account_ids),
                    Article.publish_time >= today_start
                )
            )
            today_result = await db.execute(today_query)
            today_articles = today_result.scalar() or 0
            
            # 查询本周文章数
            week_query = select(func.count(Article.id)).where(
                and_(
                    Article.account_id.in_(subscribed_account_ids),
                    Article.publish_time >= week_start
                )
            )
            week_result = await db.execute(week_query)
            week_articles = week_result.scalar() or 0
            
            # 查询各平台文章统计
            platform_query = (
                select(Account.platform, func.count(Article.id))
                .join(Article, Account.id == Article.account_id)
                .where(Article.account_id.in_(subscribed_account_ids))
                .group_by(Account.platform)
            )
            platform_result = await db.execute(platform_query)
            platform_data = platform_result.fetchall()
            
            platform_stats = {}
            for platform, count in platform_data:
                platform_stats[platform.value] = count
            
            stats = ArticleStats(
                total_articles=total_articles,
                today_articles=today_articles,
                week_articles=week_articles,
                platform_stats=platform_stats
            )
            
            logger.info(f"获取用户 {user_id} 的内容统计")
            return stats
            
        except Exception as e:
            logger.error(f"获取内容统计失败: {str(e)}")
            raise BusinessException(message="获取内容统计失败")
    
    async def refresh_user_feed_cache(self, user_id: int) -> bool:
        """
        刷新用户动态流缓存
        
        Args:
            user_id: 用户ID
        
        Returns:
            是否成功
        """
        try:
            redis = await get_redis()
            if not redis:
                return False
            
            # 删除用户相关的缓存
            pattern = f"{self.cache_prefix}feed:{user_id}:*"
            keys = await redis.keys(pattern)
            if keys:
                await redis.delete(*keys)
            
            logger.info(f"刷新用户 {user_id} 的动态流缓存")
            return True
            
        except Exception as e:
            logger.error(f"刷新动态流缓存失败: {str(e)}")
            return False
    
    async def _get_related_articles(
        self, 
        db: AsyncSession, 
        account_id: int, 
        exclude_id: int, 
        limit: int = 5
    ) -> List[ArticleResponse]:
        """获取相关文章"""
        try:
            query = (
                select(Article)
                .where(
                    and_(
                        Article.account_id == account_id,
                        Article.id != exclude_id
                    )
                )
                .order_by(desc(Article.publish_timestamp))
                .limit(limit)
            )
            
            result = await db.execute(query)
            articles_data = result.fetchall()
            
            articles = []
            for (article,) in articles_data:
                article_response = ArticleResponse(
                    id=article.id,
                    account_id=article.account_id,
                    title=article.title,
                    url=article.url,
                    content=article.content,
                    summary=article.summary,
                    publish_time=article.publish_time,
                    publish_timestamp=article.publish_timestamp,
                    images=article.images or [],
                    details=article.details or {},
                    created_at=article.created_at,
                    updated_at=article.updated_at,
                    image_count=article.image_count,
                    has_images=article.has_images,
                    thumbnail_url=article.get_thumbnail_url()
                )
                articles.append(article_response)
            
            return articles
            
        except Exception as e:
            logger.error(f"获取相关文章失败: {str(e)}")
            return []
    

    
    async def _get_cached_feed(self, cache_key: str) -> Optional[PaginatedResponse[ArticleWithAccount]]:
        """从缓存获取动态流"""
        try:
            redis = await get_redis()
            if not redis:
                return None
            
            cached_data = await redis.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                # 重构分页响应对象
                items = [ArticleWithAccount(**item) for item in data['data']]
                return PaginatedResponse.create(
                    data=items,
                    total=data['total'],
                    page=data['page'],
                    page_size=data['page_size']
                )
            
            return None
            
        except Exception as e:
            logger.error(f"获取缓存动态流失败: {str(e)}")
            traceback.print_exc()
            return None
    
    async def _cache_feed(self, cache_key: str, result: PaginatedResponse[ArticleWithAccount]) -> None:
        """缓存动态流"""
        try:
            redis = await get_redis()
            if not redis:
                return
            
            # 转换为可序列化的数据
            data = {
                'data': [item.dict() for item in result.data],
                'total': result.total,
                'page': result.page,
                'page_size': result.page_size,
                'total_pages': result.total_pages
            }
            
            await redis.setex(
                cache_key,
                self.feed_cache_ttl,
                json.dumps(data, default=str)
            )
            
        except Exception as e:
            logger.error(f"缓存动态流失败: {str(e)}")
    
    async def _get_cached_detail(self, cache_key: str) -> Optional[ArticleDetail]:
        """从缓存获取文章详情"""
        try:
            redis = await get_redis()
            if not redis:
                return None
            
            cached_data = await redis.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                return ArticleDetail(**data)
            
            return None
            
        except Exception as e:
            logger.error(f"获取缓存文章详情失败: {str(e)}")
            return None
    
    async def _cache_detail(self, cache_key: str, detail: ArticleDetail) -> None:
        """缓存文章详情"""
        try:
            redis = await get_redis()
            if not redis:
                return
            
            await redis.setex(
                cache_key,
                self.detail_cache_ttl,
                json.dumps(detail.dict(), default=str)
            )
            
        except Exception as e:
            logger.error(f"缓存文章详情失败: {str(e)}")


    async def mark_article_as_read(
        self, 
        db: AsyncSession, 
        article_id: int, 
        user_id: int
    ) -> bool:
        """
        标记文章为已读
        
        Args:
            db: 数据库会话
            article_id: 文章ID
            user_id: 用户ID
        
        Returns:
            是否成功
        """
        try:
            # 这里可以添加用户阅读记录的逻辑
            # 目前先简单返回成功
            logger.info(f"用户 {user_id} 标记文章 {article_id} 为已读")
            return True
            
        except Exception as e:
            logger.error(f"标记文章已读失败: {str(e)}")
            return False
    
    async def favorite_article(
        self, 
        db: AsyncSession, 
        article_id: int, 
        user_id: int
    ) -> bool:
        """
        收藏文章
        
        Args:
            db: 数据库会话
            article_id: 文章ID
            user_id: 用户ID
        
        Returns:
            是否成功
        """
        try:
            # 这里可以添加收藏记录的逻辑
            # 目前先简单返回成功
            logger.info(f"用户 {user_id} 收藏文章 {article_id}")
            return True
            
        except Exception as e:
            logger.error(f"收藏文章失败: {str(e)}")
            return False
    
    async def unfavorite_article(
        self, 
        db: AsyncSession, 
        article_id: int, 
        user_id: int
    ) -> bool:
        """
        取消收藏文章
        
        Args:
            db: 数据库会话
            article_id: 文章ID
            user_id: 用户ID
        
        Returns:
            是否成功
        """
        try:
            # 这里可以添加取消收藏的逻辑
            # 目前先简单返回成功
            logger.info(f"用户 {user_id} 取消收藏文章 {article_id}")
            return True
            
        except Exception as e:
            logger.error(f"取消收藏文章失败: {str(e)}")
            return False
    
    async def share_article(
        self, 
        db: AsyncSession, 
        article_id: int, 
        user_id: int
    ) -> bool:
        """
        记录文章分享统计
        
        Args:
            db: 数据库会话
            article_id: 文章ID
            user_id: 用户ID
        
        Returns:
            是否成功
        """
        try:
            # 这里可以添加分享统计的逻辑
            # 目前先简单返回成功
            logger.info(f"用户 {user_id} 分享文章 {article_id}")
            return True
            
        except Exception as e:
            logger.error(f"记录文章分享失败: {str(e)}")
            return False
    
    async def search_articles(
        self,
        db: AsyncSession,
        keyword: str,
        platform: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        user_id: Optional[int] = None
    ) -> PaginatedResponse[ArticleWithAccount]:
        """
        搜索文章
        
        Args:
            db: 数据库会话
            keyword: 搜索关键词
            platform: 平台筛选
            page: 页码
            page_size: 每页大小
            user_id: 用户ID（可选，用于筛选订阅内容）
        
        Returns:
            分页的文章列表
        """
        try:
            offset = (page - 1) * page_size
            
            # 构建基础查询
            base_query = select(Article, Account).join(Account, Article.account_id == Account.id)
            
            # 添加关键词搜索条件
            search_conditions = [
                Article.title.contains(keyword),
                Article.content.contains(keyword),
                Article.summary.contains(keyword)
            ]
            base_query = base_query.where(
                func.or_(*search_conditions)
            )
            
            # 添加平台筛选
            if platform:
                base_query = base_query.where(Account.platform == platform)
            
            # 如果提供了用户ID，只搜索用户订阅的内容
            if user_id:
                subscribed_accounts_query = select(Subscription.account_id).where(
                    Subscription.user_id == user_id
                )
                subscribed_accounts_result = await db.execute(subscribed_accounts_query)
                subscribed_account_ids = [row[0] for row in subscribed_accounts_result.fetchall()]
                
                if subscribed_account_ids:
                    base_query = base_query.where(Article.account_id.in_(subscribed_account_ids))
                else:
                    # 用户没有订阅任何账号
                    return PaginatedResponse.create(
                        data=[],
                        total=0,
                        page=page,
                        page_size=page_size
                    )
            
            # 查询总数
            count_query = select(func.count()).select_from(base_query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar() or 0
            
            # 查询文章列表
            articles_query = (
                base_query
                .order_by(desc(Article.publish_timestamp))
                .offset(offset)
                .limit(page_size)
            )
            
            articles_result = await db.execute(articles_query)
            articles_data = articles_result.fetchall()
            
            # 转换为响应模型
            articles = []
            for article, account in articles_data:
                article_with_account = ArticleWithAccount(
                    id=article.id,
                    account_id=article.account_id,
                    title=article.title,
                    url=article.url,
                    content=article.content,
                    summary=article.summary,
                    publish_time=article.publish_time,
                    publish_timestamp=article.publish_timestamp,
                    images=article.images or [],
                    details=article.details or {},
                    created_at=article.created_at,
                    updated_at=article.updated_at,
                    image_count=article.image_count,
                    has_images=article.has_images,
                    thumbnail_url=article.get_thumbnail_url(),
                    account_name=account.name,
                    account_platform=account.platform.value,
                    account_avatar_url=account.avatar_url,
                    platform_display_name=platform_service.get_platform_display_name(account.platform.value)
                )
                articles.append(article_with_account)
            
            result = PaginatedResponse.create(
                data=articles,
                total=total,
                page=page,
                page_size=page_size
            )
            
            logger.info(f"搜索文章: {keyword}，平台: {platform}，结果数: {total}")
            return result
            
        except Exception as e:
            logger.error(f"搜索文章失败: {str(e)}")
            raise BusinessException(message="搜索文章失败")


# 创建服务实例
content_service = ContentService()