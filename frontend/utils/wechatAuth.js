/**
 * 微信小程序授权优化工具
 * 提供微信授权流程优化、错误处理和状态管理
 */

/**
 * 微信授权管理器
 */
class WechatAuthManager {
  constructor() {
    this.authState = {
      isAuthorizing: false,
      lastAuthTime: null,
      authRetryCount: 0,
      maxRetryCount: 3
    }
  }

  /**
   * 优化的微信授权流程
   * @param {Object} options - 授权选项
   */
  async optimizedWechatAuth(options = {}) {
    const {
      silent = false,
      forceAuth = false,
      timeout = 10000
    } = options

    try {
      // 防止重复授权
      if (this.authState.isAuthorizing && !forceAuth) {
        console.log('授权正在进行中，跳过重复请求')
        return null
      }

      this.authState.isAuthorizing = true

      // 静默模式下的特殊处理
      if (silent) {
        // 检查授权频率限制（静默模式下更严格）
        if (!this.canAttemptAuth() && !forceAuth) {
          console.log('静默模式：授权请求过于频繁，跳过')
          return null
        }

        // 检查微信环境
        const envInfo = this.checkWechatEnvironment()
        if (!envInfo.isWechat && !envInfo.isDevelopment) {
          console.log('静默模式：非微信环境，跳过授权')
          return null
        }
      } else {
        // 交互模式下的频率检查
        if (!this.canAttemptAuth() && !forceAuth) {
          throw new Error('授权请求过于频繁，请稍后再试')
        }
      }

      console.log(`开始微信授权，模式: ${silent ? '静默' : '交互'}`)

      // 获取微信登录code
      const loginResult = await this.getWechatLoginCode(timeout)
      
      // 更新授权状态
      this.authState.lastAuthTime = Date.now()
      this.authState.authRetryCount = 0

      console.log('微信授权成功')
      return loginResult

    } catch (error) {
      this.authState.authRetryCount++
      console.error(`微信授权失败 (${silent ? '静默' : '交互'}模式):`, error)
      
      // 静默模式下不显示错误提示
      if (!silent) {
        this.handleAuthError(error)
      }
      
      throw error
    } finally {
      this.authState.isAuthorizing = false
    }
  }

  /**
   * 获取微信登录code
   * @param {number} timeout - 超时时间
   */
  async getWechatLoginCode(timeout = 10000) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error('微信授权超时'))
      }, timeout)

      uni.login({
        provider: 'weixin',
        success: (res) => {
          clearTimeout(timer)
          if (res.code) {
            console.log('微信登录code获取成功')
            resolve(res)
          } else {
            reject(new Error('获取微信登录code失败'))
          }
        },
        fail: (error) => {
          clearTimeout(timer)
          console.error('微信登录失败:', error)
          reject(new Error(this.parseWechatError(error)))
        }
      })
    })
  }

  /**
   * 检查是否可以尝试授权
   */
  canAttemptAuth() {
    // 检查重试次数
    if (this.authState.authRetryCount >= this.authState.maxRetryCount) {
      const timeSinceLastAuth = Date.now() - (this.authState.lastAuthTime || 0)
      const cooldownPeriod = 60 * 1000 // 1分钟冷却期
      
      if (timeSinceLastAuth < cooldownPeriod) {
        return false
      } else {
        // 重置重试计数
        this.authState.authRetryCount = 0
      }
    }

    return true
  }

  /**
   * 解析微信错误信息
   * @param {Object} error - 微信错误对象
   */
  parseWechatError(error) {
    const errorMap = {
      'auth deny': '用户拒绝授权',
      'auth cancel': '用户取消授权',
      'system error': '系统错误，请稍后重试',
      'network error': '网络错误，请检查网络连接',
      'timeout': '授权超时，请重试'
    }

    const errorMsg = error.errMsg || error.message || ''
    
    for (const [key, value] of Object.entries(errorMap)) {
      if (errorMsg.toLowerCase().includes(key)) {
        return value
      }
    }

    return '授权失败，请重试'
  }

  /**
   * 处理授权错误
   * @param {Error} error - 错误对象
   */
  handleAuthError(error) {
    const errorMessage = error.message || '授权失败'
    
    // 根据错误类型显示不同的提示
    if (errorMessage.includes('拒绝') || errorMessage.includes('取消')) {
      uni.showModal({
        title: '授权提示',
        content: '需要您的授权才能正常使用应用功能，请重新尝试授权',
        showCancel: true,
        cancelText: '稍后再说',
        confirmText: '重新授权',
        success: (res) => {
          if (res.confirm) {
            // 延迟重试，避免频繁请求
            setTimeout(() => {
              this.optimizedWechatAuth({ forceAuth: true })
            }, 1000)
          }
        }
      })
    } else if (errorMessage.includes('网络')) {
      uni.showToast({
        title: '网络连接异常，请检查网络后重试',
        icon: 'none',
        duration: 3000
      })
    } else if (errorMessage.includes('频繁')) {
      uni.showToast({
        title: errorMessage,
        icon: 'none',
        duration: 3000
      })
    } else {
      uni.showToast({
        title: errorMessage,
        icon: 'none',
        duration: 2000
      })
    }
  }

  /**
   * 检查微信小程序环境
   */
  checkWechatEnvironment() {
    try {
      const systemInfo = uni.getSystemInfoSync()
      
      return {
        isWechat: systemInfo.platform !== 'devtools',
        isDevelopment: systemInfo.platform === 'devtools',
        platform: systemInfo.platform,
        version: systemInfo.version,
        SDKVersion: systemInfo.SDKVersion
      }
    } catch (error) {
      console.error('获取系统信息失败:', error)
      return {
        isWechat: false,
        isDevelopment: true,
        platform: 'unknown',
        version: 'unknown',
        SDKVersion: 'unknown'
      }
    }
  }

  /**
   * 获取微信用户信息
   * @param {Object} options - 选项
   */
  async getWechatUserInfo(options = {}) {
    const { withCredentials = true, lang = 'zh_CN' } = options

    return new Promise((resolve, reject) => {
      uni.getUserInfo({
        provider: 'weixin',
        withCredentials,
        lang,
        success: (res) => {
          console.log('获取微信用户信息成功')
          resolve(res)
        },
        fail: (error) => {
          console.error('获取微信用户信息失败:', error)
          reject(new Error(this.parseWechatError(error)))
        }
      })
    })
  }

  /**
   * 检查微信授权状态
   */
  async checkWechatAuthStatus() {
    return new Promise((resolve) => {
      uni.getSetting({
        success: (res) => {
          const authSettings = res.authSetting || {}
          resolve({
            userInfo: authSettings['scope.userInfo'] !== false,
            userLocation: authSettings['scope.userLocation'] !== false,
            writePhotosAlbum: authSettings['scope.writePhotosAlbum'] !== false,
            camera: authSettings['scope.camera'] !== false
          })
        },
        fail: (error) => {
          console.error('获取授权设置失败:', error)
          resolve({})
        }
      })
    })
  }

  /**
   * 请求特定权限
   * @param {string} scope - 权限范围
   */
  async requestPermission(scope) {
    return new Promise((resolve, reject) => {
      uni.authorize({
        scope,
        success: () => {
          console.log(`权限 ${scope} 授权成功`)
          resolve(true)
        },
        fail: (error) => {
          console.error(`权限 ${scope} 授权失败:`, error)
          
          // 如果用户之前拒绝过，引导用户到设置页面
          if (error.errMsg && error.errMsg.includes('auth deny')) {
            uni.showModal({
              title: '权限申请',
              content: '需要相应权限才能正常使用功能，请在设置中开启',
              showCancel: true,
              cancelText: '取消',
              confirmText: '去设置',
              success: (res) => {
                if (res.confirm) {
                  uni.openSetting({
                    success: (settingRes) => {
                      const authSetting = settingRes.authSetting
                      if (authSetting[scope]) {
                        resolve(true)
                      } else {
                        reject(new Error('用户未开启权限'))
                      }
                    },
                    fail: () => {
                      reject(new Error('打开设置页面失败'))
                    }
                  })
                } else {
                  reject(new Error('用户取消权限设置'))
                }
              }
            })
          } else {
            reject(new Error(this.parseWechatError(error)))
          }
        }
      })
    })
  }

  /**
   * 重置授权状态
   */
  resetAuthState() {
    this.authState = {
      isAuthorizing: false,
      lastAuthTime: null,
      authRetryCount: 0,
      maxRetryCount: 3
    }
  }

  /**
   * 获取授权状态信息
   */
  getAuthStateInfo() {
    return {
      ...this.authState,
      canAttemptAuth: this.canAttemptAuth(),
      environment: this.checkWechatEnvironment()
    }
  }
}

// 创建单例实例
const wechatAuthManager = new WechatAuthManager()

export default wechatAuthManager
export { WechatAuthManager }