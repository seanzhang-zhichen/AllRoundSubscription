# 多平台内容聚合器

一个允许用户订阅多个社交媒体平台博主内容的微信小程序后端服务。

## 项目架构

### 技术栈

**后端:**
- **FastAPI** - 高性能异步Web框架
- **SQLAlchemy** - 数据库ORM，支持SQLite/PostgreSQL
- **Redis** - 缓存和会话存储
- **Celery** - 异步任务队列
- **JWT** - 无状态认证

**前端:**
- **UniApp + Vue3** - 跨平台小程序开发
- **Pinia** - 状态管理
- **uni-ui** - UI组件库

### 项目结构

```
├── app/                    # 应用主目录
│   ├── api/               # API路由
│   │   └── v1/           # API v1版本
│   ├── core/             # 核心模块
│   │   ├── config.py     # 配置管理
│   │   ├── exceptions.py # 异常处理
│   │   ├── logging.py    # 日志配置
│   │   ├── middleware.py # 中间件
│   │   └── deps.py       # 依赖注入
│   ├── db/               # 数据库相关
│   │   ├── database.py   # 数据库连接
│   │   └── redis.py      # Redis缓存
│   ├── models/           # 数据模型
│   ├── tasks/            # Celery任务
│   ├── main.py           # 应用入口
│   └── celery_app.py     # Celery配置
├── tests/                # 测试文件
├── scripts/              # 脚本文件
├── docker-compose.yml    # Docker编排
├── Dockerfile           # Docker镜像
├── requirements.txt     # Python依赖
└── .env.example        # 环境变量模板
```

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd multi-platform-content-aggregator

# 安装Python依赖
pip install -r requirements.txt

# 复制环境变量文件
cp .env.example .env
```

### 2. 配置环境变量

编辑 `.env` 文件，配置必要的环境变量：

```env
# 数据库配置
DATABASE_URL=sqlite+aiosqlite:///./content_aggregator.db

# Redis配置
REDIS_URL=redis://localhost:6379/0

# JWT配置
SECRET_KEY=your-secret-key-change-in-production

# 微信配置
WECHAT_APP_ID=your-wechat-app-id
WECHAT_APP_SECRET=your-wechat-app-secret
```

### 3. 启动服务

#### 开发环境

```bash
# 启动FastAPI服务
python scripts/start-dev.py

# 或者直接使用uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 使用Docker

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 4. 验证安装

访问以下URL验证服务是否正常运行：

- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health
- API健康检查: http://localhost:8000/api/v1/health

## 开发指南

### 运行测试

```bash
# 运行所有测试
python -m pytest

# 运行特定测试文件
python -m pytest tests/test_infrastructure.py -v

# 运行带覆盖率的测试
python -m pytest --cov=app tests/
```

### 代码格式化

```bash
# 格式化代码
black app/ tests/

# 排序导入
isort app/ tests/
```

### 数据库迁移

```bash
# 生成迁移文件
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head
```

### Celery任务

```bash
# 启动Celery Worker
celery -A app.celery_app worker --loglevel=info

# 启动Celery Beat (定时任务)
celery -A app.celery_app beat --loglevel=info
```

## 功能特性

### 已实现功能

✅ **基础架构**
- FastAPI应用框架搭建
- SQLAlchemy数据库抽象层
- Redis缓存服务
- Celery异步任务队列
- 统一错误处理和日志记录
- 安全中间件和限流机制

### 待实现功能

🔄 **用户认证系统**
- 微信小程序登录
- JWT令牌管理
- 用户权限控制

🔄 **订阅管理**
- 博主订阅/取消订阅
- 订阅数量限制
- 会员等级管理

🔄 **内容聚合**
- 多平台内容抓取
- 内容去重和过滤
- 实时推送通知

🔄 **搜索功能**
- 多平台博主搜索
- 搜索结果缓存
- 平台筛选

## API文档

启动服务后，访问 http://localhost:8000/docs 查看完整的API文档。

### 主要接口

- `GET /health` - 健康检查
- `GET /api/v1/health` - API健康检查
- 更多接口将在后续开发中添加...

## 部署

### Docker部署

```bash
# 构建镜像
docker build -t content-aggregator .

# 使用docker-compose部署
docker-compose up -d
```

### 生产环境配置

1. 修改 `.env` 文件中的生产环境配置
2. 使用PostgreSQL替代SQLite
3. 配置Redis集群
4. 设置反向代理(Nginx)
5. 配置SSL证书

## 贡献指南

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。