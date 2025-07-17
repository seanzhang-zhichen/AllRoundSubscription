<template>
  <view class="error-boundary" v-if="hasError">
    <view class="error-content">
      <image src="/static/error-icon.png" class="error-icon" mode="aspectFit" />
      <text class="error-title">页面出现错误</text>
      <text class="error-message">{{ errorMessage }}</text>
      <view class="error-actions">
        <button @click="handleRetry" class="retry-btn">重试</button>
        <button @click="handleGoHome" class="home-btn">返回首页</button>
      </view>
    </view>
  </view>
  <slot v-else />
</template>

<script>
import { ref, onErrorCaptured } from 'vue'
import { navigateToHome } from '@/utils/navigation'

export default {
  name: 'ErrorBoundary',
  props: {
    fallbackMessage: {
      type: String,
      default: '页面加载出现问题，请重试'
    }
  },
  emits: ['retry'],
  setup(props, { emit }) {
    const hasError = ref(false)
    const errorMessage = ref('')

    // 捕获子组件错误
    onErrorCaptured((error, instance, info) => {
      console.error('ErrorBoundary 捕获到错误:', error, info)
      
      hasError.value = true
      errorMessage.value = error.message || props.fallbackMessage
      
      // 阻止错误继续向上传播
      return false
    })

    // 重试处理
    const handleRetry = () => {
      hasError.value = false
      errorMessage.value = ''
      emit('retry')
    }

    // 返回首页
    const handleGoHome = () => {
      navigateToHome()
    }

    // 手动设置错误状态（供外部调用）
    const setError = (error) => {
      hasError.value = true
      errorMessage.value = error.message || error || props.fallbackMessage
    }

    // 清除错误状态
    const clearError = () => {
      hasError.value = false
      errorMessage.value = ''
    }

    return {
      hasError,
      errorMessage,
      handleRetry,
      handleGoHome,
      setError,
      clearError
    }
  }
}
</script>

<style scoped>
.error-boundary {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 40rpx;
  background-color: #f5f5f5;
}

.error-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  background-color: white;
  padding: 60rpx 40rpx;
  border-radius: 20rpx;
  box-shadow: 0 4rpx 20rpx rgba(0, 0, 0, 0.1);
}

.error-icon {
  width: 120rpx;
  height: 120rpx;
  margin-bottom: 30rpx;
  opacity: 0.6;
}

.error-title {
  font-size: 32rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 20rpx;
}

.error-message {
  font-size: 28rpx;
  color: #666;
  line-height: 1.5;
  margin-bottom: 40rpx;
  text-align: center;
}

.error-actions {
  display: flex;
  gap: 20rpx;
}

.retry-btn, .home-btn {
  padding: 25rpx 40rpx;
  border-radius: 10rpx;
  font-size: 28rpx;
  border: none;
}

.retry-btn {
  background-color: #007aff;
  color: white;
}

.home-btn {
  background-color: #f0f0f0;
  color: #333;
}
</style>