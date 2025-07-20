# 多平台内容聚合器 - 后端服务

基于 FastAPI 构建的高性能内容聚合后端服务，支持多平台内容抓取、用户管理、订阅推送等功能。

## 技术栈

- **Web框架**: FastAPI 0.104.1
- **异步运行时**: Uvicorn
- **数据库**: PostgreSQL (生产) / SQLite (开发)
- **ORM**: SQLAlchemy 2.0 + Alembic
- **缓存**: Redis
- **任务队列**: Celery
- **认证**: JWT (python-jose)
- **密码加密**: Passlib + bcrypt
- **HTTP客户端**: httpx
- **日志系统**: Loguru
- **测试框架**: pytest + pytest-asyncio

## 项目结构

```
backend/
├── app/                    # 主应用目录
│   ├── api/               # API路由
│   ├── core/              # 核心配置
│   ├── db/                # 数据库连接和会话
│   ├── models/            # SQLAlchemy模型
│   ├── schemas/           # Pydantic模式
│   ├── services/          # 业务逻辑服务
│   ├── tasks/             # Celery异步任务
│   ├── celery_app.py      # Celery应用配置
│   └── main.py            # FastAPI应用入口
├── config/                # 配置文件
├── scripts/               # 脚本工具
├── tests/                 # 测试文件
├── docker-compose.yml     # 开发环境Docker配置
├── docker-compose.prod.yml # 生产环境Docker配置
├── Dockerfile             # Docker镜像构建
├── requirements.txt       # Python依赖
└── .env.example          # 环境变量示例
```

## 快速开始

### 环境要求

- Python 3.8+
- Docker & Docker Compose (推荐)
- PostgreSQL (生产环境)
- Redis

### 使用Docker开发 (推荐)

1. 克隆项目并进入后端目录
```bash
cd backend
```

2. 复制环境变量文件
```bash
copy .env.example .env
```

3. 启动所有服务
```bash
docker-compose up -d
```

4. 查看服务状态
```bash
docker-compose ps
```

服务将在以下端口启动：
- API服务: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### 本地开发

1. 安装依赖
```bash
pip install -r requirements.txt
```

2. 配置环境变量
```bash
copy .env.example .env
# 编辑 .env 文件，配置数据库等信息
```

3. 启动Redis (如果本地没有)
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

4. 运行数据库迁移
```bash
alembic upgrade head
```

5. 启动API服务

**方法一：使用uvicorn命令**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**方法二：直接运行Python文件**
```bash
python -m app.main
```

**方法三：使用python命令运行main.py**
```bash
cd app
python main.py
```

6. 启动Celery Worker (新终端)
```bash
celery -A app.celery_app worker --loglevel=info
```

7. 启动Celery Beat (新终端)
```bash
celery -A app.celery_app beat --loglevel=info
```

## API文档

启动服务后，可以访问以下地址查看API文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 主要功能

### 用户管理
- 用户注册/登录
- JWT认证
- 用户权限管理

### 内容聚合
- 多平台内容抓取
- 内容去重和标准化
- 内容分类和标签

### 订阅管理
- 用户订阅管理
- 推送通知
- 微信推送集成

### 性能监控
- 系统性能监控
- API响应时间统计
- 错误日志记录

## 测试

运行所有测试：
```bash
pytest
```

运行特定测试文件：
```bash
pytest tests/test_api.py
```

生成测试覆盖率报告：
```bash
pytest --cov=app tests/
```

## 部署

### 生产环境部署

1. 使用生产环境Docker配置
```bash
docker-compose -f docker-compose.prod.yml up -d
```

2. 或者手动部署
```bash
pip install -r requirements-prod.txt
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### 环境变量配置

关键环境变量说明：

- `DATABASE_URL`: 数据库连接字符串
- `REDIS_URL`: Redis连接字符串
- `SECRET_KEY`: JWT密钥 (生产环境必须更改)
- `WECHAT_APP_ID`: 微信小程序ID
- `WECHAT_APP_SECRET`: 微信小程序密钥

## 开发指南

### 代码规范

项目使用以下工具保证代码质量：

- **Black**: 代码格式化
- **isort**: 导入排序
- **pytest**: 单元测试

运行代码格式化：
```bash
black app/
isort app/
```

### 数据库迁移

创建新的迁移文件：
```bash
alembic revision --autogenerate -m "描述变更"
```

应用迁移：
```bash
alembic upgrade head
```

回滚迁移：
```bash
alembic downgrade -1
```

## 日志系统

项目使用 **Loguru** 作为日志库，采用简化配置，易于使用和维护。

### 基本使用

```python
from app.core.logging import setup_logging, get_logger

# 设置日志（通常在应用启动时）
setup_logging(
    log_level="INFO",              # 日志级别
    log_file="logs/app.log"        # 可选的日志文件
)

# 获取logger实例
logger = get_logger(__name__)

# 基本日志记录
logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")

# 带上下文数据的日志
logger.bind(user_id=123, action="login").info("用户登录成功")
```

### 异常处理

```python
try:
    # 一些可能出错的代码
    pass
except Exception as e:
    logger.exception("发生异常")  # 自动包含堆栈跟踪
    logger.error("错误详情: {}", str(e))
```

### 日志格式

- **控制台输出**: `2025-07-18 17:21:29 | INFO | module:function:line | 日志消息`
- **文件输出**: `2025-07-18 17:21:29.123 | INFO | module:function:line | 日志消息`
- **自动轮转**: 文件大小达到10MB时自动轮转，保留7天的日志文件

### 环境变量配置

```bash
LOG_LEVEL=INFO                    # 日志级别
LOG_FILE=/app/logs/app.log       # 日志文件路径
```

详细使用说明请参考 [LOGGING_USAGE.md](LOGGING_USAGE.md)

## 监控和日志

- 应用日志存储在容器内的 `/app/logs/` 目录
- 使用Loguru提供简洁易读的日志格式
- 集成Prometheus性能监控和错误追踪
- 自动日志轮转和文件管理
- 支持控制台和文件双重输出

## 安全

- JWT token认证
- 密码bcrypt加密
- SQL注入防护
- CORS配置
- 请求频率限制

详细安全审计报告请查看 `SECURITY_AUDIT_REPORT.md`

## 贡献

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证

[添加许可证信息]

## 联系方式

[添加联系方式]