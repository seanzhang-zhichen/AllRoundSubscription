# API路由映射文档

本文档列出了系统中所有的API端点及其功能描述。

## 认证API (`/api/v1/auth`)

| 端点 | 方法 | 功能描述 | 认证要求 |
|------|------|----------|----------|
| `/login` | POST | 微信小程序登录 | 否 |
| `/refresh` | POST | 刷新访问令牌 | 否 |
| `/logout` | POST | 用户登出 | 是 |
| `/status` | GET | 获取认证状态 | 是 |
| `/verify` | GET | 验证访问令牌 | 是 |
| `/me` | GET | 获取当前用户信息 | 是 |

## 用户API (`/api/v1/users`)

| 端点 | 方法 | 功能描述 | 认证要求 |
|------|------|----------|----------|
| `/profile` | GET | 获取用户档案 | 是 |
| `/profile` | PUT | 更新用户档案 | 是 |
| `/membership` | GET | 获取会员信息 | 是 |
| `/membership/upgrade` | POST | 升级会员 | 是 |
| `/limits` | GET | 获取用户限制信息 | 是 |
| `/account` | DELETE | 删除用户账户 | 是 |

## 订阅API (`/api/v1/subscriptions`)

| 端点 | 方法 | 功能描述 | 认证要求 |
|------|------|----------|----------|
| `/` | POST | 创建订阅关系 | 是 |
| `/{account_id}` | DELETE | 取消订阅 | 是 |
| `/` | GET | 获取用户订阅列表 | 是 |
| `/stats` | GET | 获取用户订阅统计信息 | 是 |
| `/batch` | POST | 批量创建订阅 | 是 |
| `/status/{account_id}` | GET | 检查订阅状态 | 是 |

## 内容API (`/api/v1/content`)

| 端点 | 方法 | 功能描述 | 认证要求 |
|------|------|----------|----------|
| `/feed` | GET | 获取用户动态流 | 是 |
| `/articles/{article_id}` | GET | 获取文章详情 | 是 |
| `/accounts/{account_id}/articles` | GET | 获取指定账号的文章列表 | 是 |
| `/stats` | GET | 获取内容统计信息 | 是 |
| `/feed/refresh` | POST | 刷新动态流缓存 | 是 |
| `/platforms` | GET | 获取支持的平台列表 | 是 |
| `/platforms/{platform}/info` | GET | 获取指定平台的详细信息 | 是 |
| `/articles/{article_id}/read` | POST | 标记文章为已读 | 是 |
| `/articles/{article_id}/favorite` | POST | 收藏文章 | 是 |
| `/articles/{article_id}/favorite` | DELETE | 取消收藏文章 | 是 |
| `/articles/{article_id}/share` | POST | 记录文章分享统计 | 是 |
| `/articles/search` | GET | 搜索文章 | 是 |
| `/articles/{article_id}/images/optimize` | POST | 优化文章图片显示 | 是 |
| `/refresh` | POST | 刷新用户内容 | 是 |
| `/refresh/status` | GET | 获取刷新状态 | 是 |
| `/accounts/{account_id}/refresh` | POST | 刷新指定账号内容 | 是 |

## 搜索API (`/api/v1/search`)

| 端点 | 方法 | 功能描述 | 认证要求 |
|------|------|----------|----------|
| `/accounts` | GET | 搜索博主账号 | 是 |
| `/platforms/{platform}/accounts` | GET | 在指定平台搜索博主 | 是 |
| `/platforms` | GET | 获取支持的平台列表 | 是 |
| `/statistics` | GET | 获取搜索统计信息 | 是 |
| `/accounts/{account_id}` | GET | 根据平台账号ID获取账号信息 | 是 |
| `/accounts/by-id/{account_id}` | GET | 根据账号ID获取账号信息 | 是 |

## 推送通知API (`/api/v1/push-notifications`)

| 端点 | 方法 | 功能描述 | 认证要求 |
|------|------|----------|----------|
| `/settings` | GET | 获取推送设置 | 是 |
| `/settings` | PUT | 更新推送设置 | 是 |
| `/history` | GET | 获取推送历史记录 | 是 |
| `/stats` | GET | 获取推送统计信息 | 是 |

## 内容检测API (`/api/v1/content-detection`)

| 端点 | 方法 | 功能描述 | 认证要求 |
|------|------|----------|----------|
| `/analyze` | POST | 分析内容数据 | 是 |
| `/keywords` | GET | 获取热门关键词 | 是 |
| `/trends` | GET | 获取内容趋势 | 是 |

## 监控API (`/api/v1/monitoring`)

| 端点 | 方法 | 功能描述 | 认证要求 |
|------|------|----------|----------|
| `/metrics` | GET | 获取系统指标 | 是 |
| `/health/detailed` | GET | 获取详细健康状态 | 是 |
| `/logs` | GET | 获取系统日志 | 是 |

## 会员API (`/api/v1/membership`)

| 端点 | 方法 | 功能描述 | 认证要求 |
|------|------|----------|----------|
| `/plans` | GET | 获取会员计划列表 | 是 |
| `/benefits` | GET | 获取会员权益 | 是 |
| `/history` | GET | 获取会员历史记录 | 是 |

## 通用响应格式

系统API响应遵循以下通用格式：

### 成功响应

```json
{
  "code": 200,
  "message": "操作成功",
  "data": { ... },  // 数据对象，可选
  "timestamp": 1609459200  // 时间戳
}
```

### 分页响应

```json
{
  "code": 200,
  "message": "获取成功",
  "data": [ ... ],  // 数据数组
  "total": 100,  // 总记录数
  "page": 1,  // 当前页码
  "page_size": 20,  // 每页大小
  "total_pages": 5,  // 总页数
  "timestamp": 1609459200  // 时间戳
}
```

### 错误响应

```json
{
  "code": 400,  // HTTP状态码
  "message": "错误信息描述",
  "timestamp": 1609459200  // 时间戳
}
``` 