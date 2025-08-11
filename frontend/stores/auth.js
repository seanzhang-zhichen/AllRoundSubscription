/**
 * 认证状态管理
 */
import { defineStore } from 'pinia'
import request from '../utils/request'
import tokenManager from '../utils/tokenManager'
import wechatAuthManager from '../utils/wechatAuth'
import wechatLoginMonitor from '../utils/wechatLoginMonitor'
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
      const startTime = Date.now()
      let retryCount = 0
      
      try {
        this.loading = true
        const { silent = false, autoLogin = true, forceAuth = false } = options
        
        console.log(`开始微信登录，模式: ${silent ? '静默' : '交互'}`)
        
        // 记录Code获取开始
        const codeStartTime = Date.now()
        
        // 使用优化的微信授权流程
        const loginRes = await wechatAuthManager.optimizedWechatAuth({
          silent,
          forceAuth,
          timeout: silent ? 8000 : 15000 // 静默模式使用更短的超时时间
        })
        
        const codeDuration = Date.now() - codeStartTime
        
        if (!loginRes || !loginRes.code) {
          // 记录Code获取失败
          wechatLoginMonitor.recordCodeAcquisition({
            success: false,
            duration: codeDuration,
            error: 'code_acquisition_failed',
            errorMessage: '获取微信登录code失败'
          })
          throw new Error('获取微信登录code失败')
        }
        
        // 记录Code获取成功
        wechatLoginMonitor.recordCodeAcquisition({
          success: true,
          codeLength: loginRes.code.length,
          duration: codeDuration
        })
        
        console.log('微信授权成功，调用后端登录接口')
        
        // 调用后端登录接口，添加重试机制
        const data = await this.callLoginApiWithRetry(loginRes.code, silent)
        
        console.log('后端登录成功，保存认证信息')
        
        // 处理后端响应数据结构
        const responseData = data.data || data // 兼容不同的响应格式
        const tokens = responseData.tokens || {
          access_token: responseData.access_token,
          refresh_token: responseData.refresh_token,
          expire_at: responseData.expire_at
        }
        const user = responseData.user || responseData
        
        // 使用tokenManager保存认证信息
        tokenManager.saveTokens(tokens)
        
        // 更新store状态
        this.token = tokens.access_token
        this.refreshToken = tokens.refresh_token
        this.tokenExpireAt = tokens.expire_at
        this.isLoggedIn = true
        
        // 确保token已保存到本地存储（同步操作）
        uni.setStorageSync('token', tokens.access_token)
        uni.setStorageSync('refreshToken', tokens.refresh_token)
        uni.setStorageSync('tokenExpireAt', tokens.expire_at)
        
        console.log('认证令牌已保存:', {
          hasToken: !!tokens.access_token,
          tokenLength: tokens.access_token?.length,
          expireAt: tokens.expire_at
        })
        
        // 保存登录状态信息
        const deviceInfo = uni.getSystemInfoSync()
        tokenManager.saveLoginState({
          autoLoginEnabled: autoLogin,
          loginMethod: 'wechat',
          loginTime: new Date().toISOString(),
          deviceInfo: {
            platform: deviceInfo.platform,
            system: deviceInfo.system,
            version: deviceInfo.version,
            model: deviceInfo.model,
            brand: deviceInfo.brand
          },
          authStateInfo: wechatAuthManager.getAuthStateInfo()
        })
        
        console.log('认证状态更新完成，获取用户信息')
        
        // 获取用户信息
        const userStore = useUserStore()
        try {
          await userStore.fetchUserProfile()
          await userStore.fetchUserLimits()
        } catch (userError) {
          console.warn('获取用户信息失败，但不影响登录:', userError)
        }
        
        // 显示成功提示
        if (!silent) {
          uni.showToast({
            title: '登录成功',
            icon: 'success',
            duration: 1500
          })
          
          // 处理登录后重定向
          setTimeout(() => {
            this.handleLoginSuccess()
          }, 1500)
        } else {
          console.log('静默登录成功')
        }
        
        // 记录登录成功
        const totalDuration = Date.now() - startTime
        wechatLoginMonitor.recordSuccess({
          duration: totalDuration,
          codeLength: loginRes.code.length,
          retryCount,
          mode: silent ? 'silent' : 'interactive'
        })
        
        return {
          user: user,
          tokens: tokens
        }
        
      } catch (error) {
        console.error('微信登录失败:', error)
        
        // 记录登录失败
        const totalDuration = Date.now() - startTime
        const errorMessage = error.message || error.toString()
        let errorCode = null
        let step = 'unknown'
        
        // 分析错误发生的步骤
        if (errorMessage.includes('获取微信登录code失败')) {
          step = 'code_acquisition'
        } else if (errorMessage.includes('40029') || errorMessage.includes('invalid code')) {
          step = 'api_call'
          errorCode = '40029'
        } else if (errorMessage.includes('网络')) {
          step = 'network'
        } else if (errorMessage.includes('登录API')) {
          step = 'api_call'
        }
        
        wechatLoginMonitor.recordFailure({
          error: this.categorizeError(errorMessage),
          errorCode,
          errorMessage,
          duration: totalDuration,
          codeLength: loginRes?.code?.length || 0,
          retryCount,
          mode: silent ? 'silent' : 'interactive',
          step
        })
        
        // 根据错误类型和模式决定是否显示错误提示
        if (!silent) {
          // 交互模式下显示详细错误信息
          const friendlyMessage = this.getLoginErrorMessage(error)
          uni.showToast({
            title: friendlyMessage,
            icon: 'none',
            duration: 3000
          })
        } else {
          // 静默模式下只记录日志
          console.warn('静默登录失败，用户可稍后手动登录:', error.message)
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
     * 调用登录API并支持重试机制
     * @param {string} code - 微信登录code
     * @param {boolean} silent - 是否静默模式
     */
    async callLoginApiWithRetry(code, silent = false) {
      const maxRetries = 2
      let lastError = null
      
      for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
          console.log(`尝试调用登录API，第${attempt}次`)
          
          const data = await request.post('/auth/login', {
            code: code
          })
          
          console.log('登录API调用成功')
          return data
          
        } catch (error) {
          lastError = error
          console.error(`登录API调用失败，第${attempt}次尝试:`, error)
          
          // 检查是否是40029错误（无效code）
          const errorMessage = error.message || error.toString()
          const isInvalidCode = errorMessage.includes('40029') || 
                               errorMessage.includes('无效的code') || 
                               errorMessage.includes('invalid code')
          
          if (isInvalidCode && attempt < maxRetries) {
            console.log('检测到无效code错误，重新获取微信授权')
            
            try {
              // 重新获取微信登录code
              const newLoginRes = await wechatAuthManager.optimizedWechatAuth({
                silent: true, // 重试时使用静默模式
                forceAuth: true, // 强制重新授权
                timeout: 8000
              })
              
              if (newLoginRes && newLoginRes.code) {
                code = newLoginRes.code
                console.log('重新获取微信code成功，继续重试')
                continue
              } else {
                console.error('重新获取微信code失败')
                break
              }
            } catch (authError) {
              console.error('重新获取微信授权失败:', authError)
              break
            }
          } else {
            // 非code错误或已达到最大重试次数
            break
          }
        }
      }
      
      // 所有重试都失败，抛出最后一个错误
      throw lastError
    },

    /**
     * 错误分类
     * @param {string} errorMessage - 错误消息
     */
    categorizeError(errorMessage) {
      if (errorMessage.includes('40029') || errorMessage.includes('invalid code')) {
        return 'invalid_code_error'
      } else if (errorMessage.includes('获取微信登录code失败')) {
        return 'code_acquisition_failed'
      } else if (errorMessage.includes('网络') || errorMessage.includes('network')) {
        return 'network_error'
      } else if (errorMessage.includes('超时') || errorMessage.includes('timeout')) {
        return 'timeout_error'
      } else if (errorMessage.includes('拒绝') || errorMessage.includes('deny')) {
        return 'user_denied'
      } else if (errorMessage.includes('取消') || errorMessage.includes('cancel')) {
        return 'user_cancelled'
      } else {
        return 'unknown_error'
      }
    },

    /**
     * 获取登录错误消息
     * @param {Error} error - 错误对象
     */
    getLoginErrorMessage(error) {
      const message = error.message || error.toString()
      
      // 常见错误映射
      const errorMap = {
        '获取微信登录code失败': '微信授权失败，请重试',
        '用户拒绝授权': '需要您的授权才能使用',
        '用户取消授权': '授权已取消',
        '授权超时': '授权超时，请重试',
        '网络错误': '网络连接异常，请检查网络',
        '登录失败': '登录服务异常，请稍后重试'
      }
      
      for (const [key, value] of Object.entries(errorMap)) {
        if (message.includes(key)) {
          return value
        }
      }
      
      return '登录失败，请重试'
    },

    /**
     * 检查认证状态和令牌（用于调试）
     */
    async diagnoseAuthState() {
      try {
        // 加载令牌信息
        const tokenData = tokenManager.loadTokens()
        
        // 获取用户信息
        const userStore = useUserStore()
        
        console.log('========= 认证状态诊断 =========')
        console.log('认证状态:')
        console.log('- isLoggedIn:', this.isLoggedIn)
        console.log('- 令牌存在:', !!this.token)
        console.log('- 刷新令牌存在:', !!this.refreshToken)
        console.log('- 令牌过期时间:', this.tokenExpireAt)
        console.log('- 令牌是否过期:', tokenManager.isTokenExpired())
        
        console.log('\n本地存储令牌状态:')
        console.log('- 令牌存在:', !!tokenData?.token)
        console.log('- 刷新令牌存在:', !!tokenData?.refreshToken)
        console.log('- 令牌过期时间:', tokenData?.tokenExpireAt)
        
        console.log('\n用户信息:')
        console.log('- 用户ID:', userStore.userInfo.id)
        console.log('- 用户名:', userStore.userInfo.nickname)
        console.log('- 会员级别:', userStore.userInfo.membership_level)
        
        console.log('\n登录状态信息:')
        const loginState = tokenManager.getLoginState()
        console.log('- 登录状态:', loginState ? JSON.stringify({
          isLoggedIn: loginState.isLoggedIn,
          loginTime: loginState.loginTime,
          lastActiveTime: loginState.lastActiveTime,
          autoLoginEnabled: loginState.autoLoginEnabled
        }) : 'null')
        
        // 验证令牌
        let tokenValid = false
        try {
          tokenValid = await this.verifyToken()
        } catch (e) {
          console.log('令牌验证出错:', e.message)
        }
        console.log('- 令牌验证结果:', tokenValid)
        
        console.log('===============================')
        
        return {
          authState: {
            isLoggedIn: this.isLoggedIn,
            hasToken: !!this.token,
            tokenExpired: tokenManager.isTokenExpired(),
            tokenValid
          },
          userState: {
            hasUserId: !!userStore.userInfo.id,
            userId: userStore.userInfo.id,
            nickname: userStore.userInfo.nickname
          }
        }
        
      } catch (error) {
        console.error('诊断认证状态失败:', error)
        return { error: error.message }
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