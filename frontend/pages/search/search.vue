<template>
  <view class="container">
    <Loading v-if="loading && !searchStore.hasResults" />
    <view v-else-if="error" class="error-container">
      <view class="error-message">{{ error }}</view>
      <button v-if="canRetry" @click="retry" class="retry-btn">重试</button>
    </view>
    <view v-else class="content">
      <!-- 搜索头部 -->
      <view class="search-header">
        <view class="search-box">
          <input v-model="searchKeyword" placeholder="搜索博主..." class="search-input" @confirm="handleSearch"
            @input="onSearchInput" />
          <button @click="handleSearch" class="search-btn" :disabled="searchStore.isSearching">
            {{ searchStore.isSearching ? '搜索中' : '搜索' }}
          </button>
        </view>
      </view>

      <!-- 平台筛选 -->
      <view class="platform-filter" v-if="supportedPlatforms.length > 0">
        <scroll-view class="platform-scroll" scroll-x>
          <view class="platform-list">
            <view class="platform-item" :class="{ active: selectedPlatforms.length === 0 }" @click="selectAllPlatforms">
              <text class="platform-text">全部</text>
            </view>
            <view v-for="platform in supportedPlatforms" :key="platform.key" class="platform-item"
              :class="{ active: selectedPlatforms.includes(platform.key) }" @click="togglePlatform(platform.key)">
              <image class="platform-icon" :src="platform.icon" mode="aspectFit" />
              <text class="platform-text">{{ platform.name }}</text>
              <text v-if="searchStore.getPlatformResultCount(platform.key) > 0" class="platform-count">
                {{ searchStore.getPlatformResultCount(platform.key) }}
              </text>
            </view>
          </view>
        </scroll-view>
      </view>

      <!-- 搜索历史 -->
      <view v-if="!searchStore.currentKeyword && !searchStore.hasResults && appStore.searchHistory.length > 0"
        class="search-history">
        <view class="history-header">
          <text class="history-title">搜索历史</text>
          <button class="clear-history-btn" @click="clearSearchHistory">清除</button>
        </view>
        <view class="history-list">
          <view v-for="(keyword, index) in appStore.searchHistory" :key="index" class="history-item"
            @click="searchFromHistory(keyword)">
            <text class="history-keyword">{{ keyword }}</text>
            <view class="history-remove" @click.stop="removeHistoryItem(keyword)">×</view>
          </view>
        </view>
      </view>

      <!-- 搜索结果 -->
      <view v-if="searchStore.hasResults" class="search-results">
        <view class="results-header">
          <text class="results-count">
            {{ searchStore.currentKeyword ? `找到 ${searchStore.searchStats.totalResults} 个博主` : `共
            ${searchStore.searchStats.totalResults} 个博主` }}
          </text>
        </view>

        <view class="results-list">
          <view v-for="account in searchStore.searchResults" :key="account.id" class="account-item"
            @click="viewAccountDetail(account)">
            <view class="account-avatar">
              <image :src="account.avatar_url" mode="aspectFill" class="avatar-img" />
              <view class="platform-badge" :style="{ backgroundColor: getPlatformColor(account.platform) }">
                <image :src="getPlatformIcon(account.platform)" mode="aspectFit" class="badge-icon" />
              </view>
            </view>

            <view class="account-info">
              <view class="account-name">{{ account.name }}</view>
              <view class="account-desc">{{ account.description || '暂无简介' }}</view>
              <view class="account-stats">
                <text class="follower-count">{{ formatFollowerCount(account.follower_count) }} 关注者</text>
                <text class="platform-name">{{ getPlatformName(account.platform) }}</text>
              </view>
              
              <button class="subscribe-btn" :class="{
                subscribed: isAccountSubscribed(account.id),
                loading: subscriptionStore.isAccountLoading(account.id)
              }" @click.stop="toggleSubscribe(account)" :disabled="subscriptionStore.isAccountLoading(account.id)">
                <text v-if="isAccountSubscribed(account.id)" class="unsubscribe-text">退订</text>
                <text v-else class="subscribe-text">订阅</text>
              </button>
            </view>
          </view>
        </view>

        <!-- 加载更多 -->
        <view v-if="searchStore.pagination.hasMore" class="load-more">
          <button class="load-more-btn" @click="loadMoreResults" :disabled="searchStore.loading">
            {{ searchStore.loading ? '加载中...' : '加载更多' }}
          </button>
        </view>
      </view>

      <!-- 无搜索结果 -->
      <Empty v-if="searchStore.currentKeyword && !searchStore.hasResults && !searchStore.isSearching" icon="search"
        text="未找到相关博主" :show-action="true" action-text="换个关键词试试" @action="clearSearch" />

      <!-- 默认状态 -->
      <view v-if="!searchStore.currentKeyword && !searchStore.hasResults && appStore.searchHistory.length === 0"
        class="default-state">
        <view class="default-content">
          <image class="default-icon" src="/static/search-default.png" mode="aspectFit" />
          <text class="default-text">搜索你感兴趣的博主</text>
          <text class="default-desc">支持搜索微信公众号、微博、Twitter等平台</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import Loading from '@/components/Loading.vue'
import Empty from '@/components/Empty.vue'
import { createPageState } from '@/utils/pageState'
import { checkLoginAndNavigate } from '@/utils/navigation'
import { useSearchStore, useAppStore, useSubscriptionStore, useAuthStore } from '@/stores'
import { onShow } from '@dcloudio/uni-app'

export default {
  name: 'SearchPage',
  components: {
    Loading,
    Empty
  },
  setup() {
    // 状态管理
    const searchStore = useSearchStore()
    const appStore = useAppStore()
    const subscriptionStore = useSubscriptionStore()
    const authStore = useAuthStore()

    // 创建页面状态管理器
    const pageState = createPageState({
      enableRetry: true,
      maxRetryCount: 3
    })

    // 响应式数据
    const searchKeyword = ref('')
    const selectedPlatforms = ref([])
    const supportedPlatforms = ref([])
    const searchTimer = ref(null)

    // 计算属性
    const isLoggedIn = computed(() => authStore.isLoggedIn)
    
    // 添加计算属性来缓存订阅状态，避免重复检查
    const subscribedAccountIds = ref({});

    // 初始化页面时只检查一次所有博主的订阅状态
    const initSubscriptionStatus = () => {
      if (searchStore.searchResults && searchStore.searchResults.length > 0) {
        const ids = {};
        searchStore.searchResults.forEach(account => {
          if (account && account.id) {
            ids[account.id] = subscriptionStore.isSubscribed(account.id);
          }
        });
        subscribedAccountIds.value = ids;
      }
    };

    // 高效检查账号是否已订阅，使用缓存结果
    const isAccountSubscribed = (accountId) => {
      return subscribedAccountIds.value[accountId] || false;
    };
    
    // 更新单个账号的订阅状态缓存
    const updateSubscriptionCache = (accountId, isSubscribed) => {
      subscribedAccountIds.value = {
        ...subscribedAccountIds.value,
        [accountId]: isSubscribed
      };
    };

    // 初始化页面
    onMounted(async () => {
      try {
        // 加载支持的平台列表
        supportedPlatforms.value = appStore.supportedPlatforms

        // 如果用户已登录，加载订阅列表
        if (isLoggedIn.value) {
          await subscriptionStore.fetchSubscriptions(true)
        }

        // 如果有搜索关键词，恢复搜索状态
        if (searchStore.currentKeyword) {
          searchKeyword.value = searchStore.currentKeyword
          selectedPlatforms.value = [...searchStore.selectedPlatforms]
        } else if (!searchStore.hasResults) {
          // 如果没有搜索关键词且没有结果，加载所有博主
          await searchStore.searchAccounts('', [], true)
        }
        
        // 初始化订阅状态缓存
        initSubscriptionStatus();

        console.log('搜索页面初始化完成')
      } catch (error) {
        console.error('搜索页面初始化失败:', error)
      }
    })

    // 每次页面显示时都刷新订阅状态
    onShow(async () => {
      console.log('搜索页面显示')
      try {
        // 如果用户已登录，刷新订阅列表
        if (isLoggedIn.value) {
          await subscriptionStore.fetchSubscriptions(true)
        }
        
        // 刷新所有博主的订阅状态
        initSubscriptionStatus();
      } catch (error) {
        console.error('刷新订阅状态失败:', error)
      }
    })

    // 清理定时器
    onUnmounted(() => {
      if (searchTimer.value) {
        clearTimeout(searchTimer.value)
      }
    })

    // 搜索输入处理
    const onSearchInput = () => {
      // 清除之前的定时器
      if (searchTimer.value) {
        clearTimeout(searchTimer.value)
      }

      // 设置新的定时器，实现防抖
      searchTimer.value = setTimeout(() => {
        // 可以在这里实现搜索建议功能
        console.log('搜索输入:', searchKeyword.value)
      }, 300)
    }

    // 执行搜索
    const handleSearch = async () => {
      if (!searchKeyword.value.trim()) {
        uni.showToast({
          title: '请输入搜索关键词',
          icon: 'none'
        })
        return
      }

      await pageState.executeAsync(async () => {
        await searchStore.searchAccounts(
          searchKeyword.value,
          selectedPlatforms.value,
          true // 刷新搜索
        )
        
        // 搜索完成后更新订阅状态缓存
        initSubscriptionStatus();
      }, {
        errorMessage: '搜索失败，请重试'
      })
    }

    // 重试搜索
    const retry = async () => {
      await pageState.retry(async () => {
        if (searchStore.currentKeyword) {
          await searchStore.refreshSearch()
        }
      })
    }

    // 从搜索历史搜索
    const searchFromHistory = async (keyword) => {
      searchKeyword.value = keyword
      await handleSearch()
    }

    // 清除搜索历史
    const clearSearchHistory = async () => {
      const confirmed = await appStore.showConfirm('确认清除', '确定要清除所有搜索历史吗？')
      if (confirmed) {
        appStore.clearSearchHistory()
      }
    }

    // 删除单个历史记录
    const removeHistoryItem = (keyword) => {
      appStore.removeSearchHistory(keyword)
    }

    // 选择所有平台
    const selectAllPlatforms = async () => {
      selectedPlatforms.value = []
      // 加载所有平台的博主
      await searchStore.searchAccounts('', [], true)
    }

    // 切换平台选择
    const togglePlatform = async (platformKey) => {
      const index = selectedPlatforms.value.indexOf(platformKey)
      if (index > -1) {
        selectedPlatforms.value.splice(index, 1)
      } else {
        selectedPlatforms.value.push(platformKey)
      }

      // 如果有搜索关键词，按关键词搜索；否则加载该平台的所有博主
      if (searchStore.currentKeyword) {
        await searchStore.filterByPlatforms(selectedPlatforms.value)
      } else {
        await searchStore.searchAccounts('', selectedPlatforms.value, true)
      }
      
      // 筛选后更新订阅状态缓存
      initSubscriptionStatus();
    }

    // 加载更多结果
    const loadMoreResults = async () => {
      try {
        await searchStore.loadMoreResults()
        // 加载更多后更新订阅状态缓存
        initSubscriptionStatus();
      } catch (error) {
        console.error('加载更多失败:', error)
        uni.showToast({
          title: '加载失败，请重试',
          icon: 'none'
        })
      }
    }

    // 查看博主详情
    const viewAccountDetail = (account) => {
      console.log('查看博主详情:', account)
      uni.navigateTo({
        url: `/pages/account/detail?id=${account.id}&platform=${account.platform}`
      })
    }

    // 切换订阅状态
    const toggleSubscribe = async (account) => {
      try {
        // 检查用户是否已登录
        if (!isLoggedIn.value) {
          uni.showToast({
            title: '请先登录',
            icon: 'none'
          })
          return
        }
        
        // 获取当前订阅状态，使用缓存的订阅状态
        const currentlySubscribed = isAccountSubscribed(account.id)
        
        if (currentlySubscribed) {
          // 先更新本地状态缓存，使按钮立即变化
          updateSubscriptionCache(account.id, false);
          // 同时更新store状态，以保持一致性
          subscriptionStore.updateLocalSubscriptionState(account.id, false)
          // 取消订阅，确保传递平台参数
          await subscriptionStore.unsubscribeByAccountId(account.id, account.platform)
        } else {
          // 先更新本地状态缓存，使按钮立即变化
          updateSubscriptionCache(account.id, true);
          // 同时更新store状态，以保持一致性
          subscriptionStore.updateLocalSubscriptionState(account.id, true, account.platform)
          // 创建订阅
          await subscriptionStore.subscribeAccount(account.id, account.platform)
        }
        
        // 强制更新订阅状态视图
        await nextTick()
      } catch (error) {
        console.error('订阅操作失败:', error)
        // 操作失败时恢复原状态缓存
        const currentStatus = !isAccountSubscribed(account.id);
        updateSubscriptionCache(account.id, currentStatus);
        // 同时恢复store状态
        subscriptionStore.updateLocalSubscriptionState(account.id, currentStatus, account.platform)
      }
    }

    // 清除搜索
    const clearSearch = () => {
      searchKeyword.value = ''
      selectedPlatforms.value = []
      searchStore.clearSearchResults()
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

    return {
      // 状态
      ...pageState.state,
      searchStore,
      appStore,
      subscriptionStore,

      // 响应式数据
      searchKeyword,
      selectedPlatforms,
      supportedPlatforms,

      // 计算属性
      isLoggedIn,
      
      // 方法
      onSearchInput,
      handleSearch,
      retry,
      searchFromHistory,
      clearSearchHistory,
      removeHistoryItem,
      selectAllPlatforms,
      togglePlatform,
      loadMoreResults,
      viewAccountDetail,
      isAccountSubscribed, // 使用新的高效检查方法
      toggleSubscribe,
      clearSearch,
      getPlatformName,
      getPlatformIcon,
      getPlatformColor,
      formatFollowerCount,

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

/* 搜索头部 */
.search-header {
  margin-bottom: 20rpx;
}

.search-box {
  display: flex;
  align-items: center;
  background-color: white;
  border-radius: 10rpx;
  padding: 20rpx;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.1);
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 28rpx;
  margin-right: 20rpx;
}

.search-btn {
  background-color: #007aff;
  color: white;
  border: none;
  padding: 15rpx 30rpx;
  border-radius: 8rpx;
  font-size: 26rpx;
  min-width: 120rpx;
}

.search-btn:disabled {
  background-color: #ccc;
  opacity: 0.6;
}

/* 平台筛选 */
.platform-filter {
  margin-bottom: 20rpx;
}

.platform-scroll {
  white-space: nowrap;
}

.platform-list {
  display: flex;
  padding: 10rpx 0;
}

.platform-item {
  display: flex;
  align-items: center;
  background-color: white;
  border-radius: 20rpx;
  padding: 15rpx 25rpx;
  margin-right: 20rpx;
  border: 2rpx solid #e5e5e5;
  min-width: 120rpx;
  justify-content: center;
  position: relative;
}

.platform-item.active {
  background-color: #007aff;
  border-color: #007aff;
}

.platform-item.active .platform-text {
  color: white;
}

.platform-icon {
  width: 32rpx;
  height: 32rpx;
  margin-right: 10rpx;
}

.platform-text {
  font-size: 24rpx;
  color: #333;
  white-space: nowrap;
}

.platform-count {
  position: absolute;
  top: -10rpx;
  right: -10rpx;
  background-color: #ff4757;
  color: white;
  font-size: 20rpx;
  padding: 4rpx 8rpx;
  border-radius: 10rpx;
  min-width: 20rpx;
  text-align: center;
}

/* 搜索历史 */
.search-history {
  background-color: white;
  border-radius: 10rpx;
  padding: 30rpx;
  margin-bottom: 20rpx;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20rpx;
}

.history-title {
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
}

.clear-history-btn {
  background: none;
  border: none;
  color: #999;
  font-size: 24rpx;
  padding: 0;
}

.history-list {
  display: flex;
  flex-wrap: wrap;
  gap: 15rpx;
}

.history-item {
  display: flex;
  align-items: center;
  background-color: #f8f9fa;
  border-radius: 20rpx;
  padding: 15rpx 20rpx;
  position: relative;
}

.history-keyword {
  font-size: 26rpx;
  color: #666;
  margin-right: 10rpx;
}

.history-remove {
  color: #999;
  font-size: 30rpx;
  width: 30rpx;
  height: 30rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background-color: #e5e5e5;
}

/* 搜索结果 */
.search-results {
  background-color: white;
  border-radius: 10rpx;
  overflow: hidden;
}

.results-header {
  padding: 30rpx;
  border-bottom: 1rpx solid #f0f0f0;
}

.results-count {
  font-size: 28rpx;
  color: #666;
}

.results-list {
  padding: 0;
}

.account-item {
  display: flex;
  align-items: center;
  padding: 30rpx;
  border-bottom: 1rpx solid #f0f0f0;
  position: relative;
}

.account-item:last-child {
  border-bottom: none;
}

.account-avatar {
  position: relative;
  margin-right: 20rpx;
}

.avatar-img {
  width: 80rpx;
  height: 80rpx;
  border-radius: 50%;
}

.platform-badge {
  position: absolute;
  bottom: -5rpx;
  right: -5rpx;
  width: 30rpx;
  height: 30rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2rpx solid white;
}

.badge-icon {
  width: 20rpx;
  height: 20rpx;
}

.account-info {
  flex: 1;
  margin-right: 20rpx;
}

.account-name {
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 8rpx;
}

.account-desc {
  font-size: 24rpx;
  color: #666;
  margin-bottom: 8rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-stats {
  display: flex;
  align-items: center;
  gap: 20rpx;
}

.follower-count {
  font-size: 22rpx;
  color: #999;
}

.platform-name {
  font-size: 22rpx;
  color: #007aff;
}



.subscribe-btn {
  background-color: transparent;
  border: 1rpx solid #007aff;
  color: #007aff;
  padding: 8rpx 16rpx;
  border-radius: 10rpx;
  font-size: 22rpx;
  min-width: 80rpx;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  position: absolute;
  right: 30rpx;
  top: 28rpx;
}

.subscribe-btn:hover {
  transform: translateY(-1rpx);
  box-shadow: 0 2rpx 8rpx rgba(0, 122, 255, 0.2);
}

.subscribe-btn.subscribed {
  border: 1rpx solid #ff4757;
  background-color: transparent;
  color: #ff4757;
}

.subscribe-btn.subscribed:hover {
  border-color: #ff3742;
  box-shadow: 0 2rpx 8rpx rgba(255, 71, 87, 0.2);
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
  color: inherit;
}

.unsubscribe-text {
  color: inherit;
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

/* 默认状态 */
.default-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}

.default-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.default-icon {
  width: 200rpx;
  height: 200rpx;
  margin-bottom: 30rpx;
  opacity: 0.5;
}

.default-text {
  font-size: 32rpx;
  color: #333;
  margin-bottom: 15rpx;
}

.default-desc {
  font-size: 26rpx;
  color: #999;
  line-height: 1.5;
}

/* 响应式调整 */
@media (max-width: 750rpx) {
  .account-item {
    padding: 20rpx;
  }

  .avatar-img {
    width: 60rpx;
    height: 60rpx;
  }

  .account-name {
    font-size: 28rpx;
  }

  .account-desc {
    font-size: 22rpx;
  }
}
</style>