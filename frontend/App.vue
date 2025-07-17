<template>
  <view id="app">
    <router-view />
  </view>
</template>

<script>
import { useAuthStore } from '@/stores/auth'
import { globalRouteGuard, initPageAuth } from '@/utils/routeGuard'
import performanceOptimizer from '@/utils/performanceOptimizer'

export default {
  name: 'App',
  data() {
    return {
      autoRenewalTimer: null
    }
  },
  onLaunch: function() {
    console.log('App Launch')
    // 应用启动时的初始化逻辑
    this.initApp()
  },
  onShow: function() {
    console.log('App Show')
    // 应用从后台进入前台时的逻辑
    this.handleAppShow()
  },
  onHide: function() {
    console.log('App Hide')
    // 应用从前台进入后台时的逻辑
  },
  onUnload: function() {
    console.log('App Unload')
    // 清理定时器，防止内存泄漏
    this.stopAutoRenewalTimer()
  },
  methods: {
    async initApp() {
      try {
        // 初始化全局配置
        this.initGlobalConfig()
        
        // 初始化性能优化
        this.initPerformanceOptimization()
        
        // 初始化认证状态
        await this.initAuth()
        
        console.log('App初始化完成')
      } catch (error) {
        console.error('App初始化失败:', error)
      }
    },
    
    async initAuth() {
      try {
        // 使用增强的认证状态初始化
        const authStore = useAuthStore()
        
        const isLoggedIn = await authStore.enhancedLoginCheck()
        console.log('认证状态初始化完成:', isLoggedIn ? '已登录' : '未登录')
        
        // 如果登录成功，启动自动续期检查
        if (isLoggedIn) {
          this.startAutoRenewalTimer()
        }
      } catch (error) {
        console.error('认证状态初始化失败:', error)
      }
    },
    
    async handleAppShow() {
      try {
        // 执行全局路由守卫
        await globalRouteGuard()
      } catch (error) {
        console.error('全局路由守卫执行失败:', error)
      }
    },
    
    initGlobalConfig() {
      // 设置全局配置
      uni.setStorageSync('appVersion', '1.0.0')
      
      // 设置全局错误处理
      this.setupGlobalErrorHandler()
    },
    
    /**
     * 初始化性能优化
     */
    initPerformanceOptimization() {
      try {
        // 预加载关键资源
        const criticalResources = [
          {
            type: 'page',
            path: 'pages/index/index',
            priority: 'high'
          },
          {
            type: 'page', 
            path: 'pages/search/search',
            priority: 'normal'
          },
          {
            type: 'image',
            url: '/static/logo.png',
            priority: 'high'
          }
        ]
        
        performanceOptimizer.preloadResources(criticalResources)
        
        // 启动性能监控
        console.log('性能优化初始化完成')
        
        // 定期输出性能统计
        setInterval(() => {
          const stats = performanceOptimizer.getPerformanceStats()
          console.log('性能统计:', stats)
        }, 5 * 60 * 1000) // 每5分钟输出一次
        
      } catch (error) {
        console.error('性能优化初始化失败:', error)
      }
    },
    
    setupGlobalErrorHandler() {
      // 全局错误处理
      uni.onError((error) => {
        console.error('全局错误:', error)
        
        // 记录错误日志
        this.logError(error)
        
        // 显示用户友好的错误提示
        if (error.message && !error.message.includes('Network')) {
          uni.showToast({
            title: '系统异常，请稍后重试',
            icon: 'none',
            duration: 2000
          })
        }
      })
      
      // 全局未处理的Promise拒绝
      uni.onUnhandledRejection((event) => {
        console.error('未处理的Promise拒绝:', event.reason)
        this.logError(event.reason)
      })
    },
    
    /**
     * 启动自动续期定时器
     */
    startAutoRenewalTimer() {
      // 清除之前的定时器
      if (this.autoRenewalTimer) {
        clearInterval(this.autoRenewalTimer)
      }
      
      // 每5分钟检查一次token状态
      this.autoRenewalTimer = setInterval(async () => {
        try {
          const authStore = useAuthStore()
          
          if (authStore.isLoggedIn) {
            await authStore.autoRenewalCheck()
          } else {
            // 如果用户已登出，清除定时器
            this.stopAutoRenewalTimer()
          }
        } catch (error) {
          console.error('自动续期检查失败:', error)
        }
      }, 5 * 60 * 1000) // 5分钟
      
      console.log('自动续期定时器已启动')
    },
    
    /**
     * 停止自动续期定时器
     */
    stopAutoRenewalTimer() {
      if (this.autoRenewalTimer) {
        clearInterval(this.autoRenewalTimer)
        this.autoRenewalTimer = null
        console.log('自动续期定时器已停止')
      }
    },
    
    logError(error) {
      // 错误日志记录
      const errorLog = {
        message: error.message || error,
        stack: error.stack,
        timestamp: new Date().toISOString(),
        userAgent: uni.getSystemInfoSync(),
        route: getCurrentPages().map(page => page.route).join(' -> ')
      }
      
      // 保存到本地存储（可以后续上报到服务器）
      try {
        const logs = uni.getStorageSync('errorLogs') || []
        logs.push(errorLog)
        
        // 只保留最近50条错误日志
        if (logs.length > 50) {
          logs.splice(0, logs.length - 50)
        }
        
        uni.setStorageSync('errorLogs', logs)
      } catch (e) {
        console.error('保存错误日志失败:', e)
      }
    }
  }
}
</script>

<style>
/* 全局样式 */
@import url('./styles/global.css');

#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>