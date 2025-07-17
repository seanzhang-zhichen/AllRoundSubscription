<template>
  <view class="content-card" @click="handleCardClick">
    <!-- 博主信息 -->
    <view class="card-header">
      <view class="author-info">
        <LazyImage 
          class="author-avatar" 
          :src="article.account?.avatar_url || '/static/default-avatar.png'" 
          mode="aspectFill"
          width="80"
          height="80"
          :optimize="true"
          :show-placeholder-icon="false"
          placeholder-text=""
        />
        <view class="author-details">
          <text class="author-name">{{ article.account?.name || '未知博主' }}</text>
          <view class="meta-info">
            <text class="publish-time">{{ formatTime(article.publish_time) }}</text>
            <view class="platform-tag" :class="`platform-${article.account?.platform}`">
              <text class="platform-text">{{ getPlatformName(article.account?.platform) }}</text>
            </view>
          </view>
        </view>
      </view>
      <view class="card-actions">
        <view class="action-btn" @click.stop="handleFavorite">
          <text class="action-icon" :class="{ 'favorited': article.is_favorited }">♥</text>
        </view>
        <view class="action-btn" @click.stop="handleShare">
          <text class="action-icon">⤴</text>
        </view>
      </view>
    </view>

    <!-- 文章内容 -->
    <view class="card-content">
      <text class="article-title">{{ article.title }}</text>
      <text class="article-summary" v-if="article.summary">{{ article.summary }}</text>
      
      <!-- 图片展示 -->
      <view class="images-container" v-if="article.images && article.images.length > 0">
        <view class="image-grid" :class="`grid-${getGridClass(article.images.length)}`">
          <LazyImage 
            v-for="(image, index) in displayImages" 
            :key="index"
            class="content-image"
            :src="image"
            mode="aspectFill"
            :width="getImageWidth(article.images.length)"
            :height="getImageHeight(article.images.length)"
            :optimize="true"
            :clickable="true"
            @click="previewImage(image, article.images)"
          />
          <view 
            v-if="article.images.length > 9" 
            class="more-images"
            @click.stop="previewImage(article.images[8], article.images)"
          >
            <text class="more-text">+{{ article.images.length - 9 }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 文章统计 -->
    <view class="card-footer" v-if="showStats">
      <view class="stats-item">
        <text class="stats-icon">👁</text>
        <text class="stats-text">{{ formatNumber(article.view_count || 0) }}</text>
      </view>
      <view class="stats-item">
        <text class="stats-icon">👍</text>
        <text class="stats-text">{{ formatNumber(article.like_count || 0) }}</text>
      </view>
      <view class="stats-item">
        <text class="stats-icon">💬</text>
        <text class="stats-text">{{ formatNumber(article.comment_count || 0) }}</text>
      </view>
    </view>
  </view>
</template>

<script>
import LazyImage from './LazyImage.vue'
import { useFeedback } from '@/utils/feedbackManager'

export default {
  name: 'ContentCard',
  components: {
    LazyImage
  },
  setup() {
    const feedback = useFeedback()
    
    return {
      feedback
    }
  },
  props: {
    article: {
      type: Object,
      required: true
    },
    showStats: {
      type: Boolean,
      default: true
    }
  },
  computed: {
    displayImages() {
      if (!this.article.images || this.article.images.length === 0) {
        return []
      }
      return this.article.images.slice(0, 9)
    }
  },
  methods: {
    /**
     * 处理卡片点击
     */
    handleCardClick() {
      this.$emit('click', this.article)
    },

    /**
     * 处理收藏
     */
    async handleFavorite() {
      try {
        // 提供触觉反馈
        this.feedback.showLoading('处理中...', { duration: 500 })
        
        this.$emit('favorite', this.article)
        
        // 显示操作结果反馈
        const message = this.article.is_favorited ? '已取消收藏' : '收藏成功'
        this.feedback.showSuccess(message)
        
      } catch (error) {
        this.feedback.showError('操作失败，请重试')
      }
    },

    /**
     * 处理分享
     */
    async handleShare() {
      try {
        this.$emit('share', this.article)
        this.feedback.showSuccess('分享成功')
      } catch (error) {
        this.feedback.showError('分享失败，请重试')
      }
    },

    /**
     * 预览图片
     */
    previewImage(current, urls) {
      try {
        uni.previewImage({
          current,
          urls,
          fail: (error) => {
            console.error('图片预览失败:', error)
            this.feedback.showError('图片加载失败')
          }
        })
      } catch (error) {
        this.feedback.showError('无法预览图片')
      }
    },

    /**
     * 格式化时间
     */
    formatTime(time) {
      if (!time) return ''
      
      const now = new Date()
      const publishTime = new Date(time)
      const diff = now - publishTime
      
      const minutes = Math.floor(diff / (1000 * 60))
      const hours = Math.floor(diff / (1000 * 60 * 60))
      const days = Math.floor(diff / (1000 * 60 * 60 * 24))
      
      if (minutes < 1) {
        return '刚刚'
      } else if (minutes < 60) {
        return `${minutes}分钟前`
      } else if (hours < 24) {
        return `${hours}小时前`
      } else if (days < 7) {
        return `${days}天前`
      } else {
        return publishTime.toLocaleDateString()
      }
    },

    /**
     * 获取平台名称
     */
    getPlatformName(platform) {
      const platformMap = {
        'wechat': '微信',
        'weibo': '微博',
        'twitter': '推特',
        'douyin': '抖音',
        'xiaohongshu': '小红书'
      }
      return platformMap[platform] || '其他'
    },

    /**
     * 获取图片网格样式类
     */
    getGridClass(count) {
      if (count === 1) return 'single'
      if (count === 2) return 'double'
      if (count <= 4) return 'quad'
      return 'nine'
    },

    /**
     * 格式化数字
     */
    formatNumber(num) {
      if (num < 1000) return num.toString()
      if (num < 10000) return (num / 1000).toFixed(1) + 'k'
      if (num < 100000) return (num / 10000).toFixed(1) + 'w'
      return (num / 10000).toFixed(0) + 'w'
    },

    /**
     * 获取图片宽度
     */
    getImageWidth(count) {
      if (count === 1) return 690 // 单图全宽
      if (count === 2) return 340 // 双图各占一半
      if (count <= 4) return 340 // 四宫格
      return 220 // 九宫格
    },

    /**
     * 获取图片高度
     */
    getImageHeight(count) {
      if (count === 1) return 300 // 单图较高
      return 200 // 其他情况统一高度
    }
  }
}
</script>

<style scoped>
.content-card {
  background-color: white;
  border-radius: 12rpx;
  margin-bottom: 20rpx;
  padding: 30rpx;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20rpx;
}

.author-info {
  display: flex;
  align-items: center;
  flex: 1;
}

.author-avatar {
  width: 80rpx;
  height: 80rpx;
  border-radius: 40rpx;
  margin-right: 20rpx;
}

.author-details {
  flex: 1;
}

.author-name {
  font-size: 32rpx;
  font-weight: 600;
  color: #333;
  display: block;
  margin-bottom: 8rpx;
}

.meta-info {
  display: flex;
  align-items: center;
  gap: 20rpx;
}

.publish-time {
  font-size: 24rpx;
  color: #999;
}

.platform-tag {
  padding: 4rpx 12rpx;
  border-radius: 12rpx;
  font-size: 20rpx;
}

.platform-wechat {
  background-color: #07c160;
  color: white;
}

.platform-weibo {
  background-color: #ff8200;
  color: white;
}

.platform-twitter {
  background-color: #1da1f2;
  color: white;
}

.platform-douyin {
  background-color: #000;
  color: white;
}

.platform-xiaohongshu {
  background-color: #ff2442;
  color: white;
}

.platform-text {
  font-size: 20rpx;
}

.card-actions {
  display: flex;
  gap: 20rpx;
}

.action-btn {
  width: 60rpx;
  height: 60rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 30rpx;
  background-color: #f5f5f5;
}

.action-icon {
  font-size: 32rpx;
  color: #666;
}

.action-icon.favorited {
  color: #ff4757;
}

.card-content {
  margin-bottom: 20rpx;
}

.article-title {
  font-size: 32rpx;
  font-weight: 600;
  color: #333;
  line-height: 1.4;
  display: block;
  margin-bottom: 16rpx;
}

.article-summary {
  font-size: 28rpx;
  color: #666;
  line-height: 1.5;
  display: block;
  margin-bottom: 20rpx;
}

.images-container {
  margin-top: 20rpx;
}

.image-grid {
  display: grid;
  gap: 8rpx;
  border-radius: 8rpx;
  overflow: hidden;
}

.grid-single {
  grid-template-columns: 1fr;
}

.grid-double {
  grid-template-columns: 1fr 1fr;
}

.grid-quad {
  grid-template-columns: 1fr 1fr;
}

.grid-nine {
  grid-template-columns: 1fr 1fr 1fr;
}

.content-image {
  width: 100%;
  height: 200rpx;
  border-radius: 8rpx;
}

.grid-single .content-image {
  height: 300rpx;
}

.more-images {
  position: relative;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8rpx;
}

.more-text {
  color: white;
  font-size: 28rpx;
  font-weight: 600;
}

.card-footer {
  display: flex;
  justify-content: space-around;
  padding-top: 20rpx;
  border-top: 1rpx solid #f0f0f0;
}

.stats-item {
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.stats-icon {
  font-size: 24rpx;
}

.stats-text {
  font-size: 24rpx;
  color: #999;
}
</style>