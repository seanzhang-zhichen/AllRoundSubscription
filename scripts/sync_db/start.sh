#!/bin/bash

# 数据库同步启动脚本

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 输出当前目录和时间
echo "当前目录: $(pwd)"
echo "开始时间: $(date)"
echo "启动数据库同步程序（每小时执行一次同步）..."

# 启动Python同步脚本
python3 sync_db.py

# 退出状态
exit $? 