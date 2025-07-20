#!/usr/bin/env python3
"""
简化日志系统使用示例
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.logging import setup_logging, get_logger

def main():
    """主函数演示日志使用"""
    
    # 1. 设置日志 - 只需要两个参数
    setup_logging(
        log_level="INFO",
        log_file="logs/simple_example.log"
    )
    
    # 2. 获取日志器
    logger = get_logger("example")
    
    # 3. 记录基本日志
    logger.info("应用启动")
    logger.debug("这条调试信息不会显示，因为日志级别是INFO")
    logger.warning("这是一个警告")
    logger.error("这是一个错误")
    
    # 4. 记录带上下文的日志
    logger.bind(user_id=123, action="login").info("用户登录成功")
    logger.bind(
        method="GET",
        path="/api/users",
        status=200,
        duration=0.123
    ).info("API请求完成")
    
    # 5. 异常处理
    try:
        result = 10 / 0
    except Exception as e:
        logger.exception("计算异常")  # 自动包含堆栈跟踪
        logger.error("错误详情: {}", str(e))
    
    # 6. 不同模块的日志器
    api_logger = get_logger("api")
    db_logger = get_logger("database")
    
    api_logger.info("API模块日志")
    db_logger.info("数据库模块日志")
    
    logger.info("示例完成")

if __name__ == "__main__":
    # 创建日志目录
    os.makedirs("logs", exist_ok=True)
    
    print("运行简化日志示例...")
    main()
    print("完成！请查看控制台输出和 logs/simple_example.log 文件")