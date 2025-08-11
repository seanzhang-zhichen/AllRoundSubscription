<template>
  <view class="container">
    <!-- 骨架屏加载状态 -->
    <SkeletonScreen 
      v-if="showSkeleton" 
      type="content-card" 
      :count="3" 
      :show-image="true" 
    />
    
    <!-- 传统加载状态 -->
    <Loading v-else-if="loading && !refreshing && !showSkeleton" />
    
    <!-- 错误状态 -->
    <view v-else-if="error" class="error-container">
      <view class="error-message">{{ error }}</view>
      <button v-if="canRetry" @click="retry" class="retry-btn">重试</button>
    </view>
    
    <!-- 主内容区域 -->
    <view v-else class="content">
      <!-- 内容列表 -->
      <scroll-view 
        class="content-scroll"
        scroll-y
        refresher-enabled
        :refresher-triggered="refreshing"
        @refresherrefresh="handleRefresh"
        @scrolltolower="handleLoadMore"
        lower-threshold="100"
      >
        <!-- 动态流内容 -->
        <view class="feed-list" v-if="feedList.length > 0">
          <ContentCard
            v-for="article in feedList"
            :key="article.id"
            :article="article"
            :show-stats="false"
            @click="navigateToArticle"
            @favorite="handleFavorite"
            @share="handleShare"
          />
          
          <!-- 加载更多状态 -->
          <view class="load-more-container" v-if="hasMore">
            <view class="load-more-content" v-if="loadingMore">
              <text class="load-more-text">加载中...</text>
            </view>
            <view class="load-more-content" v-else>
              <text class="load-more-text">上拉加载更多</text>
            </view>
          </view>
          
          <!-- 没有更多内容 -->
          <view class="no-more-container" v-else-if="feedList.length > 0">
            <text class="no-more-text">没有更多内容了</text>
          </view>
        </view>

        <!-- 空状态 -->
        <Empty 
          v-else-if="!loading && !refreshing"
          icon="content"
          text="暂无动态内容"
          :show-action="true"
          action-text="刷新试试"
          @action="handleRefresh"
        />
      </scroll-view>
    </view>

    <!-- 回到顶部按钮 -->
    <view 
      class="back-to-top" 
      v-if="showBackToTop"
      @click="scrollToTop"
    >
      <text class="back-to-top-icon">↑</text>
    </view>
  </view>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { onPullDownRefresh, onReachBottom, onPageScroll, onShareAppMessage, onShow } from '@dcloudio/uni-app'
import { storeToRefs } from 'pinia'
import Loading from '@/components/Loading.vue'
import ContentCard from '@/components/ContentCard.vue'
import Empty from '@/components/Empty.vue'
import SkeletonScreen from '@/components/SkeletonScreen.vue'
import wechatShareManager from '@/utils/wechatShare'
import { useContentStore } from '@/stores/content'
import { useAuthStore } from '@/stores/auth'
import { usePageInteraction } from '@/utils/pageInteraction'
import { navigateToArticleDetail, checkLoginAndNavigate } from '@/utils/navigation'

export default {
  name: 'IndexPage',
  components: {
    Loading,
    ContentCard,
    Empty,
    SkeletonScreen
  },
  // 微信小程序分享到好友
  onShareAppMessage() {
    return wechatShareManager.configurePageShare('index', {
      shareParams: {
        share_source: 'share_menu'
      }
    })
  },
  
  // 微信小程序分享到朋友圈
  onShareTimeline() {
    const shareData = wechatShareManager.configurePageShare('index', {
      shareParams: {
        share_source: 'timeline_menu'
      }
    })
    
    return {
      title: shareData.title,
      query: wechatShareManager.extractQueryFromPath(shareData.path),
      imageUrl: shareData.imageUrl
    }
  },
  setup() {
    // 状态管理
    const contentStore = useContentStore()
    const authStore = useAuthStore()
    
    // 响应式状态
    const { 
      feedList, 
      loading, 
      refreshing, 
      loadingMore,
      pagination 
    } = storeToRefs(contentStore)
    
    const { isLoggedIn } = storeToRefs(authStore)
    
    // 创建增强的页面交互管理器
    const pageInteraction = usePageInteraction('index', {
      enableStateSync: true,
      enableFeedback: true,
      enableRetry: true,
      skeletonType: 'content-card',
      cacheStrategy: 'memory',
      refreshStrategy: 'pull',
      loadMoreStrategy: 'scroll'
    })

    // 计算属性
    const hasMore = computed(() => pagination.value.hasMore)

    // 初始化加载数据
    const initializeData = async () => {
      return await pageInteraction.loadData(
        () => contentStore.fetchFeed(true),
        {
          showSkeleton: true,
          useCache: true,
          successMessage: ''
        }
      )
    }

    // 重试逻辑
    const retry = async () => {
      await pageInteraction.retry(initializeData)
    }

    // 刷新数据
    const handleRefresh = async () => {
      // 如果已经在刷新中，则不重复触发
      if (refreshing.value) {
        return;
      }
      
      await pageInteraction.refreshData(
        () => contentStore.refreshFeed(),
        {
          successMessage: '刷新成功'
        }
      )
    }

    // 加载更多数据
    const handleLoadMore = async () => {
      await pageInteraction.loadMoreData(
        () => contentStore.loadMoreFeed()
      )
    }

    // 导航到文章详情
    const navigateToArticle = (article) => {
      checkLoginAndNavigate(() => {
        // 检查文章是否具有平台信息
        if (!article.account?.platform && !article.account_platform) {
          uni.showToast({
            title: '无法获取平台信息',
            icon: 'none',
            duration: 2000
          });
          console.error('缺少平台信息，无法跳转文章详情', article);
          return;
        }
        
        // 获取平台信息，优先使用嵌套格式，其次使用扁平格式
        const platform = article.account?.platform || article.account_platform;
        
        // 标记文章为已读
        contentStore.markArticleAsRead(article.id);
        
        // 跳转到文章详情页
        navigateToArticleDetail(article.id, platform);
      });
    };

    // 处理收藏
    const handleFavorite = async (article) => {
      if (!isLoggedIn.value) {
        uni.showToast({
          title: '请先登录',
          icon: 'none'
        })
        return
      }

      try {
        if (article.is_favorited) {
          await contentStore.unfavoriteArticle(article.id)
        } else {
          await contentStore.favoriteArticle(article.id)
        }
      } catch (error) {
        console.error('收藏操作失败:', error)
      }
    }

    // 处理分享
    const handleShare = async (article) => {
      try {
        await contentStore.shareArticle(article.id)
        
        uni.showToast({
          title: '分享成功',
          icon: 'success'
        })
      } catch (error) {
        console.error('分享失败:', error)
        uni.showToast({
          title: '分享失败',
          icon: 'none'
        })
      }
    }

    // 回到顶部
    const scrollToTop = () => {
      uni.pageScrollTo({
        scrollTop: 0,
        duration: 300
      })
    }

    // 页面滚动处理
    const handlePageScroll = (e) => {
      pageInteraction.interactionManager.handlePageScroll(e)
    }

    // 页面生命周期
    onMounted(async () => {
      console.log('首页初始化')
      
      // 等待认证状态稳定后再加载数据
      await waitForAuthState()
      await initializeData()
    })

    // 页面显示时自动刷新
    const lastRefreshTime = ref(0)
    onShow(() => {
      const now = Date.now()
      // 避免频繁刷新：两次刷新至少间隔30秒
      if (now - lastRefreshTime.value > 30000) {
        console.log('页面显示，自动刷新内容')
        handleRefresh()
        lastRefreshTime.value = now
      }
    })

    // 等待认证状态稳定
    const waitForAuthState = async () => {
      const maxWaitTime = 3000 // 最多等待3秒
      const startTime = Date.now()
      
      while (Date.now() - startTime < maxWaitTime) {
        // 检查认证状态是否已经确定（无论是否登录）
        if (!authStore.loading) {
          console.log('认证状态已确定:', isLoggedIn.value ? '已登录' : '未登录')
          break
        }
        
        // 等待100ms后再次检查
        await new Promise(resolve => setTimeout(resolve, 100))
      }
      
      if (authStore.loading) {
        console.warn('认证状态检查超时，继续加载页面')
      }
    }

    // 注册生命周期钩子
    onPullDownRefresh(handleRefresh)
    onReachBottom(handleLoadMore)
    onPageScroll(handlePageScroll)

    return {
      // 页面交互状态
      ...pageInteraction.state,
      showSkeleton: pageInteraction.state.showSkeleton,
      
      // 内容状态
      feedList,
      loading,
      refreshing,
      loadingMore,
      hasMore,
      
      // 交互状态
      showBackToTop: pageInteraction.shouldShowBackToTop,
      
      // 方法
      retry,
      handleRefresh,
      handleLoadMore,
      navigateToArticle,
      handleFavorite,
      handleShare,
      scrollToTop: pageInteraction.interactionManager.scrollToTop,
      canRetry: pageInteraction.canRetry
    }
  }
}
</script>

<style scoped>
.container {
  min-height: 100vh;
  background-color: #f5f5f5;
  position: relative;
}

.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 50vh;
  padding: 40rpx;
}

.error-message {
  color: #ff4757;
  margin-bottom: 20rpx;
  font-size: 28rpx;
  text-align: center;
  line-height: 1.5;
}

.retry-btn {
  background-color: #007aff;
  color: white;
  border: none;
  padding: 20rpx 40rpx;
  border-radius: 10rpx;
  font-size: 28rpx;
  cursor: pointer;
}

.retry-btn:active {
  background-color: #0056cc;
}

.content {
  padding: 0;
  padding-bottom: 100rpx; /* 为回到顶部按钮留出空间 */
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.content-scroll {
  height: calc(100vh - 0rpx);
}

.feed-list {
  padding-top: 10rpx;
  padding-bottom: 40rpx;
}

.load-more-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40rpx 0;
}

.load-more-content {
  display: flex;
  align-items: center;
  gap: 20rpx;
}

.load-more-text {
  font-size: 28rpx;
  color: #999;
}

.no-more-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40rpx 0;
}

.no-more-text {
  font-size: 24rpx;
  color: #ccc;
  position: relative;
}

.no-more-text::before,
.no-more-text::after {
  content: '';
  position: absolute;
  top: 50%;
  width: 60rpx;
  height: 1rpx;
  background-color: #e0e0e0;
}

.no-more-text::before {
  left: -80rpx;
}

.no-more-text::after {
  right: -80rpx;
}

.back-to-top {
  position: fixed;
  right: 30rpx;
  bottom: 100rpx;
  width: 80rpx;
  height: 80rpx;
  background-color: rgba(0, 122, 255, 0.8);
  border-radius: 40rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4rpx 12rpx rgba(0, 122, 255, 0.3);
  cursor: pointer;
  transition: all 0.3s ease;
  z-index: 999;
}

.back-to-top:active {
  background-color: rgba(0, 122, 255, 1);
  transform: scale(0.95);
}

.back-to-top-icon {
  font-size: 32rpx;
  color: white;
  font-weight: bold;
}

/* 响应式设计 */
@media screen and (max-width: 750rpx) {
  .content {
    padding: 15rpx;
  }
  
  .header {
    padding: 20rpx;
  }
  
  .title {
    font-size: 32rpx;
  }
}

/* 暗色模式支持 */
@media (prefers-color-scheme: dark) {
  .container {
    background-color: #1a1a1a;
  }
  
  .header {
    background-color: #2a2a2a;
  }
  
  .title {
    color: #fff;
  }
  
  .refresh-btn {
    background-color: #3a3a3a;
  }
  
  .refresh-icon {
    color: #ccc;
  }
  
  .load-more-text,
  .no-more-text {
    color: #888;
  }
}
</style>