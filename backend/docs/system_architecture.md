# 系统架构文档

本文档包含多平台内容聚合系统的架构设计和操作逻辑图。

## 1. 系统功能模块图

以下图表展示了系统的主要功能模块及其关系：

```mermaid
graph TD
    %% 主要用户流程
    U["用户/客户端"] --> |"登录/认证"| A["认证系统"]
    U --> |"获取内容"| C["内容系统"]
    U --> |"搜索博主"| S["搜索系统"]
    U --> |"管理订阅"| SUB["订阅系统"]
    U --> |"管理用户信息"| UM["用户管理"]
    U --> |"管理会员"| M["会员系统"]
    U --> |"接收推送"| P["推送系统"]
    
    %% 认证系统
    A --> |"微信登录"| A1["wechat_login"]
    A --> |"刷新令牌"| A2["refresh_token"]
    A --> |"登出"| A3["logout"]
    A --> |"验证状态"| A4["verify_token/auth_status"]
    
    %% 用户管理系统
    UM --> |"获取用户档案"| U1["get_user_profile"]
    UM --> |"更新用户档案"| U2["update_user_profile"]
    UM --> |"获取用户限制"| U3["get_user_limits"]
    UM --> |"删除账户"| U4["delete_user_account"]
    
    %% 会员系统
    M --> |"获取会员信息"| M1["get_membership_info"]
    M --> |"升级会员"| M2["upgrade_membership"]
    
    %% 订阅系统
    SUB --> |"获取订阅列表"| SUB1["get_user_subscriptions"]
    SUB --> |"创建订阅"| SUB2["create_subscription"]
    SUB --> |"批量创建订阅"| SUB3["batch_create_subscriptions"]
    SUB --> |"取消订阅"| SUB4["delete_subscription"]
    SUB --> |"获取订阅状态"| SUB5["check_subscription_status"]
    SUB --> |"获取订阅统计"| SUB6["get_subscription_stats"]
    
    %% 内容系统
    C --> |"获取动态流"| C1["get_user_feed"]
    C --> |"获取文章详情"| C2["get_article_detail"]
    C --> |"获取账号文章"| C3["get_articles_by_account"]
    C --> |"获取内容统计"| C4["get_content_stats"]
    C --> |"刷新内容"| C5["refresh_user_content"]
    C --> |"标记文章已读"| C6["mark_article_as_read"]
    C --> |"收藏/取消收藏"| C7["favorite/unfavorite_article"]
    C --> |"搜索文章"| C8["search_articles"]
    
    %% 搜索系统
    S --> |"搜索博主账号"| S1["search_accounts"]
    S --> |"平台搜索博主"| S2["search_accounts_by_platform"]
    S --> |"获取平台列表"| S3["get_supported_platforms"]
    S --> |"获取账号信息"| S4["get_account_by_id/platform_id"]
    S --> |"获取搜索统计"| S5["get_search_statistics"]
    
    %% 推送系统
    P --> |"获取推送设置"| P1["推送设置"]
    P --> |"触发推送"| P2["推送通知"]
    
    %% 主要数据流
    DB[(数据库)] --> A
    DB --> UM
    DB --> M
    DB --> SUB
    DB --> C
    DB --> S
    DB --> P
    
    %% 内部服务交互
    SUB -- "更新订阅关系" --> C
    C -- "内容更新" --> P
    S -- "账号信息" --> SUB
    A -- "用户认证" --> UM
    M -- "会员权限" --> SUB
    M -- "会员权限" --> C
```

## 2. 前后端交互架构图

以下图表展示了系统的前后端交互架构和内部组件关系：

```mermaid
graph TD
    %% 前端与后端交互
    classDef frontend fill:#f9d0c4,stroke:#333,stroke-width:1px
    classDef backend fill:#c4e3f9,stroke:#333,stroke-width:1px
    classDef database fill:#d5f9c4,stroke:#333,stroke-width:1px
    classDef service fill:#e3c4f9,stroke:#333,stroke-width:1px
    
    %% 前端组件
    FE["前端应用"] -->|HTTP请求| BE["后端API"]
    FE -->|"登录"| FE_Auth["身份验证"]
    FE -->|"浏览文章"| FE_Content["内容模块"]
    FE -->|"搜索"| FE_Search["搜索模块"]
    FE -->|"订阅管理"| FE_Sub["订阅模块"]
    FE -->|"用户中心"| FE_User["用户模块"]
    
    %% 后端API路由
    BE --> BE_Auth["认证路由(/auth)"]
    BE --> BE_User["用户路由(/users)"]
    BE --> BE_Sub["订阅路由(/subscriptions)"]
    BE --> BE_Content["内容路由(/content)"]
    BE --> BE_Search["搜索路由(/search)"]
    BE --> BE_Push["推送路由(/push-notifications)"]
    BE --> BE_Monitor["监控路由(/monitoring)"]
    
    %% 用户认证流程
    BE_Auth -->|"微信登录"| SVC_Auth["认证服务"]
    SVC_Auth -->|"验证code"| WechatAPI["微信API"]
    SVC_Auth -->|"生成令牌"| TokenGen["令牌生成器"]
    SVC_Auth -->|"存储用户信息"| DB_User[(用户数据)]
    
    %% 内容流程
    BE_Content -->|"获取文章"| SVC_Content["内容服务"]
    SVC_Content -->|"读取订阅内容"| DB_Article[(文章数据)]
    SVC_Content -->|"读取订阅关系"| DB_Sub[(订阅数据)]
    SVC_Content -->|"刷新内容"| SVC_Refresh["刷新服务"]
    SVC_Refresh -->|"抓取新内容"| PlatformAPI["平台API"]
    
    %% 搜索流程
    BE_Search -->|"搜索请求"| SVC_Search["搜索服务"]
    SVC_Search -->|"聚合搜索"| SearchAggregator["搜索聚合器"]
    SearchAggregator -->|"微信平台搜索"| WechatAdapter["微信适配器"]
    SearchAggregator -->|"微博平台搜索"| WeiboAdapter["微博适配器"]
    SearchAggregator -->|"推特平台搜索"| TwitterAdapter["推特适配器"]
    SVC_Search -->|"存取缓存"| SearchCache["搜索缓存"]
    
    %% 订阅流程
    BE_Sub -->|"管理订阅"| SVC_Sub["订阅服务"]
    SVC_Sub -->|"检查限制"| SVC_Limits["限制服务"]
    SVC_Sub -->|"读写订阅数据"| DB_Sub
    SVC_Limits -->|"检查会员等级"| DB_User
    
    %% 推送流程
    BE_Push -->|"发送推送"| SVC_Push["推送服务"]
    SVC_Push -->|"推送队列"| PushQueue["推送队列"]
    SVC_Push -->|"推送记录"| DB_Push[(推送记录)]
    PushQueue -->|"发送通知"| WechatAPI
    
    %% 数据库关系
    DB_Main[(主数据库)] --> DB_User
    DB_Main --> DB_Article
    DB_Main --> DB_Sub
    DB_Main --> DB_Push
    DB_Main --> DB_Account[(账号数据)]
    
    %% 缓存系统
    Redis[(Redis缓存)] --> SearchCache
    Redis --> TokenCache["令牌缓存"]
    Redis --> ContentCache["内容缓存"]
    
    %% 监控系统
    BE_Monitor -->|"收集指标"| Metrics["指标收集器"]
    Metrics -->|"存储指标"| Prometheus[(Prometheus)]
    
    %% 样式应用
    class FE,FE_Auth,FE_Content,FE_Search,FE_Sub,FE_User frontend
    class BE,BE_Auth,BE_User,BE_Sub,BE_Content,BE_Search,BE_Push,BE_Monitor backend
    class DB_Main,DB_User,DB_Article,DB_Sub,DB_Push,DB_Account,Redis,Prometheus database
    class SVC_Auth,SVC_Content,SVC_Search,SearchAggregator,WechatAdapter,WeiboAdapter,TwitterAdapter,SVC_Sub,SVC_Limits,SVC_Push,SVC_Refresh service
```

## 3. 用户操作流程图

以下图表展示了用户从登录到使用各项功能的完整流程：

```mermaid
sequenceDiagram
    actor 用户
    participant 前端 as 前端应用
    participant 认证API as 认证API
    participant 搜索API as 搜索API
    participant 订阅API as 订阅API
    participant 内容API as 内容API
    participant 推送API as 推送API
    participant 用户API as 用户API
    participant DB as 数据库
    participant 缓存 as 缓存系统
    
    %% 登录流程
    用户->>前端: 打开应用
    前端->>认证API: 微信登录请求(/auth/login)
    认证API->>DB: 验证/创建用户
    认证API->>前端: 返回令牌和用户信息
    
    %% 浏览内容流程
    用户->>前端: 浏览动态流
    前端->>内容API: 请求动态流(/content/feed)
    内容API->>缓存: 尝试获取缓存内容
    alt 缓存命中
        缓存->>内容API: 返回缓存内容
    else 缓存未命中
        内容API->>DB: 查询订阅内容
        DB->>内容API: 返回订阅内容
        内容API->>缓存: 存储到缓存
    end
    内容API->>前端: 返回动态流内容
    
    %% 搜索博主流程
    用户->>前端: 搜索博主
    前端->>搜索API: 发送搜索请求(/search/accounts)
    搜索API->>缓存: 尝试获取缓存结果
    alt 缓存命中
        缓存->>搜索API: 返回缓存结果
    else 缓存未命中
        搜索API->>搜索API: 聚合多平台搜索
        搜索API->>缓存: 存储搜索结果
    end
    搜索API->>前端: 返回搜索结果
    
    %% 订阅流程
    用户->>前端: 订阅博主
    前端->>订阅API: 发送订阅请求(/subscriptions)
    订阅API->>用户API: 检查用户订阅限制
    alt 超出限制
        用户API->>订阅API: 返回限制错误
        订阅API->>前端: 返回限制错误
    else 限制内
        订阅API->>DB: 创建订阅关系
        DB->>订阅API: 返回订阅结果
        订阅API->>内容API: 触发内容刷新
        内容API->>DB: 获取最新内容
        订阅API->>前端: 返回订阅成功
    end
    
    %% 查看文章详情
    用户->>前端: 点击文章
    前端->>内容API: 获取文章详情(/content/articles/{id})
    内容API->>DB: 查询文章详情
    DB->>内容API: 返回文章详情
    内容API->>前端: 返回文章内容
    
    %% 用户收藏文章
    用户->>前端: 收藏文章
    前端->>内容API: 发送收藏请求(/content/articles/{id}/favorite)
    内容API->>DB: 记录收藏关系
    DB->>内容API: 确认收藏成功
    内容API->>前端: 返回收藏结果
    
    %% 接收推送通知
    推送API-->>用户: 新内容推送通知
    用户->>前端: 点击推送通知
    前端->>内容API: 获取推送内容
    内容API->>前端: 返回推送内容
    
    %% 管理用户信息
    用户->>前端: 打开个人中心
    前端->>用户API: 获取用户档案(/users/profile)
    用户API->>DB: 查询用户信息
    DB->>用户API: 返回用户信息
    用户API->>前端: 返回用户档案
    
    %% 会员升级
    用户->>前端: 升级会员
    前端->>用户API: 发送升级请求(/users/membership/upgrade)
    用户API->>DB: 更新会员信息
    DB->>用户API: 确认更新
    用户API->>前端: 返回更新结果
    
    %% 刷新内容
    用户->>前端: 下拉刷新
    前端->>内容API: 请求刷新内容(/content/refresh)
    内容API->>DB: 更新内容数据
    DB->>内容API: 确认更新
    内容API->>缓存: 更新内容缓存
    内容API->>前端: 返回最新内容
```

## 4. 系统概述

该系统是一个多平台内容聚合应用，主要功能包括：

1. **用户认证系统**：通过微信小程序登录，生成JWT令牌进行身份验证
2. **用户管理系统**：管理用户档案、会员等级和使用限制
3. **搜索系统**：支持跨平台搜索博主账号，包括微信、微博、Twitter等
4. **订阅系统**：管理用户对不同平台博主的订阅关系
5. **内容系统**：聚合展示用户订阅博主的文章内容，支持阅读、收藏等操作
6. **推送系统**：向用户推送订阅博主的最新内容更新

系统采用前后端分离架构，后端基于FastAPI框架，使用SQLAlchemy进行数据库操作，Redis进行缓存，并集成了日志、监控和性能优化等功能。前端基于Vue.js开发，实现了响应式用户界面。

整个系统的核心流程是：用户登录 -> 搜索博主 -> 订阅博主 -> 浏览聚合内容 -> 接收内容更新推送，同时还支持会员升级来提升使用限制。 