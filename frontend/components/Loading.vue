<template>
  <view class="loading-container" v-if="show">
    <view class="loading-content">
      <view class="loading-spinner" :class="{ 'loading-spinner-large': size === 'large' }">
        <view class="spinner-dot" v-for="n in 3" :key="n"></view>
      </view>
      <text class="loading-text" v-if="text">{{ text }}</text>
    </view>
  </view>
</template>

<script>
export default {
  name: 'Loading',
  props: {
    show: {
      type: Boolean,
      default: false
    },
    text: {
      type: String,
      default: '加载中...'
    },
    size: {
      type: String,
      default: 'normal', // normal | large
      validator: (value) => ['normal', 'large'].includes(value)
    },
    overlay: {
      type: Boolean,
      default: false
    }
  }
}
</script>

<style scoped>
.loading-container {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40rpx;
}

.loading-container.overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 9999;
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.loading-spinner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
}

.loading-spinner-large {
  gap: 12rpx;
}

.spinner-dot {
  width: 12rpx;
  height: 12rpx;
  background-color: #3cc51f;
  border-radius: 50%;
  animation: loading-bounce 1.4s ease-in-out infinite both;
}

.loading-spinner-large .spinner-dot {
  width: 16rpx;
  height: 16rpx;
}

.spinner-dot:nth-child(1) {
  animation-delay: -0.32s;
}

.spinner-dot:nth-child(2) {
  animation-delay: -0.16s;
}

.loading-text {
  margin-top: 20rpx;
  font-size: 28rpx;
  color: #666;
  text-align: center;
}

@keyframes loading-bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}
</style>