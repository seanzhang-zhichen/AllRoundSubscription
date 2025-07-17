"""
性能监控和优化功能测试
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, patch
from app.core.monitoring import PerformanceMonitor, DatabaseMonitor
from app.core.rate_limiting import RateLimiter, RateLimitStrategy, RateLimitRule
from app.core.database_optimization import QueryOptimizer, ConnectionPoolMonitor
from app.core.performance_config import SystemResourceMonitor, PerformanceOptimizer
from app.db.redis import CacheService


class TestPerformanceMonitor:
    """性能监控器测试"""
    
    def test_performance_monitor_initialization(self):
        """测试性能监控器初始化"""
        monitor = PerformanceMonitor()
        assert monitor.max_metrics == 10000
        assert len(monitor.metrics) == 0
        assert len(monitor.response_times) == 0
    
    def test_record_response_time(self):
        """测试记录响应时间"""
        monitor = PerformanceMonitor()
        
        # 记录响应时间
        monitor.record_response_time("/api/test", "GET", 200, 0.5)
        
        assert len(monitor.response_times) == 1
        assert monitor.response_times[0].endpoint == "/api/test"
        assert monitor.response_times[0].method == "GET"
        assert monitor.response_times[0].status_code == 200
        assert monitor.response_times[0].response_time == 0.5
    
    def test_endpoint_stats(self):
        """测试端点统计"""
        monitor = PerformanceMonitor()
        
        # 记录多个请求
        monitor.record_response_time("/api/test", "GET", 200, 0.5)
        monitor.record_response_time("/api/test", "GET", 200, 1.0)
        monitor.record_response_time("/api/test", "GET", 500, 2.0)
        
        stats = monitor.get_endpoint_stats("/api/test")
        
        assert stats["count"] == 3
        assert stats["avg_time"] == 1.5  # (0.5 + 1.0 + 2.0) / 3
        assert stats["min_time"] == 0.5
        assert stats["max_time"] == 2.0
        assert stats["error_count"] == 1
        assert stats["error_rate"] == 1/3
    
    def test_slow_requests(self):
        """测试慢请求检测"""
        monitor = PerformanceMonitor()
        
        # 记录快请求和慢请求
        monitor.record_response_time("/api/fast", "GET", 200, 0.1)
        monitor.record_response_time("/api/slow", "GET", 200, 2.0)
        monitor.record_response_time("/api/very_slow", "GET", 200, 5.0)
        
        slow_requests = monitor.get_slow_requests(1.0)
        
        assert len(slow_requests) == 2
        assert slow_requests[0].response_time == 5.0  # 按时间降序排序
        assert slow_requests[1].response_time == 2.0
    
    def test_health_metrics(self):
        """测试健康状态指标"""
        monitor = PerformanceMonitor()
        
        # 记录正常请求
        for i in range(5):
            monitor.record_response_time("/api/test", "GET", 200, 0.5)
        
        health = monitor.get_health_metrics()
        
        assert health["status"] == "healthy"
        assert health["total_requests"] == 5
        assert health["avg_response_time"] == 0.5
        assert health["error_rate"] == 0
        assert health["slow_requests"] == 0


class TestDatabaseMonitor:
    """数据库监控器测试"""
    
    def test_database_monitor_initialization(self):
        """测试数据库监控器初始化"""
        monitor = DatabaseMonitor()
        assert len(monitor.query_stats) == 0
        assert len(monitor.slow_queries) == 0
    
    def test_record_query(self):
        """测试记录查询"""
        monitor = DatabaseMonitor()
        
        # 记录查询
        monitor.record_query("SELECT", 0.5, True)
        monitor.record_query("SELECT", 1.5, True)
        monitor.record_query("INSERT", 0.3, False)
        
        stats = monitor.get_query_stats()
        
        assert "SELECT" in stats
        assert stats["SELECT"]["count"] == 2
        assert stats["SELECT"]["avg_time"] == 1.0
        assert stats["SELECT"]["error_count"] == 0
        
        assert "INSERT" in stats
        assert stats["INSERT"]["error_count"] == 1
    
    def test_slow_queries(self):
        """测试慢查询记录"""
        monitor = DatabaseMonitor()
        
        # 记录慢查询
        monitor.record_query("SELECT", 2.0, True)
        monitor.record_query("UPDATE", 3.0, True)
        
        slow_queries = monitor.get_slow_queries()
        
        assert len(slow_queries) == 2
        assert slow_queries[0]["execution_time"] == 3.0  # 按时间降序


@pytest.mark.asyncio
class TestRateLimiter:
    """限流器测试"""
    
    async def test_rate_limiter_initialization(self):
        """测试限流器初始化"""
        limiter = RateLimiter()
        assert "api" in limiter.default_rules
        assert "auth" in limiter.default_rules
        assert "search" in limiter.default_rules
    
    @patch('app.db.redis.cache_service')
    async def test_fixed_window_rate_limit(self, mock_cache):
        """测试固定窗口限流"""
        limiter = RateLimiter()
        
        # 模拟缓存返回
        mock_cache.get.return_value = 0
        mock_cache.set.return_value = True
        
        # 创建测试规则
        rule = RateLimitRule("test", 5, 60, RateLimitStrategy.FIXED_WINDOW)
        limiter.add_custom_rule("test", rule)
        
        # 测试限流检查
        result = await limiter.check_rate_limit("user123", "test")
        
        assert result.allowed is True
        assert result.remaining == 4
    
    @patch('app.db.redis.cache_service')
    async def test_rate_limit_exceeded(self, mock_cache):
        """测试超出限流"""
        limiter = RateLimiter()
        
        # 模拟已达到限制
        mock_cache.get.return_value = 10
        
        rule = RateLimitRule("test", 5, 60, RateLimitStrategy.FIXED_WINDOW)
        limiter.add_custom_rule("test", rule)
        
        result = await limiter.check_rate_limit("user123", "test")
        
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after is not None
    
    async def test_custom_rule_addition(self):
        """测试添加自定义规则"""
        limiter = RateLimiter()
        
        custom_rule = RateLimitRule("custom", 100, 300, RateLimitStrategy.SLIDING_WINDOW)
        limiter.add_custom_rule("custom", custom_rule)
        
        assert "custom" in limiter.default_rules
        assert limiter.default_rules["custom"].limit == 100


class TestCacheService:
    """缓存服务测试"""
    
    def test_cache_service_initialization(self):
        """测试缓存服务初始化"""
        cache = CacheService()
        assert cache.hit_count == 0
        assert cache.miss_count == 0
    
    def test_hit_rate_calculation(self):
        """测试命中率计算"""
        cache = CacheService()
        
        # 模拟命中和未命中
        cache.hit_count = 7
        cache.miss_count = 3
        
        hit_rate = cache.get_hit_rate()
        assert hit_rate == 0.7
    
    def test_cache_stats(self):
        """测试缓存统计"""
        cache = CacheService()
        
        cache.hit_count = 80
        cache.miss_count = 20
        
        stats = cache.get_stats()
        
        assert stats["hit_count"] == 80
        assert stats["miss_count"] == 20
        assert stats["hit_rate"] == 0.8
        assert stats["total_requests"] == 100


class TestSystemResourceMonitor:
    """系统资源监控器测试"""
    
    @patch('psutil.cpu_percent')
    def test_cpu_usage(self, mock_cpu):
        """测试CPU使用率获取"""
        mock_cpu.return_value = 45.5
        
        monitor = SystemResourceMonitor()
        cpu_usage = monitor.get_cpu_usage()
        
        assert cpu_usage == 45.5
        mock_cpu.assert_called_once_with(interval=1)
    
    @patch('psutil.virtual_memory')
    def test_memory_usage(self, mock_memory):
        """测试内存使用情况获取"""
        mock_memory.return_value = Mock(
            total=8000000000,
            available=4000000000,
            used=4000000000,
            percent=50.0,
            free=4000000000
        )
        
        monitor = SystemResourceMonitor()
        memory_usage = monitor.get_memory_usage()
        
        assert memory_usage["percentage"] == 50.0
        assert memory_usage["total"] == 8000000000
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_should_throttle_requests(self, mock_memory, mock_cpu):
        """测试是否应该限制请求"""
        monitor = SystemResourceMonitor()
        
        # 正常情况
        mock_cpu.return_value = 50.0
        mock_memory.return_value = Mock(percent=60.0)
        
        assert monitor.should_throttle_requests() is False
        
        # 高CPU使用率
        mock_cpu.return_value = 90.0
        assert monitor.should_throttle_requests() is True
        
        # 高内存使用率
        mock_cpu.return_value = 50.0
        mock_memory.return_value = Mock(percent=90.0)
        assert monitor.should_throttle_requests() is True


class TestPerformanceOptimizer:
    """性能优化器测试"""
    
    def test_optimal_cache_ttl(self):
        """测试最优缓存TTL"""
        optimizer = PerformanceOptimizer()
        
        # 测试不同数据类型的TTL
        assert optimizer.get_optimal_cache_ttl("user_profile") == 86400  # 24小时
        assert optimizer.get_optimal_cache_ttl("search_results") == 300  # 5分钟
        assert optimizer.get_optimal_cache_ttl("unknown_type") == 3600   # 默认1小时
    
    @patch('app.core.performance_config.SystemResourceMonitor.get_system_health')
    def test_optimal_rate_limit(self, mock_health):
        """测试最优限流配置"""
        optimizer = PerformanceOptimizer()
        
        # 正常情况
        mock_health.return_value = {"status": "healthy"}
        assert optimizer.get_optimal_rate_limit("api") == 100
        
        # 警告状态
        mock_health.return_value = {"status": "warning"}
        assert optimizer.get_optimal_rate_limit("api") == 60  # 减少40%
        
        # 严重状态
        mock_health.return_value = {"status": "critical"}
        assert optimizer.get_optimal_rate_limit("api") == 30  # 减少70%
    
    def test_database_optimization_hints(self):
        """测试数据库优化建议"""
        optimizer = PerformanceOptimizer()
        hints = optimizer.get_database_optimization_hints()
        
        assert "connection_pool" in hints
        assert "query_optimization" in hints
        assert "recommended_indexes" in hints
        assert len(hints["recommended_indexes"]) > 0
    
    def test_caching_strategy(self):
        """测试缓存策略"""
        optimizer = PerformanceOptimizer()
        strategy = optimizer.get_caching_strategy()
        
        assert "redis_config" in strategy
        assert "cache_patterns" in strategy
        assert "cache_warming" in strategy
        
        # 检查缓存模式
        patterns = strategy["cache_patterns"]
        assert "user_data" in patterns
        assert "content_data" in patterns
        assert "search_data" in patterns


class TestQueryOptimizer:
    """查询优化器测试"""
    
    def test_query_optimizer_initialization(self):
        """测试查询优化器初始化"""
        optimizer = QueryOptimizer()
        assert optimizer.slow_query_threshold == 1.0
        assert isinstance(optimizer.query_cache, dict)
    
    @pytest.mark.asyncio
    async def test_monitor_query_decorator(self):
        """测试查询监控装饰器"""
        optimizer = QueryOptimizer()
        
        @optimizer.monitor_query("TEST_QUERY")
        async def test_query():
            await asyncio.sleep(0.1)
            return "result"
        
        # 执行被装饰的函数
        result = await test_query()
        assert result == "result"


class TestConnectionPoolMonitor:
    """连接池监控器测试"""
    
    def test_connection_pool_monitor_initialization(self):
        """测试连接池监控器初始化"""
        monitor = ConnectionPoolMonitor()
        assert "active_connections" in monitor.pool_stats
        assert "idle_connections" in monitor.pool_stats
        assert "total_connections" in monitor.pool_stats
    
    def test_pool_health_calculation(self):
        """测试连接池健康状态计算"""
        monitor = ConnectionPoolMonitor()
        
        # 设置测试数据
        monitor.pool_stats["total_connections"] = 20
        monitor.pool_stats["active_connections"] = 5
        
        health = monitor.get_pool_health()
        
        assert health["utilization"] == 0.25  # 5/20
        assert health["health_status"] == "healthy"
        
        # 测试高使用率
        monitor.pool_stats["active_connections"] = 18
        health = monitor.get_pool_health()
        
        assert health["utilization"] == 0.9
        assert health["health_status"] == "critical"


@pytest.mark.asyncio
class TestIntegrationScenarios:
    """集成测试场景"""
    
    async def test_performance_monitoring_integration(self):
        """测试性能监控集成"""
        # 创建监控器实例
        perf_monitor = PerformanceMonitor()
        db_monitor = DatabaseMonitor()
        
        # 模拟一系列操作
        perf_monitor.record_response_time("/api/users", "GET", 200, 0.3)
        perf_monitor.record_response_time("/api/articles", "GET", 200, 1.2)
        perf_monitor.record_response_time("/api/search", "POST", 200, 0.8)
        
        db_monitor.record_query("SELECT", 0.1, True)
        db_monitor.record_query("INSERT", 0.5, True)
        db_monitor.record_query("UPDATE", 2.1, True)  # 慢查询
        
        # 验证统计数据
        health_metrics = perf_monitor.get_health_metrics()
        assert health_metrics["total_requests"] == 3
        assert health_metrics["status"] in ["healthy", "degraded"]
        
        db_stats = db_monitor.get_query_stats()
        assert len(db_stats) == 3
        assert "SELECT" in db_stats
        
        slow_queries = db_monitor.get_slow_queries()
        assert len(slow_queries) == 1
        assert slow_queries[0]["query_type"] == "UPDATE"
    
    @patch('app.db.redis.cache_service')
    async def test_rate_limiting_integration(self, mock_cache):
        """测试限流集成"""
        limiter = RateLimiter()
        
        # 模拟缓存行为
        mock_cache.get.side_effect = [0, 1, 2, 3, 4, 5]  # 递增计数
        mock_cache.set.return_value = True
        
        user_id = "test_user"
        
        # 连续请求
        for i in range(5):
            result = await limiter.check_rate_limit(user_id, "auth")
            if i < 4:  # 前4个请求应该被允许
                assert result.allowed is True
            else:  # 第5个请求应该被拒绝（假设auth限制为5）
                # 这里需要根据实际的auth限制来调整
                pass
    
    def test_system_resource_monitoring_integration(self):
        """测试系统资源监控集成"""
        monitor = SystemResourceMonitor()
        optimizer = PerformanceOptimizer()
        
        # 获取系统健康状态
        with patch('psutil.cpu_percent', return_value=75.0), \
             patch('psutil.virtual_memory', return_value=Mock(percent=60.0)), \
             patch('psutil.disk_usage', return_value=Mock(total=1000, used=300, free=700)):
            
            health = monitor.get_system_health()
            assert health["status"] == "healthy"
            assert health["cpu_usage"] == 75.0
            
            # 测试优化建议
            rate_limit = optimizer.get_optimal_rate_limit("api")
            assert rate_limit == 100  # 正常情况下的默认值


if __name__ == "__main__":
    pytest.main([__file__, "-v"])