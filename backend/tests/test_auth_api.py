"""
认证API集成测试
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta

from app.models.user import User, MembershipLevel
from app.core.security import jwt_manager
from app.services.wechat import wechat_service


class TestAuthAPI:
    """认证API集成测试"""
    
    @pytest.mark.asyncio
    async def test_wechat_login_success(self, client: AsyncClient):
        """测试微信登录成功"""
        # Mock微信API响应
        mock_wechat_response = {
            "openid": "test_openid_123",
            "session_key": "test_session_key"
        }
        
        with patch.object(wechat_service, 'code_to_session', return_value=mock_wechat_response):
            response = await client.post(
                "/api/v1/auth/login",
                json={"code": "test_code_123"}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "登录成功"
        assert "data" in data
        
        # 验证返回的用户信息
        user_data = data["data"]["user"]
        assert user_data["openid"] == "test_openid_123"
        assert user_data["membership_level"] == "free"
        assert "id" in user_data
        
        # 验证返回的令牌信息
        tokens = data["data"]["tokens"]
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        assert tokens["expires_in"] > 0
    
    @pytest.mark.asyncio
    async def test_wechat_login_invalid_code(self, client: AsyncClient):
        """测试微信登录无效code"""
        # Mock微信API错误响应
        mock_error = Exception("invalid code")
        
        with patch.object(wechat_service, 'code_to_session', side_effect=mock_error):
            response = await client.post(
                "/api/v1/auth/login",
                json={"code": "invalid_code"}
            )
        
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["code"] == 500
    
    @pytest.mark.asyncio
    async def test_wechat_login_missing_code(self, client: AsyncClient):
        """测试微信登录缺少code参数"""
        response = await client.post(
            "/api/v1/auth/login",
            json={}
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_wechat_login_empty_code(self, client: AsyncClient):
        """测试微信登录空code参数"""
        response = await client.post(
            "/api/v1/auth/login",
            json={"code": ""}
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client: AsyncClient, test_user: User):
        """测试刷新令牌成功"""
        # 创建刷新令牌
        token_data = {"sub": str(test_user.id), "openid": test_user.openid}
        refresh_token = jwt_manager.create_refresh_token(token_data)
        
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "令牌刷新成功"
        assert "data" in data
        
        # 验证返回的新令牌
        token_data = data["data"]
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        assert token_data["expires_in"] > 0
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, client: AsyncClient):
        """测试刷新无效令牌"""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_refresh_token"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["code"] == 401
    
    @pytest.mark.asyncio
    async def test_refresh_token_missing(self, client: AsyncClient):
        """测试刷新令牌缺少参数"""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={}
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_refresh_token_empty(self, client: AsyncClient):
        """测试刷新空令牌"""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": ""}
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient, auth_headers: dict):
        """测试登出成功"""
        response = await client.post(
            "/api/v1/auth/logout",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "登出成功"
    
    @pytest.mark.asyncio
    async def test_logout_unauthorized(self, client: AsyncClient):
        """测试未授权登出"""
        response = await client.post("/api/v1/auth/logout")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_logout_invalid_token(self, client: AsyncClient):
        """测试无效令牌登出"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = await client.post(
            "/api/v1/auth/logout",
            headers=headers
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_auth_status_success(self, client: AsyncClient, auth_headers: dict, test_user: User):
        """测试获取认证状态成功"""
        response = await client.get(
            "/api/v1/auth/status",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "获取认证状态成功"
        assert "data" in data
        
        # 验证认证状态信息
        auth_status = data["data"]
        assert auth_status["is_authenticated"] is True
        assert auth_status["user_id"] == test_user.id
        assert auth_status["openid"] == test_user.openid
        assert auth_status["membership_level"] == test_user.membership_level.value
    
    @pytest.mark.asyncio
    async def test_get_auth_status_unauthorized(self, client: AsyncClient):
        """测试未授权获取认证状态"""
        response = await client.get("/api/v1/auth/status")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_info_success(self, client: AsyncClient, auth_headers: dict, test_user: User):
        """测试获取当前用户信息成功"""
        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "获取用户信息成功"
        assert "data" in data
        
        # 验证用户信息
        user_info = data["data"]
        assert user_info["id"] == test_user.id
        assert user_info["openid"] == test_user.openid
        assert user_info["membership_level"] == test_user.membership_level.value
        assert "subscription_limit" in user_info
        assert "daily_push_limit" in user_info
        assert "created_at" in user_info
        assert "updated_at" in user_info
    
    @pytest.mark.asyncio
    async def test_get_current_user_info_unauthorized(self, client: AsyncClient):
        """测试未授权获取用户信息"""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_auth_flow_complete(self, client: AsyncClient):
        """测试完整的认证流程"""
        # 1. 微信登录
        mock_wechat_response = {
            "openid": "test_flow_openid",
            "session_key": "test_session_key"
        }
        
        with patch.object(wechat_service, 'code_to_session', return_value=mock_wechat_response):
            login_response = await client.post(
                "/api/v1/auth/login",
                json={"code": "test_flow_code"}
            )
        
        assert login_response.status_code == 200
        login_data = login_response.json()
        
        access_token = login_data["data"]["tokens"]["access_token"]
        refresh_token = login_data["data"]["tokens"]["refresh_token"]
        
        # 2. 使用访问令牌获取用户信息
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        me_response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["data"]["openid"] == "test_flow_openid"
        
        # 3. 刷新令牌
        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        new_access_token = refresh_data["data"]["access_token"]
        
        # 4. 使用新令牌获取认证状态
        new_auth_headers = {"Authorization": f"Bearer {new_access_token}"}
        status_response = await client.get(
            "/api/v1/auth/status",
            headers=new_auth_headers
        )
        
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["data"]["is_authenticated"] is True
        
        # 5. 登出
        logout_response = await client.post(
            "/api/v1/auth/logout",
            headers=new_auth_headers
        )
        
        assert logout_response.status_code == 200
        logout_data = logout_response.json()
        assert logout_data["success"] is True


class TestAuthAPIValidation:
    """认证API参数验证测试"""
    
    @pytest.mark.asyncio
    async def test_login_code_validation(self, client: AsyncClient):
        """测试登录code参数验证"""
        # 测试各种无效的code值
        invalid_codes = [
            None,
            "",
            "   ",  # 空白字符
            "a" * 101,  # 超长code
        ]
        
        for invalid_code in invalid_codes:
            if invalid_code is None:
                response = await client.post("/api/v1/auth/login", json={})
            else:
                response = await client.post(
                    "/api/v1/auth/login",
                    json={"code": invalid_code}
                )
            
            assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_refresh_token_validation(self, client: AsyncClient):
        """测试刷新令牌参数验证"""
        # 测试各种无效的refresh_token值
        invalid_tokens = [
            None,
            "",
            "   ",  # 空白字符
        ]
        
        for invalid_token in invalid_tokens:
            if invalid_token is None:
                response = await client.post("/api/v1/auth/refresh", json={})
            else:
                response = await client.post(
                    "/api/v1/auth/refresh",
                    json={"refresh_token": invalid_token}
                )
            
            assert response.status_code == 422


class TestAuthAPIErrorHandling:
    """认证API错误处理测试"""
    
    @pytest.mark.asyncio
    async def test_login_service_error(self, client: AsyncClient):
        """测试登录服务异常处理"""
        with patch.object(wechat_service, 'code_to_session', side_effect=Exception("Service unavailable")):
            response = await client.post(
                "/api/v1/auth/login",
                json={"code": "test_code"}
            )
        
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["code"] == 500
        assert "登录服务异常" in data["detail"]["message"]
    
    @pytest.mark.asyncio
    async def test_refresh_service_error(self, client: AsyncClient):
        """测试刷新令牌服务异常处理"""
        # 创建一个看起来有效但会导致服务异常的令牌
        with patch('app.services.auth.auth_service.refresh_token', side_effect=Exception("Database error")):
            response = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "valid_looking_token"}
            )
        
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["code"] == 500
        assert "令牌刷新服务异常" in data["detail"]["message"]
    
    @pytest.mark.asyncio
    async def test_logout_service_error(self, client: AsyncClient, auth_headers: dict):
        """测试登出服务异常处理"""
        with patch('app.services.auth.auth_service.logout', side_effect=Exception("Cache error")):
            response = await client.post(
                "/api/v1/auth/logout",
                headers=auth_headers
            )
        
        # 登出异常不应该返回错误，而是返回失败状态
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "登出处理异常" in data["message"]