# 项目结构文档

## 目录结构概览

后端项目采用模块化设计，目录结构清晰，各模块职责明确。以下是主要目录结构和说明：

```
backend/
├── app/                        # 主应用程序目录
│   ├── __init__.py             # 初始化文件
│   ├── api/                    # API接口目录
│   │   ├── __init__.py
│   │   └── v1/                 # V1版本API接口
│   │       ├── __init__.py
│   │       ├── auth.py         # 认证接口
│   │       ├── content.py      # 内容接口
│   │       ├── content_detection.py  # 内容检测接口
│   │       ├── membership.py   # 会员接口
│   │       ├── monitoring.py   # 监控接口
│   │       ├── push_notifications.py # 推送通知接口
│   │       ├── router.py       # 路由配置
│   │       ├── search.py       # 搜索接口
│   │       ├── subscriptions.py # 订阅接口
│   │       └── users.py        # 用户接口
│   ├── celery_app.py           # Celery应用配置
│   ├── core/                   # 核心功能模块
│   │   ├── __init__.py
│   │   ├── alerts.py           # 告警功能
│   │   ├── config.py           # 配置管理
│   │   ├── database_optimization.py # 数据库优化
│   │   ├── deps.py             # 依赖项管理
│   │   ├── exceptions.py       # 异常定义
│   │   ├── logging.py          # 日志配置
│   │   ├── middleware.py       # 中间件
│   │   ├── monitoring.py       # 监控功能
│   │   ├── performance_config.py # 性能配置
│   │   ├── permissions.py      # 权限控制
│   │   ├── rate_limiting.py    # 速率限制
│   │   └── security.py         # 安全相关
│   ├── db/                     # 数据库相关
│   │   ├── __init__.py
│   │   ├── database.py         # 数据库连接
│   │   ├── migrations.py       # 数据迁移
│   │   └── redis.py            # Redis管理
│   ├── main.py                 # 应用入口
│   ├── models/                 # 数据模型
│   │   ├── __init__.py
│   │   ├── account.py          # 账号模型
│   │   ├── article.py          # 文章模型
│   │   ├── base.py             # 基础模型
│   │   ├── push_record.py      # 推送记录模型
│   │   ├── subscription.py     # 订阅模型
│   │   └── user.py             # 用户模型
│   ├── schemas/                # 数据校验模式
│   │   ├── __init__.py
│   │   ├── account.py          # 账号模式
│   │   ├── article.py          # 文章模式
│   │   ├── auth.py             # 认证模式
│   │   ├── common.py           # 通用模式
│   │   ├── limits.py           # 限制模式
│   │   ├── push_record.py      # 推送记录模式
│   │   ├── search.py           # 搜索模式
│   │   ├── subscription.py     # 订阅模式
│   │   └── user.py             # 用户模式
│   ├── services/               # 业务服务
│   │   ├── __init__.py
│   │   ├── auth.py             # 认证服务
│   │   ├── content.py          # 内容服务
│   │   ├── content_detection.py # 内容检测服务
│   │   ├── image.py            # 图片服务
│   │   ├── limits.py           # 限制服务
│   │   ├── membership.py       # 会员服务
│   │   ├── platform.py         # 平台服务
│   │   ├── push_notification.py # 推送通知服务
│   │   ├── push_queue.py       # 推送队列服务
│   │   ├── push_statistics.py  # 推送统计服务
│   │   ├── refresh.py          # 刷新服务
│   │   ├── search/             # 搜索服务
│   │   │   ├── __init__.py
│   │   │   ├── adapters/       # 搜索适配器
│   │   │   │   ├── __init__.py
│   │   │   │   ├── mock.py     # 模拟适配器
│   │   │   │   ├── twitter.py  # 推特适配器
│   │   │   │   ├── wechat.py   # 微信适配器
│   │   │   │   └── weibo.py    # 微博适配器
│   │   │   ├── aggregator.py   # 搜索聚合器
│   │   │   ├── base.py         # 基础搜索类
│   │   │   ├── cache.py        # 搜索缓存
│   │   │   ├── exceptions.py   # 搜索异常
│   │   │   ├── registry.py     # 适配器注册
│   │   │   └── service.py      # 搜索服务实现
│   │   ├── subscription.py     # 订阅服务
│   │   ├── user.py             # 用户服务
│   │   └── wechat.py           # 微信服务
│   └── tasks/                  # 后台任务
│       ├── __init__.py
│       ├── base.py             # 任务基类
│       ├── content.py          # 内容任务
│       ├── push.py             # 推送任务
│       └── search.py           # 搜索任务
├── config/                     # 配置文件
│   ├── grafana/                # Grafana配置
│   │   ├── dashboards/         # 仪表盘配置
│   │   │   ├── content-aggregator-dashboard.json
│   │   │   └── dashboard.yml
│   │   └── datasources/        # 数据源配置
│   │       └── prometheus.yml
│   ├── nginx.conf              # Nginx配置
│   ├── prometheus.yml          # Prometheus配置
│   └── sentinel.conf           # Redis Sentinel配置
├── docker-compose.prod.yml     # 生产环境Docker编排
├── docker-compose.yml          # 开发环境Docker编排
├── Dockerfile                  # 开发环境Docker构建
├── Dockerfile.prod             # 生产环境Docker构建
├── docs/                       # 文档目录
│   ├── api_routes.md           # API路由文档
│   ├── data_models.md          # 数据模型文档
│   ├── README.md               # 文档主页
│   ├── system_architecture.md  # 系统架构文档
│   └── system_flowcharts.md    # 系统流程图
├── requirements-prod.txt       # 生产环境依赖
├── requirements.txt            # 开发环境依赖
├── scripts/                    # 脚本目录
│   ├── backup.sh               # 备份脚本
│   ├── deploy.sh               # 部署脚本
│   ├── entrypoint.sh           # Docker入口脚本
│   ├── init-db.sql             # 数据库初始化脚本
│   ├── migrate_db.py           # 数据库迁移脚本
│   ├── start-dev.py            # 开发环境启动脚本
│   └── verify-setup.py         # 环境验证脚本
└── tests/                      # 测试目录
    ├── __init__.py
    ├── conftest.py             # 测试配置
    ├── test_auth.py            # 认证测试
    ├── test_auth_api.py        # 认证API测试
    ├── test_content_detection.py # 内容检测测试
    ├── test_content_display.py # 内容显示测试
    ├── test_content_service.py # 内容服务测试
    ├── test_e2e_comprehensive.py # 综合端到端测试
    ├── test_e2e_integration.py # 集成端到端测试
    ├── test_infrastructure.py  # 基础设施测试
    ├── test_limits.py          # 限制功能测试
    ├── test_membership.py      # 会员功能测试
    ├── test_models.py          # 数据模型测试
    ├── test_performance_monitoring.py # 性能监控测试
    ├── test_permissions.py     # 权限测试
    ├── test_push_notifications.py # 推送通知测试
    ├── test_schemas.py         # 数据模式测试
    ├── test_search_aggregator.py # 搜索聚合器测试
    ├── test_search_api.py      # 搜索API测试
    ├── test_search_service.py  # 搜索服务测试
    ├── test_subscription.py    # 订阅功能测试
    ├── test_subscription_simple.py # 简单订阅测试
    ├── test_user_management.py # 用户管理测试
    └── test_wechat_push_integration.py # 微信推送集成测试
```

## 主要模块说明

### API模块 (app/api/)

API模块采用分版本管理，目前主要是v1版本。该模块负责处理HTTP请求和响应，实现RESTful API接口。所有API接口按功能分类组织，主要包括：

- **auth.py**: 用户认证和授权相关接口
- **users.py**: 用户管理相关接口
- **subscriptions.py**: 订阅管理相关接口
- **content.py**: 内容获取和管理接口
- **search.py**: 内容搜索接口
- **monitoring.py**: 系统监控接口
- **push_notifications.py**: 推送通知接口

### 核心模块 (app/core/)

核心模块包含应用的基础设施和通用功能，为其他模块提供支持：

- **config.py**: 应用配置管理
- **deps.py**: 依赖项注入管理
- **exceptions.py**: 自定义异常定义
- **middleware.py**: HTTP中间件实现
- **logging.py**: 日志配置和管理
- **monitoring.py**: 性能监控
- **security.py**: 安全相关功能
- **rate_limiting.py**: 接口限流实现

### 数据库模块 (app/db/)

数据库模块负责数据库连接和管理：

- **database.py**: SQLAlchemy数据库配置和连接
- **redis.py**: Redis连接和缓存管理
- **migrations.py**: 数据库迁移工具

### 数据模型 (app/models/)

数据模型定义数据库表结构和关系：

- **base.py**: 模型基类
- **user.py**: 用户模型
- **account.py**: 账号模型
- **article.py**: 文章模型
- **subscription.py**: 订阅关系模型
- **push_record.py**: 推送记录模型

### 数据验证 (app/schemas/)

数据验证模块使用Pydantic定义请求和响应的数据结构和验证规则：

- **common.py**: 通用数据结构
- **user.py**: 用户相关数据结构
- **article.py**: 文章相关数据结构
- **subscription.py**: 订阅相关数据结构
- **search.py**: 搜索相关数据结构
- **auth.py**: 认证相关数据结构

### 业务服务 (app/services/)

业务服务模块实现核心业务逻辑：

- **auth.py**: 认证服务
- **user.py**: 用户服务
- **subscription.py**: 订阅管理服务
- **content.py**: 内容管理服务
- **search/**: 搜索服务
  - **adapters/**: 各平台适配器
  - **service.py**: 搜索服务实现
  - **registry.py**: 适配器注册管理
- **push_notification.py**: 推送通知服务
- **limits.py**: 资源限制服务

### 后台任务 (app/tasks/)

后台任务模块使用Celery实现异步任务处理：

- **base.py**: 任务基础类
- **content.py**: 内容相关任务
- **push.py**: 推送相关任务
- **search.py**: 搜索相关任务

### 配置文件 (config/)

配置目录包含各种部署和服务配置：

- **nginx.conf**: Nginx服务器配置
- **prometheus.yml**: Prometheus监控配置
- **grafana/**: Grafana仪表盘配置
- **sentinel.conf**: Redis Sentinel配置

### 脚本 (scripts/)

脚本目录包含各种维护和部署脚本：

- **backup.sh**: 数据备份脚本
- **deploy.sh**: 部署脚本
- **entrypoint.sh**: Docker容器入口脚本
- **init-db.sql**: 数据库初始化SQL
- **migrate_db.py**: 数据库迁移脚本

### 测试 (tests/)

测试目录包含单元测试、集成测试和端到端测试：

- **conftest.py**: 测试配置和公共fixture
- **test_*_api.py**: API接口测试
- **test_*_service.py**: 服务层测试
- **test_models.py**: 数据模型测试
- **test_e2e_*.py**: 端到端测试
- **test_*_integration.py**: 集成测试

## 应用流程

1. 用户通过HTTP请求访问API接口
2. 请求经过中间件处理(认证、日志、限流等)
3. 路由到对应的API处理函数
4. API处理函数调用相应的服务层函数
5. 服务层实现业务逻辑，访问数据库或调用外部服务
6. 长时间任务通过Celery异步执行
7. 将处理结果返回给客户端

## 部署架构

该应用支持Docker容器化部署，主要包括以下组件：

- Web应用容器(FastAPI)
- 数据库容器(SQLite或PostgreSQL)
- Redis容器(缓存和消息队列)
- Celery Worker容器(后台任务处理)
- Nginx容器(反向代理)
- Prometheus和Grafana容器(监控) 