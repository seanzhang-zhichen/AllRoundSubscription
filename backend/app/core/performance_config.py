"""
性能优化配置
"""
import psutil
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PerformanceConfig:
    """性能配置"""
    # API响应时间阈值
    slow_request_threshold: float = 1.0  # 秒
    critical_request_threshold: float = 3.0  # 秒
    
    # 数据库查询阈值
    slow_query_threshold: float = 1.0  # 秒
    critical_query_threshold: float = 5.0  # 秒
    
    # 缓存配置
    default_cache_ttl: int = 3600  # 秒
    short_cache_ttl: int = 300     # 5分钟
    long_cache_ttl: int = 86400    # 24小时
    
    # 限流配置
    default_rate_limit: int = 100  # 每分钟请求数
    auth_rate_limit: int = 10      # 认证接口限制
    search_rate_limit: int = 50    # 搜索接口限制
    
    # 系统资源阈值
    cpu_threshold: float = 80.0    # CPU使用率阈值(%)
    memory_threshold: float = 85.0  # 内存使用率阈值(%)
    disk_threshold: float = 90.0   # 磁盘使用率阈值(%)
    
    # 连接池配置
    db_pool_size: int = 20
    db_max_overflow: int = 30
    redis_max_connections: int = 50


class SystemResourceMonitor:
    """系统资源监控"""
    
    def __init__(self):
        self.config = PerformanceConfig()
    
    def get_cpu_usage(self) -> float:
        """获取CPU使用率"""
        try:
            return psutil.cpu_percent(interval=1)
        except Exception as e:
            logger.error(f"获取CPU使用率失败: {str(e)}")
            return 0.0
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用情况"""
        try:
            memory = psutil.virtual_memory()
            return {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percentage": memory.percent,
                "free": memory.free
            }
        except Exception as e:
            logger.error(f"获取内存使用情况失败: {str(e)}")
            return {"percentage": 0.0}
    
    def get_disk_usage(self, path: str = "/") -> Dict[str, Any]:
        """获取磁盘使用情况"""
        try:
            disk = psutil.disk_usage(path)
            return {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percentage": (disk.used / disk.total) * 100
            }
        except Exception as e:
            logger.error(f"获取磁盘使用情况失败: {str(e)}")
            return {"percentage": 0.0}
    
    def get_network_stats(self) -> Dict[str, Any]:
        """获取网络统计"""
        try:
            net_io = psutil.net_io_counters()
            return {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "errin": net_io.errin,
                "errout": net_io.errout,
                "dropin": net_io.dropin,
                "dropout": net_io.dropout
            }
        except Exception as e:
            logger.error(f"获取网络统计失败: {str(e)}")
            return {}
    
    def get_process_info(self) -> Dict[str, Any]:
        """获取当前进程信息"""
        try:
            process = psutil.Process()
            with process.oneshot():
                return {
                    "pid": process.pid,
                    "cpu_percent": process.cpu_percent(),
                    "memory_percent": process.memory_percent(),
                    "memory_info": process.memory_info()._asdict(),
                    "num_threads": process.num_threads(),
                    "num_fds": process.num_fds() if hasattr(process, 'num_fds') else 0,
                    "create_time": process.create_time(),
                    "status": process.status()
                }
        except Exception as e:
            logger.error(f"获取进程信息失败: {str(e)}")
            return {}
    
    def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        cpu_usage = self.get_cpu_usage()
        memory_usage = self.get_memory_usage()
        disk_usage = self.get_disk_usage()
        process_info = self.get_process_info()
        
        # 判断健康状态
        health_status = "healthy"
        warnings = []
        
        if cpu_usage > self.config.cpu_threshold:
            health_status = "warning"
            warnings.append(f"CPU使用率过高: {cpu_usage:.1f}%")
        
        memory_percent = memory_usage.get("percentage", 0)
        if memory_percent > self.config.memory_threshold:
            health_status = "critical" if health_status != "critical" else health_status
            warnings.append(f"内存使用率过高: {memory_percent:.1f}%")
        
        disk_percent = disk_usage.get("percentage", 0)
        if disk_percent > self.config.disk_threshold:
            health_status = "critical"
            warnings.append(f"磁盘使用率过高: {disk_percent:.1f}%")
        
        return {
            "status": health_status,
            "warnings": warnings,
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "disk_usage": disk_usage,
            "process_info": process_info,
            "thresholds": {
                "cpu": self.config.cpu_threshold,
                "memory": self.config.memory_threshold,
                "disk": self.config.disk_threshold
            }
        }
    
    def should_throttle_requests(self) -> bool:
        """判断是否应该限制请求"""
        cpu_usage = self.get_cpu_usage()
        memory_usage = self.get_memory_usage()
        
        # 如果CPU或内存使用率过高，建议限制请求
        return (cpu_usage > self.config.cpu_threshold or 
                memory_usage.get("percentage", 0) > self.config.memory_threshold)


class PerformanceOptimizer:
    """性能优化器"""
    
    def __init__(self):
        self.config = PerformanceConfig()
        self.resource_monitor = SystemResourceMonitor()
    
    def get_optimal_cache_ttl(self, data_type: str) -> int:
        """根据数据类型获取最优缓存TTL"""
        cache_strategies = {
            "user_profile": self.config.long_cache_ttl,      # 用户资料变化较少
            "user_subscriptions": self.config.default_cache_ttl,  # 订阅列表中等频率变化
            "article_content": self.config.long_cache_ttl,   # 文章内容不变
            "search_results": self.config.short_cache_ttl,   # 搜索结果变化较快
            "feed_content": self.config.short_cache_ttl,     # 动态内容变化快
            "platform_data": self.config.default_cache_ttl, # 平台数据中等频率
            "system_config": self.config.long_cache_ttl      # 系统配置变化少
        }
        
        return cache_strategies.get(data_type, self.config.default_cache_ttl)
    
    def get_optimal_rate_limit(self, endpoint_type: str) -> int:
        """根据端点类型获取最优限流配置"""
        # 根据系统负载动态调整
        system_health = self.resource_monitor.get_system_health()
        
        base_limits = {
            "auth": self.config.auth_rate_limit,
            "search": self.config.search_rate_limit,
            "api": self.config.default_rate_limit,
            "content": self.config.default_rate_limit
        }
        
        base_limit = base_limits.get(endpoint_type, self.config.default_rate_limit)
        
        # 根据系统状态调整
        if system_health["status"] == "critical":
            return int(base_limit * 0.3)  # 严重时减少70%
        elif system_health["status"] == "warning":
            return int(base_limit * 0.6)  # 警告时减少40%
        
        return base_limit
    
    def get_database_optimization_hints(self) -> Dict[str, Any]:
        """获取数据库优化建议"""
        return {
            "connection_pool": {
                "pool_size": self.config.db_pool_size,
                "max_overflow": self.config.db_max_overflow,
                "pool_timeout": 30,
                "pool_recycle": 3600
            },
            "query_optimization": {
                "slow_query_threshold": self.config.slow_query_threshold,
                "enable_query_cache": True,
                "batch_size": 100,
                "use_indexes": True
            },
            "recommended_indexes": [
                "CREATE INDEX IF NOT EXISTS idx_users_openid ON users(openid);",
                "CREATE INDEX IF NOT EXISTS idx_articles_account_time ON articles(account_id, publish_timestamp DESC);",
                "CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);",
                "CREATE INDEX IF NOT EXISTS idx_push_records_user_time ON push_records(user_id, push_time DESC);"
            ]
        }
    
    def get_caching_strategy(self) -> Dict[str, Any]:
        """获取缓存策略建议"""
        return {
            "redis_config": {
                "max_connections": self.config.redis_max_connections,
                "connection_pool_size": 20,
                "socket_timeout": 5,
                "socket_connect_timeout": 5
            },
            "cache_patterns": {
                "user_data": {
                    "ttl": self.get_optimal_cache_ttl("user_profile"),
                    "pattern": "user:{user_id}:*"
                },
                "content_data": {
                    "ttl": self.get_optimal_cache_ttl("article_content"),
                    "pattern": "content:{content_id}"
                },
                "search_data": {
                    "ttl": self.get_optimal_cache_ttl("search_results"),
                    "pattern": "search:{query_hash}"
                }
            },
            "cache_warming": {
                "enabled": True,
                "popular_content_threshold": 100,
                "preload_user_data": True
            }
        }


# 全局实例
performance_config = PerformanceConfig()
system_resource_monitor = SystemResourceMonitor()
performance_optimizer = PerformanceOptimizer()


def get_performance_config() -> PerformanceConfig:
    """获取性能配置"""
    return performance_config


def get_system_resource_monitor() -> SystemResourceMonitor:
    """获取系统资源监控器"""
    return system_resource_monitor


def get_performance_optimizer() -> PerformanceOptimizer:
    """获取性能优化器"""
    return performance_optimizer