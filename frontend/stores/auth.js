/**
 * 认证状态管理
 */
import { defineStore } from 'pinia'
import request from '../utils/request'
import tokenManager from '../utils/tokenManager'
import wechatAuthManager from '../utils/wechatAuth'
import { useUserStore } from './user'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    // 认证token
    token: '',
    refreshToken: '',
    
    // 登录状态
    isLoggedIn: false,
    
    // 加载状态
    loading: false,
    
    // 登录过期时间
    tokenExpireAt: null
  }),
  
  getters: {
    // 检查token是否过期
    isTokenExpired: (state) => {
      return tokenManager.isTokenExpired()
    },
    
    // 获取token状态信息
    tokenStatus: (state) => {
      return tokenManager.getTokenStatus()
    }
  },
  
  actions: {
    /**
     * 微信登录
     * @param {Object} options - 登录选项
     */
    async wechatLogin(options = {}) {
      try {
        this.loading = true
        const { silent = false, autoLogin = true, forceAuth = false } = options
        
        // 使用优化的微信授权流程
        const loginRes = await wechatAuthManager.optimizedWechatAuth({
          silent,
          forceAuth,
          timeout: 10000
        })
        
        if (!loginRes || !loginRes.code) {
          throw new Error('获取微信登录code失败')
        }
        
        // 调用后端登录接口
        const data = await request.post('/auth/login', {
          code: loginRes.code
        })
        
        // 使用tokenManager保存认证信息
        tokenManager.saveTokens(data)
        
        // 保存登录状态信息
        const deviceInfo = uni.getSystemInfoSync()
        tokenManager.saveLoginState({
          autoLoginEnabled: autoLogin,
          loginMethod: 'wechat',
          deviceInfo: {
            platform: deviceInfo.platform,
            system: deviceInfo.system,
            version: deviceInfo.version,
            model: deviceInfo.model,
            brand: deviceInfo.brand
          },
          authStateInfo: wechatAuthManager.getAuthStateInfo()
        })
        
        // 更新store状态
        this.token = data.access_token
        this.refreshToken = data.refresh_token
        this.tokenExpireAt = data.expire_at
        this.isLoggedIn = true
        
        // 获取用户信息
        const userStore = useUserStore()
        await userStore.fetchUserProfile()
        await userStore.fetchUserLimits()
        
        if (!silent) {
          uni.showToast({
            title: '登录成功',
            icon: 'success'
          })
        }
        
        // 处理登录后重定向
        this.handleLoginSuccess()
        
        return data
        
      } catch (error) {
        console.error('微信登录失败:', error)
        if (!options.silent) {
          // 错误处理已在wechatAuthManager中处理，这里只记录日志
          console.error('微信登录错误详情:', error)
        }
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * 静默登录
     * 尝试使用已保存的认证信息自动登录
     */
    async silentLogin() {
      try {
        console.log('开始静默登录')
        
        // 检查是否有持久登录状态
        if (!tokenManager.isPersistentLoginValid()) {
          console.log('持久登录状态无效')
          return false
        }
        
        // 加载已保存的token
        const tokenData = tokenManager.loadTokens()
        if (!tokenData || !tokenData.token) {
          console.log('没有保存的token')
          return false
        }
        
        // 更新store状态
        this.token = tokenData.token
        this.refreshToken = tokenData.refreshToken
        this.tokenExpireAt = tokenData.tokenExpireAt
        
        // 检查token是否过期，如果过期尝试刷新
        if (tokenManager.isTokenExpired()) {
          console.log('Token已过期，尝试刷新')
          if (this.refreshToken) {
            await this.refreshAccessToken()
          } else {
            console.log('没有refresh token，静默登录失败')
            return false
          }
        }
        
        // 验证token有效性
        const isValid = await this.verifyToken()
        if (!isValid) {
          console.log('Token验证失败')
          return false
        }
        
        this.isLoggedIn = true
        
        // 获取用户信息
        const userStore = useUserStore()
        try {
          await userStore.fetchUserProfile()
          await userStore.loadUserSettings()
        } catch (error) {
          console.error('获取用户信息失败:', error)
          // 用户信息获取失败不影响静默登录
        }
        
        // 更新最后活跃时间
        tokenManager.updateLastActiveTime()
        
        console.log('静默登录成功')
        return true
        
      } catch (error) {
        console.error('静默登录失败:', error)
        this.clearAuthData()
        return false
      }
    },
    
    /**
     * 刷新token
     */
    async refreshAccessToken() {
      try {
        if (!this.refreshToken && !tokenManager.refreshToken) {
          throw new Error('没有refresh token')
        }
        
        const refreshToken = this.refreshToken || tokenManager.refreshToken
        
        const data = await request.post('/auth/refresh', {
          refresh_token: refreshToken
        })
        
        // 使用tokenManager更新token信息
        const updatedTokenData = {
          access_token: data.access_token,
          refresh_token: refreshToken, // 保持原有的refresh token
          expire_at: data.expire_at
        }
        
        tokenManager.saveTokens(updatedTokenData)
        
        // 更新store状态
        this.token = data.access_token
        this.tokenExpireAt = data.expire_at
        
        return data
        
      } catch (error) {
        console.error('刷新token失败:', error)
        // 刷新失败，清除认证信息
        this.logout()
        throw error
      }
    },
    
    /**
     * 登出
     */
    async logout() {
      try {
        // 调用后端登出接口
        if (this.token) {
          await request.post('/auth/logout')
        }
      } catch (error) {
        console.error('登出接口调用失败:', error)
      } finally {
        // 清除认证信息
        this.clearAuthData()
        
        // 清除用户数据
        const userStore = useUserStore()
        userStore.clearUserData()
        
        // 跳转到登录页
        uni.reLaunch({
          url: '/pages/login/login'
        })
        
        uni.showToast({
          title: '已退出登录',
          icon: 'success'
        })
      }
    },
    
    /**
     * 检查登录状态
     */
    async checkLoginStatus() {
      try {
        // 使用tokenManager加载认证信息
        const tokenData = tokenManager.loadTokens()
        
        if (!tokenData || !tokenData.token) {
          return false
        }
        
        // 更新store状态
        this.token = tokenData.token
        this.refreshToken = tokenData.refreshToken
        this.tokenExpireAt = tokenData.tokenExpireAt
        
        // 检查token是否过期
        if (tokenManager.isTokenExpired()) {
          // 尝试刷新token
          if (this.refreshToken) {
            await this.refreshAccessToken()
          } else {
            this.clearAuthData()
            return false
          }
        }
        
        this.isLoggedIn = true
        
        // 获取用户信息
        const userStore = useUserStore()
        await userStore.fetchUserProfile()
        await userStore.loadUserSettings()
        
        return true
        
      } catch (error) {
        console.error('检查登录状态失败:', error)
        this.clearAuthData()
        return false
      }
    },
    
    /**
     * 清除认证数据
     */
    clearAuthData() {
      this.token = ''
      this.refreshToken = ''
      this.tokenExpireAt = null
      this.isLoggedIn = false
      
      // 使用tokenManager清除本地存储
      tokenManager.clearTokens()
      tokenManager.clearLoginState()
    },

    /**
     * 自动续期检查
     * 在token即将过期时自动刷新
     */
    async autoRenewalCheck() {
      try {
        if (!this.isLoggedIn || !this.token) {
          return false
        }

        // 检查是否需要重新认证
        if (tokenManager.needsReauthentication()) {
          console.log('需要重新认证，清除登录状态')
          this.clearAuthData()
          return false
        }

        // 检查token是否即将过期
        if (tokenManager.isTokenExpiringSoon()) {
          console.log('Token即将过期，开始自动刷新')
          try {
            await this.refreshAccessToken()
            console.log('Token自动刷新成功')
            return true
          } catch (error) {
            console.error('Token自动刷新失败:', error)
            this.clearAuthData()
            return false
          }
        }

        // 更新最后活跃时间
        tokenManager.updateLastActiveTime()
        return true

      } catch (error) {
        console.error('自动续期检查失败:', error)
        return false
      }
    },

    /**
     * 增强的登录状态检查
     * 包含静默登录和自动续期
     */
    async enhancedLoginCheck() {
      try {
        // 首先尝试静默登录
        const silentLoginSuccess = await this.silentLogin()
        if (silentLoginSuccess) {
          console.log('静默登录成功')
          return true
        }

        // 静默登录失败，检查常规登录状态
        const regularLoginSuccess = await this.checkLoginStatus()
        if (regularLoginSuccess) {
          console.log('常规登录检查成功')
          return true
        }

        console.log('登录状态检查失败')
        return false

      } catch (error) {
        console.error('增强登录状态检查失败:', error)
        this.clearAuthData()
        return false
      }
    },
    
    /**
     * 验证token有效性
     */
    async verifyToken() {
      try {
        await request.get('/auth/verify')
        return true
      } catch (error) {
        console.error('Token验证失败:', error)
        return false
      }
    },
    
    /**
     * 处理登录成功后的逻辑
     */
    handleLoginSuccess() {
      // 检查是否有重定向URL
      const redirectUrl = uni.getStorageSync('redirectAfterLogin')
      
      if (redirectUrl) {
        // 清除重定向信息
        uni.removeStorageSync('redirectAfterLogin')
        
        // 延迟跳转，确保登录状态已更新
        setTimeout(() => {
          if (redirectUrl.startsWith('pages/')) {
            // 处理tabBar页面
            const tabBarPages = ['pages/index/index', 'pages/search/search', 'pages/subscription/subscription', 'pages/profile/profile']
            if (tabBarPages.includes(redirectUrl)) {
              uni.switchTab({
                url: `/${redirectUrl}`
              })
            } else {
              uni.navigateTo({
                url: `/${redirectUrl}`
              })
            }
          } else {
            uni.navigateTo({
              url: redirectUrl
            })
          }
        }, 1500) // 等待toast显示完成
      } else {
        // 默认跳转到首页
        setTimeout(() => {
          uni.switchTab({
            url: '/pages/index/index'
          })
        }, 1500)
      }
    }
  }
})