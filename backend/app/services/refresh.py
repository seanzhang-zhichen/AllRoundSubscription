"""
内容刷新服务
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from app.models.article import Article
from app.models.account import Account
from app.models.subscription import Subscription
from app.db.redis import get_redis
from app.core.exceptions import BusinessException
import json
import logging

logger = logging.getLogger(__name__)


class ContentRefreshService:
    """内容刷新服务"""
    
    def __init__(self):
        self.refresh_cache_prefix = "refresh:"
        self.last_refresh_key = "last_refresh"
        self.refresh_lock_ttl = 300  # 5分钟刷新锁
        self.min_refresh_interval = 60  # 最小刷新间隔1分钟
        self.batch_size = 100  # 批量处理大小
    
    async def refresh_user_content(
        self, 
        db: AsyncSession, 
        user_id: int, 
        force: bool = False
    ) -> Dict[str, Any]:
        """
        刷新用户内容
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            force: 是否强制刷新
        
        Returns:
            刷新结果
        """
        try:
            # 检查刷新频率限制
            if not force and not await self._can_refresh(user_id):
                last_refresh = await self._get_last_refresh_time(user_id)
                return {
                    'success': False,
                    'message': '刷新过于频繁，请稍后再试',
                    'last_refresh': last_refresh,
                    'min_interval': self.min_refresh_interval
                }
            
            # 获取刷新锁
            lock_acquired = await self._acquire_refresh_lock(user_id)
            if not lock_acquired:
                return {
                    'success': False,
                    'message': '正在刷新中，请稍候',
                    'status': 'refreshing'
                }
            
            try:
                # 执行刷新操作
                refresh_result = await self._perform_content_refresh(db, user_id)
                
                # 更新最后刷新时间
                await self._update_last_refresh_time(user_id)
                
                # 清除相关缓存
                await self._clear_user_caches(user_id)
                
                return {
                    'success': True,
                    'message': '内容刷新成功',
                    'refresh_time': datetime.now().isoformat(),
                    'stats': refresh_result
                }
                
            finally:
                # 释放刷新锁
                await self._release_refresh_lock(user_id)
                
        except Exception as e:
            logger.error(f"刷新用户内容失败: {str(e)}")
            await self._release_refresh_lock(user_id)
            raise BusinessException(message="内容刷新失败")
    
    async def refresh_account_content(
        self, 
        db: AsyncSession, 
        account_id: int
    ) -> Dict[str, Any]:
        """
        刷新指定账号的内容
        
        Args:
            db: 数据库会话
            account_id: 账号ID
        
        Returns:
            刷新结果
        """
        try:
            # 获取账号信息
            account_query = select(Account).where(Account.id == account_id)
            account_result = await db.execute(account_query)
            account = account_result.scalar_one_or_none()
            
            if not account:
                raise BusinessException(message="账号不存在", status_code=404)
            
            # 模拟从平台获取最新内容（实际实现中会调用对应平台的API）
            new_articles = await self._fetch_account_latest_content(account)
            
            # 保存新文章到数据库
            saved_count = 0
            for article_data in new_articles:
                # 检查文章是否已存在
                existing_query = select(Article).where(Article.url == article_data['url'])
                existing_result = await db.execute(existing_query)
                if existing_result.scalar_one_or_none():
                    continue
                
                # 创建新文章
                article = Article(
                    account_id=account.id,
                    title=article_data['title'],
                    url=article_data['url'],
                    content=article_data.get('content'),
                    summary=article_data.get('summary'),
                    publish_time=article_data['publish_time'],
                    publish_timestamp=int(article_data['publish_time'].timestamp()),
                    images=article_data.get('images'),
                    details=article_data.get('details', {})
                )
                db.add(article)
                saved_count += 1
            
            await db.commit()
            
            # 清除相关缓存
            await self._clear_account_caches(account_id)
            
            return {
                'success': True,
                'account_id': account_id,
                'account_name': account.name,
                'new_articles': saved_count,
                'refresh_time': datetime.now().isoformat()
            }
            
        except BusinessException:
            raise
        except Exception as e:
            logger.error(f"刷新账号内容失败: {str(e)}")
            raise BusinessException(message="账号内容刷新失败")
    
    async def get_refresh_status(self, user_id: int) -> Dict[str, Any]:
        """
        获取刷新状态
        
        Args:
            user_id: 用户ID
        
        Returns:
            刷新状态信息
        """
        try:
            last_refresh = await self._get_last_refresh_time(user_id)
            can_refresh = await self._can_refresh(user_id)
            is_refreshing = await self._is_refreshing(user_id)
            
            next_refresh_time = None
            if last_refresh and not can_refresh:
                next_refresh_time = last_refresh + timedelta(seconds=self.min_refresh_interval)
            
            return {
                'can_refresh': can_refresh,
                'is_refreshing': is_refreshing,
                'last_refresh': last_refresh.isoformat() if last_refresh else None,
                'next_refresh_time': next_refresh_time.isoformat() if next_refresh_time else None,
                'min_interval': self.min_refresh_interval
            }
            
        except Exception as e:
            logger.error(f"获取刷新状态失败: {str(e)}")
            return {
                'can_refresh': True,
                'is_refreshing': False,
                'last_refresh': None,
                'next_refresh_time': None,
                'min_interval': self.min_refresh_interval
            }
    
    async def schedule_batch_refresh(self, db: AsyncSession) -> Dict[str, Any]:
        """
        调度批量刷新任务
        
        Args:
            db: 数据库会话
        
        Returns:
            批量刷新结果
        """
        try:
            # 获取需要刷新的账号列表（有订阅者的账号）
            accounts_query = (
                select(Account.id, Account.name, Account.platform, func.count(Subscription.id).label('subscriber_count'))
                .join(Subscription, Account.id == Subscription.account_id)
                .group_by(Account.id, Account.name, Account.platform)
                .having(func.count(Subscription.id) > 0)
                .order_by(desc('subscriber_count'))
                .limit(self.batch_size)
            )
            
            accounts_result = await db.execute(accounts_query)
            accounts_data = accounts_result.fetchall()
            
            refresh_results = []
            total_new_articles = 0
            
            for account_id, account_name, platform, subscriber_count in accounts_data:
                try:
                    result = await self.refresh_account_content(db, account_id)
                    refresh_results.append({
                        'account_id': account_id,
                        'account_name': account_name,
                        'platform': platform.value,
                        'subscriber_count': subscriber_count,
                        'new_articles': result.get('new_articles', 0),
                        'success': result.get('success', False)
                    })
                    total_new_articles += result.get('new_articles', 0)
                    
                except Exception as e:
                    logger.error(f"批量刷新账号 {account_id} 失败: {str(e)}")
                    refresh_results.append({
                        'account_id': account_id,
                        'account_name': account_name,
                        'platform': platform.value,
                        'subscriber_count': subscriber_count,
                        'new_articles': 0,
                        'success': False,
                        'error': str(e)
                    })
            
            return {
                'success': True,
                'total_accounts': len(accounts_data),
                'total_new_articles': total_new_articles,
                'refresh_time': datetime.now().isoformat(),
                'results': refresh_results
            }
            
        except Exception as e:
            logger.error(f"批量刷新失败: {str(e)}")
            raise BusinessException(message="批量刷新失败")
    
    async def _can_refresh(self, user_id: int) -> bool:
        """检查是否可以刷新"""
        try:
            last_refresh = await self._get_last_refresh_time(user_id)
            if not last_refresh:
                return True
            
            time_since_last = datetime.now() - last_refresh
            return time_since_last.total_seconds() >= self.min_refresh_interval
            
        except Exception:
            return True
    
    async def _get_last_refresh_time(self, user_id: int) -> Optional[datetime]:
        """获取最后刷新时间"""
        try:
            redis = await get_redis()
            if not redis:
                return None
            
            key = f"{self.refresh_cache_prefix}{self.last_refresh_key}:{user_id}"
            timestamp = await redis.get(key)
            
            if timestamp:
                return datetime.fromisoformat(timestamp.decode())
            
            return None
            
        except Exception as e:
            logger.error(f"获取最后刷新时间失败: {str(e)}")
            return None
    
    async def _update_last_refresh_time(self, user_id: int) -> None:
        """更新最后刷新时间"""
        try:
            redis = await get_redis()
            if not redis:
                return
            
            key = f"{self.refresh_cache_prefix}{self.last_refresh_key}:{user_id}"
            await redis.setex(key, 3600, datetime.now().isoformat())  # 1小时过期
            
        except Exception as e:
            logger.error(f"更新最后刷新时间失败: {str(e)}")
    
    async def _acquire_refresh_lock(self, user_id: int) -> bool:
        """获取刷新锁"""
        try:
            redis = await get_redis()
            if not redis:
                return True  # Redis不可用时允许刷新
            
            lock_key = f"{self.refresh_cache_prefix}lock:{user_id}"
            result = await redis.set(lock_key, "1", ex=self.refresh_lock_ttl, nx=True)
            return result is not None
            
        except Exception as e:
            logger.error(f"获取刷新锁失败: {str(e)}")
            return True
    
    async def _release_refresh_lock(self, user_id: int) -> None:
        """释放刷新锁"""
        try:
            redis = await get_redis()
            if not redis:
                return
            
            lock_key = f"{self.refresh_cache_prefix}lock:{user_id}"
            await redis.delete(lock_key)
            
        except Exception as e:
            logger.error(f"释放刷新锁失败: {str(e)}")
    
    async def _is_refreshing(self, user_id: int) -> bool:
        """检查是否正在刷新"""
        try:
            redis = await get_redis()
            if not redis:
                return False
            
            lock_key = f"{self.refresh_cache_prefix}lock:{user_id}"
            result = await redis.get(lock_key)
            return result is not None
            
        except Exception:
            return False
    
    async def _perform_content_refresh(self, db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """执行内容刷新"""
        try:
            # 获取用户订阅的账号
            subscriptions_query = (
                select(Account)
                .join(Subscription, Account.id == Subscription.account_id)
                .where(Subscription.user_id == user_id)
            )
            
            subscriptions_result = await db.execute(subscriptions_query)
            accounts = subscriptions_result.scalars().all()
            
            total_new_articles = 0
            refreshed_accounts = 0
            
            for account in accounts:
                try:
                    result = await self.refresh_account_content(db, account.id)
                    if result.get('success'):
                        total_new_articles += result.get('new_articles', 0)
                        refreshed_accounts += 1
                        
                except Exception as e:
                    logger.error(f"刷新账号 {account.id} 失败: {str(e)}")
                    continue
            
            return {
                'total_accounts': len(accounts),
                'refreshed_accounts': refreshed_accounts,
                'total_new_articles': total_new_articles
            }
            
        except Exception as e:
            logger.error(f"执行内容刷新失败: {str(e)}")
            return {
                'total_accounts': 0,
                'refreshed_accounts': 0,
                'total_new_articles': 0
            }
    
    async def _fetch_account_latest_content(self, account: Account) -> List[Dict[str, Any]]:
        """
        从平台获取账号最新内容（模拟实现）
        
        实际实现中应该调用对应平台的API
        """
        # 这里是模拟实现，实际应该根据平台调用相应的API
        mock_articles = []
        
        # 模拟生成1-3篇新文章
        import random
        num_articles = random.randint(0, 3)
        
        for i in range(num_articles):
            mock_article = {
                'title': f'{account.name} 的最新动态 {i+1}',
                'url': f'https://example.com/{account.platform.value}/{account.account_id}/article_{datetime.now().timestamp()}_{i}',
                'content': f'这是来自 {account.name} 的最新内容 {i+1}',
                'summary': f'最新内容摘要 {i+1}',
                'publish_time': datetime.now() - timedelta(minutes=random.randint(1, 60)),
                'images': [f'https://example.com/image_{i+1}.jpg'] if random.choice([True, False]) else None,
                'details': {
                    'platform': account.platform.value,
                    'fetched_at': datetime.now().isoformat()
                }
            }
            mock_articles.append(mock_article)
        
        return mock_articles
    
    async def _clear_user_caches(self, user_id: int) -> None:
        """清除用户相关缓存"""
        try:
            redis = await get_redis()
            if not redis:
                return
            
            # 清除动态流缓存
            feed_pattern = f"content:feed:{user_id}:*"
            feed_keys = await redis.keys(feed_pattern)
            if feed_keys:
                await redis.delete(*feed_keys)
            
            # 清除文章详情缓存
            detail_pattern = f"content:detail:*:{user_id}"
            detail_keys = await redis.keys(detail_pattern)
            if detail_keys:
                await redis.delete(*detail_keys)
            
            logger.info(f"清除用户 {user_id} 的缓存")
            
        except Exception as e:
            logger.error(f"清除用户缓存失败: {str(e)}")
    
    async def _clear_account_caches(self, account_id: int) -> None:
        """清除账号相关缓存"""
        try:
            redis = await get_redis()
            if not redis:
                return
            
            # 清除账号文章缓存
            account_pattern = f"content:account:{account_id}:*"
            account_keys = await redis.keys(account_pattern)
            if account_keys:
                await redis.delete(*account_keys)
            
            logger.info(f"清除账号 {account_id} 的缓存")
            
        except Exception as e:
            logger.error(f"清除账号缓存失败: {str(e)}")


# 创建服务实例
refresh_service = ContentRefreshService()