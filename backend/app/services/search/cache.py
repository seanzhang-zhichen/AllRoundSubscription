"""
搜索结果缓存机制
"""
import json
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import redis
from app.core.config import settings
from app.services.search.base import SearchResult, PlatformSearchResult


class SearchCache:
    """搜索结果缓存类"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        初始化搜索缓存
        
        Args:
            redis_client: Redis客户端，如果为None则创建新的连接
        """
        if redis_client is None:
            self.redis = redis.from_url(settings.redis_url_with_auth)
        else:
            self.redis = redis_client
        
        # 缓存配置
        self.search_cache_ttl = 300  # 搜索结果缓存5分钟
        self.account_cache_ttl = 1800  # 账号信息缓存30分钟
        self.platform_status_ttl = 60  # 平台状态缓存1分钟
    
    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """
        生成缓存键
        
        Args:
            prefix: 缓存键前缀
            **kwargs: 用于生成键的参数
            
        Returns:
            str: 缓存键
        """
        # 将参数排序并序列化
        sorted_params = sorted(kwargs.items())
        params_str = json.dumps(sorted_params, ensure_ascii=False, sort_keys=True)
        
        # 生成哈希值
        hash_obj = hashlib.md5(params_str.encode('utf-8'))
        hash_str = hash_obj.hexdigest()
        
        return f"search:{prefix}:{hash_str}"
    
    async def get_search_result(
        self,
        keyword: str,
        platforms: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Optional[SearchResult]:
        """
        获取搜索结果缓存
        
        Args:
            keyword: 搜索关键词
            platforms: 平台列表
            page: 页码
            page_size: 每页大小
            
        Returns:
            Optional[SearchResult]: 缓存的搜索结果，如果不存在返回None
        """
        try:
            cache_key = self._generate_cache_key(
                "result",
                keyword=keyword,
                platforms=platforms or [],
                page=page,
                page_size=page_size
            )
            
            cached_data = self.redis.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                return SearchResult(**data)
            
            return None
        except Exception as e:
            # 缓存错误不应该影响正常功能
            print(f"获取搜索结果缓存失败: {e}")
            return None
    
    async def set_search_result(
        self,
        keyword: str,
        platforms: Optional[List[str]],
        page: int,
        page_size: int,
        result: SearchResult
    ) -> bool:
        """
        设置搜索结果缓存
        
        Args:
            keyword: 搜索关键词
            platforms: 平台列表
            page: 页码
            page_size: 每页大小
            result: 搜索结果
            
        Returns:
            bool: 是否设置成功
        """
        try:
            cache_key = self._generate_cache_key(
                "result",
                keyword=keyword,
                platforms=platforms or [],
                page=page,
                page_size=page_size
            )
            
            # 序列化结果
            data = result.model_dump()
            cached_data = json.dumps(data, ensure_ascii=False, default=str)
            
            # 设置缓存
            self.redis.setex(cache_key, self.search_cache_ttl, cached_data)
            return True
        except Exception as e:
            print(f"设置搜索结果缓存失败: {e}")
            return False
    
    async def get_platform_result(
        self,
        keyword: str,
        platform: str,
        page: int = 1,
        page_size: int = 20
    ) -> Optional[PlatformSearchResult]:
        """
        获取平台搜索结果缓存
        
        Args:
            keyword: 搜索关键词
            platform: 平台标识
            page: 页码
            page_size: 每页大小
            
        Returns:
            Optional[PlatformSearchResult]: 缓存的平台搜索结果
        """
        try:
            cache_key = self._generate_cache_key(
                "platform",
                keyword=keyword,
                platform=platform,
                page=page,
                page_size=page_size
            )
            
            cached_data = self.redis.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                return PlatformSearchResult(**data)
            
            return None
        except Exception as e:
            print(f"获取平台搜索结果缓存失败: {e}")
            return None
    
    async def set_platform_result(
        self,
        keyword: str,
        platform: str,
        page: int,
        page_size: int,
        result: PlatformSearchResult
    ) -> bool:
        """
        设置平台搜索结果缓存
        
        Args:
            keyword: 搜索关键词
            platform: 平台标识
            page: 页码
            page_size: 每页大小
            result: 平台搜索结果
            
        Returns:
            bool: 是否设置成功
        """
        try:
            cache_key = self._generate_cache_key(
                "platform",
                keyword=keyword,
                platform=platform,
                page=page,
                page_size=page_size
            )
            
            # 序列化结果
            data = result.model_dump()
            cached_data = json.dumps(data, ensure_ascii=False, default=str)
            
            # 设置缓存
            self.redis.setex(cache_key, self.search_cache_ttl, cached_data)
            return True
        except Exception as e:
            print(f"设置平台搜索结果缓存失败: {e}")
            return False
    
    async def get_account_info(
        self,
        platform: str,
        account_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取账号信息缓存
        
        Args:
            platform: 平台标识
            account_id: 账号ID
            
        Returns:
            Optional[Dict[str, Any]]: 缓存的账号信息
        """
        try:
            cache_key = self._generate_cache_key(
                "account",
                platform=platform,
                account_id=account_id
            )
            
            cached_data = self.redis.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
            
            return None
        except Exception as e:
            print(f"获取账号信息缓存失败: {e}")
            return None
    
    async def set_account_info(
        self,
        platform: str,
        account_id: str,
        account_info: Dict[str, Any]
    ) -> bool:
        """
        设置账号信息缓存
        
        Args:
            platform: 平台标识
            account_id: 账号ID
            account_info: 账号信息
            
        Returns:
            bool: 是否设置成功
        """
        try:
            cache_key = self._generate_cache_key(
                "account",
                platform=platform,
                account_id=account_id
            )
            
            cached_data = json.dumps(account_info, ensure_ascii=False, default=str)
            self.redis.setex(cache_key, self.account_cache_ttl, cached_data)
            return True
        except Exception as e:
            print(f"设置账号信息缓存失败: {e}")
            return False
    
    async def get_platform_status(self, platform: str) -> Optional[bool]:
        """
        获取平台状态缓存
        
        Args:
            platform: 平台标识
            
        Returns:
            Optional[bool]: 平台是否可用，None表示无缓存
        """
        try:
            cache_key = f"search:platform_status:{platform}"
            cached_data = self.redis.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            print(f"获取平台状态缓存失败: {e}")
            return None
    
    async def set_platform_status(self, platform: str, is_available: bool) -> bool:
        """
        设置平台状态缓存
        
        Args:
            platform: 平台标识
            is_available: 平台是否可用
            
        Returns:
            bool: 是否设置成功
        """
        try:
            cache_key = f"search:platform_status:{platform}"
            cached_data = json.dumps(is_available)
            self.redis.setex(cache_key, self.platform_status_ttl, cached_data)
            return True
        except Exception as e:
            print(f"设置平台状态缓存失败: {e}")
            return False    
    async def clear_search_cache(self, pattern: str = "search:*") -> int:
        """
        清除搜索相关缓存
        
        Args:
            pattern: 缓存键模式
            
        Returns:
            int: 清除的缓存数量
        """
        try:
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            print(f"清除搜索缓存失败: {e}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            Dict[str, Any]: 缓存统计信息
        """
        try:
            search_keys = len(self.redis.keys("search:result:*"))
            platform_keys = len(self.redis.keys("search:platform:*"))
            account_keys = len(self.redis.keys("search:account:*"))
            status_keys = len(self.redis.keys("search:platform_status:*"))
            
            return {
                "search_results": search_keys,
                "platform_results": platform_keys,
                "account_info": account_keys,
                "platform_status": status_keys,
                "total": search_keys + platform_keys + account_keys + status_keys,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"获取缓存统计失败: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
