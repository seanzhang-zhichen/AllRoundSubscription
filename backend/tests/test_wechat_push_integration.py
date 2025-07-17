"""
微信推送功能集成测试
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.wechat import wechat_service


class TestWeChatPushIntegration:
    """微信推送集成测试"""
    
    @pytest.mark.asyncio
    async def test_wechat_push_configuration_check(self):
        """测试微信推送配置检查"""
        # Test that the service properly handles missing configuration
        result = await wechat_service.send_template_message(
            openid="test_openid",
            article_title="测试文章",
            account_name="测试博主",
            article_id=123
        )
        
        # Should fail gracefully when template ID is not configured
        assert result["success"] is False
        assert "微信模板ID未配置" in result["error"]
    
    @pytest.mark.asyncio
    async def test_wechat_push_with_mock_config(self):
        """测试带模拟配置的微信推送"""
        # Mock the configuration
        with patch('app.services.wechat.settings') as mock_settings:
            mock_settings.WECHAT_SERVICE_APP_ID = "test_app_id"
            mock_settings.WECHAT_SERVICE_APP_SECRET = "test_app_secret"
            mock_settings.WECHAT_TEMPLATE_ID = "test_template_id"
            mock_settings.WECHAT_MINI_PROGRAM_APP_ID = "test_mini_app_id"
            mock_settings.WECHAT_MINI_PROGRAM_PATH = "pages/article/detail"
            
            # Mock HTTP client
            with patch('app.services.wechat.httpx.AsyncClient') as mock_client:
                # Mock access token response
                mock_token_response = MagicMock()
                mock_token_response.json.return_value = {
                    "access_token": "test_access_token",
                    "expires_in": 7200
                }
                mock_token_response.raise_for_status.return_value = None
                
                # Mock template message response
                mock_template_response = MagicMock()
                mock_template_response.json.return_value = {
                    "errcode": 0,
                    "msgid": "test_msgid_12345"
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
                    
                    # Test successful push
                    result = await wechat_service.send_template_message(
                        openid="test_openid",
                        article_title="测试文章标题",
                        account_name="测试博主",
                        article_id=123,
                        platform_name="微博"
                    )
                    
                    # Verify success
                    assert result["success"] is True
                    assert result["msgid"] == "test_msgid_12345"
                    assert result["message"] == "推送成功"
                    
                    # Verify HTTP calls were made
                    assert mock_client_instance.get.called
                    assert mock_client_instance.post.called
                    
                    # Verify template message data structure
                    post_call_args = mock_client_instance.post.call_args
                    message_data = post_call_args[1]['json']
                    
                    assert message_data['touser'] == 'test_openid'
                    assert message_data['template_id'] == 'test_template_id'
                    assert '🔔' in message_data['data']['first']['value']
                    assert '📝' in message_data['data']['keyword1']['value']
                    assert '测试博主' in message_data['data']['keyword1']['value']
                    assert '测试文章标题' in message_data['data']['keyword2']['value']
                    assert '💡' in message_data['data']['remark']['value']
                    
                    # Verify mini-program jump configuration
                    assert 'miniprogram' in message_data
                    assert message_data['miniprogram']['appid'] == 'test_mini_app_id'
                    assert 'pages/article/detail?id=123' in message_data['miniprogram']['pagepath']
    
    @pytest.mark.asyncio
    async def test_wechat_push_error_handling(self):
        """测试微信推送错误处理"""
        with patch('app.services.wechat.settings') as mock_settings:
            mock_settings.WECHAT_SERVICE_APP_ID = "test_app_id"
            mock_settings.WECHAT_SERVICE_APP_SECRET = "test_app_secret"
            mock_settings.WECHAT_TEMPLATE_ID = "test_template_id"
            
            with patch('app.services.wechat.httpx.AsyncClient') as mock_client:
                # Mock access token response
                mock_token_response = MagicMock()
                mock_token_response.json.return_value = {
                    "access_token": "test_access_token",
                    "expires_in": 7200
                }
                mock_token_response.raise_for_status.return_value = None
                
                # Mock template message error response (user not subscribed)
                mock_template_response = MagicMock()
                mock_template_response.json.return_value = {
                    "errcode": 43004,
                    "errmsg": "require subscribe hint"
                }
                mock_template_response.raise_for_status.return_value = None
                
                mock_client_instance = AsyncMock()
                mock_client_instance.get.return_value = mock_token_response
                mock_client_instance.post.return_value = mock_template_response
                mock_client.return_value.__aenter__.return_value = mock_client_instance
                
                with patch('app.services.wechat.get_redis') as mock_redis:
                    mock_redis.return_value = None
                    
                    result = await wechat_service.send_template_message(
                        openid="test_openid",
                        article_title="测试文章",
                        account_name="测试博主",
                        article_id=123
                    )
                    
                    # Verify error handling
                    assert result["success"] is False
                    assert result["error_code"] == 43004
                    assert "用户未关注服务号" in result["error"]
    
    @pytest.mark.asyncio
    async def test_push_notification_unified_interface(self):
        """测试推送通知统一接口"""
        with patch('app.services.wechat.settings') as mock_settings:
            mock_settings.WECHAT_SERVICE_APP_ID = "test_app_id"
            mock_settings.WECHAT_SERVICE_APP_SECRET = "test_app_secret"
            mock_settings.WECHAT_TEMPLATE_ID = "test_template_id"
            
            with patch('app.services.wechat.httpx.AsyncClient') as mock_client:
                mock_token_response = MagicMock()
                mock_token_response.json.return_value = {
                    "access_token": "test_access_token",
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
                    
                    # Test unified push notification interface
                    article_data = {
                        "id": 456,
                        "title": "统一接口测试文章",
                        "account_name": "测试账号",
                        "platform_display_name": "微信公众号"
                    }
                    
                    result = await wechat_service.send_push_notification(
                        user_openid="test_user_openid",
                        article_data=article_data
                    )
                    
                    assert result["success"] is True
                    assert result["msgid"] == "test_msgid"
    
    @pytest.mark.asyncio
    async def test_access_token_caching(self):
        """测试访问令牌缓存机制"""
        with patch('app.services.wechat.settings') as mock_settings:
            mock_settings.WECHAT_SERVICE_APP_ID = "test_app_id"
            mock_settings.WECHAT_SERVICE_APP_SECRET = "test_app_secret"
            
            # Mock Redis with cached token
            with patch('app.services.wechat.get_redis') as mock_get_redis:
                mock_redis = AsyncMock()
                mock_redis.get.return_value = b"cached_access_token"
                mock_get_redis.return_value = mock_redis
                
                # Get access token (should use cached version)
                token = await wechat_service.get_service_access_token()
                
                assert token == "cached_access_token"
                mock_redis.get.assert_called_once_with("wechat_service_access_token")
    
    @pytest.mark.asyncio
    async def test_message_template_formatting(self):
        """测试消息模板格式化"""
        with patch('app.services.wechat.settings') as mock_settings:
            mock_settings.WECHAT_SERVICE_APP_ID = "test_app_id"
            mock_settings.WECHAT_SERVICE_APP_SECRET = "test_app_secret"
            mock_settings.WECHAT_TEMPLATE_ID = "test_template_id"
            
            with patch('app.services.wechat.httpx.AsyncClient') as mock_client:
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
                    
                    # Test with long title (should be truncated)
                    long_title = "这是一个非常长的文章标题，用来测试标题截断功能是否正常工作，应该会被截断到60个字符以内"
                    
                    await wechat_service.send_template_message(
                        openid="test_openid",
                        article_title=long_title,
                        account_name="测试博主",
                        article_id=123,
                        platform_name="微博"
                    )
                    
                    # Verify template message formatting
                    post_call_args = mock_client_instance.post.call_args
                    message_data = post_call_args[1]['json']
                    
                    # Check title truncation
                    title_value = message_data['data']['keyword2']['value']
                    assert len(title_value) <= 63  # 60 + "..."
                    assert title_value.endswith('...')
                    
                    # Check emoji usage
                    assert '🔔' in message_data['data']['first']['value']
                    assert '📝' in message_data['data']['keyword1']['value']
                    assert '💡' in message_data['data']['remark']['value']
                    
                    # Check color formatting
                    assert message_data['data']['first']['color'] == '#FF6B35'
                    assert message_data['data']['keyword1']['color'] == '#2E86AB'
                    assert message_data['data']['keyword2']['color'] == '#333333'


class TestPushRequirements:
    """推送需求验证测试"""
    
    @pytest.mark.asyncio
    async def test_requirement_2_1_wechat_push_message(self):
        """
        需求2.1验证: WHEN 订阅的博主发布新内容 THEN 系统 SHALL 通过微信服务号向用户发送推送消息
        """
        with patch('app.services.wechat.settings') as mock_settings:
            mock_settings.WECHAT_SERVICE_APP_ID = "test_app_id"
            mock_settings.WECHAT_SERVICE_APP_SECRET = "test_app_secret"
            mock_settings.WECHAT_TEMPLATE_ID = "test_template_id"
            
            with patch('app.services.wechat.httpx.AsyncClient') as mock_client:
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
                    
                    # 模拟博主发布新内容后的推送
                    result = await wechat_service.send_push_notification(
                        user_openid="subscribed_user_openid",
                        article_data={
                            "id": 1,
                            "title": "博主新发布的文章",
                            "account_name": "关注的博主",
                            "platform_display_name": "微博"
                        }
                    )
                    
                    # 验证推送成功
                    assert result["success"] is True
                    assert "msgid" in result
                    
                    # 验证是通过微信服务号发送的模板消息
                    assert mock_client_instance.post.called
                    post_call_args = mock_client_instance.post.call_args
                    assert "template/send" in post_call_args[0][0]  # URL contains template/send
    
    @pytest.mark.asyncio
    async def test_requirement_2_2_jump_to_article_detail(self):
        """
        需求2.2验证: WHEN 用户点击推送消息 THEN 系统 SHALL 直接跳转到对应的动态详情页面
        """
        with patch('app.services.wechat.settings') as mock_settings:
            mock_settings.WECHAT_SERVICE_APP_ID = "test_app_id"
            mock_settings.WECHAT_SERVICE_APP_SECRET = "test_app_secret"
            mock_settings.WECHAT_TEMPLATE_ID = "test_template_id"
            mock_settings.WECHAT_MINI_PROGRAM_APP_ID = "mini_app_id"
            mock_settings.WECHAT_MINI_PROGRAM_PATH = "pages/article/detail"
            
            with patch('app.services.wechat.httpx.AsyncClient') as mock_client:
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
                    
                    article_id = 12345
                    await wechat_service.send_template_message(
                        openid="test_openid",
                        article_title="测试文章",
                        account_name="测试博主",
                        article_id=article_id,
                        platform_name="微博"
                    )
                    
                    # 验证消息包含小程序跳转配置
                    post_call_args = mock_client_instance.post.call_args
                    message_data = post_call_args[1]['json']
                    
                    assert 'miniprogram' in message_data
                    assert message_data['miniprogram']['appid'] == 'mini_app_id'
                    assert f'pages/article/detail?id={article_id}' in message_data['miniprogram']['pagepath']