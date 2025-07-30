<template>
  <view class="container">
    <Loading v-if="loading" />
    <view v-else-if="error" class="error-container">
      <view class="error-message">{{ error }}</view>
      <button v-if="canRetry" @click="retry" class="retry-btn">重试</button>
    </view>
    <view v-else-if="article" class="content">
      <!-- 文章头部信息 -->
      <view class="article-header">
        <view class="author-info">
          <image 
            :src="article.account?.avatar_url || '/static/default-avatar.png'" 
            class="author-avatar" 
            mode="aspectFill"
          />
          <view class="author-details">
            <text class="author-name">{{ article.account?.name || '未知博主' }}</text>
            <text class="publish-time">{{ formatTime(article.publish_time) }}</text>
          </view>
        </view>
        <view class="header-actions">
           <view 
            class="platform-tag" 
            :class="`platform-${article.account?.platform}`"
            v-if="article.account?.platform"
          >
            <text class="platform-text">{{ getPlatformName(article.account?.platform) }}</text>
          </view>
          <view class="action-btn" @click="handleFavorite">
            <text class="action-icon" :class="{ 'favorited': article.is_favorited }">♥</text>
          </view>
        </view>
      </view>
      
      <!-- 文章内容 -->
      <view class="article-content">
        <text class="article-title">{{ article.title }}</text>
        
        <!-- 文章摘要 -->
        <text class="article-summary" v-if="article.summary">{{ article.summary }}</text>
        
        <!-- 文章正文 -->
        <view class="article-body" v-if="article.content">
          <rich-text :nodes="formatContent(article.content)" class="rich-content"></rich-text>
        </view>
        
        <!-- 图片展示 -->
        <view class="images-container" v-if="article.images && article.images.length > 0">
          <view class="image-grid" :class="`grid-${getGridClass(article.images.length)}`">
            <image 
              v-for="(image, index) in article.images" 
              :key="index"
              class="content-image"
              :src="image"
              mode="aspectFill"
              @click="previewImage(image, article.images)"
              lazy-load
            />
          </view>
        </view>
      </view>
      
      <!-- 相关文章推荐 -->
      <view class="related-articles" v-if="relatedArticles.length > 0">
        <view class="section-title">相关推荐</view>
        <view class="related-list">
          <view 
            v-for="relatedArticle in relatedArticles" 
            :key="relatedArticle.id"
            class="related-item"
            @click="navigateToArticle(relatedArticle.id, relatedArticle.account?.platform)"
          >
            <image 
              :src="relatedArticle.images?.[0] || '/static/empty-content.png'" 
              class="related-image"
              mode="aspectFill"
            />
            <view class="related-content">
              <text class="related-title">{{ relatedArticle.title }}</text>
              <view class="related-meta">
                <text class="related-author">{{ relatedArticle.account?.name }}</text>
                <text class="related-time">{{ formatTime(relatedArticle.publish_time) }}</text>
              </view>
            </view>
          </view>
        </view>
      </view>
      
      <!-- 底部操作栏 -->
      <view class="article-actions">
        <ShareButton 
          shareType="article"
          :article="article"
          shareSource="article_detail"
          buttonText="分享"
          @share-success="onShareSuccess"
          @share-fail="onShareFail"
        />
        <button @click="handleOpenOriginal" class="action-btn primary">
          <text class="action-text">查看原文</text>
        </button>
      </view>
    </view>
  </view>
</template>

<script>
import { ref, onMounted } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { useContentStore } from '@/stores/content'
import Loading from '@/components/Loading.vue'
import ShareButton from '@/components/ShareButton.vue'
import wechatShareManager from '@/utils/wechatShare'
import { createPageState } from '@/utils/pageState'
import { checkLoginAndNavigate, navigateBack } from '@/utils/navigation'

export default {
  name: 'ArticleDetailPage',
  components: {
    Loading,
    ShareButton
  },
  // 微信小程序分享到好友
  onShareAppMessage() {
    // 如果页面实例有分享配置，使用它
    if (this.$shareConfig) {
      return this.$shareConfig
    }
    
    // 默认分享配置
    const article = this.article
    if (article) {
      return wechatShareManager.configureArticleShare(article, {
        shareSource: 'share_menu'
      })
    }
    
    return {
      title: '内容聚合 - 发现精彩内容',
      path: 'pages/index/index'
    }
  },
  
  // 微信小程序分享到朋友圈
  onShareTimeline() {
    // 如果页面实例有朋友圈分享配置，使用它
    if (this.$timelineShareConfig) {
      return this.$timelineShareConfig
    }
    
    // 默认朋友圈分享配置
    const article = this.article
    if (article) {
      const shareData = wechatShareManager.configureArticleShare(article, {
        shareSource: 'timeline_menu'
      })
      
      return {
        title: shareData.title,
        query: wechatShareManager.extractQueryFromPath(shareData.path),
        imageUrl: shareData.imageUrl
      }
    }
    
    return {
      title: '内容聚合 - 发现精彩内容',
      query: 'share_source=timeline_menu'
    }
  },
  setup() {
    const contentStore = useContentStore()
    
    // 创建页面状态管理器
    const pageState = createPageState({
      enableRetry: true,
      maxRetryCount: 3
    })

    const articleId = ref('')
    const platform = ref('')
    const article = ref(null)
    const relatedArticles = ref([])

    // 重试逻辑
    const retry = async () => {
      await pageState.retry(async () => {
        if (articleId.value) {
          await loadArticleDetail(articleId.value, platform.value)
        }
      })
    }

    // 加载文章详情
    const loadArticleDetail = async (id, plat) => {
      await pageState.executeAsync(async () => {
        try {
          // 获取文章详情
          const articleData = await contentStore.fetchArticleDetail(id, plat)
          article.value = articleData
          
          // 标记文章为已读
          await contentStore.markArticleAsRead(id)
          
          // 加载相关文章推荐
          await loadRelatedArticles(articleData)
          
        } catch (error) {
          console.error('加载文章详情失败:', error)
          throw error
        }
      }, {
        errorMessage: '文章加载失败，请重试'
      })
    }

    // 加载相关文章推荐
    const loadRelatedArticles = async (currentArticle) => {
      try {
        if (currentArticle.account?.id && currentArticle.account?.platform) {
          // 获取同一博主的其他文章
          const accountArticles = await contentStore.fetchAccountArticles(
            currentArticle.account.id, 
            1, 
            5,
            currentArticle.account.platform
          )
          
          // 过滤掉当前文章
          relatedArticles.value = accountArticles.items
            .filter(item => item.id !== currentArticle.id)
            .slice(0, 3)
        }
      } catch (error) {
        console.error('加载相关文章失败:', error)
        // 相关文章加载失败不影响主要功能
      }
    }

    // 处理收藏
    const handleFavorite = async () => {
      checkLoginAndNavigate(async () => {
        try {
          if (article.value.is_favorited) {
            await contentStore.unfavoriteArticle(article.value.id)
            article.value.is_favorited = false
          } else {
            await contentStore.favoriteArticle(article.value.id)
            article.value.is_favorited = true
          }
        } catch (error) {
          console.error('收藏操作失败:', error)
        }
      })
    }



    // 处理打开原文
    const handleOpenOriginal = () => {
      checkLoginAndNavigate(() => {
        if (article.value?.url) {
          // 在小程序中打开网页
          uni.navigateTo({
            url: `/pages/webview/webview?url=${encodeURIComponent(article.value.url)}`
          })
        } else {
          uni.showToast({
            title: '原文链接不存在',
            icon: 'none'
          })
        }
      })
    }

    // 预览图片
    const previewImage = (current, urls) => {
      uni.previewImage({
        current,
        urls
      })
    }

    // 导航到其他文章
    const navigateToArticle = (id, plat) => {
      uni.navigateTo({
        url: `/pages/article/detail?id=${id}&platform=${plat}`
      })
    }

    // 格式化时间
    const formatTime = (time) => {
      if (!time) return ''
      
      const now = new Date()
      const publishTime = new Date(time)
      const diff = now - publishTime
      
      const minutes = Math.floor(diff / (1000 * 60))
      const hours = Math.floor(diff / (1000 * 60 * 60))
      const days = Math.floor(diff / (1000 * 60 * 60 * 24))
      
      if (minutes < 1) {
        return '刚刚'
      } else if (minutes < 60) {
        return `${minutes}分钟前`
      } else if (hours < 24) {
        return `${hours}小时前`
      } else if (days < 7) {
        return `${days}天前`
      } else {
        return publishTime.toLocaleDateString()
      }
    }

    // 获取平台名称
    const getPlatformName = (platform) => {
      const platformMap = {
        'wechat': '微信',
        'weibo': '微博',
        'twitter': '推特',
        'douyin': '抖音',
        'xiaohongshu': '小红书'
      }
      return platformMap[platform] || '其他'
    }

    // 获取图片网格样式类
    const getGridClass = (count) => {
      if (count === 1) return 'single'
      if (count === 2) return 'double'
      if (count <= 4) return 'quad'
      return 'nine'
    }

    // 格式化数字
    const formatNumber = (num) => {
      if (num < 1000) return num.toString()
      if (num < 10000) return (num / 1000).toFixed(1) + 'k'
      if (num < 100000) return (num / 10000).toFixed(1) + 'w'
      return (num / 10000).toFixed(0) + 'w'
    }

    // 格式化文章内容
    const formatContent = (content) => {
      if (!content) return ''
      
      // 简单的HTML内容处理
      // 将换行符转换为<br>标签
      let formattedContent = content.replace(/\n/g, '<br>')
      
      // 处理链接
      formattedContent = formattedContent.replace(
        /(https?:\/\/[^\s]+)/g,
        '<a href="$1" style="color: #007aff;">$1</a>'
      )
      
      return formattedContent
    }

    // 处理分享成功
    const onShareSuccess = (shareEvent) => {
      console.log('分享成功:', shareEvent)
      uni.showToast({
        title: '分享成功',
        icon: 'success'
      })
    }

    // 处理分享失败
    const onShareFail = (shareEvent) => {
      console.error('分享失败:', shareEvent)
      uni.showToast({
        title: '分享失败，请重试',
        icon: 'none'
      })
    }

    // 处理返回
    const handleBack = () => {
      navigateBack()
    }

    onLoad((options) => {
      if (options.id) {
        articleId.value = options.id
        platform.value = options.platform
        loadArticleDetail(options.id, options.platform)
        
        // 处理分享链接点击
        wechatShareManager.handleShareLinkClick(options)
      } else {
        pageState.setError('文章ID不存在')
      }
    })

    onMounted(() => {
      console.log('文章详情页面初始化')
    })

    return {
      ...pageState.state,
      articleId,
      article,
      relatedArticles,
      retry,
      handleFavorite,
      handleOpenOriginal,
      handleBack,
      previewImage,
      navigateToArticle,
      formatTime,
      getPlatformName,
      getGridClass,
      formatNumber,
      formatContent,
      onShareSuccess,
      onShareFail,
      canRetry: pageState.canRetry
    }
  }
}
</script>

<style scoped>
.container {
  min-height: 100vh;
  background-color: #f5f5f5;
  padding-bottom: 120rpx; /* 为底部操作栏留出空间 */
}

.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 50vh;
}

.error-message {
  color: #ff4757;
  margin-bottom: 20rpx;
  font-size: 28rpx;
}

.retry-btn {
  background-color: #007aff;
  color: white;
  border: none;
  padding: 20rpx 40rpx;
  border-radius: 10rpx;
  font-size: 28rpx;
}

.content {
  background-color: white;
  min-height: 100vh;
}

/* 文章头部 */
.article-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 30rpx;
  border-bottom: 1rpx solid #f0f0f0;
}

.author-info {
  display: flex;
  align-items: center;
  flex: 1;
}

.author-avatar {
  width: 80rpx;
  height: 80rpx;
  border-radius: 40rpx;
  margin-right: 20rpx;
}

.author-details {
  flex: 1;
  margin-right: 20rpx;
}

.author-name {
  display: block;
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 8rpx;
}

.publish-time {
  display: block;
  font-size: 24rpx;
  color: #999;
}

.platform-tag {
  padding: 8rpx 16rpx;
  border-radius: 20rpx;
  margin-left: 20rpx;
}

.platform-wechat {
  background-color: #07c160;
}

.platform-weibo {
  background-color: #ff8200;
}

.platform-twitter {
  background-color: #1da1f2;
}

.platform-douyin {
  background-color: #000;
}

.platform-xiaohongshu {
  background-color: #ff2442;
}

.platform-text {
  font-size: 22rpx;
  color: white;
}

.header-actions {
  display: flex;
  gap: 20rpx;
}

.action-btn {
  width: 60rpx;
  height: 60rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background-color: #f0f0f0;
  transition: all 0.2s;
}

.action-btn:active {
  transform: scale(0.9);
  background-color: #e0e0e0;
}

.action-icon {
  font-size: 32rpx;
  color: #666;
}

.action-icon.favorited {
  color: #ff4757;
}

/* 文章内容 */
.article-content {
  padding: 40rpx 30rpx;
}

.article-title {
  display: block;
  font-size: 44rpx;
  font-weight: bold;
  color: #2c3e50;
  line-height: 1.4;
  margin-bottom: 40rpx;
}

.article-summary {
  display: block;
  font-size: 28rpx;
  color: #666;
  line-height: 1.6;
  margin-bottom: 40rpx;
  padding: 20rpx;
  background-color: #f8f9fa;
  border-radius: 12rpx;
  border-left: 4rpx solid #007aff;
}

.article-body {
  line-height: 1.8;
  margin-bottom: 40rpx;
}

.rich-content {
  font-size: 32rpx;
  color: #333;
  line-height: 1.8;
  word-wrap: break-word;
}

/* 图片展示 */
.images-container {
  margin: 30rpx 0;
}

.image-grid {
  display: grid;
  gap: 8rpx;
  border-radius: 8rpx;
  overflow: hidden;
}

.grid-single {
  grid-template-columns: 1fr;
}

.grid-double {
  grid-template-columns: 1fr 1fr;
}

.grid-quad {
  grid-template-columns: 1fr 1fr;
}

.grid-nine {
  grid-template-columns: 1fr 1fr 1fr;
}

.content-image {
  width: 100%;
  height: 200rpx;
  border-radius: 8rpx;
}

.grid-single .content-image {
  height: 400rpx;
}

/* 相关文章推荐 */
.related-articles {
  margin-top: 40rpx;
  padding: 30rpx;
  background-color: #f8f9fa;
}

.section-title {
  font-size: 32rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 30rpx;
  padding-bottom: 20rpx;
  border-bottom: 2rpx solid #007aff;
}

.related-list {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.related-item {
  display: flex;
  padding: 20rpx;
  background-color: white;
  border-radius: 12rpx;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.1);
}

.related-image {
  width: 120rpx;
  height: 90rpx;
  border-radius: 8rpx;
  margin-right: 20rpx;
  flex-shrink: 0;
}

.related-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.related-title {
  font-size: 28rpx;
  color: #333;
  line-height: 1.4;
  margin-bottom: 12rpx;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.related-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.related-author {
  font-size: 24rpx;
  color: #666;
}

.related-time {
  font-size: 22rpx;
  color: #999;
}

/* 底部操作栏 */
.article-actions {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  padding: 20rpx;
  background-color: white;
  border-top: 1rpx solid #f0f0f0;
  box-shadow: 0 -2rpx 8rpx rgba(0, 0, 0, 0.1);
}

.article-actions .action-btn {
  flex: 1;
  margin: 0 10rpx;
  padding: 25rpx;
  border: none;
  border-radius: 50rpx;
  background-color: #f0f0f0;
  font-size: 28rpx;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  width: auto;
  height: auto;
  transition: background-color 0.2s;
}

.article-actions .action-btn:active {
  background-color: #e0e0e0;
}

.article-actions .action-btn.primary {
  background-color: #007aff;
  color: white;
}

.article-actions .action-btn.primary:active {
  background-color: #0056b3;
}

.article-actions .action-btn.primary .action-text {
  color: white;
}

.action-text {
  color: #333;
  font-size: 28rpx;
}

/* 响应式调整 */
@media screen and (max-width: 750rpx) {
  .article-content {
    padding: 20rpx;
  }
  
  .article-header {
    padding: 20rpx;
  }
  
  .related-articles {
    padding: 20rpx;
  }
}
</style>