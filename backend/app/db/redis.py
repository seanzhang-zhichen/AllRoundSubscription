"""
Redis缓存配置
"""
import redis.asyncio as redis
from typing import Optional, Any, List, Dict, Callable
import json
from app.core.logging import get_logger
import hashlib
import time
from functools import wraps
from app.core.config import settings
from app.core.monitoring import get_performance_monitor

logger = get_logger(__name__)
performance_monitor = get_performance_monitor()

# Redis连接池
redis_pool = None


async def get_redis_pool():
    """获取Redis连接池"""
    global redis_pool
    if redis_pool is None and settings.REDIS_URL:
        try:
            # 使用带认证的Redis URL
            redis_url = settings.redis_url_with_auth
            redis_pool = redis.ConnectionPool.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20
            )
        except Exception as e:
            logger.warning(f"Redis连接池创建失败: {str(e)}")
            redis_pool = None
    return redis_pool


async def get_redis() -> Optional[redis.Redis]:
    """获取Redis客户端"""
    try:
        pool = await get_redis_pool()
        if pool is None:
            return None
        return redis.Redis(connection_pool=pool)
    except Exception as e:
        logger.warning(f"获取Redis客户端失败: {str(e)}")
        return None


class CacheService:
    """增强的缓存服务类"""
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._redis_lock = None
        self.hit_count = 0
        self.miss_count = 0
    
    async def _get_redis(self) -> Optional[redis.Redis]:
        """获取Redis客户端实例"""
        if self._redis is None:
            # 使用简单的双重检查锁定模式
            if self._redis_lock is None:
                import asyncio
                self._redis_lock = asyncio.Lock()
            
            async with self._redis_lock:
                if self._redis is None:
                    self._redis = await get_redis()
        return self._redis
    
    async def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """设置缓存"""
        start_time = time.time()
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                logger.debug(f"Redis不可用，跳过缓存设置: {key}")
                return False
                
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            await redis_client.set(key, value, ex=expire)
            
            # 记录缓存操作性能
            operation_time = time.time() - start_time
            performance_monitor.record_metric("cache.set.duration", operation_time, {"key": key})
            
            return True
        except Exception as e:
            logger.debug(f"设置缓存失败: {key}, 错误: {str(e)}")
            performance_monitor.record_metric("cache.set.error", 1, {"key": key})
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        start_time = time.time()
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                logger.debug(f"Redis不可用，跳过缓存获取: {key}")
                self.miss_count += 1
                return None
                
            value = await redis_client.get(key)
            
            operation_time = time.time() - start_time
            
            if value is None:
                self.miss_count += 1
                performance_monitor.record_metric("cache.miss", 1, {"key": key})
                performance_monitor.record_metric("cache.get.duration", operation_time, {"key": key, "result": "miss"})
                return None
            
            self.hit_count += 1
            performance_monitor.record_metric("cache.hit", 1, {"key": key})
            performance_monitor.record_metric("cache.get.duration", operation_time, {"key": key, "result": "hit"})
            
            # 尝试解析JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            logger.debug(f"获取缓存失败: {key}, 错误: {str(e)}")
            performance_monitor.record_metric("cache.get.error", 1, {"key": key})
            return None
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                logger.debug(f"Redis不可用，跳过缓存删除: {key}")
                return False
            result = await redis_client.delete(key)
            performance_monitor.record_metric("cache.delete", 1, {"key": key})
            return result > 0
        except Exception as e:
            logger.debug(f"删除缓存失败: {key}, 错误: {str(e)}")
            performance_monitor.record_metric("cache.delete.error", 1, {"key": key})
            return False
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                logger.debug(f"Redis不可用，跳过缓存存在性检查: {key}")
                return False
            return await redis_client.exists(key) > 0
        except Exception as e:
            logger.debug(f"检查缓存存在性失败: {key}, 错误: {str(e)}")
            return False
    
    async def get_or_set(self, key: str, factory: Callable, expire: int = 3600) -> Any:
        """获取缓存，如果不存在则通过工厂函数生成并缓存"""
        value = await self.get(key)
        if value is not None:
            return value
        
        # 缓存未命中，生成新值
        start_time = time.time()
        try:
            if callable(factory):
                if hasattr(factory, '__call__') and hasattr(factory, '__await__'):
                    # 异步函数
                    new_value = await factory()
                else:
                    # 同步函数
                    new_value = factory()
            else:
                new_value = factory
            
            generation_time = time.time() - start_time
            performance_monitor.record_metric("cache.generation.duration", generation_time, {"key": key})
            
            # 设置缓存
            await self.set(key, new_value, expire)
            return new_value
            
        except Exception as e:
            logger.error(f"缓存工厂函数执行失败: {key}, 错误: {str(e)}")
            performance_monitor.record_metric("cache.generation.error", 1, {"key": key})
            raise
    
    async def mget(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取缓存"""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                logger.debug(f"Redis不可用，跳过批量缓存获取: {keys}")
                self.miss_count += len(keys)
                return {}
                
            values = await redis_client.mget(keys)
            
            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        result[key] = value
                    self.hit_count += 1
                else:
                    self.miss_count += 1
            
            return result
        except Exception as e:
            logger.debug(f"批量获取缓存失败: {keys}, 错误: {str(e)}")
            return {}
    
    async def mset(self, mapping: Dict[str, Any], expire: int = 3600) -> bool:
        """批量设置缓存"""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                logger.debug(f"Redis不可用，跳过批量缓存设置: {list(mapping.keys())}")
                return False
            
            # 准备数据
            cache_data = {}
            for key, value in mapping.items():
                if isinstance(value, (dict, list)):
                    cache_data[key] = json.dumps(value, ensure_ascii=False)
                else:
                    cache_data[key] = value
            
            # 批量设置
            await redis_client.mset(cache_data)
            
            # 设置过期时间
            if expire > 0:
                pipe = redis_client.pipeline()
                for key in cache_data.keys():
                    pipe.expire(key, expire)
                await pipe.execute()
            
            return True
        except Exception as e:
            logger.debug(f"批量设置缓存失败: {list(mapping.keys())}, 错误: {str(e)}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """按模式删除缓存"""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                logger.debug(f"Redis不可用，跳过模式删除缓存: {pattern}")
                return 0
            keys = await redis_client.keys(pattern)
            if keys:
                deleted = await redis_client.delete(*keys)
                performance_monitor.record_metric("cache.delete_pattern", deleted, {"pattern": pattern})
                return deleted
            return 0
        except Exception as e:
            logger.debug(f"按模式删除缓存失败: {pattern}, 错误: {str(e)}")
            return 0
    
    def get_hit_rate(self) -> float:
        """获取缓存命中率"""
        total = self.hit_count + self.miss_count
        if total == 0:
            return 0.0
        return self.hit_count / total
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": self.get_hit_rate(),
            "total_requests": self.hit_count + self.miss_count
        }


def cache_key_generator(*args, **kwargs) -> str:
    """生成缓存键"""
    key_parts = []
    for arg in args:
        if hasattr(arg, '__dict__'):
            # 对象类型，使用类名
            key_parts.append(arg.__class__.__name__)
        else:
            key_parts.append(str(arg))
    
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}:{v}")
    
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(expire: int = 3600, key_prefix: str = ""):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            func_name = f"{func.__module__}.{func.__name__}"
            cache_key = f"{key_prefix}:{func_name}:{cache_key_generator(*args, **kwargs)}"
            
            # 尝试从缓存获取
            cached_result = await cache_service.get(cache_key)
            if cached_result is not None:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_result
            
            # 缓存未命中，执行函数
            logger.debug(f"缓存未命中: {cache_key}")
            result = await func(*args, **kwargs)
            
            # 存储到缓存
            await cache_service.set(cache_key, result, expire)
            return result
        
        return wrapper
    return decorator


def cache_invalidate(key_pattern: str):
    """缓存失效装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            # 执行成功后清除相关缓存
            await cache_service.delete_pattern(key_pattern)
            logger.debug(f"缓存失效: {key_pattern}")
            return result
        return wrapper
    return decorator


# 全局缓存服务实例
cache_service = CacheService()