<template>
  <view class="page-preloader" v-if="visible">
    <view class="preloader-content">
      <!-- Logo -->
      <view class="logo-container">
        <image src="/static/logo.png" class="logo" mode="aspectFit" />
      </view>
      
      <!-- 加载动画 -->
      <view class="loading-animation">
        <view class="loading-dots">
          <view class="dot" :class="{ active: activeIndex === 0 }"></view>
          <view class="dot" :class="{ active: activeIndex === 1 }"></view>
          <view class="dot" :class="{ active: activeIndex === 2 }"></view>
        </view>
      </view>
      
      <!-- 加载文本 -->
      <view class="loading-text">
        <text class="text">{{ loadingText }}</text>
      </view>
      
      <!-- 进度条 -->
      <view class="progress-container" v-if="showProgress">
        <view class="progress-bar">
          <view class="progress-fill" :style="{ width: progress + '%' }"></view>
        </view>
        <text class="progress-text">{{ Math.round(progress) }}%</text>
      </view>
      
      <!-- 提示信息 -->
      <view class="tips-container" v-if="showTips">
        <text class="tips-text">{{ currentTip }}</text>
      </view>
    </view>
  </view>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'

export default {
  name: 'PagePreloader',
  props: {
    // 是否显示
    visible: {
      type: Boolean,
      default: true
    },
    // 是否显示进度条
    showProgress: {
      type: Boolean,
      default: false
    },
    // 进度值 (0-100)
    progress: {
      type: Number,
      default: 0
    },
    // 是否显示提示
    showTips: {
      type: Boolean,
      default: true
    },
    // 自定义加载文本
    customLoadingText: {
      type: String,
      default: ''
    },
    // 动画持续时间
    duration: {
      type: Number,
      default: 2000
    }
  },
  emits: ['complete'],
  setup(props, { emit }) {
    // 状态管理
    const activeIndex = ref(0)
    const currentTipIndex = ref(0)
    
    // 动画定时器
    const animationTimer = ref(null)
    const tipTimer = ref(null)
    
    // 加载文本列表
    const loadingTexts = [
      '正在加载...',
      '初始化中...',
      '准备就绪...',
      '即将完成...'
    ]
    
    // 提示信息列表
    const tips = [
      '💡 发现更多精彩内容',
      '🔍 搜索你感兴趣的博主',
      '📱 一站式内容聚合平台',
      '⚡ 实时推送最新动态',
      '🎯 个性化内容推荐'
    ]
    
    // 计算属性
    const loadingText = computed(() => {
      if (props.customLoadingText) {
        return props.customLoadingText
      }
      
      const progressIndex = Math.floor((props.progress / 100) * loadingTexts.length)
      return loadingTexts[Math.min(progressIndex, loadingTexts.length - 1)]
    })
    
    const currentTip = computed(() => {
      return tips[currentTipIndex.value]
    })
    
    // 启动加载动画
    const startAnimation = () => {
      animationTimer.value = setInterval(() => {
        activeIndex.value = (activeIndex.value + 1) % 3
      }, 500)
    }
    
    // 启动提示轮播
    const startTipRotation = () => {
      tipTimer.value = setInterval(() => {
        currentTipIndex.value = (currentTipIndex.value + 1) % tips.length
      }, 3000)
    }
    
    // 停止所有动画
    const stopAnimations = () => {
      if (animationTimer.value) {
        clearInterval(animationTimer.value)
        animationTimer.value = null
      }
      
      if (tipTimer.value) {
        clearInterval(tipTimer.value)
        tipTimer.value = null
      }
    }
    
    // 完成加载
    const complete = () => {
      stopAnimations()
      emit('complete')
    }
    
    // 生命周期
    onMounted(() => {
      startAnimation()
      
      if (props.showTips) {
        startTipRotation()
      }
      
      // 如果设置了持续时间，自动完成
      if (props.duration > 0) {
        setTimeout(() => {
          complete()
        }, props.duration)
      }
    })
    
    onUnmounted(() => {
      stopAnimations()
    })
    
    return {
      activeIndex,
      currentTipIndex,
      loadingText,
      currentTip,
      complete
    }
  }
}
</script>

<style scoped>
.page-preloader {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.preloader-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 60rpx;
}

.logo-container {
  margin-bottom: 60rpx;
  animation: logoFloat 2s ease-in-out infinite;
}

@keyframes logoFloat {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10rpx);
  }
}

.logo {
  width: 120rpx;
  height: 120rpx;
  border-radius: 20rpx;
  box-shadow: 0 8rpx 24rpx rgba(0, 0, 0, 0.15);
}

.loading-animation {
  margin-bottom: 40rpx;
}

.loading-dots {
  display: flex;
  gap: 16rpx;
  align-items: center;
  justify-content: center;
}

.dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.3);
  transition: all 0.3s ease;
}

.dot.active {
  background-color: rgba(255, 255, 255, 0.9);
  transform: scale(1.2);
}

.loading-text {
  margin-bottom: 40rpx;
}

.text {
  font-size: 32rpx;
  color: rgba(255, 255, 255, 0.9);
  font-weight: 500;
}

.progress-container {
  width: 300rpx;
  margin-bottom: 40rpx;
}

.progress-bar {
  width: 100%;
  height: 6rpx;
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 3rpx;
  overflow: hidden;
  margin-bottom: 16rpx;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #fff 0%, rgba(255, 255, 255, 0.8) 100%);
  border-radius: 3rpx;
  transition: width 0.3s ease;
  animation: progressShimmer 2s infinite;
}

@keyframes progressShimmer {
  0% {
    background-position: -100% 0;
  }
  100% {
    background-position: 100% 0;
  }
}

.progress-text {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.7);
  text-align: center;
}

.tips-container {
  position: absolute;
  bottom: 100rpx;
  left: 60rpx;
  right: 60rpx;
}

.tips-text {
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.8);
  text-align: center;
  line-height: 1.5;
  animation: tipFadeIn 0.5s ease-in-out;
}

@keyframes tipFadeIn {
  from {
    opacity: 0;
    transform: translateY(20rpx);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 响应式设计 */
@media screen and (max-width: 750rpx) {
  .preloader-content {
    padding: 40rpx;
  }
  
  .logo {
    width: 100rpx;
    height: 100rpx;
  }
  
  .text {
    font-size: 28rpx;
  }
  
  .progress-container {
    width: 250rpx;
  }
  
  .tips-container {
    bottom: 80rpx;
    left: 40rpx;
    right: 40rpx;
  }
  
  .tips-text {
    font-size: 24rpx;
  }
}

/* 暗色模式支持 */
@media (prefers-color-scheme: dark) {
  .page-preloader {
    background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
  }
}

/* 减少动画效果（用户偏好） */
@media (prefers-reduced-motion: reduce) {
  .page-preloader,
  .logo-container,
  .dot,
  .progress-fill,
  .tips-text {
    animation: none;
  }
  
  .dot.active {
    transform: none;
  }
}
</style>