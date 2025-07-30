# 后端代码文档

本文档详细描述了AllRoundSubscription项目后端的文件结构和各个模块的功能。

## 项目结构

后端采用模块化和分层设计，主要包括以下几个部分：

- **api**: API路由和接口处理
- **core**: 核心配置和功能
- **models**: 数据库模型
- **schemas**: 数据校验和序列化
- **services**: 业务逻辑服务
- **db**: 数据库连接和管理
- **tasks**: 后台任务

## 主要文件和模块说明

### 主入口

#### `main.py`
FastAPI应用程序的主入口。

**主要功能**:
- 配置和启动FastAPI应用
- 注册中间件和路由
- 设置异常处理器
- 管理应用生命周期
- 配置日志记录

**主要函数**:
- `cleanup_stale_logs()`: 清理旧日志文件，防止文件锁问题
- `create_tables()`: 创建数据库表
- `lifespan()`: 应用生命周期管理，启动和关闭时的操作
- `business_exception_handler()`: 业务异常处理器
- `global_exception_handler()`: 全局异常处理器
- `health_check()`: 健康检查接口

### API 模块

#### `api/v1/router.py`
API V1版本的主路由配置。

**主要功能**:
- 注册所有API路由
- 提供健康检查接口

#### `api/v1/auth.py`
认证相关的API接口。

**主要功能**:
- 用户登录
- 令牌刷新
- 微信登录

#### `api/v1/users.py`
用户管理相关的API接口。

**主要功能**:
- 获取用户信息
- 更新用户资料
- 用户管理操作

#### `api/v1/subscriptions.py`
订阅管理相关的API接口。

**主要功能**:
- 创建订阅
- 取消订阅
- 获取用户订阅列表
- 批量订阅操作

#### `api/v1/content.py`
内容管理相关的API接口。

**主要功能**:
- 获取文章内容
- 内容展示和管理

#### `api/v1/search.py`
搜索相关的API接口。

**主要功能**:
- 搜索博主账号
- 平台特定搜索
- 获取支持的平台列表
- 获取搜索统计信息
- 根据ID获取账号信息

**主要函数**:
- `search_accounts()`: 搜索博主账号
- `search_accounts_by_platform()`: 在指定平台搜索博主
- `get_supported_platforms()`: 获取支持的平台列表
- `get_search_statistics()`: 获取搜索统计信息
- `get_account_by_platform_id()`: 根据平台账号ID获取账号信息
- `get_account_by_id()`: 根据账号ID获取账号信息

#### `api/v1/monitoring.py`
监控相关的API接口。

**主要功能**:
- 系统状态监控
- 性能指标收集

#### `api/v1/push_notifications.py`
推送通知相关的API接口。

**主要功能**:
- 发送推送通知
- 管理推送记录

### Core 模块

#### `core/config.py`
应用配置管理。

**主要类**:
- `Settings`: 应用配置类，集中管理所有配置项

**主要功能**:
- 基本项目信息配置
- 服务器配置
- 数据库配置
- Redis配置
- JWT配置
- 微信配置
- 日志配置
- Celery配置
- 监控配置

#### `core/logging.py`
日志配置和管理。

**主要功能**:
- 设置日志格式和输出
- 提供日志记录器

#### `core/exceptions.py`
异常定义和处理。

**主要类**:
- `BusinessException`: 业务异常基类
- `ErrorCode`: 错误码枚举

**主要功能**:
- 定义业务异常类型
- 提供错误码和错误消息

#### `core/middleware.py`
中间件定义和配置。

**主要类**:
- `LoggingMiddleware`: 日志中间件
- `RateLimitMiddleware`: 速率限制中间件
- `SecurityHeadersMiddleware`: 安全头部中间件

#### `core/deps.py`
依赖项定义。

**主要函数**:
- `get_current_user()`: 获取当前用户的依赖函数
- `get_optional_user()`: 获取可选当前用户的依赖函数

#### `core/monitoring.py`
监控和指标收集。

**主要类**:
- `MetricsCollector`: 指标收集器

**主要功能**:
- 系统指标收集
- 性能监控

### Models 模块

#### `models/base.py`
模型基类定义。

**主要类**:
- `BaseModel`: 所有数据库模型的基类

**主要功能**:
- 提供通用字段和功能(id, created_at, updated_at等)

#### `models/user.py`
用户相关模型。

**主要类**:
- `User`: 用户模型
- `MembershipLevel`: 会员等级枚举

**主要功能**:
- 用户数据结构定义
- 会员等级和权限逻辑
- 用户订阅限制计算

#### `models/account.py`
账号相关模型。

**主要类**:
- `Account`: 博主账号模型
- `Platform`: 平台类型枚举

**主要功能**:
- 博主账号数据结构定义
- 平台类型定义

#### `models/article.py`
文章相关模型。

**主要类**:
- `Article`: 文章模型

**主要功能**:
- 文章数据结构定义

#### `models/subscription.py`
订阅相关模型。

**主要类**:
- `Subscription`: 订阅关系模型

**主要功能**:
- 用户与博主账号的订阅关系

#### `models/push_record.py`
推送记录相关模型。

**主要类**:
- `PushRecord`: 推送记录模型
- `PushStatus`: 推送状态枚举

**主要功能**:
- 推送记录数据结构定义
- 推送状态跟踪

### Schemas 模块

#### `schemas/common.py`
通用响应模式定义。

**主要类**:
- `DataResponse`: 数据响应模式
- `PaginatedResponse`: 分页响应模式

#### `schemas/user.py`
用户相关的请求和响应模式。

**主要类**:
- `UserCreate`: 用户创建请求
- `UserUpdate`: 用户更新请求
- `UserResponse`: 用户响应

#### `schemas/auth.py`
认证相关的请求和响应模式。

**主要类**:
- `Token`: 令牌响应
- `TokenData`: 令牌数据
- `LoginRequest`: 登录请求

#### `schemas/subscription.py`
订阅相关的请求和响应模式。

**主要类**:
- `SubscriptionCreate`: 订阅创建请求
- `SubscriptionResponse`: 订阅响应
- `SubscriptionWithAccount`: 带账号信息的订阅响应
- `SubscriptionList`: 订阅列表查询参数
- `BatchSubscriptionCreate`: 批量订阅创建请求

#### `schemas/article.py`
文章相关的请求和响应模式。

**主要类**:
- `ArticleCreate`: 文章创建请求
- `ArticleResponse`: 文章响应
- `ArticleList`: 文章列表查询参数

#### `schemas/search.py`
搜索相关的请求和响应模式。

**主要类**:
- `SearchRequest`: 搜索请求
- `SearchResponse`: 搜索响应
- `PlatformSearchRequest`: 平台搜索请求
- `SupportedPlatformsResponse`: 支持的平台响应

### Services 模块

#### `services/auth.py`
认证相关服务。

**主要类**:
- `AuthService`: 认证服务类

**主要功能**:
- 用户认证
- JWT令牌生成和验证
- 微信登录处理

#### `services/subscription.py`
订阅管理服务。

**主要类**:
- `SubscriptionService`: 订阅服务类

**主要功能**:
- 创建和删除订阅
- 获取用户订阅列表
- 批量订阅处理
- 订阅状态检查

**主要函数**:
- `create_subscription()`: 创建订阅关系
- `delete_subscription()`: 删除订阅关系
- `get_user_subscriptions()`: 获取用户订阅列表
- `get_subscription_stats()`: 获取用户订阅统计信息
- `batch_create_subscriptions()`: 批量创建订阅
- `check_subscription_status()`: 检查订阅状态

#### `services/search/service.py`
搜索服务实现。

**主要类**:
- `SearchService`: 搜索服务类

**主要功能**:
- 博主账号搜索
- 平台特定搜索
- 搜索统计和信息

#### `services/search/adapters/`
各平台搜索适配器。

**主要类**:
- `WechatAdapter`: 微信搜索适配器
- `WeiboAdapter`: 微博搜索适配器
- `TwitterAdapter`: 推特搜索适配器

**主要功能**:
- 实现各平台特定的搜索逻辑
- 转换平台数据为统一格式

#### `services/search/registry.py`
搜索适配器注册管理。

**主要类**:
- `AdapterRegistry`: 适配器注册类

**主要功能**:
- 管理和注册搜索适配器
- 提供适配器查找功能

#### `services/content.py`
内容服务。

**主要类**:
- `ContentService`: 内容服务类

**主要功能**:
- 获取和管理文章内容
- 内容刷新和更新

#### `services/limits.py`
限制服务。

**主要类**:
- `LimitsService`: 限制服务类

**主要功能**:
- 检查用户订阅限制
- 检查推送限制

#### `services/push_notification.py`
推送通知服务。

**主要类**:
- `PushNotificationService`: 推送通知服务类

**主要功能**:
- 发送推送通知
- 管理推送记录

### DB 模块

#### `db/database.py`
数据库连接和会话管理。

**主要类**:
- `Base`: SQLAlchemy模型基类

**主要功能**:
- 创建数据库引擎
- 管理数据库会话
- 提供数据库依赖

**主要函数**:
- `get_db()`: 获取数据库会话的依赖函数
- `init_db()`: 初始化数据库

#### `db/redis.py`
Redis连接和缓存管理。

**主要类**:
- `CacheService`: 缓存服务类

**主要功能**:
- 管理Redis连接
- 提供缓存操作接口

### Tasks 模块

#### `tasks/base.py`
任务基础设施。

**主要功能**:
- 配置Celery应用
- 提供任务基类

#### `tasks/content.py`
内容相关任务。

**主要功能**:
- 定期内容更新任务
- 内容处理后台任务

#### `tasks/push.py`
推送相关任务。

**主要功能**:
- 推送通知后台任务
- 推送队列处理

#### `tasks/search.py`
搜索相关任务。

**主要功能**:
- 搜索索引更新任务
- 定期搜索数据同步

## 核心流程

### 用户认证流程
1. 用户通过微信授权登录
2. `auth.py`处理授权回调，验证用户信息
3. 创建或更新用户记录
4. 生成JWT令牌返回给客户端

### 订阅管理流程
1. 用户搜索或浏览账号
2. 用户发起订阅请求
3. `subscription_service.py`验证用户订阅限制
4. 创建订阅关系
5. 用户可查看和管理订阅列表

### 内容推送流程
1. 后台任务定期爬取订阅账号的新内容
2. 检测到新内容后，创建推送任务
3. 推送服务根据用户设置发送通知
4. 记录推送状态和结果

### 搜索处理流程
1. 用户输入搜索关键词
2. 搜索服务根据平台选择合适的适配器
3. 适配器执行平台特定搜索
4. 统一处理和返回搜索结果

## 配置和部署

系统支持不同的部署环境，通过环境变量和配置文件进行配置。主要配置项包括：

- 数据库连接信息
- Redis连接信息
- 日志级别和格式
- 微信应用配置
- JWT密钥和过期时间
- 监控和指标收集开关

通过Docker容器化部署，支持开发、测试和生产环境。 