"""
新内容检测服务
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func, text
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.account import Account, Platform
from app.models.article import Article
from app.models.subscription import Subscription
from app.models.push_record import PushRecord, PushStatus
from app.services.platform import platform_service
from app.db.redis import get_redis
from app.core.exceptions import BusinessException
import json

logger = logging.getLogger(__name__)


class ContentDetectionService:
    """新内容检测服务"""
    
    def __init__(self):
        self.cache_prefix = "content_detection:"
        self.last_check_key = "last_content_check"
        self.new_articles_queue_key = "new_articles_queue"
        
    async def detect_new_content(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """
        检测新内容
        
        Args:
            db: 数据库会话
            
        Returns:
            新文章列表
        """
        try:
            logger.info("开始检测新内容...")
            
            # 获取上次检查时间
            last_check_time = await self._get_last_check_time()
            current_time = datetime.now()
            
            # 如果是首次检查，设置为5分钟前
            if not last_check_time:
                last_check_time = current_time - timedelta(minutes=5)
            
            logger.info(f"上次检查时间: {last_check_time}, 当前时间: {current_time}")
            
            # 查询新文章
            new_articles = await self._find_new_articles(db, last_check_time)
            
            if new_articles:
                logger.info(f"发现 {len(new_articles)} 篇新文章")
                
                # 为每篇新文章创建推送队列记录
                push_queue_items = await self._create_push_queue_items(db, new_articles)
                
                # 将推送任务添加到队列
                await self._add_to_push_queue(push_queue_items)
                
                # 更新最后检查时间
                await self._update_last_check_time(current_time)
                
                return [self._article_to_dict(article) for article in new_articles]
            else:
                logger.info("未发现新内容")
                # 仍然更新检查时间
                await self._update_last_check_time(current_time)
                return []
                
        except Exception as e:
            logger.error(f"检测新内容失败: {str(e)}", exc_info=True)
            raise BusinessException(message="检测新内容失败")
    
    async def get_content_change_notifications(
        self, 
        db: AsyncSession, 
        user_id: int
    ) -> List[Dict[str, Any]]:
        """
        获取用户的内容变更通知
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            内容变更通知列表
        """
        try:
            # 获取用户订阅的账号
            subscribed_accounts_query = (
                select(Subscription.account_id)
                .where(Subscription.user_id == user_id)
            )
            subscribed_accounts_result = await db.execute(subscribed_accounts_query)
            subscribed_account_ids = [row[0] for row in subscribed_accounts_result.fetchall()]
            
            if not subscribed_account_ids:
                return []
            
            # 获取最近24小时的新文章
            since_time = datetime.now() - timedelta(hours=24)
            
            new_articles_query = (
                select(Article, Account)
                .join(Account, Article.account_id == Account.id)
                .where(
                    and_(
                        Article.account_id.in_(subscribed_account_ids),
                        Article.created_at >= since_time
                    )
                )
                .order_by(desc(Article.created_at))
                .limit(50)  # 限制返回数量
            )
            
            articles_result = await db.execute(new_articles_query)
            articles_data = articles_result.fetchall()
            
            notifications = []
            for article, account in articles_data:
                notification = {
                    "article_id": article.id,
                    "account_id": article.account_id,
                    "account_name": account.name,
                    "account_platform": account.platform,
                    "title": article.title,
                    "url": article.url,
                    "summary": article.summary,
                    "publish_time": article.publish_time,
                    "created_at": article.created_at,
                    "has_images": article.has_images,
                    "thumbnail_url": article.get_thumbnail_url()
                }
                notifications.append(notification)
            
            logger.info(f"获取用户 {user_id} 的内容变更通知: {len(notifications)} 条")
            return notifications
            
        except Exception as e:
            logger.error(f"获取内容变更通知失败: {str(e)}", exc_info=True)
            raise BusinessException(message="获取内容变更通知失败")
    
    async def get_push_queue_status(self) -> Dict[str, Any]:
        """
        获取推送队列状态
        
        Returns:
            推送队列状态信息
        """
        try:
            redis = await get_redis()
            if not redis:
                return {"queue_length": 0, "status": "redis_unavailable"}
            
            # 获取队列长度
            queue_length = await redis.llen(self.new_articles_queue_key)
            
            # 获取最近的队列项目（用于调试）
            recent_items = await redis.lrange(self.new_articles_queue_key, 0, 4)
            recent_items_parsed = []
            
            for item in recent_items:
                try:
                    parsed_item = json.loads(item)
                    recent_items_parsed.append({
                        "article_id": parsed_item.get("article_id"),
                        "user_count": len(parsed_item.get("user_ids", [])),
                        "created_at": parsed_item.get("created_at")
                    })
                except Exception:
                    continue
            
            status = {
                "queue_length": queue_length,
                "status": "active",
                "recent_items": recent_items_parsed,
                "last_check_time": await self._get_last_check_time()
            }
            
            logger.debug(f"推送队列状态: {status}")
            return status
            
        except Exception as e:
            logger.error(f"获取推送队列状态失败: {str(e)}")
            return {"queue_length": 0, "status": "error", "error": str(e)}
    
    async def clear_push_queue(self) -> bool:
        """
        清空推送队列（用于调试和维护）
        
        Returns:
            是否成功
        """
        try:
            redis = await get_redis()
            if not redis:
                return False
            
            await redis.delete(self.new_articles_queue_key)
            logger.info("推送队列已清空")
            return True
            
        except Exception as e:
            logger.error(f"清空推送队列失败: {str(e)}")
            return False
    
    async def _find_new_articles(
        self, 
        db: AsyncSession, 
        since_time: datetime
    ) -> List[Article]:
        """查找新文章"""
        try:
            # 查询在指定时间之后创建的文章
            new_articles_query = (
                select(Article)
                .options(selectinload(Article.account))
                .where(Article.created_at > since_time)
                .order_by(desc(Article.created_at))
            )
            
            result = await db.execute(new_articles_query)
            articles = result.scalars().all()
            
            logger.debug(f"查找到 {len(articles)} 篇新文章（自 {since_time}）")
            return list(articles)
            
        except Exception as e:
            logger.error(f"查找新文章失败: {str(e)}")
            return []
    
    async def _create_push_queue_items(
        self, 
        db: AsyncSession, 
        articles: List[Article]
    ) -> List[Dict[str, Any]]:
        """为新文章创建推送队列项目"""
        try:
            push_queue_items = []
            
            for article in articles:
                # 获取订阅了该账号的用户
                subscribers_query = (
                    select(Subscription.user_id)
                    .where(Subscription.account_id == article.account_id)
                )
                subscribers_result = await db.execute(subscribers_query)
                user_ids = [row[0] for row in subscribers_result.fetchall()]
                
                if user_ids:
                    # 创建推送队列项目
                    queue_item = {
                        "article_id": article.id,
                        "account_id": article.account_id,
                        "user_ids": user_ids,
                        "title": article.title,
                        "url": article.url,
                        "summary": article.summary,
                        "publish_time": article.publish_time.isoformat(),
                        "created_at": datetime.now().isoformat(),
                        "status": "pending"
                    }
                    push_queue_items.append(queue_item)
                    
                    logger.debug(
                        f"为文章 {article.id} 创建推送队列项目，"
                        f"目标用户数: {len(user_ids)}"
                    )
            
            return push_queue_items
            
        except Exception as e:
            logger.error(f"创建推送队列项目失败: {str(e)}")
            return []
    
    async def _add_to_push_queue(self, queue_items: List[Dict[str, Any]]) -> bool:
        """将项目添加到推送队列"""
        try:
            if not queue_items:
                return True
            
            redis = await get_redis()
            if not redis:
                logger.warning("Redis不可用，无法添加到推送队列")
                return False
            
            # 将队列项目添加到Redis列表
            for item in queue_items:
                await redis.lpush(
                    self.new_articles_queue_key,
                    json.dumps(item, default=str)
                )
            
            logger.info(f"添加 {len(queue_items)} 个项目到推送队列")
            return True
            
        except Exception as e:
            logger.error(f"添加到推送队列失败: {str(e)}")
            return False
    
    async def _get_last_check_time(self) -> Optional[datetime]:
        """获取上次检查时间"""
        try:
            redis = await get_redis()
            if not redis:
                return None
            
            timestamp_str = await redis.get(
                f"{self.cache_prefix}{self.last_check_key}"
            )
            
            if timestamp_str:
                return datetime.fromisoformat(timestamp_str.decode())
            
            return None
            
        except Exception as e:
            logger.error(f"获取上次检查时间失败: {str(e)}")
            return None
    
    async def _update_last_check_time(self, check_time: datetime) -> bool:
        """更新最后检查时间"""
        try:
            redis = await get_redis()
            if not redis:
                return False
            
            await redis.set(
                f"{self.cache_prefix}{self.last_check_key}",
                check_time.isoformat(),
                ex=86400  # 24小时过期
            )
            
            return True
            
        except Exception as e:
            logger.error(f"更新最后检查时间失败: {str(e)}")
            return False
    
    def _article_to_dict(self, article: Article) -> Dict[str, Any]:
        """将文章对象转换为字典"""
        return {
            "id": article.id,
            "account_id": article.account_id,
            "title": article.title,
            "url": article.url,
            "summary": article.summary,
            "publish_time": article.publish_time,
            "created_at": article.created_at,
            "has_images": article.has_images,
            "image_count": article.image_count,
            "thumbnail_url": article.get_thumbnail_url()
        }


# 创建服务实例
content_detection_service = ContentDetectionService()