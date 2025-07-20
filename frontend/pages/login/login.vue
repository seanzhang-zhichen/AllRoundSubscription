<template>
  <view class="container">
    <Loading v-if="loading" />
    <view v-else-if="error" class="error-container">
      <view class="error-message">{{ error }}</view>
      <button v-if="canRetry" @click="retry" class="retry-btn">重试</button>
    </view>
    <view v-else class="content">
      <view class="logo-section">
        <image src="/static/logo.png" class="logo" />
        <text class="app-name">内容聚合</text>
        <text class="app-desc">一站式多平台内容订阅</text>
      </view>
      
      <view class="login-section">
        <button 
          @click="handleWechatLogin" 
          class="login-btn"
          :disabled="loading"
          :class="{ 'btn-disabled': loading }"
        >
          <text class="login-text" v-if="!loading">微信授权登录</text>
          <text class="login-text" v-else>登录中...</text>
        </button>
        
        <!-- 错误提示 -->
        <view v-if="error" class="error-tip">
          <text class="error-text">{{ error }}</text>
        </view>
        
        <!-- 开发环境提示 -->
        <view class="dev-notice" v-if="isDevelopment">
          <text class="dev-text">开发环境：点击登录将使用模拟数据</text>
        </view>
        
        <view class="privacy-notice">
          <text class="notice-text">登录即表示同意</text>
          <text class="link-text" @click="showPrivacyPolicy">《隐私政策》</text>
          <text class="notice-text">和</text>
          <text class="link-text" @click="showUserAgreement">《用户协议》</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { onMounted, ref, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useUserStore } from '@/stores/user'
import Loading from '@/components/Loading.vue'
import { createPageState } from '@/utils/pageState'
import { navigateToHome } from '@/utils/navigation'

export default {
  name: 'LoginPage',
  components: {
    Loading
  },
  setup() {
    const authStore = useAuthStore()
    const userStore = useUserStore()
    
    // 页面状态管理
    const pageState = createPageState({
      enableRetry: true,
      maxRetryCount: 3
    })

    // 登录状态
    const isLoggingIn = ref(false)
    const loginError = ref('')

    // 计算属性
    const loading = computed(() => pageState.state.loading || isLoggingIn.value || authStore.loading)
    const error = computed(() => pageState.state.error || loginError.value)
    const isDevelopment = computed(() => {
      try {
        const systemInfo = uni.getSystemInfoSync()
        return !systemInfo.platform || systemInfo.platform === 'devtools'
      } catch (e) {
        return true
      }
    })

    // 重试逻辑
    const retry = async () => {
      loginError.value = ''
      await pageState.retry(async () => {
        await handleWechatLogin()
      })
    }

    // 处理微信登录
    const handleWechatLogin = async () => {
      try {
        isLoggingIn.value = true
        loginError.value = ''
        
        // 检查微信小程序环境
        if (!uni.getSystemInfoSync().platform || uni.getSystemInfoSync().platform === 'devtools') {
          // 开发环境模拟登录
          console.log('开发环境模拟微信登录')
          await simulateLogin()
          return
        }

        // 调用优化的微信登录，强制获取新的code
        await authStore.wechatLogin({
          silent: false,
          autoLogin: true,
          forceAuth: false
        })
        
        // 登录成功的跳转逻辑已在authStore.handleLoginSuccess()中处理
        
      } catch (error) {
        console.error('微信登录失败:', error)
        loginError.value = error.message || '登录失败，请重试'
        
        // 错误处理已在wechatAuthManager中处理，这里不再显示toast
        // 只在特殊情况下显示错误信息
        if (error.message && error.message.includes('频繁')) {
          uni.showToast({
            title: error.message,
            icon: 'none',
            duration: 3000
          })
        }
      } finally {
        isLoggingIn.value = false
      }
    }

    // 开发环境模拟登录
    const simulateLogin = async () => {
      return new Promise((resolve) => {
        setTimeout(() => {
          // 模拟设置登录状态
          authStore.token = 'mock_token_' + Date.now()
          authStore.refreshToken = 'mock_refresh_token_' + Date.now()
          authStore.tokenExpireAt = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
          authStore.isLoggedIn = true
          
          // 保存到本地存储
          uni.setStorageSync('token', authStore.token)
          uni.setStorageSync('refreshToken', authStore.refreshToken)
          uni.setStorageSync('tokenExpireAt', authStore.tokenExpireAt)
          
          // 模拟用户信息
          userStore.userInfo = {
            id: 1,
            openid: 'mock_openid_' + Date.now(),
            nickname: '测试用户',
            avatar_url: 'https://via.placeholder.com/100',
            membership_level: 'free',
            membership_expire_at: null,
            created_at: new Date().toISOString()
          }
          
          // 显示登录成功提示
          uni.showToast({
            title: '登录成功',
            icon: 'success'
          })
          
          // 处理登录成功后的重定向
          authStore.handleLoginSuccess()
          
          resolve()
        }, 1000)
      })
    }

    // 显示隐私政策
    const showPrivacyPolicy = () => {
      uni.showModal({
        title: '隐私政策',
        content: '我们重视您的隐私保护。本应用仅收集必要的用户信息用于提供服务，不会泄露给第三方。详细内容请查看完整版隐私政策。',
        showCancel: false,
        confirmText: '我知道了'
      })
    }

    // 显示用户协议
    const showUserAgreement = () => {
      uni.showModal({
        title: '用户协议',
        content: '使用本应用即表示您同意遵守用户协议。请合理使用应用功能，不得进行违法违规操作。详细条款请查看完整版用户协议。',
        showCancel: false,
        confirmText: '我知道了'
      })
    }

    // 检查登录状态（使用增强版本）
    const checkLoginStatus = async () => {
      try {
        const isLoggedIn = await authStore.enhancedLoginCheck()
        if (isLoggedIn) {
          // 已登录，跳转到首页
          console.log('用户已登录，跳转到首页')
          navigateToHome()
        }
      } catch (error) {
        console.error('检查登录状态失败:', error)
        // 清除可能存在的无效数据
        authStore.clearAuthData()
      }
    }

    // 页面初始化
    onMounted(() => {
      console.log('登录页面初始化')
      checkLoginStatus()
    })

    return {
      loading,
      error,
      isDevelopment,
      retry,
      handleWechatLogin,
      showPrivacyPolicy,
      showUserAgreement,
      canRetry: pageState.canRetry,
      isLoggingIn
    }
  }
}
</script>

<style scoped>
.container {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 50vh;
}

.error-message {
  color: #ff4757;
  margin-bottom: 20rpx;
  font-size: 28rpx;
}

.retry-btn {
  background-color: #007aff;
  color: white;
  border: none;
  padding: 20rpx 40rpx;
  border-radius: 10rpx;
  font-size: 28rpx;
}

.content {
  width: 100%;
  padding: 60rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.logo-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 120rpx;
}

.logo {
  width: 160rpx;
  height: 160rpx;
  border-radius: 20rpx;
  margin-bottom: 40rpx;
}

.app-name {
  font-size: 48rpx;
  font-weight: bold;
  color: white;
  margin-bottom: 20rpx;
}

.app-desc {
  font-size: 28rpx;
  color: rgba(255, 255, 255, 0.8);
}

.login-section {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.login-btn {
  width: 100%;
  background-color: #07c160;
  color: white;
  border: none;
  padding: 30rpx;
  border-radius: 50rpx;
  font-size: 32rpx;
  margin-bottom: 40rpx;
  transition: all 0.3s ease;
}

.login-btn.btn-disabled {
  background-color: #a0a0a0;
  opacity: 0.6;
}

.login-text {
  color: white;
  font-size: 32rpx;
}

.error-tip {
  width: 100%;
  padding: 20rpx;
  margin-bottom: 20rpx;
  background-color: rgba(255, 71, 87, 0.1);
  border: 1rpx solid rgba(255, 71, 87, 0.3);
  border-radius: 10rpx;
}

.error-text {
  color: #ff4757;
  font-size: 26rpx;
  text-align: center;
}

.dev-notice {
  width: 100%;
  padding: 15rpx;
  margin-bottom: 30rpx;
  background-color: rgba(255, 193, 7, 0.1);
  border: 1rpx solid rgba(255, 193, 7, 0.3);
  border-radius: 8rpx;
}

.dev-text {
  color: #ffc107;
  font-size: 22rpx;
  text-align: center;
}

.privacy-notice {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
}

.notice-text {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.7);
}

.link-text {
  font-size: 24rpx;
  color: #ffd700;
  text-decoration: underline;
}
</style>