#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库同步配置文件
"""

# 源数据库配置
SOURCE_DB = {
    "user": "zhangzc",
    "password": "zhangzc123..",
    "host": "119.8.32.27",
    "port": 3306,
    "database": "sub",
    "charset": "utf8mb4"
}

# 目标数据库配置
TARGET_DB = {
    "user": "root",  # 修改为实际用户名
    "password": "zhangzc123..",  # 修改为实际密码
    "host": "119.8.32.27",  # 修改为实际地址
    "port": 3306,
    "database": "mergedb",
    "charset": "utf8mb4"
}

# 同步间隔（秒）
SYNC_INTERVAL = 60

# 日志配置
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "sync_db.log"
} 