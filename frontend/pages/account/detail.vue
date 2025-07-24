<template>
  <view class="container">
    <Loading v-if="loading" />
    <view v-else-if="error" class="error-container">
      <view class="error-message">{{ error }}</view>
      <button v-if="canRetry" @click="retry" class="retry-btn">重试</button>
    </view>
    <view v-else-if="accountInfo" class="content">
      <!-- 博主信息头部 -->
      <view class="account-header">
        <view class="account-basic">
          <view class="account-avatar">
            <image :src="accountInfo.avatar_url" mode="aspectFill" class="avatar-img" />
            <view class="platform-badge" :style="{ backgroundColor: getPlatformColor(accountInfo.platform) }">
              <image :src="getPlatformIcon(accountInfo.platform)" mode="aspectFit" class="badge-icon" />
            </view>
          </view>
          
          <view class="account-info">
            <view class="account-name">{{ accountInfo.name }}</view>
            <view class="account-platform">{{ getPlatformName(accountInfo.platform) }}</view>
            <view class="account-stats">
              <text class="follower-count">{{ formatFollowerCount(accountInfo.follower_count) }} 关注者</text>
            </view>
          </view>
        </view>
        
        <view class="account-description" v-if="accountInfo.description">
          <text class="desc-text">{{ accountInfo.description }}</text>
        </view>
        
        <!-- 订阅按钮 -->
        <view class="subscribe-section">
          <button 
            class="subscribe-btn"
            :class="{ 
              subscribed: isSubscribed,
              loading: subscriptionStore.loading 
            }"
            @click="toggleSubscribe"
            :disabled="subscriptionStore.loading"
          >
            <text v-if="subscriptionStore.loading" class="loading-text">处理中...</text>
            <text v-else-if="isSubscribed" class="unsubscribe-text">退订</text>
            <text v-else class="subscribe-text">订阅</text>
          </button>
          
          <view v-if="!isLoggedIn" class="login-tip">
            <text class="tip-text">登录后可订阅博主动态</text>
          </view>
        </view>
      </view>
      
      <!-- 最新文章 -->
      <view class="articles-section" v-if="articles.length > 0">
        <view class="section-header">
          <text class="section-title">最新文章</text>
          <text class="article-count">共 {{ totalArticles }} 篇</text>
        </view>
        
        <view class="articles-list">
          <view 
            v-for="article in articles" 
            :key="article.id"
            class="article-item"
            @click="viewArticle(article)"
          >
            <view class="article-content">
              <view class="article-title">{{ article.title }}</view>
              <view class="article-summary" v-if="article.summary">
                {{ article.summary }}
              </view>
              <view class="article-meta">
                <text class="publish-time">{{ formatTime(article.publish_time) }}</text>
                <text class="read-count" v-if="article.read_count">{{ article.read_count }} 阅读</text>
              </view>
            </view>
            
            <view class="article-thumb" v-if="article.cover_image">
              <image :src="article.cover_image" mode="aspectFill" class="thumb-img" />
            </view>
          </view>
        </view>
        
        <!-- 加载更多文章 -->
        <view v-if="hasMoreArticles" class="load-more">
          <button 
            class="load-more-btn" 
            @click="loadMoreArticles"
            :disabled="loadingArticles"
          >
            {{ loadingArticles ? '加载中...' : '加载更多文章' }}
          </button>
        </view>
      </view>
      
      <!-- 暂无文章 -->
      <view v-else class="no-articles">
        <image class="no-data-icon" src="/static/no-articles.png" mode="aspectFit" />
        <text class="no-data-text">该博主暂无文章</text>
      </view>
    </view>
  </view>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import Loading from '@/components/Loading.vue'
import { createPageState } from '@/utils/pageState'
import { checkLoginAndNavigate } from '@/utils/navigation'
import { useSubscriptionStore, useAuthStore, useAppStore, useContentStore } from '@/stores'
import request from '@/utils/request'

export default {
  name: 'AccountDetailPage',
  components: {
    Loading
  },
  setup() {
    // 状态管理
    const subscriptionStore = useSubscriptionStore()
    const authStore = useAuthStore()
    const appStore = useAppStore()
    const contentStore = useContentStore()
    
    // 创建页面状态管理器
    const pageState = createPageState({
      enableRetry: true,
      maxRetryCount: 3
    })

    // 响应式数据
    const accountInfo = ref(null)
    const articles = ref([])
    const totalArticles = ref(0)
    const hasMoreArticles = ref(false)
    const loadingArticles = ref(false)
    const currentPage = ref(1)
    const accountId = ref(null)

    // 计算属性
    const isLoggedIn = computed(() => authStore.isLoggedIn)
    const isSubscribed = computed(() => {
      return accountId.value ? subscriptionStore.isSubscribed(accountId.value) : false
    })

    // 初始化页面
    onMounted(async () => {
      try {
        // 获取页面参数
        const pages = getCurrentPages()
        const currentPage = pages[pages.length - 1]
        const options = currentPage.options || {}
        
        accountId.value = parseInt(options.id)
        
        if (!accountId.value) {
          throw new Error('缺少博主ID参数')
        }
        
        // 如果用户已登录，加载订阅列表
        if (isLoggedIn.value) {
          await subscriptionStore.fetchSubscriptions(true)
        }
        
        // 加载博主信息和文章
        await loadAccountInfo()
        await loadArticles(true)
        
        console.log('博主详情页面初始化完成')
      } catch (error) {
        console.error('博主详情页面初始化失败:', error)
        pageState.setError(error.message || '页面加载失败')
      }
    })

    // 加载博主信息
    const loadAccountInfo = async () => {
      try {
        const data = await request.get(`/search/accounts/by-id/${accountId.value}`)
        accountInfo.value = data
      } catch (error) {
        console.error('加载博主信息失败:', error)
        throw new Error('加载博主信息失败')
      }
    }

    // 加载文章列表
    const loadArticles = async (refresh = false) => {
      try {
        if (refresh) {
          currentPage.value = 1
          articles.value = []
        }
        
        loadingArticles.value = true
        
        const response = await request.get(`/content/accounts/${accountId.value}/articles`, {
          page: currentPage.value,
          page_size: 10
        })
        
        // 处理响应数据结构
        const data = response.data || []
        const total = response.total || 0
        
        if (refresh) {
          articles.value = data
        } else {
          articles.value.push(...data)
        }
        
        totalArticles.value = total
        hasMoreArticles.value = data.length === 10
        currentPage.value += 1
        
      } catch (error) {
        console.error('加载文章失败:', error)
        uni.showToast({
          title: '加载文章失败',
          icon: 'none'
        })
      } finally {
        loadingArticles.value = false
      }
    }

    // 加载更多文章
    const loadMoreArticles = async () => {
      await loadArticles(false)
    }

    // 重试加载
    const retry = async () => {
      await pageState.retry(async () => {
        await loadAccountInfo()
        await loadArticles(true)
      })
    }

    // 切换订阅状态
    const toggleSubscribe = async () => {
      if (!isLoggedIn.value) {
        checkLoginAndNavigate(() => {
          // 登录后重新执行订阅操作
          toggleSubscribe()
        })
        return
      }

      try {
        if (isSubscribed.value) {
          // 取消订阅
          await subscriptionStore.unsubscribeByAccountId(accountId.value)
        } else {
          // 创建订阅
          await subscriptionStore.subscribeAccount(accountId.value)
        }
      } catch (error) {
        console.error('订阅操作失败:', error)
      }
    }

    // 查看文章详情
    const viewArticle = (article) => {
      uni.navigateTo({
        url: `/pages/article/detail?id=${article.id}`
      })
    }

    // 获取平台信息
    const getPlatformInfo = (platformKey) => {
      return appStore.getPlatformInfo(platformKey) || {}
    }

    const getPlatformName = (platformKey) => {
      const platform = getPlatformInfo(platformKey)
      return platform.name || platformKey
    }

    const getPlatformIcon = (platformKey) => {
      const platform = getPlatformInfo(platformKey)
      return platform.icon || '/static/platform-default.png'
    }

    const getPlatformColor = (platformKey) => {
      const platform = getPlatformInfo(platformKey)
      return platform.color || '#999'
    }

    // 格式化关注者数量
    const formatFollowerCount = (count) => {
      if (!count) return '0'
      if (count < 1000) return count.toString()
      if (count < 10000) return (count / 1000).toFixed(1) + 'K'
      if (count < 100000) return (count / 10000).toFixed(1) + 'W'
      return (count / 10000).toFixed(0) + 'W'
    }

    // 格式化时间
    const formatTime = (time) => {
      if (!time) return ''
      const date = new Date(time)
      const now = new Date()
      const diff = now - date
      
      if (diff < 60000) return '刚刚'
      if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
      if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
      if (diff < 2592000000) return Math.floor(diff / 86400000) + '天前'
      
      return date.toLocaleDateString()
    }

    return {
      // 状态
      ...pageState.state,
      subscriptionStore,
      
      // 响应式数据
      accountInfo,
      articles,
      totalArticles,
      hasMoreArticles,
      loadingArticles,
      
      // 计算属性
      isLoggedIn,
      isSubscribed,
      
      // 方法
      retry,
      toggleSubscribe,
      loadMoreArticles,
      viewArticle,
      getPlatformName,
      getPlatformIcon,
      getPlatformColor,
      formatFollowerCount,
      formatTime,
      
      // 页面状态
      canRetry: pageState.canRetry
    }
  }
}
</script>

<style scoped>
.container {
  min-height: 100vh;
  background-color: #f5f5f5;
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
  padding: 20rpx;
}

/* 博主信息头部 */
.account-header {
  background-color: white;
  border-radius: 15rpx;
  padding: 40rpx;
  margin-bottom: 20rpx;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.08);
}

.account-basic {
  display: flex;
  align-items: flex-start;
  margin-bottom: 30rpx;
}

.account-avatar {
  position: relative;
  margin-right: 30rpx;
}

.avatar-img {
  width: 120rpx;
  height: 120rpx;
  border-radius: 60rpx;
}

.platform-badge {
  position: absolute;
  bottom: -5rpx;
  right: -5rpx;
  width: 40rpx;
  height: 40rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 3rpx solid white;
}

.badge-icon {
  width: 24rpx;
  height: 24rpx;
}

.account-info {
  flex: 1;
}

.account-name {
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 10rpx;
}

.account-platform {
  font-size: 26rpx;
  color: #007aff;
  margin-bottom: 15rpx;
}

.account-stats {
  display: flex;
  align-items: center;
}

.follower-count {
  font-size: 24rpx;
  color: #666;
}

.account-description {
  margin-bottom: 30rpx;
}

.desc-text {
  font-size: 28rpx;
  color: #666;
  line-height: 1.6;
}

/* 订阅按钮区域 */
.subscribe-section {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.subscribe-btn {
  background-color: #007aff;
  color: white;
  border: none;
  padding: 20rpx 60rpx;
  border-radius: 30rpx;
  font-size: 28rpx;
  min-width: 200rpx;
  transition: all 0.3s ease;
  margin-bottom: 15rpx;
}

.subscribe-btn:hover {
  transform: translateY(-2rpx);
  box-shadow: 0 6rpx 16rpx rgba(0, 122, 255, 0.3);
}

.subscribe-btn.subscribed {
  background-color: #ff4757;
  color: white;
}

.subscribe-btn.subscribed:hover {
  background-color: #ff3742;
  box-shadow: 0 6rpx 16rpx rgba(255, 71, 87, 0.3);
}

.subscribe-btn.loading {
  background-color: #ccc;
  cursor: not-allowed;
}

.subscribe-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.loading-text {
  color: #666;
}

.subscribe-text {
  color: white;
}

.unsubscribe-text {
  color: white;
}

.login-tip {
  margin-top: 10rpx;
}

.tip-text {
  font-size: 24rpx;
  color: #999;
}

/* 文章区域 */
.articles-section {
  background-color: white;
  border-radius: 15rpx;
  overflow: hidden;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.08);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 30rpx 40rpx;
  border-bottom: 1rpx solid #f0f0f0;
}

.section-title {
  font-size: 32rpx;
  font-weight: bold;
  color: #333;
}

.article-count {
  font-size: 24rpx;
  color: #999;
}

.articles-list {
  padding: 0;
}

.article-item {
  display: flex;
  align-items: flex-start;
  padding: 30rpx 40rpx;
  border-bottom: 1rpx solid #f0f0f0;
}

.article-item:last-child {
  border-bottom: none;
}

.article-content {
  flex: 1;
  margin-right: 20rpx;
}

.article-title {
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 15rpx;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.article-summary {
  font-size: 26rpx;
  color: #666;
  margin-bottom: 15rpx;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.article-meta {
  display: flex;
  align-items: center;
  gap: 20rpx;
}

.publish-time {
  font-size: 22rpx;
  color: #999;
}

.read-count {
  font-size: 22rpx;
  color: #999;
}

.article-thumb {
  flex-shrink: 0;
  width: 120rpx;
  height: 90rpx;
  border-radius: 8rpx;
  overflow: hidden;
}

.thumb-img {
  width: 100%;
  height: 100%;
}

/* 加载更多 */
.load-more {
  padding: 30rpx;
  text-align: center;
}

.load-more-btn {
  background: none;
  border: 1rpx solid #e5e5e5;
  color: #666;
  padding: 20rpx 40rpx;
  border-radius: 10rpx;
  font-size: 26rpx;
}

.load-more-btn:disabled {
  opacity: 0.6;
}

/* 暂无文章 */
.no-articles {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80rpx 40rpx;
  background-color: white;
  border-radius: 15rpx;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.08);
}

.no-data-icon {
  width: 160rpx;
  height: 160rpx;
  margin-bottom: 30rpx;
  opacity: 0.5;
}

.no-data-text {
  font-size: 28rpx;
  color: #999;
}

/* 响应式调整 */
@media (max-width: 750rpx) {
  .account-header {
    padding: 30rpx;
  }
  
  .account-basic {
    margin-bottom: 20rpx;
  }
  
  .avatar-img {
    width: 100rpx;
    height: 100rpx;
    border-radius: 50rpx;
  }
  
  .account-name {
    font-size: 32rpx;
  }
  
  .article-item {
    padding: 20rpx 30rpx;
  }
  
  .article-title {
    font-size: 28rpx;
  }
  
  .article-summary {
    font-size: 24rpx;
  }
}
</style>