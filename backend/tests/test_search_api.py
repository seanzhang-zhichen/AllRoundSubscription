"""
搜索API集成测试
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime

from app.models.user import User, MembershipLevel
from app.models.account import Platform
from app.services.search.base import SearchResult
from app.schemas.account import AccountResponse


class TestSearchAPI:
    """搜索API集成测试"""
    
    @pytest.mark.asyncio
    async def test_search_accounts_success(self, client, auth_headers):
        """测试搜索博主成功"""
        # Mock搜索结果
        mock_accounts = [
            AccountResponse(
                id=1,
                name="测试博主1",
                platform="weibo",
                account_id="test_account_1",
                avatar_url="https://example.com/avatar1.jpg",
                description="这是测试博主1",
                follower_count=10000,
                details={},
                created_at=datetime.now(),
                updated_at=datetime.now(),
                platform_display_name="微博"
            ),
            AccountResponse(
                id=2,
                name="测试博主2",
                platform="wechat",
                account_id="test_account_2",
                avatar_url="https://example.com/avatar2.jpg",
                description="这是测试博主2",
                follower_count=5000,
                details={},
                created_at=datetime.now(),
                updated_at=datetime.now(),
                platform_display_name="微信公众号"
            )
        ]
        
        mock_search_result = SearchResult(
            accounts=mock_accounts,
            total=2,
            page=1,
            page_size=20,
            has_more=False
        )
        
        with patch('app.api.v1.search.search_service') as mock_service:
            mock_service.search_accounts.return_value = mock_search_result
            
            response = await client.get(
                "/api/v1/search/accounts",
                params={"keyword": "测试"},
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "搜索完成，找到 2 个结果"
        assert "data" in data
        
        # 验证搜索结果
        search_data = data["data"]
        assert search_data["total"] == 2
        assert search_data["page"] == 1
        assert search_data["page_size"] == 20
        assert search_data["has_more"] is False
        assert "search_time_ms" in search_data
        assert len(search_data["accounts"]) == 2
        
        # 验证账号信息
        account1 = search_data["accounts"][0]
        assert account1["name"] == "测试博主1"
        assert account1["platform"] == "weibo"
        assert account1["platform_display_name"] == "微博"
    
    @pytest.mark.asyncio
    async def test_search_accounts_with_platforms_filter(self, client, auth_headers):
        """测试带平台筛选的搜索"""
        mock_search_result = SearchResult(
            accounts=[],
            total=0,
            page=1,
            page_size=20,
            has_more=False
        )
        
        with patch('app.api.v1.search.search_service') as mock_service:
            mock_service.search_accounts.return_value = mock_search_result
            
            response = await client.get(
                "/api/v1/search/accounts",
                params={
                    "keyword": "测试",
                    "platforms": "weibo,wechat",
                    "page": 1,
                    "page_size": 10
                },
                headers=auth_headers
            )
        
        assert response.status_code == 200
        
        # 验证调用参数
        mock_service.search_accounts.assert_called_once_with(
            keyword="测试",
            platforms=["weibo", "wechat"],
            page=1,
            page_size=10
        )
    
    @pytest.mark.asyncio
    async def test_search_accounts_invalid_platform(self, client, auth_headers):
        """测试无效平台参数"""
        response = await client.get(
            "/api/v1/search/accounts",
            params={
                "keyword": "测试",
                "platforms": "invalid_platform"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "不支持的平台类型" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_search_accounts_missing_keyword(self, client, auth_headers):
        """测试缺少关键词参数"""
        response = await client.get(
            "/api/v1/search/accounts",
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_search_accounts_unauthorized(self, client):
        """测试未授权访问"""
        response = await client.get(
            "/api/v1/search/accounts",
            params={"keyword": "测试"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_search_by_platform_success(self, client, auth_headers):
        """测试平台搜索成功"""
        mock_accounts = [
            AccountResponse(
                id=1,
                name="微博博主",
                platform="weibo",
                account_id="weibo_account",
                avatar_url="https://example.com/avatar.jpg",
                description="微博博主描述",
                follower_count=20000,
                details={},
                created_at=datetime.now(),
                updated_at=datetime.now(),
                platform_display_name="微博"
            )
        ]
        
        mock_search_result = SearchResult(
            accounts=mock_accounts,
            total=1,
            page=1,
            page_size=20,
            platform="weibo",
            has_more=False
        )
        
        with patch('app.api.v1.search.search_service') as mock_service:
            mock_service.search_by_platform.return_value = mock_search_result
            
            response = await client.get(
                "/api/v1/search/platforms/weibo/accounts",
                params={"keyword": "测试"},
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "在 weibo 平台找到 1 个结果"
        
        search_data = data["data"]
        assert search_data["platform"] == "weibo"
        assert search_data["total"] == 1
        assert len(search_data["accounts"]) == 1
    
    @pytest.mark.asyncio
    async def test_search_by_platform_invalid_platform(self, client, auth_headers):
        """测试无效平台搜索"""
        response = await client.get(
            "/api/v1/search/platforms/invalid_platform/accounts",
            params={"keyword": "测试"},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "不支持的平台类型" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_supported_platforms_success(self, client, auth_headers):
        """测试获取支持的平台列表成功"""
        with patch('app.api.v1.search.search_service') as mock_service:
            mock_service.get_supported_platforms.return_value = ["weibo", "wechat"]
            
            response = await client.get(
                "/api/v1/search/platforms",
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        
        platforms_data = data["data"]
        assert platforms_data["total"] > 0
        assert platforms_data["enabled_count"] == 2
        assert len(platforms_data["platforms"]) > 0
        
        # 验证平台信息结构
        platform_info = platforms_data["platforms"][0]
        assert "platform" in platform_info
        assert "display_name" in platform_info
        assert "is_supported" in platform_info
    
    @pytest.mark.asyncio
    async def test_get_search_statistics_success(self, client, auth_headers):
        """测试获取搜索统计信息成功"""
        mock_stats = {
            "supported_platforms": ["weibo", "wechat"],
            "registered_adapters": ["weibo", "wechat", "twitter"],
            "platform_status": {"weibo": True, "wechat": True, "twitter": False},
            "cache_stats": {"hit_rate": 0.85, "total_requests": 1000},
            "timestamp": "2024-01-01T10:00:00"
        }
        
        with patch('app.api.v1.search.search_service') as mock_service:
            mock_service.get_search_statistics.return_value = mock_stats
            
            response = await client.get(
                "/api/v1/search/statistics",
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        
        stats_data = data["data"]
        assert stats_data["supported_platforms"] == ["weibo", "wechat"]
        assert stats_data["registered_adapters"] == ["weibo", "wechat", "twitter"]
        assert "platform_status" in stats_data
        assert "cache_stats" in stats_data
        assert "timestamp" in stats_data
    
    @pytest.mark.asyncio
    async def test_get_account_by_platform_id_success(self, client, auth_headers):
        """测试根据平台账号ID获取账号信息成功"""
        mock_account = AccountResponse(
            id=1,
            name="特定博主",
            platform="weibo",
            account_id="specific_account",
            avatar_url="https://example.com/avatar.jpg",
            description="特定博主描述",
            follower_count=50000,
            details={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
            platform_display_name="微博"
        )
        
        with patch('app.api.v1.search.search_service') as mock_service:
            mock_service.get_account_by_platform_id.return_value = mock_account
            
            response = await client.get(
                "/api/v1/search/accounts/specific_account",
                params={"platform": "weibo"},
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "获取账号信息成功"
        
        account_data = data["data"]
        assert account_data["name"] == "特定博主"
        assert account_data["platform"] == "weibo"
        assert account_data["account_id"] == "specific_account"
    
    @pytest.mark.asyncio
    async def test_get_account_by_platform_id_not_found(self, client, auth_headers):
        """测试账号不存在的情况"""
        with patch('app.api.v1.search.search_service') as mock_service:
            mock_service.get_account_by_platform_id.return_value = None
            
            response = await client.get(
                "/api/v1/search/accounts/nonexistent_account",
                params={"platform": "weibo"},
                headers=auth_headers
            )
        
        assert response.status_code == 404
        assert "未找到账号" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_search_service_exception_handling(self, client, auth_headers):
        """测试搜索服务异常处理"""
        with patch('app.api.v1.search.search_service') as mock_service:
            mock_service.search_accounts.side_effect = Exception("搜索服务异常")
            
            response = await client.get(
                "/api/v1/search/accounts",
                params={"keyword": "测试"},
                headers=auth_headers
            )
        
        assert response.status_code == 500
        assert "搜索服务暂时不可用" in response.json()["detail"]


class TestSearchAPIValidation:
    """搜索API参数验证测试"""
    
    @pytest.mark.asyncio
    async def test_search_keyword_validation(self, client, auth_headers):
        """测试搜索关键词验证"""
        # 测试各种无效的关键词
        invalid_keywords = [
            "",  # 空字符串
            "   ",  # 空白字符
            "a" * 101,  # 超长关键词
        ]
        
        for invalid_keyword in invalid_keywords:
            response = await client.get(
                "/api/v1/search/accounts",
                params={"keyword": invalid_keyword},
                headers=auth_headers
            )
            
            assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_pagination_validation(self, client, auth_headers):
        """测试分页参数验证"""
        with patch('app.api.v1.search.search_service') as mock_service:
            mock_service.search_accounts.return_value = SearchResult(
                accounts=[], total=0, page=1, page_size=20, has_more=False
            )
            
            # 测试无效页码
            response = await client.get(
                "/api/v1/search/accounts",
                params={"keyword": "测试", "page": 0},
                headers=auth_headers
            )
            assert response.status_code == 422
            
            # 测试无效页面大小
            response = await client.get(
                "/api/v1/search/accounts",
                params={"keyword": "测试", "page_size": 101},
                headers=auth_headers
            )
            assert response.status_code == 422
            
            # 测试有效参数
            response = await client.get(
                "/api/v1/search/accounts",
                params={"keyword": "测试", "page": 1, "page_size": 50},
                headers=auth_headers
            )
            assert response.status_code == 200


class TestSearchAPIPerformance:
    """搜索API性能测试"""
    
    @pytest.mark.asyncio
    async def test_search_response_time_tracking(self, client, auth_headers):
        """测试搜索响应时间跟踪"""
        mock_search_result = SearchResult(
            accounts=[], total=0, page=1, page_size=20, has_more=False
        )
        
        with patch('app.api.v1.search.search_service') as mock_service:
            # 模拟慢速搜索
            async def slow_search(*args, **kwargs):
                import asyncio
                await asyncio.sleep(0.1)  # 模拟100ms延迟
                return mock_search_result
            
            mock_service.search_accounts.side_effect = slow_search
            
            response = await client.get(
                "/api/v1/search/accounts",
                params={"keyword": "测试"},
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证响应时间被记录
        search_data = data["data"]
        assert "search_time_ms" in search_data
        assert search_data["search_time_ms"] >= 100  # 至少100ms