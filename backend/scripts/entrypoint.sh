#!/bin/bash

# 生产环境启动脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Content Aggregator API...${NC}"

# 等待数据库启动
echo -e "${YELLOW}Waiting for database...${NC}"
while ! nc -z db 5432; do
  sleep 1
done
echo -e "${GREEN}Database is ready!${NC}"

# 等待Redis启动
echo -e "${YELLOW}Waiting for Redis...${NC}"
while ! nc -z redis-master 6379; do
  sleep 1
done
echo -e "${GREEN}Redis is ready!${NC}"

# 运行数据库迁移
echo -e "${YELLOW}Running database migrations...${NC}"
alembic upgrade head
echo -e "${GREEN}Database migrations completed!${NC}"

# 创建必要的目录
mkdir -p /app/logs /app/static /app/media

# 设置权限
chmod -R 755 /app/logs /app/static /app/media

# 预热应用
echo -e "${YELLOW}Warming up application...${NC}"
python -c "
import asyncio
from app.main import app
from app.core.database import engine
from sqlalchemy import text

async def warmup():
    try:
        async with engine.begin() as conn:
            await conn.execute(text('SELECT 1'))
        print('Database connection test passed')
    except Exception as e:
        print(f'Database connection test failed: {e}')
        exit(1)

asyncio.run(warmup())
"

echo -e "${GREEN}Application warmup completed!${NC}"

# 启动应用
echo -e "${GREEN}Starting application with command: $@${NC}"
exec "$@"