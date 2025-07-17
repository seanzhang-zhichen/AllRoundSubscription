"""
推送通知功能测试
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.push_notification import push_notification_service
from app.services.wechat import wechat_service
from app.services.push_queue import push_queue_service
from app.models.user import User
from app.models.article import Article
from app.models.account import Account
from app.models.push_record import PushRecord, PushStatus
from app.models.user import MembershipLevel


class TestWeChatPushService:
    """微信推送服务测试"""
    
    @pytest.mark.asyncio
    async def test_send_template_message_success(self):
        """测试发送模板消息成功"""
        with patch('app.services.wechat.httpx.AsyncClient') as mock_client:
            # Mock access token response
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {
                "access_token": "test_token",
                "expires_in": 7200
            }
            mock_token_response.raise_for_status.return_value = None
            
            # Mock template message response
            mock_template_response = MagicMock()
            mock_template_response.json.return_value = {
                "errcode": 0,
                "msgid": "test_msgid_123"
            }
            mock_template_response.raise_for_status.return_value = None
            
            # Configure mock client
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_token_response
            mock_client_instance.post.return_value = mock_template_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Mock Redis
            with patch('app.services.wechat.get_redis') as mock_redis:
                mock_redis.return_value = None
                
                # Test send template message
                result = await wechat_service.send_template_message(
                    openid="test_openid",
                    article_title="测试文章标题",
                    account_name="测试博主",
                    article_id=123,
                    platform_name="微博"
                )
                
                assert result["success"] is True
                assert result["msgid"] == "test_msgid_123"
                assert result["message"] == "推送成功"
    
    @pytest.mark.asyncio
    async def test_send_template_message_user_not_subscribed(self):
        """测试用户未关注服务号的情况"""
        with patch('app.services.wechat.httpx.AsyncClient') as mock_client:
            # Mock access token response
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {
                "access_token": "test_token",
                "expires_in": 7200
            }
            mock_token_response.raise_for_status.return_value = None
            
            # Mock template message error response
            mock_template_response = MagicMock()
            mock_template_response.json.return_value = {
                "errcode": 43004,
                "errmsg": "require subscribe hint"
            }
            mock_template_response.raise_for_status.return_value = None
            
            # Configure mock client
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_token_response
            mock_client_instance.post.return_value = mock_template_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Mock Redis
            with patch('app.services.wechat.get_redis') as mock_redis:
                mock_redis.return_value = None
                
                # Test send template message
                result = await wechat_service.send_template_message(
                    openid="test_openid",
                    article_title="测试文章标题",
                    account_name="测试博主",
                    article_id=123,
                    platform_name="微博"
                )
                
                assert result["success"] is False
                assert result["error_code"] == 43004
                assert "用户未关注服务号" in result["error"]
    
    @pytest.mark.asyncio
    async def test_send_push_notification_with_url(self):
        """测试带URL的推送通知"""
        with patch.object(wechat_service, 'send_template_message') as mock_send:
            mock_send.return_value = {
                "success": True,
                "msgid": "test_msgid",
                "message": "推送成功"
            }
            
            article_data = {
                "id": 123,
                "title": "测试文章",
                "account_name": "测试博主",
                "platform_display_name": "微博",
                "url": "https://example.com/article/123"
            }
            
            result = await wechat_service.send_push_notification(
                user_openid="test_openid",
                article_data=article_data
            )
            
            assert result["success"] is True
            mock_send.assert_called_once_with(
                openid="test_openid",
                article_title="测试文章",
                account_name="测试博主",
                article_id=123,
                platform_name="微博"
            )


class TestPushNotificationService:
    """推送通知服务测试"""
    
    @pytest.mark.asyncio
    async def test_send_article_notification_success(self, db_session: AsyncSession):
        """测试发送文章推送通知成功"""
        # Create test data
        user = User(
            id=1,
            openid="test_openid",
            nickname="测试用户",
            membership_level=MembershipLevel.FREE
        )
        
        account = Account(
            id=1,
            name="测试博主",
            platform="weibo",
            account_id="test_account"
        )
        
        article = Article(
            id=1,
            account_id=1,
            title="测试文章标题",
            url="https://example.com/article/1",
            content="测试内容"
        )
        
        # Mock database queries
        with patch.object(db_session, 'execute') as mock_execute:
            # Mock user query
            user_result = MagicMock()
            user_result.scalar_one_or_none.return_value = user
            
            # Mock article query
            article_result = MagicMock()
            article_result.first.return_value = (article, account)
            
            mock_execute.side_effect = [user_result, article_result]
            
            # Mock limits service
            with patch('app.services.push_notification.limits_service') as mock_limits:
                mock_limits.check_push_limit.return_value = {
                    "can_push": True,
                    "message": "可以推送"
                }
                mock_limits.increment_push_count.return_value = None
                
                # Mock WeChat service
                with patch('app.services.push_notification.wechat_service') as mock_wechat:
                    mock_wechat.send_push_notification.return_value = {
                        "success": True,
                        "msgid": "test_msgid"
                    }
                    
                    # Mock database operations
                    with patch.object(db_session, 'add'), \
                         patch.object(db_session, 'flush'), \
                         patch.object(db_session, 'commit'):
                        
                        result = await push_notification_service.send_article_notification(
                            db_session, user_id=1, article_id=1
                        )
                        
                        assert result["success"] is True
                        assert result["message"] == "推送成功"
                        assert "msgid" in result
    
    @pytest.mark.asyncio
    async def test_send_article_notification_limit_reached(self, db_session: AsyncSession):
        """测试达到推送限制的情况"""
        user = User(
            id=1,
            openid="test_openid",
            nickname="测试用户",
            membership_level=MembershipLevel.FREE
        )
        
        # Mock database queries
        with patch.object(db_session, 'execute') as mock_execute:
            user_result = MagicMock()
            user_result.scalar_one_or_none.return_value = user
            mock_execute.return_value = user_result
            
            # Mock limits service - limit reached
            with patch('app.services.push_notification.limits_service') as mock_limits:
                mock_limits.check_push_limit.return_value = {
                    "can_push": False,
                    "message": "今日推送次数已达上限"
                }
                
                # Mock database operations
                with patch.object(db_session, 'add'), \
                     patch.object(db_session, 'commit'):
                    
                    result = await push_notification_service.send_article_notification(
                        db_session, user_id=1, article_id=1
                    )
                    
                    assert result["success"] is False
                    assert result["skipped"] is True
                    assert result["reason"] == "push_limit_reached"
                    assert "今日推送次数已达上限" in result["message"]
    
    @pytest.mark.asyncio
    async def test_batch_send_notifications(self, db_session: AsyncSession):
        """测试批量发送推送通知"""
        user_ids = [1, 2, 3]
        article_id = 1
        
        # Mock individual send results
        send_results = [
            {"success": True, "message": "推送成功"},
            {"success": False, "error": "用户未关注服务号"},
            {"success": False, "skipped": True, "reason": "push_limit_reached"}
        ]
        
        with patch.object(push_notification_service, 'send_article_notification') as mock_send:
            mock_send.side_effect = send_results
            
            result = await push_notification_service.batch_send_notifications(
                db_session, user_ids, article_id
            )
            
            assert result["total_users"] == 3
            assert result["success_count"] == 1
            assert result["failed_count"] == 1
            assert result["skipped_count"] == 1
            assert len(result["results"]) == 3
    
    @pytest.mark.asyncio
    async def test_get_user_push_statistics(self, db_session: AsyncSession):
        """测试获取用户推送统计"""
        user_id = 1
        
        # Mock database queries
        with patch.object(db_session, 'execute') as mock_execute:
            # Mock total stats query
            total_result = MagicMock()
            total_result.first.return_value = MagicMock(
                total=10, success=8, failed=1, skipped=1
            )
            
            # Mock today stats query
            today_result = MagicMock()
            today_result.scalar.return_value = 3
            
            mock_execute.side_effect = [total_result, today_result]
            
            # Mock limits service
            with patch('app.services.push_notification.limits_service') as mock_limits:
                mock_limits.get_user_limits.return_value = {
                    "push_limit": 5
                }
                
                result = await push_notification_service.get_user_push_statistics(
                    db_session, user_id
                )
                
                assert result["user_id"] == user_id
                assert result["total_pushes"] == 10
                assert result["success_pushes"] == 8
                assert result["failed_pushes"] == 1
                assert result["skipped_pushes"] == 1
                assert result["success_rate"] == 80.0
                assert result["today_pushes"] == 3
                assert result["daily_limit"] == 5
                assert result["remaining_pushes"] == 2
                assert result["can_push"] is True


class TestPushQueueService:
    """推送队列服务测试"""
    
    @pytest.mark.asyncio
    async def test_process_push_item_success(self, db_session: AsyncSession):
        """测试处理推送项目成功"""
        push_item = {
            "article_id": 1,
            "user_ids": [1, 2, 3]
        }
        
        # Mock limits service
        with patch('app.services.push_queue.limits_service') as mock_limits:
            mock_limits.check_push_limit.return_value = {
                "can_push": True
            }
            
            # Mock database operations
            with patch.object(db_session, 'add_all'), \
                 patch.object(db_session, 'commit'):
                
                result = await push_queue_service.process_push_item(
                    db_session, push_item
                )
                
                assert result["success"] is True
                assert result["article_id"] == 1
                assert result["total_users"] == 3
                assert result["processed_users"] == 3
                assert result["failed_users"] == 0
    
    @pytest.mark.asyncio
    async def test_process_push_item_with_limits(self, db_session: AsyncSession):
        """测试处理推送项目时有用户达到限制"""
        push_item = {
            "article_id": 1,
            "user_ids": [1, 2, 3]
        }
        
        # Mock limits service - some users reach limit
        def mock_check_limit(user_id, db, raise_exception=False):
            if user_id == 2:
                return {"can_push": False}
            return {"can_push": True}
        
        with patch('app.services.push_queue.limits_service') as mock_limits:
            mock_limits.check_push_limit.side_effect = mock_check_limit
            
            # Mock database operations
            with patch.object(db_session, 'add_all'), \
                 patch.object(db_session, 'commit'):
                
                result = await push_queue_service.process_push_item(
                    db_session, push_item
                )
                
                assert result["success"] is True
                assert result["total_users"] == 3
                assert result["processed_users"] == 2
                assert result["failed_users"] == 1
    
    @pytest.mark.asyncio
    async def test_get_queue_statistics(self):
        """测试获取队列统计"""
        with patch('app.services.push_queue.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.llen.side_effect = [5, 2]  # pending, failed
            mock_redis.scard.return_value = 1  # processing
            mock_get_redis.return_value = mock_redis
            
            result = await push_queue_service.get_queue_statistics()
            
            assert result["pending_queue_length"] == 5
            assert result["failed_queue_length"] == 2
            assert result["processing_count"] == 1
            assert result["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_retry_failed_items(self):
        """测试重试失败项目"""
        with patch('app.services.push_queue.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            # Mock failed items
            mock_redis.rpop.side_effect = [
                '{"article_id": 1, "user_ids": [1, 2]}',
                '{"article_id": 2, "user_ids": [3, 4]}',
                None  # No more items
            ]
            mock_redis.lpush.return_value = None
            mock_get_redis.return_value = mock_redis
            
            result = await push_queue_service.retry_failed_items(max_items=5)
            
            assert result["success"] is True
            assert result["retried_count"] == 2
            assert "重试了 2 个失败项目" in result["message"]


class TestPushLimitsIntegration:
    """推送限制集成测试"""
    
    @pytest.mark.asyncio
    async def test_free_user_push_limit(self, db_session: AsyncSession):
        """测试免费用户推送限制 - 需求2.4"""
        # This test verifies requirement 2.4: 
        # IF 用户是免费用户 THEN 系统 SHALL 限制每日推送次数为5次
        
        user = User(
            id=1,
            openid="test_openid",
            nickname="免费用户",
            membership_level=MembershipLevel.FREE
        )
        
        # Mock that user has already received 5 pushes today
        with patch('app.services.push_notification.limits_service') as mock_limits:
            mock_limits.check_push_limit.return_value = {
                "can_push": False,
                "message": "今日推送次数已达上限(5次)"
            }
            
            with patch.object(db_session, 'execute') as mock_execute:
                user_result = MagicMock()
                user_result.scalar_one_or_none.return_value = user
                mock_execute.return_value = user_result
                
                with patch.object(db_session, 'add'), \
                     patch.object(db_session, 'commit'):
                    
                    result = await push_notification_service.send_article_notification(
                        db_session, user_id=1, article_id=1
                    )
                    
                    # Verify that push is skipped due to limit
                    assert result["success"] is False
                    assert result["skipped"] is True
                    assert result["reason"] == "push_limit_reached"
                    assert "上限" in result["message"]
    
    @pytest.mark.asyncio
    async def test_premium_user_unlimited_pushes(self, db_session: AsyncSession):
        """测试高级会员无限推送 - 需求2.5"""
        # This test verifies requirement 2.5:
        # IF 用户是付费会员 THEN 系统 SHALL 根据会员等级提供不同的推送次数限制
        
        user = User(
            id=1,
            openid="test_openid",
            nickname="高级会员",
            membership_level=MembershipLevel.PREMIUM
        )
        
        account = Account(
            id=1,
            name="测试博主",
            platform="weibo",
            account_id="test_account"
        )
        
        article = Article(
            id=1,
            account_id=1,
            title="测试文章",
            url="https://example.com/article/1",
            content="测试内容"
        )
        
        # Mock that premium user can always push (no limit)
        with patch('app.services.push_notification.limits_service') as mock_limits:
            mock_limits.check_push_limit.return_value = {
                "can_push": True,
                "message": "高级会员无推送限制"
            }
            mock_limits.increment_push_count.return_value = None
            
            with patch.object(db_session, 'execute') as mock_execute:
                # Mock user query
                user_result = MagicMock()
                user_result.scalar_one_or_none.return_value = user
                
                # Mock article query
                article_result = MagicMock()
                article_result.first.return_value = (article, account)
                
                mock_execute.side_effect = [user_result, article_result]
                
                # Mock WeChat service
                with patch('app.services.push_notification.wechat_service') as mock_wechat:
                    mock_wechat.send_push_notification.return_value = {
                        "success": True,
                        "msgid": "test_msgid"
                    }
                    
                    with patch.object(db_session, 'add'), \
                         patch.object(db_session, 'flush'), \
                         patch.object(db_session, 'commit'):
                        
                        result = await push_notification_service.send_article_notification(
                            db_session, user_id=1, article_id=1
                        )
                        
                        # Verify that premium user can push without limit
                        assert result["success"] is True
                        assert result["message"] == "推送成功"


class TestPushMessageFormat:
    """推送消息格式测试"""
    
    @pytest.mark.asyncio
    async def test_message_template_format(self):
        """测试推送消息模板格式"""
        with patch('app.services.wechat.httpx.AsyncClient') as mock_client:
            # Mock access token and template message responses
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {
                "access_token": "test_token",
                "expires_in": 7200
            }
            
            mock_template_response = MagicMock()
            mock_template_response.json.return_value = {
                "errcode": 0,
                "msgid": "test_msgid"
            }
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_token_response
            mock_client_instance.post.return_value = mock_template_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            with patch('app.services.wechat.get_redis') as mock_redis:
                mock_redis.return_value = None
                
                await wechat_service.send_template_message(
                    openid="test_openid",
                    article_title="这是一个很长的文章标题，用来测试标题截断功能是否正常工作",
                    account_name="测试博主",
                    article_id=123,
                    platform_name="微博"
                )
                
                # Verify the POST call was made with correct template data
                mock_client_instance.post.assert_called_once()
                call_args = mock_client_instance.post.call_args
                
                # Check that the message data contains expected format
                message_data = call_args[1]['json']
                assert message_data['touser'] == 'test_openid'
                assert '🔔' in message_data['data']['first']['value']
                assert '📝' in message_data['data']['keyword1']['value']
                assert '💡' in message_data['data']['remark']['value']
                
                # Check title truncation (should be limited to 60 chars)
                title_value = message_data['data']['keyword2']['value']
                assert len(title_value) <= 63  # 60 + "..."
                assert title_value.endswith('...')


@pytest.fixture
async def db_session():
    """Mock database session fixture"""
    session = AsyncMock(spec=AsyncSession)
    return session