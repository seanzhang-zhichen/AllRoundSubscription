#!/usr/bin/env python3
"""
测试修复后的应用启动
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

async def test_database_connection():
    """测试数据库连接"""
    try:
        from app.db.database import engine
        from sqlalchemy import text
        
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✅ 数据库连接正常")
            return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

async def test_redis_connection():
    """测试Redis连接"""
    try:
        from app.db.redis import get_redis
        
        redis_client = await get_redis()
        if redis_client is None:
            print("⚠️  Redis未配置或不可用（这是正常的）")
            return True
        
        await redis_client.ping()
        print("✅ Redis连接正常")
        return True
    except Exception as e:
        print(f"⚠️  Redis连接失败（这是正常的）: {e}")
        return True  # Redis失败不影响应用启动

async def test_monitoring():
    """测试监控功能"""
    try:
        from app.core.monitoring import metrics_collector
        
        await metrics_collector.collect_all_metrics()
        print("✅ 监控指标收集正常")
        return True
    except Exception as e:
        print(f"❌ 监控指标收集失败: {e}")
        return False

async def test_logging():
    """测试日志功能"""
    try:
        from app.core.logging import setup_logging, get_logger
        
        # 测试日志设置
        setup_logging(log_level="INFO", log_file="logs/test.log")
        logger = get_logger("test")
        logger.info("测试日志消息")
        print("✅ 日志功能正常")
        return True
    except Exception as e:
        print(f"❌ 日志功能失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("🔧 开始测试修复后的应用...")
    print()
    
    tests = [
        ("数据库连接", test_database_connection),
        ("Redis连接", test_redis_connection),
        ("监控功能", test_monitoring),
        ("日志功能", test_logging),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"测试 {test_name}...")
        try:
            result = await test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            results.append(False)
        print()
    
    # 总结
    passed = sum(results)
    total = len(results)
    
    print("=" * 50)
    print(f"测试完成: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！应用应该可以正常启动了。")
        return 0
    else:
        print("⚠️  部分测试失败，但应用仍可能正常启动。")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)