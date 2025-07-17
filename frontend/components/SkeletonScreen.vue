<template>
  <view class="skeleton-screen" :class="{ 'skeleton-dark': isDark }">
    <!-- 内容卡片骨架屏 -->
    <template v-if="type === 'content-card'">
      <view class="skeleton-card" v-for="n in count" :key="n">
        <view class="skeleton-header">
          <view class="skeleton-avatar"></view>
          <view class="skeleton-info">
            <view class="skeleton-line skeleton-title"></view>
            <view class="skeleton-line skeleton-subtitle"></view>
          </view>
          <view class="skeleton-action"></view>
        </view>
        <view class="skeleton-content">
          <view class="skeleton-line" v-for="i in 3" :key="i"></view>
        </view>
        <view class="skeleton-image" v-if="showImage"></view>
        <view class="skeleton-footer">
          <view class="skeleton-tag" v-for="i in 2" :key="i"></view>
          <view class="skeleton-time"></view>
        </view>
      </view>
    </template>

    <!-- 列表项骨架屏 -->
    <template v-else-if="type === 'list-item'">
      <view class="skeleton-list-item" v-for="n in count" :key="n">
        <view class="skeleton-avatar"></view>
        <view class="skeleton-content">
          <view class="skeleton-line skeleton-title"></view>
          <view class="skeleton-line skeleton-subtitle"></view>
        </view>
        <view class="skeleton-arrow"></view>
      </view>
    </template>

    <!-- 搜索结果骨架屏 -->
    <template v-else-if="type === 'search-result'">
      <view class="skeleton-search-item" v-for="n in count" :key="n">
        <view class="skeleton-avatar"></view>
        <view class="skeleton-content">
          <view class="skeleton-line skeleton-name"></view>
          <view class="skeleton-line skeleton-desc"></view>
          <view class="skeleton-tags">
            <view class="skeleton-tag" v-for="i in 3" :key="i"></view>
          </view>
        </view>
        <view class="skeleton-button"></view>
      </view>
    </template>

    <!-- 个人资料骨架屏 -->
    <template v-else-if="type === 'profile'">
      <view class="skeleton-profile">
        <view class="skeleton-profile-header">
          <view class="skeleton-large-avatar"></view>
          <view class="skeleton-profile-info">
            <view class="skeleton-line skeleton-name"></view>
            <view class="skeleton-line skeleton-level"></view>
          </view>
        </view>
        <view class="skeleton-stats">
          <view class="skeleton-stat" v-for="i in 3" :key="i">
            <view class="skeleton-stat-number"></view>
            <view class="skeleton-stat-label"></view>
          </view>
        </view>
        <view class="skeleton-actions">
          <view class="skeleton-action-btn" v-for="i in 2" :key="i"></view>
        </view>
      </view>
    </template>

    <!-- 文章详情骨架屏 -->
    <template v-else-if="type === 'article-detail'">
      <view class="skeleton-article">
        <view class="skeleton-article-header">
          <view class="skeleton-line skeleton-title-large"></view>
          <view class="skeleton-article-meta">
            <view class="skeleton-avatar"></view>
            <view class="skeleton-meta-info">
              <view class="skeleton-line skeleton-author"></view>
              <view class="skeleton-line skeleton-time"></view>
            </view>
          </view>
        </view>
        <view class="skeleton-article-content">
          <view class="skeleton-line" v-for="i in 8" :key="i"></view>
          <view class="skeleton-image"></view>
          <view class="skeleton-line" v-for="i in 4" :key="i + 8"></view>
        </view>
      </view>
    </template>

    <!-- 通用骨架屏 -->
    <template v-else>
      <view class="skeleton-generic">
        <view class="skeleton-line" v-for="n in count" :key="n" 
              :style="{ width: getRandomWidth() }"></view>
      </view>
    </template>
  </view>
</template>

<script>
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'

export default {
  name: 'SkeletonScreen',
  props: {
    // 骨架屏类型
    type: {
      type: String,
      default: 'generic',
      validator: (value) => [
        'content-card',
        'list-item', 
        'search-result',
        'profile',
        'article-detail',
        'generic'
      ].includes(value)
    },
    // 显示数量
    count: {
      type: Number,
      default: 3
    },
    // 是否显示图片占位
    showImage: {
      type: Boolean,
      default: true
    },
    // 是否启用动画
    animated: {
      type: Boolean,
      default: true
    },
    // 自定义样式
    customStyle: {
      type: Object,
      default: () => ({})
    }
  },
  setup() {
    const appStore = useAppStore()
    
    const isDark = computed(() => appStore.isDarkMode)
    
    // 生成随机宽度（用于通用骨架屏）
    const getRandomWidth = () => {
      const widths = ['60%', '80%', '70%', '90%', '65%', '85%']
      return widths[Math.floor(Math.random() * widths.length)]
    }
    
    return {
      isDark,
      getRandomWidth
    }
  }
}
</script>

<style scoped>
.skeleton-screen {
  padding: 20rpx;
}

/* 基础骨架元素 */
.skeleton-line,
.skeleton-avatar,
.skeleton-image,
.skeleton-button,
.skeleton-tag,
.skeleton-action {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 8rpx;
}

.skeleton-line {
  height: 32rpx;
  margin-bottom: 16rpx;
}

.skeleton-avatar {
  width: 80rpx;
  height: 80rpx;
  border-radius: 50%;
  flex-shrink: 0;
}

.skeleton-large-avatar {
  width: 120rpx;
  height: 120rpx;
  border-radius: 50%;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
}

.skeleton-image {
  width: 100%;
  height: 300rpx;
  margin: 20rpx 0;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 12rpx;
}

.skeleton-button {
  width: 120rpx;
  height: 60rpx;
  border-radius: 30rpx;
}

.skeleton-tag {
  width: 80rpx;
  height: 40rpx;
  border-radius: 20rpx;
  margin-right: 16rpx;
}

.skeleton-action {
  width: 40rpx;
  height: 40rpx;
  border-radius: 50%;
}

/* 内容卡片骨架屏 */
.skeleton-card {
  background-color: white;
  border-radius: 16rpx;
  padding: 30rpx;
  margin-bottom: 20rpx;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.1);
}

.skeleton-header {
  display: flex;
  align-items: center;
  margin-bottom: 20rpx;
}

.skeleton-info {
  flex: 1;
  margin-left: 20rpx;
}

.skeleton-title {
  width: 60%;
  height: 36rpx;
  margin-bottom: 12rpx;
}

.skeleton-subtitle {
  width: 40%;
  height: 28rpx;
}

.skeleton-content {
  margin: 20rpx 0;
}

.skeleton-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 20rpx;
}

.skeleton-time {
  width: 120rpx;
  height: 28rpx;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 8rpx;
}

/* 列表项骨架屏 */
.skeleton-list-item {
  display: flex;
  align-items: center;
  padding: 30rpx;
  background-color: white;
  border-bottom: 1rpx solid #f0f0f0;
}

.skeleton-list-item .skeleton-content {
  flex: 1;
  margin-left: 20rpx;
}

.skeleton-arrow {
  width: 24rpx;
  height: 24rpx;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 4rpx;
}

/* 搜索结果骨架屏 */
.skeleton-search-item {
  display: flex;
  align-items: center;
  padding: 30rpx;
  background-color: white;
  border-radius: 16rpx;
  margin-bottom: 20rpx;
}

.skeleton-search-item .skeleton-content {
  flex: 1;
  margin-left: 20rpx;
}

.skeleton-name {
  width: 70%;
  height: 36rpx;
  margin-bottom: 12rpx;
}

.skeleton-desc {
  width: 90%;
  height: 28rpx;
  margin-bottom: 16rpx;
}

.skeleton-tags {
  display: flex;
  align-items: center;
}

/* 个人资料骨架屏 */
.skeleton-profile {
  background-color: white;
  border-radius: 16rpx;
  padding: 40rpx;
}

.skeleton-profile-header {
  display: flex;
  align-items: center;
  margin-bottom: 40rpx;
}

.skeleton-profile-info {
  flex: 1;
  margin-left: 30rpx;
}

.skeleton-name {
  width: 60%;
  height: 40rpx;
  margin-bottom: 16rpx;
}

.skeleton-level {
  width: 40%;
  height: 32rpx;
}

.skeleton-stats {
  display: flex;
  justify-content: space-around;
  margin-bottom: 40rpx;
}

.skeleton-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.skeleton-stat-number {
  width: 60rpx;
  height: 40rpx;
  margin-bottom: 12rpx;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 8rpx;
}

.skeleton-stat-label {
  width: 80rpx;
  height: 28rpx;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 8rpx;
}

.skeleton-actions {
  display: flex;
  gap: 20rpx;
}

.skeleton-action-btn {
  flex: 1;
  height: 80rpx;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 40rpx;
}

/* 文章详情骨架屏 */
.skeleton-article {
  background-color: white;
  border-radius: 16rpx;
  padding: 40rpx;
}

.skeleton-article-header {
  margin-bottom: 40rpx;
}

.skeleton-title-large {
  width: 90%;
  height: 48rpx;
  margin-bottom: 30rpx;
}

.skeleton-article-meta {
  display: flex;
  align-items: center;
}

.skeleton-meta-info {
  flex: 1;
  margin-left: 20rpx;
}

.skeleton-author {
  width: 50%;
  height: 32rpx;
  margin-bottom: 12rpx;
}

.skeleton-article-content {
  line-height: 1.8;
}

/* 通用骨架屏 */
.skeleton-generic {
  padding: 20rpx;
}

/* 动画 */
@keyframes skeleton-loading {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

/* 暗色模式 */
.skeleton-dark .skeleton-line,
.skeleton-dark .skeleton-avatar,
.skeleton-dark .skeleton-image,
.skeleton-dark .skeleton-button,
.skeleton-dark .skeleton-tag,
.skeleton-dark .skeleton-action,
.skeleton-dark .skeleton-large-avatar,
.skeleton-dark .skeleton-time,
.skeleton-dark .skeleton-arrow,
.skeleton-dark .skeleton-stat-number,
.skeleton-dark .skeleton-stat-label,
.skeleton-dark .skeleton-action-btn {
  background: linear-gradient(90deg, #2a2a2a 25%, #3a3a3a 50%, #2a2a2a 75%);
  background-size: 200% 100%;
}

.skeleton-dark .skeleton-card,
.skeleton-dark .skeleton-list-item,
.skeleton-dark .skeleton-search-item,
.skeleton-dark .skeleton-profile,
.skeleton-dark .skeleton-article {
  background-color: #1a1a1a;
}

/* 禁用动画（用户偏好） */
@media (prefers-reduced-motion: reduce) {
  .skeleton-line,
  .skeleton-avatar,
  .skeleton-image,
  .skeleton-button,
  .skeleton-tag,
  .skeleton-action,
  .skeleton-large-avatar,
  .skeleton-time,
  .skeleton-arrow,
  .skeleton-stat-number,
  .skeleton-stat-label,
  .skeleton-action-btn {
    animation: none;
    background: #f0f0f0;
  }
  
  .skeleton-dark .skeleton-line,
  .skeleton-dark .skeleton-avatar,
  .skeleton-dark .skeleton-image,
  .skeleton-dark .skeleton-button,
  .skeleton-dark .skeleton-tag,
  .skeleton-dark .skeleton-action,
  .skeleton-dark .skeleton-large-avatar,
  .skeleton-dark .skeleton-time,
  .skeleton-dark .skeleton-arrow,
  .skeleton-dark .skeleton-stat-number,
  .skeleton-dark .skeleton-stat-label,
  .skeleton-dark .skeleton-action-btn {
    background: #2a2a2a;
  }
}

/* 响应式设计 */
@media screen and (max-width: 750rpx) {
  .skeleton-card,
  .skeleton-profile,
  .skeleton-article {
    padding: 30rpx;
  }
  
  .skeleton-list-item,
  .skeleton-search-item {
    padding: 25rpx;
  }
}
</style>