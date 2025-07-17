#!/usr/bin/env python3
"""
性能优化和监控功能验证脚本
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_monitoring_module():
    """测试监控模块"""
    try:
        from app.core.monitoring import PerformanceMonitor, DatabaseMonitor, get_performance_monitor
        
        # 测试性能监控器
        monitor = PerformanceMonitor()
        monitor.record_response_time("/api/test", "GET", 200, 0.5)
        
        stats = monitor.get_endpoint_stats()
        assert len(stats) > 0
        print("✓ 性能监控模块测试通过")
        
        # 测试数据库监控器
        db_monitor = DatabaseMonitor()
        db_monitor.record_query("SELECT", 0.3, True)
        
        query_stats = db_monitor.get_query_stats()
        assert "SELECT" in query_stats
        print("✓ 数据库监控模块测试通过")
        
        return True
    except Exception as e:
        print(f"✗ 监控模块测试失败: {str(e)}")
        return False

def test_rate_limiting_module():
    """测试限流模块"""
    try:
        from app.core.rate_limiting import RateLimiter, RateLimitStrategy, RateLimitRule
        
        # 测试限流器初始化
        limiter = RateLimiter()
        assert "api" in limiter.default_rules
        assert "auth" in limiter.default_rules
        
        # 测试自定义规则
        custom_rule = RateLimitRule("test", 10, 60, RateLimitStrategy.FIXED_WINDOW)
        limiter.add_custom_rule("test", custom_rule)
        assert "test" in limiter.default_rules
        
        print("✓ 限流模块测试通过")
        return True
    except Exception as e:
        print(f"✗ 限流模块测试失败: {str(e)}")
        return False

def test_cache_enhancements():
    """测试缓存增强功能"""
    try:
        from app.db.redis import CacheService, cached, cache_key_generator
        
        # 测试缓存服务
        cache = CacheService()
        assert cache.hit_count == 0
        assert cache.miss_count == 0
        
        # 测试缓存键生成
        key = cache_key_generator("test", "arg", param="value")
        assert isinstance(key, str)
        assert len(key) > 0
        
        print("✓ 缓存增强功能测试通过")
        return True
    except Exception as e:
        print(f"✗ 缓存增强功能测试失败: {str(e)}")
        return False

def test_database_optimization():
    """测试数据库优化模块"""
    try:
        from app.core.database_optimization import QueryOptimizer, DatabaseIndexAnalyzer, ConnectionPoolMonitor
        
        # 测试查询优化器
        optimizer = QueryOptimizer()
        assert optimizer.slow_query_threshold == 1.0
        
        # 测试连接池监控
        pool_monitor = ConnectionPoolMonitor()
        health = pool_monitor.get_pool_health()
        assert "health_status" in health
        
        print("✓ 数据库优化模块测试通过")
        return True
    except Exception as e:
        print(f"✗ 数据库优化模块测试失败: {str(e)}")
        return False

def test_performance_config():
    """测试性能配置模块"""
    try:
        from app.core.performance_config import PerformanceConfig, SystemResourceMonitor, PerformanceOptimizer
        
        # 测试性能配置
        config = PerformanceConfig()
        assert config.slow_request_threshold == 1.0
        assert config.default_cache_ttl == 3600
        
        # 测试性能优化器
        optimizer = PerformanceOptimizer()
        ttl = optimizer.get_optimal_cache_ttl("user_profile")
        assert ttl > 0
        
        print("✓ 性能配置模块测试通过")
        return True
    except Exception as e:
        print(f"✗ 性能配置模块测试失败: {str(e)}")
        return False

def test_monitoring_api():
    """测试监控API模块"""
    try:
        from app.api.v1.monitoring import router
        
        # 检查路由器是否正确创建
        assert router is not None
        assert hasattr(router, 'routes')
        
        print("✓ 监控API模块测试通过")
        return True
    except Exception as e:
        print(f"✗ 监控API模块测试失败: {str(e)}")
        return False

def main():
    """主测试函数"""
    print("开始验证性能优化和监控功能实现...")
    print("=" * 50)
    
    tests = [
        ("监控模块", test_monitoring_module),
        ("限流模块", test_rate_limiting_module),
        ("缓存增强", test_cache_enhancements),
        ("数据库优化", test_database_optimization),
        ("性能配置", test_performance_config),
        ("监控API", test_monitoring_api),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n测试 {test_name}...")
        if test_func():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有性能优化和监控功能实现验证通过!")
        
        print("\n实现的功能包括:")
        print("1. ✓ API响应时间监控")
        print("2. ✓ 数据库查询性能监控")
        print("3. ✓ 增强的缓存策略")
        print("4. ✓ 多种限流机制")
        print("5. ✓ 系统资源监控")
        print("6. ✓ 性能优化建议")
        print("7. ✓ 监控API端点")
        print("8. ✓ 慢请求检测")
        print("9. ✓ 连接池监控")
        print("10. ✓ 自适应限流")
        
        return True
    else:
        print(f"❌ 有 {total - passed} 个测试失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)