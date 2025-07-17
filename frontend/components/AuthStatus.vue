<template>
  <view class="auth-status" v-if="showStatus">
    <view class="status-item" :class="statusClass">
      <text class="status-icon">{{ statusIcon }}</text>
      <text class="status-text">{{ statusText }}</text>
    </view>
    <view class="token-info" v-if="showDetails && authStore.isLoggedIn">
      <text class="info-text">剩余时间: {{ tokenStatus.remainingTimeFormatted }}</text>
    </view>
  </view>
</template>

<script>
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

export default {
  name: 'AuthStatus',
  props: {
    showStatus: {
      type: Boolean,
      default: true
    },
    showDetails: {
      type: Boolean,
      default: false
    }
  },
  setup(props) {
    const authStore = useAuthStore()
    
    // 计算认证状态
    const tokenStatus = computed(() => authStore.tokenStatus)
    
    const statusClass = computed(() => {
      if (!authStore.isLoggedIn) return 'status-error'
      if (tokenStatus.value.isExpiringSoon) return 'status-warning'
      return 'status-success'
    })
    
    const statusIcon = computed(() => {
      if (!authStore.isLoggedIn) return '❌'
      if (tokenStatus.value.isExpiringSoon) return '⚠️'
      return '✅'
    })
    
    const statusText = computed(() => {
      if (!authStore.isLoggedIn) return '未登录'
      if (tokenStatus.value.isExpired) return '登录已过期'
      if (tokenStatus.value.isExpiringSoon) return '登录即将过期'
      return '已登录'
    })
    
    return {
      authStore,
      tokenStatus,
      statusClass,
      statusIcon,
      statusText
    }
  }
}
</script>

<style scoped>
.auth-status {
  padding: 10rpx;
  border-radius: 8rpx;
  background-color: #f8f9fa;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 10rpx;
}

.status-success {
  color: #28a745;
}

.status-warning {
  color: #ffc107;
}

.status-error {
  color: #dc3545;
}

.status-icon {
  font-size: 24rpx;
}

.status-text {
  font-size: 24rpx;
  font-weight: 500;
}

.token-info {
  margin-top: 8rpx;
  padding-left: 34rpx;
}

.info-text {
  font-size: 20rpx;
  color: #6c757d;
}
</style>