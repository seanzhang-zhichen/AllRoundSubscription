"""
新内容检测服务测试
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.content_detection import content_detection_service
from app.models.article import Article
from app.models.account import Account, Platform
from app.models.subscription import Subscription
from app.models.user import User, MembershipLevel


@pytest.fixture
def mock_db():
    """模拟数据库会话"""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_articles():
    """示例文章数据"""
    return [
        Article(
            id=1,
            account_id=1,
            title="测试文章1",
            url="https://example.com/article1",
            summary="这是测试文章1的摘要",
            publish_time=datetime.now(),
            publish_timestamp=int(datetime.now().timestamp()),
            images=["https://example.com/image1.jpg"],
            created_at=datetime.now()
        ),
        Article(
            id=2,
            account_id=2,
            title="测试文章2",
            url="https://example.com/article2",
            summary="这是测试文章2的摘要",
            publish_time=datetime.now(),
            publish_timestamp=int(datetime.now().timestamp()),
            images=[],
            created_at=datetime.now()
        )
    ]


@pytest.fixture
def sample_subscriptions():
    """示例订阅数据"""
    return [
        (1,),  # user_id = 1 订阅了 account_id = 1
        (2,),  # user_id = 2 订阅了 account_id = 1
    ]


class TestContentDetectionService:
    """新内容检测服务测试类"""
    
    @pytest.mark.asyncio
    async def test_detect_new_content_success(self, mock_db, sample_articles):
        """测试成功检测新内容"""
        # 模拟数据库查询返回新文章
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_articles
        mock_db.execute.return_value = mock_result
        
        # 模拟Redis操作
        with patch('app.services.content_detection.get_redis') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            
            # 模拟获取上次检查时间
            mock_redis_client.get.return_value = None
            
            # 模拟订阅查询
            subscription_result = MagicMock()
            subscription_result.fetchall.return_value = [(1,), (2,)]
            mock_db.execute.side_effect = [mock_result, subscription_result, subscription_result]
            
            # 执行测试
            result = await content_detection_service.detect_new_content(mock_db)
            
            # 验证结果
            assert len(result) == 2
            assert result[0]["id"] == 1
            assert result[0]["title"] == "测试文章1"
            assert result[1]["id"] == 2
            assert result[1]["title"] == "测试文章2"
            
            # 验证Redis操作被调用
            mock_redis_client.lpush.assert_called()
            mock_redis_client.set.assert_called()
    
    @pytest.mark.asyncio
    async def test_detect_new_content_no_articles(self, mock_db):
        """测试没有新文章的情况"""
        # 模拟数据库查询返回空结果
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        # 模拟Redis操作
        with patch('app.services.content_detection.get_redis') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            mock_redis_client.get.return_value = None
            
            # 执行测试
            result = await content_detection_service.detect_new_content(mock_db)
            
            # 验证结果
            assert len(result) == 0
            
            # 验证仍然更新了检查时间
            mock_redis_client.set.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_content_change_notifications(self, mock_db):
        """测试获取内容变更通知"""
        # 模拟订阅查询
        subscription_result = MagicMock()
        subscription_result.fetchall.return_value = [(1,), (2,)]
        
        # 模拟文章查询
        article_result = MagicMock()
        article_data = [
            (
                Article(
                    id=1,
                    account_id=1,
                    title="通知文章1",
                    url="https://example.com/notify1",
                    summary="通知摘要1",
                    publish_time=datetime.now(),
                    created_at=datetime.now(),
                    images=[]
                ),
                Account(
                    id=1,
                    name="测试账号1",
                    platform="wechat",
                    avatar_url="https://example.com/avatar1.jpg"
                )
            )
        ]
        article_result.fetchall.return_value = article_data
        
        mock_db.execute.side_effect = [subscription_result, article_result]
        
        # 执行测试
        result = await content_detection_service.get_content_change_notifications(mock_db, 1)
        
        # 验证结果
        assert len(result) == 1
        assert result[0]["article_id"] == 1
        assert result[0]["account_name"] == "测试账号1"
        assert result[0]["title"] == "通知文章1"
    
    @pytest.mark.asyncio
    async def test_get_content_change_notifications_no_subscriptions(self, mock_db):
        """测试用户没有订阅时的通知获取"""
        # 模拟空订阅查询
        subscription_result = MagicMock()
        subscription_result.fetchall.return_value = []
        mock_db.execute.return_value = subscription_result
        
        # 执行测试
        result = await content_detection_service.get_content_change_notifications(mock_db, 1)
        
        # 验证结果
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_get_push_queue_status(self):
        """测试获取推送队列状态"""
        with patch('app.services.content_detection.get_redis') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            
            # 模拟队列长度
            mock_redis_client.llen.return_value = 5
            mock_redis_client.lrange.return_value = [
                '{"article_id": 1, "user_ids": [1, 2], "created_at": "2024-01-01T10:00:00"}'
            ]
            
            # 执行测试
            result = await content_detection_service.get_push_queue_status()
            
            # 验证结果
            assert result["queue_length"] == 5
            assert result["status"] == "active"
            assert len(result["recent_items"]) == 1
            assert result["recent_items"][0]["article_id"] == 1
    
    @pytest.mark.asyncio
    async def test_get_push_queue_status_redis_unavailable(self):
        """测试Redis不可用时的队列状态获取"""
        with patch('app.services.content_detection.get_redis') as mock_redis:
            mock_redis.return_value = None
            
            # 执行测试
            result = await content_detection_service.get_push_queue_status()
            
            # 验证结果
            assert result["queue_length"] == 0
            assert result["status"] == "redis_unavailable"
    
    @pytest.mark.asyncio
    async def test_clear_push_queue(self):
        """测试清空推送队列"""
        with patch('app.services.content_detection.get_redis') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            
            # 执行测试
            result = await content_detection_service.clear_push_queue()
            
            # 验证结果
            assert result is True
            mock_redis_client.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_clear_push_queue_redis_unavailable(self):
        """测试Redis不可用时的队列清空"""
        with patch('app.services.content_detection.get_redis') as mock_redis:
            mock_redis.return_value = None
            
            # 执行测试
            result = await content_detection_service.clear_push_queue()
            
            # 验证结果
            assert result is False