"""
认证功能测试
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from jose import jwt

from app.core.security import jwt_manager, JWTManager
from app.core.exceptions import AuthenticationException
from app.services.auth import auth_service
from app.services.wechat import wechat_service
from app.models.user import User, MembershipLevel
from app.core.config import settings


class TestJWTManager:
    """JWT管理器测试"""
    
    def test_create_access_token(self):
        """测试创建访问令牌"""
        data = {"sub": "123", "openid": "test_openid"}
        token = jwt_manager.create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # 验证令牌内容
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "123"
        assert payload["openid"] == "test_openid"
        assert payload["type"] == "access"
        assert "exp" in payload
    
    def test_create_refresh_token(self):
        """测试创建刷新令牌"""
        data = {"sub": "123", "openid": "test_openid"}
        token = jwt_manager.create_refresh_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # 验证令牌内容
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "123"
        assert payload["openid"] == "test_openid"
        assert payload["type"] == "refresh"
        assert "exp" in payload
    
    def test_verify_valid_token(self):
        """测试验证有效令牌"""
        data = {"sub": "123", "openid": "test_openid"}
        token = jwt_manager.create_access_token(data)
        
        payload = jwt_manager.verify_token(token, "access")
        
        assert payload["sub"] == "123"
        assert payload["openid"] == "test_openid"
        assert payload["type"] == "access"
    
    def test_verify_invalid_token(self):
        """测试验证无效令牌"""
        with pytest.raises(AuthenticationException):
            jwt_manager.verify_token("invalid_token", "access")
    
    def test_verify_wrong_token_type(self):
        """测试验证错误令牌类型"""
        data = {"sub": "123", "openid": "test_openid"}
        token = jwt_manager.create_access_token(data)
        
        with pytest.raises(AuthenticationException):
            jwt_manager.verify_token(token, "refresh")
    
    def test_get_user_id_from_token(self):
        """测试从令牌获取用户ID"""
        data = {"sub": "123", "openid": "test_openid"}
        token = jwt_manager.create_access_token(data)
        
        user_id = jwt_manager.get_user_id_from_token(token)
        assert user_id == 123


class TestWeChatService:
    """微信服务测试"""
    
    @pytest.mark.asyncio
    async def test_code_to_session_success(self):
        """测试成功的code换session"""
        mock_response = {
            "openid": "test_openid",
            "session_key": "test_session_key"
        }
        
        # Mock WeChat configuration
        with patch.object(wechat_service, 'app_id', 'test_app_id'):
            with patch.object(wechat_service, 'app_secret', 'test_app_secret'):
                with patch('httpx.AsyncClient') as mock_client:
                    mock_response_obj = MagicMock()
                    mock_response_obj.json.return_value = mock_response
                    mock_response_obj.raise_for_status.return_value = None
                    
                    mock_client.return_value.__aenter__.return_value.get.return_value = mock_response_obj
                    
                    result = await wechat_service.code_to_session("test_code")
                    
                    assert result["openid"] == "test_openid"
                    assert result["session_key"] == "test_session_key"
    
    @pytest.mark.asyncio
    async def test_code_to_session_error(self):
        """测试code换session错误"""
        mock_response = {
            "errcode": 40029,
            "errmsg": "invalid code"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response_obj
            
            with pytest.raises(Exception):  # 应该抛出BusinessException
                await wechat_service.code_to_session("invalid_code")


class TestAuthService:
    """认证服务测试"""
    
    @pytest.mark.asyncio
    async def test_wechat_login_new_user(self):
        """测试新用户微信登录"""
        mock_db = AsyncMock()
        mock_wechat_data = {
            "openid": "test_openid",
            "session_key": "test_session_key"
        }
        
        # Mock用户不存在
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        # Mock创建新用户
        new_user = User(
            id=1,
            openid="test_openid",
            membership_level=MembershipLevel.FREE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_db.refresh = AsyncMock()
        
        with patch.object(wechat_service, 'code_to_session', return_value=mock_wechat_data):
            with patch.object(auth_service, '_get_or_create_user', return_value=new_user):
                with patch.object(auth_service, '_cache_user_session'):
                    result = await auth_service.wechat_login("test_code", mock_db)
                    
                    assert "user" in result
                    assert "tokens" in result
                    assert result["user"]["id"] == 1
                    assert result["user"]["openid"] == "test_openid"
                    assert "access_token" in result["tokens"]
                    assert "refresh_token" in result["tokens"]
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self):
        """测试成功刷新令牌"""
        mock_db = AsyncMock()
        
        # 创建测试用户
        test_user = User(
            id=1,
            openid="test_openid",
            membership_level=MembershipLevel.FREE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # 创建刷新令牌
        token_data = {"sub": "1", "openid": "test_openid"}
        refresh_token = jwt_manager.create_refresh_token(token_data)
        
        with patch.object(auth_service, '_get_user_by_id', return_value=test_user):
            result = await auth_service.refresh_token(refresh_token, mock_db)
            
            assert "access_token" in result
            assert "token_type" in result
            assert "expires_in" in result
            assert result["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_verify_access_token_success(self):
        """测试成功验证访问令牌"""
        mock_db = AsyncMock()
        
        # 创建测试用户
        test_user = User(
            id=1,
            openid="test_openid",
            membership_level=MembershipLevel.FREE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # 创建访问令牌
        token_data = {"sub": "1", "openid": "test_openid"}
        access_token = jwt_manager.create_access_token(token_data)
        
        with patch.object(auth_service, '_get_user_by_id', return_value=test_user):
            result = await auth_service.verify_access_token(access_token, mock_db)
            
            assert result.id == 1
            assert result.openid == "test_openid"
    
    @pytest.mark.asyncio
    async def test_verify_access_token_invalid(self):
        """测试验证无效访问令牌"""
        mock_db = AsyncMock()
        
        with pytest.raises(AuthenticationException):
            await auth_service.verify_access_token("invalid_token", mock_db)


class TestUserModel:
    """用户模型测试"""
    
    def test_get_subscription_limit_free_user(self):
        """测试免费用户订阅限制"""
        user = User(
            openid="test_openid",
            membership_level=MembershipLevel.FREE
        )
        
        assert user.get_subscription_limit() == 10
    
    def test_get_subscription_limit_basic_user(self):
        """测试基础会员订阅限制"""
        user = User(
            openid="test_openid",
            membership_level=MembershipLevel.BASIC,
            membership_expire_at=datetime.utcnow() + timedelta(days=30)
        )
        
        assert user.get_subscription_limit() == 50
    
    def test_get_subscription_limit_premium_user(self):
        """测试高级会员订阅限制"""
        user = User(
            openid="test_openid",
            membership_level=MembershipLevel.PREMIUM,
            membership_expire_at=datetime.utcnow() + timedelta(days=30)
        )
        
        assert user.get_subscription_limit() == -1  # 无限制
    
    def test_get_daily_push_limit_free_user(self):
        """测试免费用户推送限制"""
        user = User(
            openid="test_openid",
            membership_level=MembershipLevel.FREE
        )
        
        assert user.get_daily_push_limit() == 5
    
    def test_is_membership_active_free_user(self):
        """测试免费用户会员状态"""
        user = User(
            openid="test_openid",
            membership_level=MembershipLevel.FREE
        )
        
        assert user.is_membership_active is True
    
    def test_is_membership_active_expired_user(self):
        """测试过期会员状态"""
        user = User(
            openid="test_openid",
            membership_level=MembershipLevel.BASIC,
            membership_expire_at=datetime.utcnow() - timedelta(days=1)
        )
        
        assert user.is_membership_active is False
    
    def test_is_membership_active_valid_user(self):
        """测试有效会员状态"""
        user = User(
            openid="test_openid",
            membership_level=MembershipLevel.BASIC,
            membership_expire_at=datetime.utcnow() + timedelta(days=30)
        )
        
        assert user.is_membership_active is True