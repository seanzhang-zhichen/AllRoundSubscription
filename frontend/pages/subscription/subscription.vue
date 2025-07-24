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
            已订阅: {{ subscriptions.length }}/{{ userLimits.subscription_limit }}
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
        <button v-if="subscriptions.length > 0" class="btn btn-outline btn-sm" @click="toggleBatchMode">
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
      <view v-if="!loading && subscriptions.length > 0" class="subscription-list">
        <!-- 按平台分组显示 -->
        <view v-for="(platformSubs, platform) in subscriptionsByPlatform" :key="platform" class="platform-group">
          <view class="platform-header">
            <text class="platform-name">{{ getPlatformName(platform) }}</text>
            <text class="platform-count">({{ platformSubs.length }})</text>
          </view>

          <view class="subscription-items">
            <view v-for="subscription in platformSubs" :key="subscription.id" class="subscription-item"
              @click="handleItemClick(subscription)">
              <!-- 批量选择模式的复选框 -->
              <view v-if="batchMode" class="checkbox-container">
                <checkbox :checked="selectedSubscriptions.includes(subscription.id)"
                  @click.stop="toggleSelection(subscription.id)" />
              </view>

              <!-- 博主头像 -->
              <image class="avatar" :src="subscription.account.avatar_url || '/static/default-avatar.png'"
                mode="aspectFill" />

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
                <button class="btn btn-danger btn-sm" @click.stop="handleUnsubscribe(subscription)" 
                       :disabled="subscriptionStore.isAccountLoading(subscription.account.id)">
                  <text class="btn-text">取消订阅</text>
                </button>
              </view>
            </view>
          </view>
        </view>

        <!-- 加载更多 -->
        <view v-if="hasMore" class="load-more">
          <button class="btn btn-outline btn-sm" @click="loadMore" :disabled="loading">
            <text class="btn-text">{{ loading ? '加载中...' : '加载更多' }}</text>
          </button>
        </view>
      </view>

      <!-- 空状态 -->
      <Empty v-else-if="!loading && subscriptions.length === 0" icon="subscription" text="还没有订阅任何博主" :show-action="true" action-text="去搜索博主"
        @action="handleNavigateToSearch" />
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
import { ref, computed, onMounted, onActivated } from 'vue'
import { onPullDownRefresh, onShow, onLoad } from '@dcloudio/uni-app'
import { useSubscriptionStore } from '@/stores/subscription'
import { useUserStore } from '@/stores/user'
import { useAuthStore } from '@/stores/auth'
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
  onLoad() {
    console.log('====== 订阅页面加载(onLoad) ======')
    // 在页面加载完成后立即初始化数据
    if (this.loadInitialData) {
      this.loadInitialData()
    }
  },
  onShow() {
    console.log('====== 订阅页面显示(onShow) ======')
    // 每次显示页面时检查数据状态
    if(this.subscriptions && this.subscriptions.length) {
      console.log('订阅页面onShow: 当前已有数据，数量:', this.subscriptions.length)
      // 即使已有数据，也刷新一次，确保数据最新
      if (this.refreshSubscriptions) {
        console.log('订阅页面onShow: 尽管已有数据，仍然刷新确保数据最新')
        this.refreshSubscriptions()
      }
    } else {
      console.log('订阅页面onShow: 无数据或数据为空，尝试加载数据')
      // 如果没有数据，尝试加载数据
      if (!this.loading && this.loadInitialData) {
        this.loadInitialData()
      }
    }
  },
  setup() {
    console.log('====== 订阅页面setup函数执行 ======')
    // Store实例
    const subscriptionStore = useSubscriptionStore()
    const userStore = useUserStore()
    const authStore = useAuthStore()

    // 页面状态管理器
    const pageState = createPageState({
      enableRetry: true,
      maxRetryCount: 3
    })

    // 响应式数据
    const batchMode = ref(false)
    const selectedSubscriptions = ref([])
    const showUpgrade = ref(false)
    const initialLoadComplete = ref(false) 
    
    // 计算属性
    const isLoggedIn = computed(() => authStore.isLoggedIn)
    
    // 添加生命周期钩子
    onMounted(() => {
      console.log('====== 订阅页面已挂载(onMounted) ======')
      // 不需要在onMounted中调用loadInitialData，因为已经在onLoad中调用了
    })
    
    onActivated(() => {
      console.log('====== 订阅页面已激活(onActivated) ======')
      console.log('当前订阅数量:', subscriptionStore.subscriptions.length)
      console.log('onActivated中判断是否需要刷新数据')
      
      // 仅当登录状态有效时刷新数据，避免重复登录检查
      if (isLoggedIn.value && initialLoadComplete.value) {
        loadSubscriptions(true)
      }
    })

    // 初始加载处理
    const loadInitialData = async () => {
      console.log('===== 开始执行初始化加载 =====')
      // 首先检查登录状态
      if (isLoggedIn.value) {
        console.log('用户已登录，直接加载订阅列表')
        await loadSubscriptions(true)
        initialLoadComplete.value = true
      } else {
        console.log('用户未登录，尝试进行登录状态验证')
        const loginSuccess = await authStore.enhancedLoginCheck()
        
        if (loginSuccess) {
          console.log('登录状态验证成功，加载订阅列表')
          await loadSubscriptions(true)
          initialLoadComplete.value = true
        } else {
          console.log('登录状态验证失败，显示登录提示')
          uni.showModal({
            title: '提示',
            content: '请先登录后使用此功能',
            showCancel: true,
            cancelText: '取消',
            confirmText: '去登录',
            success: (res) => {
              if (res.confirm) {
                uni.navigateTo({
                  url: '/pages/login/login'
                })
              }
            }
          })
        }
      }
    }

    // 计算属性
    const subscriptions = computed(() => {
      const subs = subscriptionStore.subscriptions
      console.log('计算属性subscriptions被访问, 订阅数量:', subs.length)
      return subs
    })
    const subscriptionsByPlatform = computed(() => {
      console.log('计算属性subscriptionsByPlatform被访问')
      const grouped = subscriptionStore.subscriptionsByPlatform
      console.log('分组后平台数量:', Object.keys(grouped).length)
      return grouped
    })
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
        'zhihu': '知乎'
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
      console.log('===== 调用loadSubscriptions函数开始 =====')
      console.log('参数 refresh:', refresh)
      console.log('调用前状态 - loading:', pageState.state.loading)
      console.log('调用前状态 - 订阅数量:', subscriptionStore.subscriptions.length)
      try {
        await pageState.executeAsync(async () => {
          console.log('===== 开始执行订阅列表获取逻辑 =====')
          console.log('开始获取订阅数据，是否刷新:', refresh)
          await subscriptionStore.fetchSubscriptions(refresh)
          console.log('订阅列表API调用成功')
          console.log('订阅列表获取完成，当前列表长度:', subscriptionStore.subscriptions.length)
          
          // 同时更新用户限制信息
          console.log('开始获取用户限制信息')
          await userStore.fetchUserLimits()
          console.log('用户限制信息获取完成:', JSON.stringify(userStore.userLimits))
        }, {
          errorMessage: '加载订阅列表失败',
          showLoading: refresh
        })
        console.log('pageState.executeAsync执行完成，无异常')
      } catch (error) {
        console.error('===== 加载订阅列表失败 =====')
        console.error('错误对象:', error)
        console.log('错误消息:', error.message)
        console.log('错误堆栈:', error.stack)
        console.log('网络状态:', uni.getNetworkType())
      } finally {
        console.log('===== loadSubscriptions执行完成 =====')
        console.log('最终状态 - loading:', pageState.state.loading)
        console.log('最终状态 - 错误:', pageState.state.error)
        console.log('最终状态 - 订阅数量:', subscriptionStore.subscriptions.length)
        console.log('最终状态 - 空状态判断:', subscriptionStore.subscriptions.length === 0)
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
      console.log('===== 开始刷新订阅列表(refreshSubscriptions) =====')
      try {
        console.log('重置订阅商店的分页信息，确保从头开始获取')
        // 确保刷新时重置分页，确保能获取最新数据
        subscriptionStore.pagination = {
          page: 1,
          size: 20,
          total: 0,
          hasMore: true
        }
        
        // 强制刷新数据
        await loadSubscriptions(true)
        
        // 在刷新后检查并打印数据
        console.log('刷新完成，检查数据：订阅数量=', subscriptionStore.subscriptions.length)
        console.log('分组后数据:', Object.keys(subscriptionStore.subscriptionsByPlatform).length, '个平台')
        
        // 如果刷新后依然没有数据但API返回了数据，可能是UI没有更新
        if (subscriptionStore.subscriptions.length > 0 && Object.keys(subscriptionStore.subscriptionsByPlatform).length === 0) {
          console.warn('警告：API返回了数据，但分组结果为空，可能存在数据格式问题')
          console.log('尝试重新载入页面以解决问题')
          setTimeout(() => {
            // 如果在APP中，可以尝试刷新当前页面
            const pages = getCurrentPages()
            const currentPage = pages[pages.length - 1]
            if (currentPage && currentPage.route.includes('subscription')) {
              uni.redirectTo({
                url: '/pages/subscription/subscription'
              })
            }
          }, 500)
        }
      } catch (error) {
        console.error('刷新订阅列表失败:', error)
      } finally {
        console.log('停止下拉刷新动画')
        uni.stopPullDownRefresh()
        console.log('===== 刷新订阅列表完成 =====')
      }
    }

    // 加载更多
    const loadMore = async () => {
      console.log('===== 尝试加载更多订阅(loadMore) =====')
      console.log('当前状态 - hasMore:', hasMore.value, '| loading:', loading.value)
      
      if (!hasMore.value || loading.value) {
        console.log('不满足加载条件，直接返回')
        return
      }
      
      try {
        console.log('开始执行加载更多')
        await loadSubscriptions(false)
        console.log('加载更多完成')
      } catch (error) {
        console.error('加载更多失败:', error)
      } finally {
        console.log('===== 加载更多操作结束 =====')
      }
    }

    // 处理取消订阅
    const handleUnsubscribe = async (subscription) => {
      try {
        await subscriptionStore.unsubscribeAccount(subscription.id)
        // 更新用户限制信息
        await userStore.fetchUserLimits()
      } catch (error) {
        console.error('取消订阅失败:', error)
      }
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
      console.log('订阅页面挂载，准备加载数据')
      // 检查已在onLoad中完成，这里不需要重复检查
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
      isLoggedIn,
      subscriptionStore,

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
      loadInitialData,
      loadSubscriptions,
      refreshSubscriptions,

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