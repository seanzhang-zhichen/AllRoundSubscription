<template>
  <view class="empty-container">
    <view class="empty-content">
      <image 
        class="empty-icon" 
        :src="iconSrc" 
        mode="aspectFit"
      />
      <text class="empty-text">{{ text }}</text>
      <view class="empty-action" v-if="showAction">
        <button 
          class="btn btn-outline btn-sm" 
          @click="handleAction"
        >
          {{ actionText }}
        </button>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  name: 'Empty',
  props: {
    text: {
      type: String,
      default: '暂无数据'
    },
    icon: {
      type: String,
      default: 'default'
    },
    showAction: {
      type: Boolean,
      default: false
    },
    actionText: {
      type: String,
      default: '重新加载'
    }
  },
  computed: {
    iconSrc() {
      const iconMap = {
        'default': '/static/empty-default.png',
        'search': '/static/empty-search.png',
        'subscription': '/static/empty-subscription.png',
        'content': '/static/empty-content.png',
        'network': '/static/empty-network.png'
      }
      return iconMap[this.icon] || iconMap['default']
    }
  },
  methods: {
    handleAction() {
      this.$emit('action')
    }
  }
}
</script>

<style scoped>
.empty-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400rpx;
  padding: 40rpx;
}

.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.empty-icon {
  width: 120rpx;
  height: 120rpx;
  margin-bottom: 30rpx;
  opacity: 0.5;
}

.empty-text {
  font-size: 28rpx;
  color: #999;
  line-height: 1.5;
  margin-bottom: 30rpx;
}

.empty-action {
  margin-top: 20rpx;
}
</style>