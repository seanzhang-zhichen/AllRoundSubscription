#!/usr/bin/env python3
"""
测试简化的loguru日志系统
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.logging import setup_logging, get_logger

def test_basic_logging():
    """测试基本日志功能"""
    print("=== 测试基本日志功能 ===")
    
    # 设置日志
    setup_logging(
        log_level="DEBUG",
        log_file="test_logs/test.log"
    )
    
    # 获取logger
    logger = get_logger("test_module")
    
    # 测试不同级别的日志
    logger.debug("这是一个调试消息")
    logger.info("这是一个信息消息")
    logger.warning("这是一个警告消息")
    logger.error("这是一个错误消息")
    
    # 测试带额外数据的日志
    logger.bind(user_id=123, ip="192.168.1.1").info("用户登录")
    
    print("基本日志测试完成")

def test_named_logger():
    """测试命名日志器"""
    print("\n=== 测试命名日志器 ===")
    
    logger = get_logger("api_service")
    
    # 测试API相关日志
    logger.bind(
        method="GET", 
        path="/api/v1/users", 
        status_code=200,
        response_time=0.123
    ).info("API请求处理完成")
    
    print("命名日志器测试完成")

def test_exception_logging():
    """测试异常日志"""
    print("\n=== 测试异常日志功能 ===")
    
    logger = get_logger("exception_test")
    
    try:
        # 故意引发异常
        result = 1 / 0
    except Exception as e:
        logger.exception("计算错误")
        logger.error("处理异常: {}", str(e))
    
    print("异常日志测试完成")

def test_performance_logging():
    """测试性能日志"""
    print("\n=== 测试性能日志 ===")
    
    logger = get_logger("performance")
    
    # 模拟性能指标记录
    logger.bind(
        function="user_search",
        duration=0.234,
        query="python",
        results=42
    ).info("性能指标记录")
    
    print("性能日志测试完成")

if __name__ == "__main__":
    # 创建测试日志目录
    os.makedirs("test_logs", exist_ok=True)
    
    # 运行所有测试
    test_basic_logging()
    test_named_logger()
    test_exception_logging()
    test_performance_logging()
    
    print("\n=== 所有测试完成 ===")
    print("请检查 test_logs/ 目录下的日志文件")