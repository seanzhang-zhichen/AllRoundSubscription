<template>
  <view class="lazy-image-container" :style="containerStyle">
    <!-- 占位符 -->
    <view 
      v-if="!loaded && !error" 
      class="image-placeholder"
      :style="placeholderStyle"
    >
      <view class="placeholder-content">
        <view class="placeholder-icon" v-if="showPlaceholderIcon">
          <text class="icon-text">📷</text>
        </view>
        <view class="placeholder-text" v-if="placeholderText">
          {{ placeholderText }}
        </view>
        <view class="loading-spinner" v-if="loading">
          <view class="spinner"></view>
        </view>
      </view>
    </view>
    
    <!-- 实际图片 -->
    <image
      v-if="shouldLoad"
      :src="optimizedSrc"
      :mode="mode"
      :lazy-load="true"
      :fade-in="true"
      :webp="true"
      class="lazy-image"
      :class="{ 'image-loaded': loaded, 'image-error': error }"
      :style="imageStyle"
      @load="handleLoad"
      @error="handleError"
      @click="handleClick"
    />
    
    <!-- 错误状态 -->
    <view 
      v-if="error" 
      class="image-error-placeholder"
      :style="placeholderStyle"
      @click="retry"
    >
      <view class="error-content">
        <text class="error-icon">❌</text>
        <text class="error-text">图片加载失败</text>
        <text class="retry-text">点击重试</text>
      </view>
    </view>
    
    <!-- 加载进度条 -->
    <view 
      v-if="loading && showProgress" 
      class="loading-progress"
    >
      <view class="progress-bar" :style="{ width: progress + '%' }"></view>
    </view>
  </view>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import performanceOptimizer from '@/utils/performanceOptimizer'
import { useCache, CacheType, CachePriority } from '@/utils/cacheManager'
import { useNetwork } from '@/utils/networkManager'

export default {
  name: 'LazyImage',
  props: {
    // 图片源
    src: {
      type: String,
      required: true
    },
    // 图片模式
    mode: {
      type: String,
      default: 'aspectFill'
    },
    // 宽度
    width: {
      type: [String, Number],
      default: '100%'
    },
    // 高度
    height: {
      type: [String, Number],
      default: 'auto'
    },
    // 占位符文本
    placeholderText: {
      type: String,
      default: ''
    },
    // 是否显示占位符图标
    showPlaceholderIcon: {
      type: Boolean,
      default: true
    },
    // 是否显示加载进度
    showProgress: {
      type: Boolean,
      default: false
    },
    // 懒加载阈值（像素）
    threshold: {
      type: Number,
      default: 100
    },
    // 是否启用图片优化
    optimize: {
      type: Boolean,
      default: true
    },
    // 图片优化选项
    optimizeOptions: {
      type: Object,
      default: () => ({})
    },
    // 重试次数
    maxRetries: {
      type: Number,
      default: 3
    },
    // 是否可点击
    clickable: {
      type: Boolean,
      default: false
    }
  },
  emits: ['load', 'error', 'click'],
  setup(props, { emit }) {
    // 状态管理
    const loaded = ref(false)
    const loading = ref(false)
    const error = ref(false)
    const shouldLoad = ref(false)
    const progress = ref(0)
    const retryCount = ref(0)
    
    // 交叉观察器
    const observer = ref(null)
    const containerRef = ref(null)
    
    // 缓存和网络管理
    const cache = useCache()
    const network = useNetwork()

    // 计算属性
    const containerStyle = computed(() => ({
      width: typeof props.width === 'number' ? `${props.width}rpx` : props.width,
      height: typeof props.height === 'number' ? `${props.height}rpx` : props.height,
      position: 'relative',
      overflow: 'hidden'
    }))

    const placeholderStyle = computed(() => ({
      width: '100%',
      height: '100%',
      backgroundColor: '#f5f5f5',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      position: 'absolute',
      top: 0,
      left: 0,
      zIndex: 1
    }))

    const imageStyle = computed(() => ({
      width: '100%',
      height: '100%',
      opacity: loaded.value ? 1 : 0,
      transition: 'opacity 0.3s ease-in-out'
    }))

    const optimizedSrc = computed(() => {
      if (!props.src || !props.optimize) {
        return props.src
      }

      // 根据网络状况调整图片质量
      const quality = network.getRecommendedImageQuality()
      const qualityMap = { low: 0.6, medium: 0.8, high: 1.0 }

      return performanceOptimizer.optimizeImage(props.src, {
        width: typeof props.width === 'number' ? props.width : 750,
        height: typeof props.height === 'number' ? props.height : 750,
        quality: qualityMap[quality] || 0.8,
        ...props.optimizeOptions
      })
    })

    // 缓存键
    const cacheKey = computed(() => `image:${optimizedSrc.value}`)

    // 初始化懒加载
    const initLazyLoad = () => {
      try {
        // 创建交叉观察器
        observer.value = uni.createIntersectionObserver()
        
        observer.value.relativeToViewport({
          bottom: props.threshold
        }).observe('.lazy-image-container', (res) => {
          if (res.intersectionRatio > 0 && !shouldLoad.value) {
            console.log('图片进入可视区域，开始加载:', props.src)
            shouldLoad.value = true
            startLoading()
          }
        })
      } catch (error) {
        console.error('懒加载初始化失败:', error)
        // 如果懒加载失败，直接加载图片
        shouldLoad.value = true
        startLoading()
      }
    }

    // 开始加载
    const startLoading = async () => {
      if (loading.value || loaded.value) return
      
      // 首先检查缓存
      try {
        const cachedImage = await cache.get(cacheKey.value)
        if (cachedImage) {
          console.log('使用缓存图片:', props.src)
          loaded.value = true
          emit('load', { cached: true })
          return
        }
      } catch (error) {
        console.warn('获取图片缓存失败:', error)
      }
      
      loading.value = true
      progress.value = 0
      error.value = false

      // 模拟加载进度（实际项目中可以通过其他方式获取真实进度）
      if (props.showProgress) {
        const progressInterval = setInterval(() => {
          if (progress.value < 90) {
            progress.value += Math.random() * 20
          } else {
            clearInterval(progressInterval)
          }
        }, 100)
      }
    }

    // 处理图片加载成功
    const handleLoad = async (event) => {
      loading.value = false
      loaded.value = true
      progress.value = 100
      error.value = false
      retryCount.value = 0

      // 缓存图片信息
      try {
        await cache.set(cacheKey.value, {
          src: optimizedSrc.value,
          loadTime: Date.now(),
          size: event.detail?.width * event.detail?.height || 0
        }, {
          type: CacheType.IMAGE,
          priority: CachePriority.NORMAL,
          ttl: 24 * 60 * 60 * 1000 // 24小时
        })
      } catch (error) {
        console.warn('缓存图片信息失败:', error)
      }

      console.log('图片加载成功:', props.src)
      emit('load', event)
    }

    // 处理图片加载失败
    const handleError = (event) => {
      loading.value = false
      loaded.value = false
      error.value = true
      progress.value = 0

      console.error('图片加载失败:', props.src, event)
      emit('error', event)
    }

    // 重试加载
    const retry = () => {
      if (retryCount.value >= props.maxRetries) {
        console.log('已达到最大重试次数，停止重试')
        return
      }

      retryCount.value++
      console.log(`重试加载图片 (${retryCount.value}/${props.maxRetries}):`, props.src)
      
      // 重置状态
      loaded.value = false
      loading.value = false
      error.value = false
      
      // 延迟重试，避免频繁请求
      setTimeout(() => {
        startLoading()
      }, 1000 * retryCount.value)
    }

    // 处理点击事件
    const handleClick = (event) => {
      if (props.clickable) {
        emit('click', event)
      }
    }

    // 预加载图片
    const preloadImage = async () => {
      try {
        await performanceOptimizer.preloadResources([{
          type: 'image',
          url: optimizedSrc.value
        }], {
          priority: 'low'
        })
      } catch (error) {
        console.error('图片预加载失败:', error)
      }
    }

    // 监听src变化
    watch(() => props.src, (newSrc, oldSrc) => {
      if (newSrc !== oldSrc) {
        // 重置状态
        loaded.value = false
        loading.value = false
        error.value = false
        shouldLoad.value = false
        retryCount.value = 0
        
        // 重新初始化懒加载
        if (observer.value) {
          observer.value.disconnect()
        }
        initLazyLoad()
      }
    })

    // 生命周期
    onMounted(() => {
      initLazyLoad()
      
      // 如果图片在可视区域内，立即开始预加载
      if (props.optimize) {
        preloadImage()
      }
    })

    onUnmounted(() => {
      if (observer.value) {
        observer.value.disconnect()
      }
    })

    return {
      loaded,
      loading,
      error,
      shouldLoad,
      progress,
      containerStyle,
      placeholderStyle,
      imageStyle,
      optimizedSrc,
      handleLoad,
      handleError,
      handleClick,
      retry
    }
  }
}
</script>

<style scoped>
.lazy-image-container {
  position: relative;
  overflow: hidden;
  border-radius: 8rpx;
}

.image-placeholder {
  background: linear-gradient(45deg, #f0f0f0 25%, transparent 25%), 
              linear-gradient(-45deg, #f0f0f0 25%, transparent 25%), 
              linear-gradient(45deg, transparent 75%, #f0f0f0 75%), 
              linear-gradient(-45deg, transparent 75%, #f0f0f0 75%);
  background-size: 20rpx 20rpx;
  background-position: 0 0, 0 10rpx, 10rpx -10rpx, -10rpx 0rpx;
  animation: placeholder-shimmer 2s infinite linear;
}

@keyframes placeholder-shimmer {
  0% {
    background-position: 0 0, 0 10rpx, 10rpx -10rpx, -10rpx 0rpx;
  }
  100% {
    background-position: 20rpx 20rpx, 20rpx 30rpx, 30rpx 10rpx, 10rpx 20rpx;
  }
}

.placeholder-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #999;
}

.placeholder-icon {
  margin-bottom: 16rpx;
}

.icon-text {
  font-size: 48rpx;
  opacity: 0.5;
}

.placeholder-text {
  font-size: 24rpx;
  color: #999;
  margin-bottom: 16rpx;
}

.loading-spinner {
  display: flex;
  align-items: center;
  justify-content: center;
}

.spinner {
  width: 40rpx;
  height: 40rpx;
  border: 4rpx solid #f3f3f3;
  border-top: 4rpx solid #007aff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.lazy-image {
  display: block;
  transition: opacity 0.3s ease-in-out;
}

.image-loaded {
  opacity: 1;
}

.image-error {
  opacity: 0;
}

.image-error-placeholder {
  background-color: #f8f8f8;
  border: 2rpx dashed #ddd;
  cursor: pointer;
}

.error-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #999;
}

.error-icon {
  font-size: 48rpx;
  margin-bottom: 16rpx;
  opacity: 0.5;
}

.error-text {
  font-size: 24rpx;
  color: #666;
  margin-bottom: 8rpx;
}

.retry-text {
  font-size: 20rpx;
  color: #007aff;
}

.loading-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 4rpx;
  background-color: rgba(0, 0, 0, 0.1);
  z-index: 2;
}

.progress-bar {
  height: 100%;
  background-color: #007aff;
  transition: width 0.3s ease;
}

/* 响应式设计 */
@media screen and (max-width: 750rpx) {
  .icon-text {
    font-size: 40rpx;
  }
  
  .placeholder-text {
    font-size: 22rpx;
  }
  
  .error-text {
    font-size: 22rpx;
  }
}

/* 暗色模式支持 */
@media (prefers-color-scheme: dark) {
  .image-placeholder {
    background-color: #2a2a2a;
  }
  
  .placeholder-content,
  .error-content {
    color: #ccc;
  }
  
  .image-error-placeholder {
    background-color: #2a2a2a;
    border-color: #444;
  }
  
  .loading-progress {
    background-color: rgba(255, 255, 255, 0.1);
  }
}
</style>