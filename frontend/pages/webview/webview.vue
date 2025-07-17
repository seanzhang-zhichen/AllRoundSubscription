<template>
  <view class="webview-container">
    <web-view :src="url" @message="handleMessage" @error="handleError"></web-view>
  </view>
</template>

<script>
import { ref, onLoad } from 'vue'

export default {
  name: 'WebViewPage',
  setup() {
    const url = ref('')

    const handleMessage = (event) => {
      console.log('WebView message:', event)
    }

    const handleError = (event) => {
      console.error('WebView error:', event)
      uni.showToast({
        title: '页面加载失败',
        icon: 'none'
      })
    }

    onLoad((options) => {
      if (options.url) {
        url.value = decodeURIComponent(options.url)
      } else {
        uni.showToast({
          title: '链接地址不存在',
          icon: 'none'
        })
        setTimeout(() => {
          uni.navigateBack()
        }, 1500)
      }
    })

    return {
      url,
      handleMessage,
      handleError
    }
  }
}
</script>

<style scoped>
.webview-container {
  width: 100%;
  height: 100vh;
}
</style>