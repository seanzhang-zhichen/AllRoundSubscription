# 简化日志使用指南

## 概述

项目已简化为使用loguru的最基本功能，去除了复杂的JSON格式、Prometheus集成等功能。

## 基本使用

### 1. 设置日志

```python
from app.core.logging import setup_logging

# 基本设置
setup_logging()

# 自定义设置
setup_logging(
    log_level="DEBUG",  # 日志级别
    log_file="logs/app.log"  # 可选的日志文件
)
```

### 2. 获取日志器

```python
from app.core.logging import get_logger

# 获取默认日志器
logger = get_logger()

# 获取命名日志器
logger = get_logger("my_module")
```

### 3. 记录日志

```python
# 基本日志
logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")

# 带额外数据的日志
logger.bind(user_id=123, action="login").info("用户登录")

# 异常日志
try:
    # 一些可能出错的代码
    pass
except Exception as e:
    logger.exception("发生异常")  # 自动包含堆栈跟踪
    logger.error("错误详情: {}", str(e))
```

## 日志格式

### 控制台输出格式
```
2025-07-18 17:21:29 | INFO     | module:function:line | 日志消息
```

### 文件输出格式
```
2025-07-18 17:21:29.123 | INFO     | module:function:line | 日志消息
```

## 配置选项

- `log_level`: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `log_file`: 日志文件路径，如果不指定则只输出到控制台

## 文件轮转

当指定日志文件时，自动启用文件轮转：
- 文件大小达到10MB时自动轮转
- 保留7天的日志文件
- 旧文件自动删除

## 示例

```python
from app.core.logging import setup_logging, get_logger

# 初始化日志
setup_logging(log_level="INFO", log_file="logs/app.log")

# 获取日志器
logger = get_logger(__name__)

# 记录不同类型的日志
logger.info("应用启动")
logger.bind(user_id=123).info("用户操作")
logger.warning("资源使用率较高")
logger.error("处理请求失败")
```

这样的配置既简单又实用，满足大部分应用的日志需求。