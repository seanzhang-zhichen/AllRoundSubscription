<template>
  <view class="container">
    <Loading v-if="loading" />
    <view v-else-if="error" class="error-container">
      <view class="error-message">{{ error }}</view>
      <button v-if="canRetry" @click="retry" class="retry-btn">重试</button>
    </view>
    <scroll-view v-else class="content" scroll-y :refresher-enabled="true" 
      :refresher-triggered="refreshing" @refresherrefresh="onRefresh">
      <!-- 用户信息卡片 -->
      <view class="user-info-card">
        <view class="user-header">
          <view class="avatar">
            <image 
              :src="userInfo.avatar_url || '/static/default-avatar.png'" 
              class="avatar-img" 
              mode="aspectFill"
            />
          </view>
          <view class="user-details">
            <text class="nickname">{{ userInfo.nickname || '未设置昵称' }}</text>
            <view class="membership-badge" :class="membershipClass">
              <text class="membership-text">{{ membershipLevelName }}</text>
            </view>
          </view>
          <view class="edit-btn" @click="showEditProfile">
            <text class="edit-text">编辑</text>
          </view>
        </view>
        
        <!-- 使用统计 -->
        <view class="stats-section">
          <view class="stats-item">
            <text class="stats-number">{{ userLimits?.current_subscriptions || 0 }}</text>
            <text class="stats-label">已订阅</text>
          </view>
          <view class="stats-divider"></view>
          <view class="stats-item">
            <text class="stats-number">{{ userLimits?.today_pushes || 0 }}</text>
            <text class="stats-label">今日推送</text>
          </view>
          <view class="stats-divider"></view>
          <view class="stats-item">
            <text class="stats-number">{{ daysSinceJoined }}</text>
            <text class="stats-label">使用天数</text>
          </view>
        </view>
      </view>

      <!-- 会员权益卡片 -->
      <view class="membership-card">
        <view class="card-header">
          <text class="card-title">会员权益</text>
          <view class="upgrade-btn" @click="showMembershipUpgrade" v-if="!isPaidMember">
            <text class="upgrade-text">升级</text>
          </view>
        </view>
        <view class="benefits-list">
          <view class="benefit-item">
            <view class="benefit-icon">📚</view>
            <view class="benefit-content">
              <text class="benefit-title">订阅限制</text>
              <text class="benefit-desc">{{ subscriptionLimitText }}</text>
            </view>
          </view>
          <view class="benefit-item">
            <view class="benefit-icon">🔔</view>
            <view class="benefit-content">
              <text class="benefit-title">推送限制</text>
              <text class="benefit-desc">{{ pushLimitText }}</text>
            </view>
          </view>
          <view class="benefit-item" v-if="userInfo.membership_expire_at">
            <view class="benefit-icon">⏰</view>
            <view class="benefit-content">
              <text class="benefit-title">到期时间</text>
              <text class="benefit-desc">{{ formatExpireTime }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 设置菜单 -->
      <view class="menu-section">
        <view class="menu-item" @click="showPushSettings">
          <view class="menu-icon">🔔</view>
          <text class="menu-text">推送设置</text>
          <text class="menu-arrow">></text>
        </view>
        <view class="menu-item" @click="showAbout">
          <view class="menu-icon">ℹ️</view>
          <text class="menu-text">关于我们</text>
          <text class="menu-arrow">></text>
        </view>
      </view>

      <!-- 退出登录按钮 -->
      <view class="logout-section">
        <button class="logout-btn" @click="handleLogout">退出登录</button>
      </view>
    </scroll-view>

    <!-- 编辑资料弹窗 -->
    <view class="modal" v-if="showEditModal" @click="hideEditProfile">
      <view class="modal-content" @click.stop>
        <view class="modal-header">
          <text class="modal-title">编辑资料</text>
          <view class="modal-close" @click="hideEditProfile">×</view>
        </view>
        <view class="modal-body">
          <view class="form-item">
            <text class="form-label">昵称</text>
            <input 
              class="form-input" 
              v-model="editForm.nickname" 
              placeholder="请输入昵称"
              maxlength="20"
            />
          </view>
        </view>
        <view class="modal-footer">
          <button class="modal-btn cancel-btn" @click="hideEditProfile">取消</button>
          <button class="modal-btn confirm-btn" @click="saveProfile" :disabled="saving">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </view>
      </view>
    </view>

    <!-- 推送设置弹窗 -->
    <view class="modal" v-if="showPushModal" @click="hidePushSettings">
      <view class="modal-content" @click.stop>
        <view class="modal-header">
          <text class="modal-title">推送设置</text>
          <view class="modal-close" @click="hidePushSettings">×</view>
        </view>
        <view class="modal-body">
          <view class="form-item">
            <text class="form-label">启用推送</text>
            <switch 
              :checked="settingsForm.push_enabled" 
              @change="onPushEnabledChange"
              color="#007aff"
            />
          </view>
          <view class="form-item" v-if="settingsForm.push_enabled">
            <text class="form-label">推送时间段</text>
            <view class="time-range">
              <picker 
                mode="time" 
                :value="settingsForm.push_time_start" 
                @change="onStartTimeChange"
              >
                <view class="time-picker">{{ settingsForm.push_time_start }}</view>
              </picker>
              <text class="time-separator">至</text>
              <picker 
                mode="time" 
                :value="settingsForm.push_time_end" 
                @change="onEndTimeChange"
              >
                <view class="time-picker">{{ settingsForm.push_time_end }}</view>
              </picker>
            </view>
          </view>
        </view>
        <view class="modal-footer">
          <button class="modal-btn cancel-btn" @click="hidePushSettings">取消</button>
          <button class="modal-btn confirm-btn" @click="savePushSettings" :disabled="saving">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { onMounted, ref, computed } from 'vue'
import { useUserStore } from '@/stores/user'
import { useAuthStore } from '@/stores/auth'
import Loading from '@/components/Loading.vue'
import { createPageState } from '@/utils/pageState'
import { checkLoginAndNavigate, navigateToLogin } from '@/utils/navigation'

export default {
  name: 'ProfilePage',
  components: {
    Loading
  },
  setup() {
    const userStore = useUserStore()
    const authStore = useAuthStore()
    
    // 创建页面状态管理器
    const pageState = createPageState({
      enableRetry: true,
      maxRetryCount: 3
    })

    // 确保userLimits有默认值
    if (!userStore.userLimits) {
      userStore.$patch({
        userLimits: {
          subscription_limit: 10,
          current_subscriptions: 0,
          push_limit: 10,
          today_pushes: 0
        }
      })
    }

    // 弹窗状态
    const showEditModal = ref(false)
    const showPushModal = ref(false)
    const saving = ref(false)

    // 表单数据
    const editForm = ref({
      nickname: ''
    })

    const settingsForm = ref({
      push_enabled: true,
      push_time_start: '09:00',
      push_time_end: '22:00',
      language: 'zh-CN'
    })

    // 计算属性
    const userInfo = computed(() => userStore.userInfo)
    const userLimits = computed(() => userStore.userLimits)
    const membershipLevelName = computed(() => userStore.membershipLevelName)
    const isPaidMember = computed(() => userStore.isPaidMember)

    // 会员等级样式类
    const membershipClass = computed(() => {
      const level = userInfo.value?.membership_level || 'free'
      return {
        'membership-free': level === 'free',
        'membership-basic': level === 'basic',
        'membership-premium': level === 'premium'
      }
    })

    // 使用天数计算
    const daysSinceJoined = computed(() => {
      if (!userInfo.value?.created_at) return 0
      const joinDate = new Date(userInfo.value.created_at)
      const today = new Date()
      const diffTime = Math.abs(today - joinDate)
      return Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    })

    // 订阅限制文本
    const subscriptionLimitText = computed(() => {
      const limit = userLimits.value?.subscription_limit || 10
      const current = userLimits.value?.current_subscriptions || 0
      if (limit === -1) return '无限制'
      return `${current}/${limit}个`
    })

    // 推送限制文本
    const pushLimitText = computed(() => {
      const limit = userLimits.value?.push_limit || 10
      const current = userLimits.value?.today_pushes || 0
      if (limit === -1) return '无限制'
      return `${current}/${limit}次/天`
    })

    // 到期时间格式化
    const formatExpireTime = computed(() => {
      if (!userInfo.value?.membership_expire_at) return ''
      const expireDate = new Date(userInfo.value.membership_expire_at)
      return expireDate.toLocaleDateString('zh-CN')
    })

    // 初始化数据
    const initializeData = async () => {
      try {
        pageState.setLoading(true)
        
        // 检查登录状态
        const isLoggedIn = await authStore.checkLoginStatus()
        if (!isLoggedIn) {
          navigateToLogin()
          return
        }

        // 获取用户信息和限制
        try {
          await userStore.fetchUserProfile()
        } catch (e) {
          console.error('获取用户资料失败:', e)
        }
        
        try {
          await userStore.fetchUserLimits()
        } catch (e) {
          console.error('获取用户限制失败:', e)
        }

        // 加载用户设置
        try {
          userStore.loadUserSettings()
        } catch (e) {
          console.error('加载用户设置失败:', e)
        }
        
        // 初始化表单数据
        editForm.value.nickname = userInfo.value.nickname || ''
        settingsForm.value = { 
          ...settingsForm.value,
          ...(userStore.userSettings || {})
        }
        
      } catch (error) {
        console.error('初始化数据失败:', error)
        pageState.setError('加载用户信息失败')
      } finally {
        pageState.setLoading(false)
      }
    }

    // 重试逻辑
    const retry = async () => {
      await pageState.retry(initializeData)
    }

    // 显示编辑资料弹窗
    const showEditProfile = () => {
      editForm.value.nickname = userInfo.value.nickname || ''
      showEditModal.value = true
    }

    // 隐藏编辑资料弹窗
    const hideEditProfile = () => {
      showEditModal.value = false
    }

    // 保存用户资料
    const saveProfile = async () => {
      try {
        saving.value = true
        
        await userStore.updateUserProfile({
          nickname: editForm.value.nickname
        })
        
        uni.showToast({
          title: '保存成功',
          icon: 'success'
        })
        
        hideEditProfile()
        
      } catch (error) {
        console.error('保存资料失败:', error)
        uni.showToast({
          title: '保存失败，请重试',
          icon: 'none'
        })
      } finally {
        saving.value = false
      }
    }

    // 显示会员升级
    const showMembershipUpgrade = () => {
      uni.showActionSheet({
        itemList: ['V1 - ¥6.9/月', 'V2 - ¥9.9/月', 'V3 - ¥14.9/月', 'V4 - ¥19.9/月', 'V5 - ¥29.9/月'],
        success: async (res) => {
          const levels = ['v1', 'v2', 'v3', 'v4', 'v5']
          const level = levels[res.tapIndex]
          
          uni.showModal({
            title: '确认升级',
            content: `确定要升级到${levels[res.tapIndex].toUpperCase()} 吗？`,
            success: async (modalRes) => {
              if (modalRes.confirm) {
                try {
                  await userStore.upgradeMembership(level, 1)
                } catch (error) {
                  console.error('升级失败:', error)
                }
              }
            }
          })
        }
      })
    }

    // 显示推送设置弹窗
    const showPushSettings = () => {
      settingsForm.value = { 
        ...settingsForm.value,
        ...(userStore.userSettings || {})
      }
      showPushModal.value = true
    }

    // 隐藏推送设置弹窗
    const hidePushSettings = () => {
      showPushModal.value = false
    }

    // 推送开关变化
    const onPushEnabledChange = (e) => {
      settingsForm.value.push_enabled = e.detail.value
    }

    // 开始时间变化
    const onStartTimeChange = (e) => {
      settingsForm.value.push_time_start = e.detail.value
    }

    // 结束时间变化
    const onEndTimeChange = (e) => {
      settingsForm.value.push_time_end = e.detail.value
    }

    // 保存推送设置
    const savePushSettings = async () => {
      try {
        saving.value = true
        
        await userStore.updateUserSettings(settingsForm.value)
        
        uni.showToast({
          title: '设置已保存',
          icon: 'success'
        })
        
        hidePushSettings()
        
      } catch (error) {
        console.error('保存设置失败:', error)
        uni.showToast({
          title: '保存失败，请重试',
          icon: 'none'
        })
      } finally {
        saving.value = false
      }
    }

    // 显示关于我们
    const showAbout = () => {
      uni.showModal({
        title: '关于我们',
        content: '多平台内容聚合小程序 v1.0.0\n\n一个让您轻松管理多平台内容订阅的工具',
        showCancel: false,
        confirmText: '知道了'
      })
    }

    // 处理登出
    const handleLogout = async () => {
      uni.showModal({
        title: '确认登出',
        content: '确定要退出登录吗？',
        success: async (res) => {
          if (res.confirm) {
            try {
              await authStore.logout()
            } catch (error) {
              console.error('登出失败:', error)
              uni.showToast({
                title: '登出失败，请重试',
                icon: 'none'
              })
            }
          }
        }
      })
    }

    // 添加刷新状态和方法
    const refreshing = ref(false)

    // 下拉刷新方法
    const onRefresh = async () => {
      refreshing.value = true
      try {
        await initializeData()
        uni.showToast({
          title: '刷新成功',
          icon: 'success'
        })
      } catch (error) {
        console.error('刷新失败:', error)
      } finally {
        refreshing.value = false
      }
    }

    onMounted(() => {
      initializeData()
    })

    return {
      ...pageState.state,
      retry,
      canRetry: pageState.canRetry,
      
      // 添加刷新状态
      refreshing,
      onRefresh,
      
      // 数据
      userInfo,
      userLimits,
      membershipLevelName,
      isPaidMember,
      membershipClass,
      daysSinceJoined,
      subscriptionLimitText,
      pushLimitText,
      formatExpireTime,
      
      // 弹窗状态
      showEditModal,
      showPushModal,
      saving,
      
      // 表单数据
      editForm,
      settingsForm,
      
      // 方法
      showEditProfile,
      hideEditProfile,
      saveProfile,
      showMembershipUpgrade,
      showPushSettings,
      hidePushSettings,
      onPushEnabledChange,
      onStartTimeChange,
      onEndTimeChange,
      savePushSettings,
      showAbout,
      handleLogout
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

/* 用户信息卡片 */
.user-info-card {
  background-color: white;
  border-radius: 16rpx;
  margin-bottom: 30rpx;
  overflow: hidden;
}

.user-header {
  display: flex;
  align-items: center;
  padding: 30rpx;
}

.avatar {
  margin-right: 30rpx;
}

.avatar-img {
  width: 120rpx;
  height: 120rpx;
  border-radius: 60rpx;
  border: 2rpx solid #f0f0f0;
}

.user-details {
  flex: 1;
}

.nickname {
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 12rpx;
}

.membership-badge {
  display: inline-block;
  padding: 8rpx 16rpx;
  border-radius: 20rpx;
  font-size: 24rpx;
}

.membership-free {
  background-color: #f0f0f0;
  color: #666;
}

.membership-basic {
  background-color: #e3f2fd;
  color: #1976d2;
}

.membership-premium {
  background-color: #fff3e0;
  color: #f57c00;
}

.membership-text {
  font-weight: 500;
}

.edit-btn {
  padding: 12rpx 24rpx;
  background-color: #f8f9fa;
  border-radius: 20rpx;
  border: 1rpx solid #e9ecef;
}

.edit-text {
  font-size: 26rpx;
  color: #007aff;
}

/* 统计区域 */
.stats-section {
  display: flex;
  padding: 30rpx;
  border-top: 1rpx solid #f0f0f0;
}

.stats-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stats-number {
  font-size: 32rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 8rpx;
}

.stats-label {
  font-size: 24rpx;
  color: #999;
}

.stats-divider {
  width: 1rpx;
  height: 60rpx;
  background-color: #f0f0f0;
  margin: 0 20rpx;
}

/* 会员权益卡片 */
.membership-card {
  background-color: white;
  border-radius: 16rpx;
  margin-bottom: 30rpx;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 30rpx;
  border-bottom: 1rpx solid #f0f0f0;
}

.card-title {
  font-size: 32rpx;
  font-weight: bold;
  color: #333;
}

.upgrade-btn {
  padding: 12rpx 24rpx;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 20rpx;
}

.upgrade-text {
  font-size: 26rpx;
  color: white;
  font-weight: 500;
}

.benefits-list {
  padding: 20rpx 30rpx 30rpx;
}

.benefit-item {
  display: flex;
  align-items: center;
  margin-bottom: 24rpx;
}

.benefit-item:last-child {
  margin-bottom: 0;
}

.benefit-icon {
  width: 60rpx;
  height: 60rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32rpx;
  margin-right: 20rpx;
}

.benefit-content {
  flex: 1;
}

.benefit-title {
  font-size: 28rpx;
  color: #333;
  font-weight: 500;
  margin-bottom: 6rpx;
}

.benefit-desc {
  font-size: 24rpx;
  color: #666;
}

/* 菜单区域 */
.menu-section {
  background-color: white;
  border-radius: 16rpx;
  margin-bottom: 30rpx;
  overflow: hidden;
}

.menu-item {
  display: flex;
  align-items: center;
  padding: 30rpx;
  border-bottom: 1rpx solid #f0f0f0;
}

.menu-item:last-child {
  border-bottom: none;
}

.menu-icon {
  width: 50rpx;
  height: 50rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28rpx;
  margin-right: 20rpx;
}

.menu-text {
  flex: 1;
  font-size: 30rpx;
  color: #333;
}

.menu-value {
  font-size: 26rpx;
  color: #999;
  margin-right: 10rpx;
}

.menu-arrow {
  font-size: 30rpx;
  color: #ccc;
}

/* 退出登录区域 */
.logout-section {
  margin-bottom: 40rpx;
}

.logout-btn {
  width: 100%;
  background-color: #ff4757;
  color: white;
  border: none;
  padding: 30rpx;
  border-radius: 16rpx;
  font-size: 32rpx;
  font-weight: 500;
}

/* 弹窗样式 */
.modal {
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

.modal-content {
  background-color: white;
  border-radius: 20rpx;
  width: 600rpx;
  max-height: 80vh;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 30rpx;
  border-bottom: 1rpx solid #f0f0f0;
}

.modal-title {
  font-size: 32rpx;
  font-weight: bold;
  color: #333;
}

.modal-close {
  width: 60rpx;
  height: 60rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40rpx;
  color: #999;
}

.modal-body {
  padding: 30rpx;
  max-height: 400rpx;
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  padding: 20rpx 30rpx 30rpx;
  gap: 20rpx;
}

.modal-btn {
  flex: 1;
  padding: 24rpx;
  border-radius: 12rpx;
  font-size: 30rpx;
  border: none;
}

.cancel-btn {
  background-color: #f8f9fa;
  color: #666;
}

.confirm-btn {
  background-color: #007aff;
  color: white;
}

.confirm-btn:disabled {
  background-color: #ccc;
}

/* 表单样式 */
.form-item {
  margin-bottom: 30rpx;
}

.form-item:last-child {
  margin-bottom: 0;
}

.form-label {
  display: block;
  font-size: 28rpx;
  color: #333;
  margin-bottom: 16rpx;
  font-weight: 500;
}

.form-input {
  width: 100%;
  padding: 24rpx;
  border: 1rpx solid #e9ecef;
  border-radius: 12rpx;
  font-size: 28rpx;
  background-color: #f8f9fa;
}

.form-input:focus {
  border-color: #007aff;
  background-color: white;
}

/* 时间选择器 */
.time-range {
  display: flex;
  align-items: center;
  gap: 20rpx;
}

.time-picker {
  flex: 1;
  padding: 24rpx;
  border: 1rpx solid #e9ecef;
  border-radius: 12rpx;
  background-color: #f8f9fa;
  text-align: center;
  font-size: 28rpx;
  color: #333;
}

.time-separator {
  font-size: 26rpx;
  color: #666;
}
</style>