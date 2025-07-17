# 文章详情页面

## 功能概述

文章详情页面 (`pages/article/detail.vue`) 提供完整的文章阅读体验，包括文章内容展示、图片优化显示、分享功能和相关文章推荐。

## 主要功能

### 1. 文章详情展示
- **文章头部信息**: 显示博主头像、名称、发布时间和平台标识
- **文章标题**: 突出显示文章标题
- **文章摘要**: 以特殊样式展示文章摘要（如果有）
- **文章正文**: 使用 rich-text 组件渲染格式化的文章内容
- **文章统计**: 显示阅读量、点赞数、评论数等统计信息

### 2. 图片优化显示和懒加载
- **智能网格布局**: 根据图片数量自动调整网格布局
  - 1张图片: 单列大图显示
  - 2张图片: 双列显示
  - 3-4张图片: 2x2网格
  - 5-9张图片: 3x3网格
- **懒加载**: 使用 `lazy-load` 属性优化图片加载性能
- **图片预览**: 点击图片可全屏预览，支持滑动查看多张图片
- **响应式设计**: 图片大小根据屏幕尺寸自适应

### 3. 分享功能
- **多种分享方式**: 
  - 分享到微信好友
  - 分享到微信朋友圈
  - 复制文章链接
- **分享统计**: 记录分享行为用于数据分析
- **错误处理**: 分享失败时显示友好提示

### 4. 相关文章推荐
- **智能推荐**: 基于同一博主的其他文章进行推荐
- **精简展示**: 显示文章缩略图、标题、博主和发布时间
- **快速导航**: 点击推荐文章可直接跳转到对应详情页

### 5. 交互功能
- **收藏功能**: 支持收藏/取消收藏文章
- **查看原文**: 在内置浏览器中打开原文链接
- **返回导航**: 支持返回上一页面

## 技术实现

### 数据获取
```javascript
// 获取文章详情
const articleData = await contentStore.fetchArticleDetail(id)

// 加载相关文章
const accountArticles = await contentStore.fetchAccountArticles(
  currentArticle.account.id, 1, 5
)
```

### 图片懒加载
```vue
<image 
  :src="image"
  mode="aspectFill"
  lazy-load
  @click="previewImage(image, article.images)"
/>
```

### 内容格式化
```javascript
const formatContent = (content) => {
  // 将换行符转换为<br>标签
  let formattedContent = content.replace(/\n/g, '<br>')
  
  // 处理链接
  formattedContent = formattedContent.replace(
    /(https?:\/\/[^\s]+)/g,
    '<a href="$1" style="color: #007aff;">$1</a>'
  )
  
  return formattedContent
}
```

### 分享实现
```javascript
const handleShare = () => {
  uni.showActionSheet({
    itemList: ['分享到微信', '分享到朋友圈', '复制链接'],
    success: async (res) => {
      // 根据用户选择执行对应分享操作
    }
  })
}
```

## 页面状态管理

### 加载状态
- `loading`: 页面加载状态
- `error`: 错误信息
- `canRetry`: 是否可以重试

### 数据状态
- `article`: 当前文章详情
- `relatedArticles`: 相关文章列表
- `articleId`: 当前文章ID

## 错误处理

### 网络错误
- 自动重试机制（最多3次）
- 友好的错误提示
- 重试按钮

### 数据验证
- 文章ID验证
- 文章数据完整性检查
- 图片链接有效性验证

## 性能优化

### 图片优化
- 懒加载减少初始加载时间
- 缩略图优先加载
- 图片预加载策略

### 缓存策略
- 文章详情缓存
- 相关文章缓存
- 图片缓存

### 内存管理
- 组件销毁时清理缓存
- 图片资源及时释放

## 用户体验

### 视觉设计
- 清晰的信息层次
- 舒适的阅读体验
- 一致的视觉风格

### 交互反馈
- 加载状态提示
- 操作成功/失败反馈
- 平滑的页面转场

### 无障碍支持
- 语义化的HTML结构
- 合适的颜色对比度
- 触摸目标大小符合规范

## 相关文件

- `pages/article/detail.vue` - 文章详情页面主文件
- `pages/webview/webview.vue` - 原文查看页面
- `stores/content.js` - 内容状态管理
- `components/ContentCard.vue` - 内容卡片组件（参考）

## API 依赖

- `GET /api/v1/articles/{id}` - 获取文章详情
- `GET /api/v1/articles` - 获取博主文章列表
- `POST /api/v1/articles/{id}/read` - 标记文章已读
- `POST /api/v1/articles/{id}/favorite` - 收藏文章
- `DELETE /api/v1/articles/{id}/favorite` - 取消收藏
- `POST /api/v1/articles/{id}/share` - 记录分享统计