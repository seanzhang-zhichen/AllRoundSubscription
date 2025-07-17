<template>
  <view class="share-button-container">
    <!-- 分享按钮 -->
    <button 
      v-if="showButton"
      @click="handleShareClick" 
      class="share-btn"
      :class="{ 'share-btn-mini': mini }"
    >
      <uni-icons type="redo" size="16" color="#666"></uni-icons>
      <text class="share-text" v-if="!mini">{{ buttonText }}</text>
    </button>
    
    <!-- 分享弹窗 -->
    <uni-popup ref="sharePopup" type="bottom" background-color="#fff">
      <view class="share-popup">
        <view class="share-header">
          <text class="share-title">分享到</text>
          <view class="share-close" @click="closeSharePopup">
            <uni-icons type="close" size="20" color="#999"></uni-icons>
          </view>
        </view>
        
        <view class="share-content">
          <view class="share-preview" v-if="shareData">
            <image 
              v-if="shareData.imageUrl" 
              :src="shareData.imageUrl" 
              class="share-preview-image"
              mode="aspectFill"
            />
            <view class="share-preview-info">
              <text class="share-preview-title">{{ shareData.title }}</text>
              <text class="share-preview-desc">{{ shareDescription }}</text>
            </view>
          </view>
          
          <view class="share-options">
            <view class="share-option" @click="shareToFriend">
              <view class="share-option-icon friend-icon">
                <uni-icons type="chat" size="24" color="#07c160"></uni-icons>
              </view>
              <text class="share-option-text">微信好友</text>
            </view>
            
            <view class="share-option" @click="shareToTimeline">
              <view class="share-option-icon timeline-icon">
                <uni-icons type="pyq" size="24" color="#07c160"></uni-icons>
              </view>
              <text class="share-option-text">朋友圈</text>
            </view>
            
            <view class="share-option" @click="copyLink">
              <view class="share-option-icon copy-icon">
                <uni-icons type="paperclip" size="24" color="#666"></uni-icons>
              </view>
              <text class="share-option-text">复制链接</text>
            </view>
          </view>
        </view>
      </view>
    </uni-popup>
  </view>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import wechatShareManager from '@/utils/wechatShare'

export default {
  name: 'ShareButton',
  props: {
    // 分享类型：'article' | 'page'
    shareType: {
      type: String,
      default: 'page'
    },
    // 文章数据（当shareType为article时使用）
    article: {
      type: Object,
      default: null
    },
    // 页面名称（当shareType为page时使用）
    pageName: {
      type: String,
      default: 'index'
    },
    // 自定义分享数据
    customShareData: {
      type: Object,
      default: null
    },
    // 是否显示分享按钮
    showButton: {
      type: Boolean,
      default: true
    },
    // 按钮文本
    buttonText: {
      type: String,
      default: '分享'
    },
    // 迷你模式（只显示图标）
    mini: {
      type: Boolean,
      default: false
    },
    // 分享来源
    shareSource: {
      type: String,
      default: 'share_button'
    }
  },
  emits: ['share-success', 'share-fail'],
  setup(props, { emit }) {
    const sharePopup = ref(null)
    const shareData = ref(null)
    
    // 分享描述
    const shareDescription = computed(() => {
      if (props.shareType === 'article' && props.article) {
        return props.article.summary || '来自内容聚合的精彩文章'
      }
      return '发现更多精彩内容'
    })
    
    // 初始化分享数据
    const initShareData = () => {
      if (props.customShareData) {
        shareData.value = props.customShareData
      } else if (props.shareType === 'article' && props.article) {
        shareData.value = wechatShareManager.configureArticleShare(props.article, {
          shareSource: props.shareSource
        })
      } else {
        shareData.value = wechatShareManager.configurePageShare(props.pageName, {
          shareParams: {
            share_source: props.shareSource
          }
        })
      }
    }
    
    // 处理分享按钮点击
    const handleShareClick = () => {
      initShareData()
      sharePopup.value?.open()
    }
    
    // 关闭分享弹窗
    const closeSharePopup = () => {
      sharePopup.value?.close()
    }
    
    // 分享到微信好友
    const shareToFriend = async () => {
      try {
        const shareConfig = await wechatShareManager.shareToFriend(shareData.value)
        
        // 触发页面的onShareAppMessage
        const pages = getCurrentPages()
        const currentPage = pages[pages.length - 1]
        
        if (currentPage && currentPage.onShareAppMessage) {
          // 设置分享配置到页面实例
          currentPage.$shareConfig = shareConfig
        }
        
        closeSharePopup()
        
        // 显示分享提示
        uni.showModal({
          title: '分享提示',
          content: '请点击右上角菜单选择"转发"来分享给好友',
          showCancel: false,
          confirmText: '我知道了'
        })
        
        emit('share-success', { type: 'friend', data: shareData.value })
        
      } catch (error) {
        console.error('分享到好友失败:', error)
        emit('share-fail', { type: 'friend', error })
      }
    }
    
    // 分享到朋友圈
    const shareToTimeline = async () => {
      try {
        const shareConfig = await wechatShareManager.shareToTimeline(shareData.value)
        
        // 触发页面的onShareTimeline
        const pages = getCurrentPages()
        const currentPage = pages[pages.length - 1]
        
        if (currentPage && currentPage.onShareTimeline) {
          // 设置分享配置到页面实例
          currentPage.$timelineShareConfig = shareConfig
        }
        
        closeSharePopup()
        
        // 显示分享提示
        uni.showModal({
          title: '分享提示',
          content: '请点击右上角菜单选择"分享到朋友圈"',
          showCancel: false,
          confirmText: '我知道了'
        })
        
        emit('share-success', { type: 'timeline', data: shareData.value })
        
      } catch (error) {
        console.error('分享到朋友圈失败:', error)
        emit('share-fail', { type: 'timeline', error })
      }
    }
    
    // 复制链接
    const copyLink = () => {
      try {
        const fullUrl = `https://your-domain.com/${shareData.value.path}`
        
        uni.setClipboardData({
          data: fullUrl,
          success: () => {
            uni.showToast({
              title: '链接已复制',
              icon: 'success'
            })
            closeSharePopup()
          },
          fail: () => {
            uni.showToast({
              title: '复制失败',
              icon: 'none'
            })
          }
        })
      } catch (error) {
        console.error('复制链接失败:', error)
        uni.showToast({
          title: '复制失败',
          icon: 'none'
        })
      }
    }
    
    onMounted(() => {
      initShareData()
    })
    
    return {
      sharePopup,
      shareData,
      shareDescription,
      handleShareClick,
      closeSharePopup,
      shareToFriend,
      shareToTimeline,
      copyLink
    }
  }
}
</script>

<style scoped>
.share-button-container {
  display: inline-block;
}

.share-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16rpx 24rpx;
  background-color: #f8f9fa;
  border: 1rpx solid #e9ecef;
  border-radius: 20rpx;
  font-size: 28rpx;
  color: #666;
  transition: all 0.3s ease;
}

.share-btn:active {
  background-color: #e9ecef;
  transform: scale(0.95);
}

.share-btn-mini {
  padding: 12rpx;
  border-radius: 50%;
  width: 60rpx;
  height: 60rpx;
}

.share-text {
  margin-left: 8rpx;
  font-size: 26rpx;
}

.share-popup {
  padding: 0;
  border-radius: 20rpx 20rpx 0 0;
  overflow: hidden;
}

.share-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 30rpx 40rpx 20rpx;
  border-bottom: 1rpx solid #f0f0f0;
}

.share-title {
  font-size: 32rpx;
  font-weight: 600;
  color: #333;
}

.share-close {
  padding: 10rpx;
}

.share-content {
  padding: 30rpx 40rpx 60rpx;
}

.share-preview {
  display: flex;
  align-items: flex-start;
  padding: 20rpx;
  background-color: #f8f9fa;
  border-radius: 12rpx;
  margin-bottom: 40rpx;
}

.share-preview-image {
  width: 80rpx;
  height: 80rpx;
  border-radius: 8rpx;
  margin-right: 20rpx;
  flex-shrink: 0;
}

.share-preview-info {
  flex: 1;
  min-width: 0;
}

.share-preview-title {
  display: block;
  font-size: 28rpx;
  font-weight: 500;
  color: #333;
  margin-bottom: 8rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.share-preview-desc {
  display: block;
  font-size: 24rpx;
  color: #666;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.share-options {
  display: flex;
  justify-content: space-around;
  align-items: center;
}

.share-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20rpx;
  cursor: pointer;
  transition: all 0.3s ease;
}

.share-option:active {
  transform: scale(0.95);
}

.share-option-icon {
  width: 80rpx;
  height: 80rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16rpx;
  transition: all 0.3s ease;
}

.friend-icon {
  background-color: rgba(7, 193, 96, 0.1);
}

.timeline-icon {
  background-color: rgba(7, 193, 96, 0.1);
}

.copy-icon {
  background-color: rgba(102, 102, 102, 0.1);
}

.share-option-text {
  font-size: 24rpx;
  color: #666;
}

.share-option:active .share-option-icon {
  transform: scale(0.9);
}
</style>