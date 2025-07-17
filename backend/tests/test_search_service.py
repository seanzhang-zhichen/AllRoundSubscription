"""
搜索服务测试
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.services.search.service import SearchService
from app.services.search.adapters.mock import MockPlatformAdapter
from app.services.search.cache import SearchCache
from app.models.account import Platform


class TestSearchService:
    """搜索服务测试类"""
    
    @pytest.fixture
    def search_service(self):
        """创建搜索服务实例"""
        service = SearchService()
        return service
    
    @pytest.fixture
    def mock_adapter(self):
        """创建Mock适配器"""
        adapter = MockPlatformAdapter(Platform.WEIBO, enabled=True)
        return adapter
    
    @pytest.fixture
    def mock_cache(self):
        """创建Mock缓存"""
        cache = MagicMock(spec=SearchCache)
        cache.get_search_result = AsyncMock(return_value=None)
        cache.set_search_result = AsyncMock(return_value=True)
        cache.get_platform_result = AsyncMock(return_value=None)
        cache.set_platform_result = AsyncMock(return_value=True)
        cache.get_platform_status = AsyncMock(return_value=None)
        cache.set_platform_status = AsyncMock(return_value=True)
        return cache
    
    def test_register_adapter(self, search_service, mock_adapter):
        """测试注册适配器"""
        search_service.register_adapter(mock_adapter)
        
        assert mock_adapter.platform.value in search_service._adapters
        assert search_service.get_adapter(mock_adapter.platform.value) == mock_adapter
    
    def test_get_supported_platforms(self, search_service, mock_adapter):
        """测试获取支持的平台列表"""
        search_service.register_adapter(mock_adapter)
        
        platforms = search_service.get_supported_platforms()
        assert mock_adapter.platform.value in platforms
    
    @pytest.mark.asyncio
    async def test_search_accounts_with_mock_adapter(self, search_service, mock_adapter):
        """测试使用Mock适配器搜索账号"""
        search_service.register_adapter(mock_adapter)
        search_service.cache = MagicMock(spec=SearchCache)
        search_service.cache.get_search_result = AsyncMock(return_value=None)
        search_service.cache.set_search_result = AsyncMock(return_value=True)
        search_service.cache.get_platform_status = AsyncMock(return_value=None)
        search_service.cache.set_platform_status = AsyncMock(return_value=True)
        
        result = await search_service.search_accounts(
            keyword="测试",
            platforms=[mock_adapter.platform.value],
            page=1,
            page_size=10
        )
        
        assert result is not None
        assert result.total >= 0
        assert result.page == 1
        assert result.page_size == 10
        assert len(result.accounts) <= 10
    
    @pytest.mark.asyncio
    async def test_search_by_platform(self, search_service, mock_adapter):
        """测试按平台搜索"""
        search_service.register_adapter(mock_adapter)
        search_service.cache = MagicMock(spec=SearchCache)
        search_service.cache.get_platform_result = AsyncMock(return_value=None)
        search_service.cache.set_platform_result = AsyncMock(return_value=True)
        search_service.cache.get_platform_status = AsyncMock(return_value=None)
        search_service.cache.set_platform_status = AsyncMock(return_value=True)
        
        result = await search_service.search_by_platform(
            keyword="科技",
            platform=mock_adapter.platform.value,
            page=1,
            page_size=5
        )
        
        assert result is not None
        assert result.platform == mock_adapter.platform.value
        assert result.page == 1
        assert result.page_size == 5
    
    @pytest.mark.asyncio
    async def test_search_accounts_no_adapters(self, search_service):
        """测试没有适配器时的搜索"""
        result = await search_service.search_accounts(
            keyword="测试",
            platforms=["nonexistent"],
            page=1,
            page_size=10
        )
        
        assert result.total == 0
        assert len(result.accounts) == 0
    
    @pytest.mark.asyncio
    async def test_get_search_statistics(self, search_service, mock_adapter):
        """测试获取搜索统计信息"""
        search_service.register_adapter(mock_adapter)
        
        stats = await search_service.get_search_statistics()
        
        assert "supported_platforms" in stats
        assert "registered_adapters" in stats
        assert "cache_stats" in stats
        assert "timestamp" in stats
        assert mock_adapter.platform.value in stats["supported_platforms"]


class TestMockPlatformAdapter:
    """Mock平台适配器测试类"""
    
    @pytest.fixture
    def mock_adapter(self):
        """创建Mock适配器"""
        return MockPlatformAdapter(Platform.WEIBO, enabled=True)
    
    def test_platform_properties(self, mock_adapter):
        """测试平台属性"""
        assert mock_adapter.platform == Platform.WEIBO
        assert mock_adapter.platform_name == "Mock Weibo"
        assert mock_adapter.is_enabled is True
    
    @pytest.mark.asyncio
    async def test_search_accounts(self, mock_adapter):
        """测试搜索账号"""
        result = await mock_adapter.search_accounts("测试", page=1, page_size=5)
        
        assert result.success is True
        assert result.platform == Platform.WEIBO.value
        assert result.total >= 0
        assert len(result.accounts) <= 5
    
    @pytest.mark.asyncio
    async def test_search_accounts_disabled(self, mock_adapter):
        """测试禁用状态下的搜索"""
        mock_adapter.set_enabled(False)
        
        result = await mock_adapter.search_accounts("测试", page=1, page_size=5)
        
        assert result.success is False
        assert "禁用" in result.error_message
    
    @pytest.mark.asyncio
    async def test_get_account_info(self, mock_adapter):
        """测试获取账号信息"""
        # 获取第一个模拟账号的ID
        mock_accounts = mock_adapter._mock_accounts
        if mock_accounts:
            account_id = mock_accounts[0]["id"]
            
            account_info = await mock_adapter.get_account_info(account_id)
            
            assert account_info is not None
            assert account_info["id"] == account_id
    
    @pytest.mark.asyncio
    async def test_get_account_info_not_found(self, mock_adapter):
        """测试获取不存在的账号信息"""
        account_info = await mock_adapter.get_account_info("nonexistent_id")
        
        assert account_info is None
    
    def test_normalize_account_data(self, mock_adapter):
        """测试数据标准化"""
        raw_data = {
            "id": "test_id",
            "name": "测试账号",
            "avatar": "https://example.com/avatar.jpg",
            "description": "测试描述",
            "followers": 1000,
            "verified": True
        }
        
        normalized = mock_adapter.normalize_account_data(raw_data)
        
        assert normalized["account_id"] == "test_id"
        assert normalized["name"] == "测试账号"
        assert normalized["platform"] == Platform.WEIBO.value
        assert normalized["avatar_url"] == "https://example.com/avatar.jpg"
        assert normalized["description"] == "测试描述"
        assert normalized["follower_count"] == 1000
        assert normalized["details"]["verified"] is True


class TestSearchCache:
    """搜索缓存测试类"""
    
    @pytest.fixture
    def mock_redis(self):
        """创建Mock Redis客户端"""
        redis_mock = MagicMock()
        redis_mock.get.return_value = None
        redis_mock.setex.return_value = True
        redis_mock.keys.return_value = []
        redis_mock.delete.return_value = 0
        return redis_mock
    
    @pytest.fixture
    def search_cache(self, mock_redis):
        """创建搜索缓存实例"""
        return SearchCache(redis_client=mock_redis)
    
    def test_generate_cache_key(self, search_cache):
        """测试缓存键生成"""
        key1 = search_cache._generate_cache_key("test", keyword="hello", page=1)
        key2 = search_cache._generate_cache_key("test", keyword="hello", page=1)
        key3 = search_cache._generate_cache_key("test", keyword="world", page=1)
        
        # 相同参数应该生成相同的键
        assert key1 == key2
        # 不同参数应该生成不同的键
        assert key1 != key3
        # 键应该包含前缀
        assert key1.startswith("search:test:")
    
    @pytest.mark.asyncio
    async def test_get_search_result_cache_miss(self, search_cache, mock_redis):
        """测试搜索结果缓存未命中"""
        mock_redis.get.return_value = None
        
        result = await search_cache.get_search_result("test", ["weibo"], 1, 10)
        
        assert result is None
        assert mock_redis.get.called
    
    @pytest.mark.asyncio
    async def test_set_search_result(self, search_cache, mock_redis):
        """测试设置搜索结果缓存"""
        from app.services.search.base import SearchResult
        
        search_result = SearchResult(
            accounts=[],
            total=0,
            page=1,
            page_size=10,
            has_more=False
        )
        
        success = await search_cache.set_search_result(
            "test", ["weibo"], 1, 10, search_result
        )
        
        assert success is True
        assert mock_redis.setex.called
    
    @pytest.mark.asyncio
    async def test_get_cache_stats(self, search_cache, mock_redis):
        """测试获取缓存统计"""
        mock_redis.keys.side_effect = [
            ["key1", "key2"],  # search:result:*
            ["key3"],          # search:platform:*
            ["key4", "key5"],  # search:account:*
            []                 # search:platform_status:*
        ]
        
        stats = await search_cache.get_cache_stats()
        
        assert stats["search_results"] == 2
        assert stats["platform_results"] == 1
        assert stats["account_info"] == 2
        assert stats["platform_status"] == 0
        assert stats["total"] == 5
        assert "timestamp" in stats