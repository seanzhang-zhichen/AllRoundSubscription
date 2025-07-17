"""
搜索聚合器测试
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.services.search.aggregator import SearchAggregator
from app.services.search.adapters.mock import MockPlatformAdapter
from app.services.search.base import PlatformSearchResult
from app.models.account import Platform
from app.schemas.account import AccountResponse
from datetime import datetime


class TestSearchAggregator:
    """搜索聚合器测试类"""
    
    @pytest.fixture
    def aggregator(self):
        """创建搜索聚合器实例"""
        return SearchAggregator(timeout_seconds=5)
    
    @pytest.fixture
    def mock_adapters(self):
        """创建多个Mock适配器"""
        adapters = [
            MockPlatformAdapter(Platform.WEIBO, enabled=True),
            MockPlatformAdapter(Platform.WECHAT, enabled=True),
            MockPlatformAdapter(Platform.TWITTER, enabled=True)
        ]
        return adapters
    
    @pytest.mark.asyncio
    async def test_aggregate_search_results_success(self, aggregator, mock_adapters):
        """测试成功聚合搜索结果"""
        result, error_info = await aggregator.aggregate_search_results(
            mock_adapters, "测试", page=1, page_size=10
        )
        
        assert result is not None
        assert result.total >= 0
        assert result.page == 1
        assert result.page_size == 10
        assert error_info["successful_platforms"] >= 0
        assert isinstance(error_info["failed_platforms"], list)
    
    @pytest.mark.asyncio
    async def test_aggregate_search_results_with_failures(self, aggregator):
        """测试部分适配器失败的情况"""
        # 创建一个会失败的适配器
        failing_adapter = MockPlatformAdapter(Platform.WEIBO, enabled=False)
        working_adapter = MockPlatformAdapter(Platform.WECHAT, enabled=True)
        
        result, error_info = await aggregator.aggregate_search_results(
            [failing_adapter, working_adapter], "测试", page=1, page_size=5
        )
        
        assert result is not None
        assert error_info["failed_platforms"] or error_info["successful_platforms"] > 0
    
    @pytest.mark.asyncio
    async def test_aggregate_search_results_timeout(self):
        """测试搜索超时情况"""
        # 创建一个会超时的适配器
        slow_adapter = MockPlatformAdapter(Platform.WEIBO, enabled=True)
        
        # Mock search_accounts 方法使其超时
        async def slow_search(*args, **kwargs):
            await asyncio.sleep(10)  # 超过超时时间
            return PlatformSearchResult(
                platform=Platform.WEIBO.value,
                accounts=[],
                total=0,
                success=True
            )
        
        slow_adapter.search_accounts = slow_search
        
        aggregator = SearchAggregator(timeout_seconds=1)  # 设置短超时时间
        result, error_info = await aggregator.aggregate_search_results(
            [slow_adapter], "测试", page=1, page_size=5
        )
        
        assert result is not None
        assert result.total == 0  # 超时应该返回空结果
    
    def test_deduplicate_accounts(self, aggregator):
        """测试账号去重功能"""
        # 创建重复的账号数据
        accounts = [
            AccountResponse(
                id=1,
                name="测试账号",
                platform="weibo",
                account_id="123",
                avatar_url="",
                description="",
                follower_count=1000,
                details={},
                created_at=datetime.now(),
                updated_at=datetime.now(),
                platform_display_name="微博"
            ),
            AccountResponse(
                id=2,
                name="测试账号",  # 同名账号
                platform="wechat",
                account_id="456",
                avatar_url="",
                description="",
                follower_count=2000,  # 更多粉丝
                details={},
                created_at=datetime.now(),
                updated_at=datetime.now(),
                platform_display_name="微信"
            ),
            AccountResponse(
                id=3,
                name="另一个账号",
                platform="twitter",
                account_id="789",
                avatar_url="",
                description="",
                follower_count=500,
                details={},
                created_at=datetime.now(),
                updated_at=datetime.now(),
                platform_display_name="Twitter"
            )
        ]
        
        unique_accounts = aggregator._deduplicate_accounts(accounts)
        
        # 应该保留粉丝数更多的同名账号
        assert len(unique_accounts) == 2
        test_account = next((acc for acc in unique_accounts if acc.name == "测试账号"), None)
        assert test_account is not None
        assert test_account.follower_count == 2000  # 应该保留粉丝数更多的
    
    def test_calculate_relevance_score(self, aggregator):
        """测试相关性得分计算"""
        account = AccountResponse(
            id=1,
            name="科技达人",
            platform="weibo",
            account_id="123",
            avatar_url="",
            description="专注科技资讯分享",
            follower_count=10000,
            details={"verified": True},
            created_at=datetime.now(),
            updated_at=datetime.now(),
            platform_display_name="微博"
        )
        
        # 测试完全匹配
        score1 = aggregator.calculate_relevance_score(account, "科技达人")
        assert score1 > 0.5  # 完全匹配应该有较高得分
        
        # 测试部分匹配
        score2 = aggregator.calculate_relevance_score(account, "科技")
        assert score2 > 0.3  # 部分匹配应该有中等得分
        
        # 测试描述匹配
        score3 = aggregator.calculate_relevance_score(account, "资讯")
        assert score3 > 0.1  # 描述匹配应该有一定得分
        
        # 测试无匹配
        score4 = aggregator.calculate_relevance_score(account, "美食")
        assert score4 >= 0  # 无匹配但有粉丝数和认证加分
    
    def test_sort_by_relevance(self, aggregator):
        """测试按相关性排序"""
        accounts = [
            AccountResponse(
                id=1,
                name="科技新闻",
                platform="weibo",
                account_id="123",
                avatar_url="",
                description="",
                follower_count=1000,
                details={},
                created_at=datetime.now(),
                updated_at=datetime.now(),
                platform_display_name="微博"
            ),
            AccountResponse(
                id=2,
                name="科技达人",  # 更相关的名称
                platform="wechat",
                account_id="456",
                avatar_url="",
                description="专注科技资讯",
                follower_count=500,
                details={},
                created_at=datetime.now(),
                updated_at=datetime.now(),
                platform_display_name="微信"
            )
        ]
        
        sorted_accounts = aggregator.sort_by_relevance(accounts, "科技达人")
        
        # 更相关的账号应该排在前面
        assert sorted_accounts[0].name == "科技达人"
        assert sorted_accounts[1].name == "科技新闻"


class TestSearchExceptions:
    """搜索异常测试类"""
    
    def test_search_exception_creation(self):
        """测试搜索异常创建"""
        from app.services.search.exceptions import (
            SearchException, PlatformAPIException, PlatformUnavailableException,
            SearchTimeoutException, RateLimitException, AuthenticationException
        )
        
        # 基础异常
        base_exc = SearchException("测试错误", "weibo", "TEST_ERROR")
        assert base_exc.message == "测试错误"
        assert base_exc.platform == "weibo"
        assert base_exc.error_code == "TEST_ERROR"
        
        # API异常
        api_exc = PlatformAPIException("API错误", "weibo", 500, {"error": "server error"})
        assert api_exc.status_code == 500
        assert api_exc.response_data == {"error": "server error"}
        
        # 平台不可用异常
        unavailable_exc = PlatformUnavailableException("weibo", "维护中")
        assert "weibo" in str(unavailable_exc)
        assert "维护中" in str(unavailable_exc)
        
        # 超时异常
        timeout_exc = SearchTimeoutException("weibo", 10)
        assert "10秒" in str(timeout_exc)
        
        # 限流异常
        rate_limit_exc = RateLimitException("weibo", 60)
        assert "60秒" in str(rate_limit_exc)
        
        # 认证异常
        auth_exc = AuthenticationException("weibo", "令牌过期")
        assert "令牌过期" in str(auth_exc)