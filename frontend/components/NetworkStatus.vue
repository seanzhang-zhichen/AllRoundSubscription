<template>
  <view class="network-status" v-if="showStatus">
    <!-- 网络状态指示器 -->
    <view class="status-indicator" :class="statusClass">
      <view class="indicator-dot"></view>
      <text class="status-text">{{ statusText }}</text>
    </view>
    
    <!-- 详细信息（可展开） -->
    <view class="status-details" v-if="showDetails">
      <view class="detail-item">
        <text class="detail-label">网络类型:</text>
        <text class="detail-value">{{ networkTypeText }}</text>
      </view>
      <view class="detail-item">
        <text class="detail-label">连接质量:</text>
        <text class="detail-value">{{ qualityText }}</text>
      </view>
      <view class="detail-item" v-if="networkState.latency > 0">
        <text class="detail-label">延迟:</text>
        <text class="detail-value">{{ networkState.latency }}ms</text>
      </view>
      <view class="detail-item" v-if="networkState.downloadSpeed > 0">
        <text class="detail-label">速度:</text>
        <text class="detail-value">{{ formatSpeed(networkState.downloadSpeed) }}</text>
      </view>
    </view>
    
    <!-- 离线提示 -->
    <view class="offline-notice" v-if="!networkState.isOnline">
      <text class="offline-text">当前处于离线状态，部分功能可能受限</text>
      <view class="offline-actions">
        <button class="retry-btn" @click="retryConnection">重试连接</button>
      </view>
    </view>
  </view>
</template>

<script>
import { computed, ref } from 'vue'
import { useNetwork } from '@/utils/networkManager'
import { useFeedback } from '@/utils/feedbackManager'

export default {
  name: 'NetworkStatus',
  props: {
    // 是否显示状态
    show: {
      type: Boolean,
      default: true
    },
    // 是否显示详细信息
    showDetails: {
      type: Boolean,
      default: false
    },
    // 是否只在离线时显示
    showOnlyWhenOffline: {
      type: Boolean,
      default: false
    },
    // 自动隐藏时间（毫秒）
    autoHideDelay: {
      type: Number,
      default: 0
    }
  },
  setup(props) {
    const network = useNetwork()
    const feedback = useFeedback()
    
    const { networkState } = network
    
    // 显示状态
    const showStatus = computed(() => {
      if (!props.show) return false
      if (props.showOnlyWhenOffline) {
        return !networkState.isOnline
      }
      return true
    })
    
    // 状态样式类
    const statusClass = computed(() => {
      if (!networkState.isOnline) return 'status-offline'
      
      switch (networkState.connectionQuality) {
        case 'excellent': return 'status-excellent'
        case 'good': return 'status-good'
        case 'fair': return 'status-fair'
        case 'poor': return 'status-poor'
        default: return 'status-unknown'
      }
    })
    
    // 状态文本
    const statusText = computed(() => {
      if (!networkState.isOnline) return '离线'
      
      const qualityMap = {
        'excellent': '优秀',
        'good': '良好',
        'fair': '一般',
        'poor': '较差'
      }
      
      return qualityMap[networkState.connectionQuality] || '未知'
    })
    
    // 网络类型文本
    const networkTypeText = computed(() => {
      return network.getNetworkTypeDescription()
    })
    
    // 质量文本
    const qualityText = computed(() => {
      return network.getQualityDescription()
    })
    
    // 格式化速度
    const formatSpeed = (speedKbps) => {
      if (speedKbps < 1024) {
        return `${speedKbps.toFixed(1)} Kbps`
      } else {
        return `${(speedKbps / 1024).toFixed(1)} Mbps`
      }
    }
    
    // 重试连接
    const retryConnection = async () => {
      try {
        feedback.showLoading('检查网络连接...')
        
        // 触发网络状态更新
        await network.updateNetworkStatus()
        
        feedback.hideLoading()
        
        if (networkState.isOnline) {
          feedback.showSuccess('网络连接已恢复')
        } else {
          feedback.showWarning('网络仍然不可用，请检查网络设置')
        }
      } catch (error) {
        feedback.hideLoading()
        feedback.showError('网络检查失败')
      }
    }
    
    return {
      networkState,
      showStatus,
      statusClass,
      statusText,
      networkTypeText,
      qualityText,
      formatSpeed,
      retryConnection
    }
  }
}
</script>

<style scoped>
.network-status {
  background-color: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 16rpx 24rpx;
  border-radius: 8rpx;
  margin: 16rpx;
  font-size: 24rpx;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.indicator-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-excellent .indicator-dot {
  background-color: #52c41a;
  box-shadow: 0 0 8rpx rgba(82, 196, 26, 0.6);
}

.status-good .indicator-dot {
  background-color: #1890ff;
  box-shadow: 0 0 8rpx rgba(24, 144, 255, 0.6);
}

.status-fair .indicator-dot {
  background-color: #faad14;
  box-shadow: 0 0 8rpx rgba(250, 173, 20, 0.6);
}

.status-poor .indicator-dot {
  background-color: #ff4d4f;
  box-shadow: 0 0 8rpx rgba(255, 77, 79, 0.6);
}

.status-offline .indicator-dot {
  background-color: #8c8c8c;
  box-shadow: 0 0 8rpx rgba(140, 140, 140, 0.6);
}

.status-text {
  font-size: 28rpx;
  font-weight: 500;
}

.status-details {
  margin-top: 16rpx;
  padding-top: 16rpx;
  border-top: 1rpx solid rgba(255, 255, 255, 0.2);
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8rpx;
}

.detail-label {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.8);
}

.detail-value {
  font-size: 24rpx;
  font-weight: 500;
}

.offline-notice {
  margin-top: 16rpx;
  padding-top: 16rpx;
  border-top: 1rpx solid rgba(255, 255, 255, 0.2);
}

.offline-text {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.9);
  line-height: 1.4;
  margin-bottom: 16rpx;
}

.offline-actions {
  display: flex;
  justify-content: center;
}

.retry-btn {
  background-color: #1890ff;
  color: white;
  border: none;
  padding: 16rpx 32rpx;
  border-radius: 6rpx;
  font-size: 24rpx;
  cursor: pointer;
}

.retry-btn:active {
  background-color: #0050b3;
}

/* 响应式设计 */
@media screen and (max-width: 750rpx) {
  .network-status {
    margin: 12rpx;
    padding: 12rpx 20rpx;
  }
  
  .status-text {
    font-size: 26rpx;
  }
  
  .detail-label,
  .detail-value,
  .offline-text {
    font-size: 22rpx;
  }
}

/* 动画效果 */
.indicator-dot {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.1);
    opacity: 0.8;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

.status-offline .indicator-dot {
  animation: none;
  opacity: 0.6;
}
</style>