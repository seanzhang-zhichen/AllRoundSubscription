<template>
  <view class="container">
    <Loading v-if="loading && subscriptions.length === 0" />
    <view v-else-if="error" class="error-container">
      <view class="error-message">{{ error }}</view>
      <button v-if="canRetry" @click="retry" class="retry-btn">重试</button>
    </view>
    <view v-else class="content">
      <!-- 头部信息 -->
      <view class="header">
        <text class="title">我的订阅</text>
        <view class="subscription-count" :class="{ 'limit-reached': isSubscriptionLimitReached }">
          <text class="count-text">
            已订阅: {{ userLimits.current_subscriptions }}/{{ userLimits.subscription_limit }}
          </text>
        </view>
      </view>

      <!-- 会员限制提示 -->
      <view v-if="isSubscriptionLimitReached" class="limit-warning">
        <view class="warning-content">
          <text class="warning-text">订阅数量已达上限</text>
          <button class="upgrade-btn" @click="showUpgradeModal">升级会员</button>
        </view>
      </view>

      <!-- 操作栏 -->
      <view class="action-bar">
        <button class="btn btn-outline btn-sm" @click="handleNavigateToSearch">
          <text class="btn-text">+ 添加订阅</text>
        </button>
        <button 
          v-if="subscriptions.length > 0" 
          class="btn btn-outline btn-sm" 
          @click="toggleBatchMode"
        >
          <text class="btn-text">{{ batchMode ? '取消' : '管理' }}</text>
        </button>
      </view>

      <!-- 批量操作栏 -->
      <view v-if="batchMode && selectedSubscriptions.length > 0" class="batch-actions">
        <text class="selected-count">已选择 {{ selectedSubscriptions.length }} 个</text>
        <button class="btn btn-danger btn-sm" @click="handleBatchUnsubscribe">
          <text class="btn-text">批量取消订阅</text>
        </button>
      </view>

      <!-- 订阅列表 -->
      <view v-if="subscriptions.length > 0" class="subscription-list">
        <!-- 按平台分组显示 -->
        <view 
          v-for="(platformSubs, platform) in subscriptionsByPlatform" 
          :key="platform" 
          class="platform-group"
        >
          <view class="platform-header">
            <text class="platform-name">{{ getPlatformName(platform) }}</text>
            <text class="platform-count">({{ platformSubs.length }})</text>
          </view>
          
          <view class="subscription-items">
            <view 
              v-for="subscription in platformSubs" 
              :key="subscription.id"
              class="subscription-item"
              @click="handleItemClick(subscription)"
            >
              <!-- 批量选择模式的复选框 -->
              <view v-if="batchMode" class="checkbox-container">
                <checkbox 
                  :checked="selectedSubscriptions.includes(subscription.id)"
                  @click.stop="toggleSelection(subscription.id)"
                />
              </view>

              <!-- 博主头像 -->
              <image 
                class="avatar" 
                :src="subscription.account.avatar_url || '/static/default-avatar.png'"
                mode="aspectFill"
              />

              <!-- 博主信息 -->
              <view class="account-info">
                <text class="account-name">{{ subscription.account.name }}</text>
                <text class="account-desc">{{ subscription.account.description || '暂无简介' }}</text>
                <view class="account-meta">
                  <text class="platform-tag">{{ getPlatformName(subscription.account.platform) }}</text>
                  <text class="follower-count" v-if="subscription.account.follower_count">
                    {{ formatFollowerCount(subscription.account.follower_count) }} 关注者
                  </text>
                </view>
              </view>

              <!-- 操作按钮 -->
              <view v-if="!batchMode" class="action-buttons">
                <button 
                  class="btn btn-danger btn-sm" 
                  @click.stop="handleUnsubscribe(subscription)"
                >
                  <text class="btn-text">取消订阅</text>
                </button>
              </view>
            </view>
          </view>
        </view>

        <!-- 加载更多 -->
        <view v-if="hasMore" class="load-more">
          <button 
            class="btn btn-outline btn-sm" 
            @click="loadMore"
            :disabled="loading"
          >
            <text class="btn-text">{{ loading ? '加载中...' : '加载更多' }}</text>
          </button>
        </view>
      </view>

      <!-- 空状态 -->
      <Empty 
        v-else
        icon="subscription"
        text="还没有订阅任何博主"
        :show-action="true"
        action-text="去搜索博主"
        @action="handleNavigateToSearch"
      />
    </view>

    <!-- 会员升级弹窗 -->
    <view v-if="showUpgrade" class="upgrade-modal" @click="hideUpgradeModal">
      <view class="upgrade-content" @click.stop>
        <view class="upgrade-header">
          <text class="upgrade-title">升级会员</text>
          <text class="close-btn" @click="hideUpgradeModal">×</text>
        </view>
        
        <view class="membership-options">
          <view class="membership-option" @click="upgradeMembership('basic')">
            <view class="option-header">
              <text class="option-title">基础会员</text>
              <text class="option-price">¥9.9/月</text>
            </view>
            <view class="option-benefits">
              <text class="benefit-item">• 订阅数量：50个</text>
              <text class="benefit-item">• 推送次数：20次/天</text>
            </view>
          </view>
          
          <view class="membership-option premium" @click="upgradeMembership('premium')">
            <view class="option-header">
              <text class="option-title">高级会员</text>
              <text class="option-price">¥19.9/月</text>
            </view>
            <view class="option-benefits">
              <text class="benefit-item">• 订阅数量：无限制</text>
              <text class="benefit-item">• 推送次数：无限制</text>
              <text class="benefit-item">• 优先客服支持</text>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { ref, computed, onMounted, onPullDownRefresh } from 'vue'
import { useSubscriptionStore } from '@/stores/subscription'
import { useUserStore } from '@/stores/user'
import Loading from '@/components/Loading.vue'
import Empty from '@/components/Empty.vue'
import { createPageState, enhancePageLifecycle } from '@/utils/pageState'
import { navigateToSearch, checkLoginAndNavigate } from '@/utils/navigation'

export default {
  name: 'SubscriptionPage',
  components: {
    Loading,
    Empty
  },
  setup() {
    // Store实例
    const subscriptionStore = useSubscriptionStore()
    const userStore = useUserStore()

    // 页面状态管理器
    const pageState = createPageState({
      enableRetry: true,
      maxRetryCount: 3
    })

    // 响应式数据
    const batchMode = ref(false)
    const selectedSubscriptions = ref([])
    const showUpgrade = ref(false)

    // 计算属性
    const subscriptions = computed(() => subscriptionStore.subscriptions)
    const subscriptionsByPlatform = computed(() => subscriptionStore.subscriptionsByPlatform)
    const userLimits = computed(() => userStore.userLimits)
    const isSubscriptionLimitReached = computed(() => userStore.isSubscriptionLimitReached)
    const hasMore = computed(() => subscriptionStore.pagination.hasMore)
    const loading = computed(() => subscriptionStore.loading || pageState.state.loading)

    // 平台名称映射
    const getPlatformName = (platform) => {
      const platformMap = {
        'wechat': '微信公众号',
        'weibo': '微博',
        'twitter': 'Twitter',
        'douyin': '抖音',
        'xiaohongshu': '小红书'
      }
      return platformMap[platform] || platform
    }

    // 格式化关注者数量
    const formatFollowerCount = (count) => {
      if (count >= 10000) {
        return `${(count / 10000).toFixed(1)}万`
      } else if (count >= 1000) {
        return `${(count / 1000).toFixed(1)}k`
      }
      return count.toString()
    }

    // 加载订阅列表
    const loadSubscriptions = async (refresh = false) => {
      try {
        await pageState.executeAsync(async () => {
          await subscriptionStore.fetchSubscriptions(refresh)
          // 同时更新用户限制信息
          await userStore.fetchUserLimits()
        }, {
          errorMessage: '加载订阅列表失败',
          showLoading: refresh
        })
      } catch (error) {
        console.error('加载订阅列表失败:', error)
      }
    }

    // 重试逻辑
    const retry = async () => {
      await pageState.retry(async () => {
        await loadSubscriptions(true)
      })
    }

    // 刷新订阅列表
    const refreshSubscriptions = async () => {
      await loadSubscriptions(true)
      uni.stopPullDownRefresh()
    }

    // 加载更多
    const loadMore = async () => {
      if (!hasMore.value || loading.value) return
      await loadSubscriptions(false)
    }

    // 处理取消订阅
    const handleUnsubscribe = async (subscription) => {
      uni.showModal({
        title: '确认取消订阅',
        content: `确定要取消订阅「${subscription.account.name}」吗？`,
        success: async (res) => {
          if (res.confirm) {
            try {
              await subscriptionStore.unsubscribeAccount(subscription.id)
              // 更新用户限制信息
              await userStore.fetchUserLimits()
            } catch (error) {
              console.error('取消订阅失败:', error)
            }
          }
        }
      })
    }

    // 批量模式切换
    const toggleBatchMode = () => {
      batchMode.value = !batchMode.value
      if (!batchMode.value) {
        selectedSubscriptions.value = []
      }
    }

    // 切换选择状态
    const toggleSelection = (subscriptionId) => {
      const index = selectedSubscriptions.value.indexOf(subscriptionId)
      if (index > -1) {
        selectedSubscriptions.value.splice(index, 1)
      } else {
        selectedSubscriptions.value.push(subscriptionId)
      }
    }

    // 处理项目点击
    const handleItemClick = (subscription) => {
      if (batchMode.value) {
        toggleSelection(subscription.id)
      } else {
        // 可以跳转到博主详情页面
        console.log('查看博主详情:', subscription.account.name)
      }
    }

    // 批量取消订阅
    const handleBatchUnsubscribe = async () => {
      if (selectedSubscriptions.value.length === 0) return

      uni.showModal({
        title: '确认批量取消订阅',
        content: `确定要取消订阅选中的 ${selectedSubscriptions.value.length} 个博主吗？`,
        success: async (res) => {
          if (res.confirm) {
            try {
              await subscriptionStore.batchUnsubscribe(selectedSubscriptions.value)
              // 更新用户限制信息
              await userStore.fetchUserLimits()
              // 退出批量模式
              batchMode.value = false
              selectedSubscriptions.value = []
            } catch (error) {
              console.error('批量取消订阅失败:', error)
            }
          }
        }
      })
    }

    // 导航到搜索页面
    const handleNavigateToSearch = () => {
      navigateToSearch()
    }

    // 显示升级弹窗
    const showUpgradeModal = () => {
      showUpgrade.value = true
    }

    // 隐藏升级弹窗
    const hideUpgradeModal = () => {
      showUpgrade.value = false
    }

    // 升级会员
    const upgradeMembership = async (level) => {
      try {
        await userStore.upgradeMembership(level)
        hideUpgradeModal()
        // 刷新页面数据
        await loadSubscriptions(true)
      } catch (error) {
        console.error('升级会员失败:', error)
      }
    }

    // 增强页面生命周期
    const lifecycle = enhancePageLifecycle(pageState, {
      enablePullRefresh: true,
      onRefresh: refreshSubscriptions
    })

    // 页面初始化
    onMounted(async () => {
      // 检查登录状态
      checkLoginAndNavigate(async () => {
        await loadSubscriptions(true)
      })
    })

    // 注册生命周期钩子
    onPullDownRefresh(lifecycle.onPullDownRefresh)

    return {
      // 状态
      ...pageState.state,
      subscriptions,
      subscriptionsByPlatform,
      userLimits,
      isSubscriptionLimitReached,
      hasMore,
      loading,
      batchMode,
      selectedSubscriptions,
      showUpgrade,
      
      // 方法
      retry,
      loadMore,
      handleUnsubscribe,
      toggleBatchMode,
      toggleSelection,
      handleItemClick,
      handleBatchUnsubscribe,
      handleNavigateToSearch,
      showUpgradeModal,
      hideUpgradeModal,
      upgradeMembership,
      getPlatformName,
      formatFollowerCount,
      
      // 计算属性
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

/* 头部样式 */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30rpx;
}

.title {
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
}

.subscription-count {
  background-color: #e8f4fd;
  padding: 10rpx 20rpx;
  border-radius: 20rpx;
  transition: all 0.3s ease;
}

.subscription-count.limit-reached {
  background-color: #ffebee;
}

.subscription-count.limit-reached .count-text {
  color: #f44336;
}

.count-text {
  font-size: 24rpx;
  color: #007aff;
}

/* 限制警告样式 */
.limit-warning {
  background-color: #fff3cd;
  border: 1px solid #ffeaa7;
  border-radius: 10rpx;
  padding: 20rpx;
  margin-bottom: 20rpx;
}

.warning-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.warning-text {
  color: #856404;
  font-size: 28rpx;
}

.upgrade-btn {
  background-color: #ff6b35;
  color: white;
  border: none;
  padding: 10rpx 20rpx;
  border-radius: 20rpx;
  font-size: 24rpx;
}

/* 操作栏样式 */
.action-bar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20rpx;
}

.btn {
  border-radius: 20rpx;
  font-size: 28rpx;
  padding: 15rpx 30rpx;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-outline {
  background-color: white;
  border: 1px solid #007aff;
}

.btn-outline .btn-text {
  color: #007aff;
}

.btn-danger {
  background-color: #ff4757;
}

.btn-danger .btn-text {
  color: white;
}

.btn-sm {
  padding: 10rpx 20rpx;
  font-size: 24rpx;
}

.btn-text {
  font-size: inherit;
}

/* 批量操作栏样式 */
.batch-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #e3f2fd;
  padding: 15rpx 20rpx;
  border-radius: 10rpx;
  margin-bottom: 20rpx;
}

.selected-count {
  color: #1976d2;
  font-size: 28rpx;
}

/* 订阅列表样式 */
.subscription-list {
  margin-top: 20rpx;
}

.platform-group {
  margin-bottom: 30rpx;
}

.platform-header {
  display: flex;
  align-items: center;
  margin-bottom: 15rpx;
  padding: 0 10rpx;
}

.platform-name {
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
}

.platform-count {
  font-size: 24rpx;
  color: #666;
  margin-left: 10rpx;
}

.subscription-items {
  background-color: white;
  border-radius: 10rpx;
  overflow: hidden;
}

.subscription-item {
  display: flex;
  align-items: center;
  padding: 20rpx;
  border-bottom: 1px solid #f0f0f0;
  transition: background-color 0.2s ease;
}

.subscription-item:last-child {
  border-bottom: none;
}

.subscription-item:active {
  background-color: #f8f9fa;
}

.checkbox-container {
  margin-right: 15rpx;
}

.avatar {
  width: 80rpx;
  height: 80rpx;
  border-radius: 40rpx;
  margin-right: 20rpx;
  background-color: #f0f0f0;
}

.account-info {
  flex: 1;
  min-width: 0;
}

.account-name {
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
  display: block;
  margin-bottom: 8rpx;
}

.account-desc {
  font-size: 24rpx;
  color: #666;
  display: block;
  margin-bottom: 10rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-meta {
  display: flex;
  align-items: center;
  gap: 15rpx;
}

.platform-tag {
  background-color: #e8f4fd;
  color: #007aff;
  font-size: 20rpx;
  padding: 4rpx 10rpx;
  border-radius: 10rpx;
}

.follower-count {
  font-size: 20rpx;
  color: #999;
}

.action-buttons {
  margin-left: 15rpx;
}

/* 加载更多样式 */
.load-more {
  display: flex;
  justify-content: center;
  margin-top: 30rpx;
}

/* 会员升级弹窗样式 */
.upgrade-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.upgrade-content {
  background-color: white;
  border-radius: 20rpx;
  margin: 40rpx;
  max-width: 600rpx;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
}

.upgrade-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 30rpx;
  border-bottom: 1px solid #f0f0f0;
}

.upgrade-title {
  font-size: 32rpx;
  font-weight: bold;
  color: #333;
}

.close-btn {
  font-size: 40rpx;
  color: #999;
  width: 40rpx;
  height: 40rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.membership-options {
  padding: 30rpx;
}

.membership-option {
  border: 2px solid #e0e0e0;
  border-radius: 15rpx;
  padding: 25rpx;
  margin-bottom: 20rpx;
  transition: all 0.3s ease;
}

.membership-option:last-child {
  margin-bottom: 0;
}

.membership-option:active {
  transform: scale(0.98);
}

.membership-option.premium {
  border-color: #ff6b35;
  background-color: #fff8f5;
}

.option-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15rpx;
}

.option-title {
  font-size: 28rpx;
  font-weight: bold;
  color: #333;
}

.option-price {
  font-size: 24rpx;
  color: #ff6b35;
  font-weight: bold;
}

.option-benefits {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.benefit-item {
  font-size: 24rpx;
  color: #666;
  line-height: 1.4;
}

/* 响应式适配 */
@media (max-width: 750rpx) {
  .action-bar {
    flex-direction: column;
    gap: 15rpx;
  }
  
  .batch-actions {
    flex-direction: column;
    gap: 15rpx;
    text-align: center;
  }
  
  .subscription-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 15rpx;
  }
  
  .account-info {
    width: 100%;
  }
  
  .action-buttons {
    margin-left: 0;
    width: 100%;
  }
}
</style>