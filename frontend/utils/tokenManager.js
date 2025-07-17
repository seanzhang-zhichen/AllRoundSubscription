/**
 * JWT令牌管理工具
 * 提供令牌存储、验证和刷新功能
 * 支持静默登录和自动续期
 */

// 存储键名常量
const STORAGE_KEYS = {
  TOKEN: 'token',
  REFRESH_TOKEN: 'refreshToken',
  TOKEN_EXPIRE_AT: 'tokenExpireAt',
  USER_INFO: 'userInfo',
  LOGIN_STATE: 'loginState',
  LAST_LOGIN_TIME: 'lastLoginTime',
  AUTO_LOGIN_ENABLED: 'autoLoginEnabled'
}

/**
 * JWT令牌管理器
 */
class TokenManager {
  constructor() {
    this.token = ''
    this.refreshToken = ''
    this.tokenExpireAt = null
  }

  /**
   * 保存令牌信息
   * @param {Object} tokenData - 令牌数据
   */
  saveTokens(tokenData) {
    const { access_token, refresh_token, expire_at } = tokenData
    
    this.token = access_token
    this.refreshToken = refresh_token
    this.tokenExpireAt = expire_at
    
    // 保存到本地存储
    try {
      uni.setStorageSync(STORAGE_KEYS.TOKEN, access_token)
      uni.setStorageSync(STORAGE_KEYS.REFRESH_TOKEN, refresh_token)
      uni.setStorageSync(STORAGE_KEYS.TOKEN_EXPIRE_AT, expire_at)
      
      console.log('令牌保存成功')
    } catch (error) {
      console.error('令牌保存失败:', error)
      throw new Error('令牌保存失败')
    }
  }

  /**
   * 从本地存储加载令牌
   */
  loadTokens() {
    try {
      this.token = uni.getStorageSync(STORAGE_KEYS.TOKEN) || ''
      this.refreshToken = uni.getStorageSync(STORAGE_KEYS.REFRESH_TOKEN) || ''
      this.tokenExpireAt = uni.getStorageSync(STORAGE_KEYS.TOKEN_EXPIRE_AT) || null
      
      console.log('令牌加载成功:', {
        hasToken: !!this.token,
        hasRefreshToken: !!this.refreshToken,
        expireAt: this.tokenExpireAt
      })
      
      return {
        token: this.token,
        refreshToken: this.refreshToken,
        tokenExpireAt: this.tokenExpireAt
      }
    } catch (error) {
      console.error('令牌加载失败:', error)
      this.clearTokens()
      return null
    }
  }

  /**
   * 清除所有令牌信息
   */
  clearTokens() {
    this.token = ''
    this.refreshToken = ''
    this.tokenExpireAt = null
    
    try {
      uni.removeStorageSync(STORAGE_KEYS.TOKEN)
      uni.removeStorageSync(STORAGE_KEYS.REFRESH_TOKEN)
      uni.removeStorageSync(STORAGE_KEYS.TOKEN_EXPIRE_AT)
      uni.removeStorageSync(STORAGE_KEYS.USER_INFO)
      
      console.log('令牌清除成功')
    } catch (error) {
      console.error('令牌清除失败:', error)
    }
  }

  /**
   * 检查令牌是否存在
   */
  hasToken() {
    return !!this.token || !!uni.getStorageSync(STORAGE_KEYS.TOKEN)
  }

  /**
   * 检查令牌是否过期
   */
  isTokenExpired() {
    if (!this.tokenExpireAt) {
      return true
    }
    
    const expireTime = new Date(this.tokenExpireAt).getTime()
    const currentTime = Date.now()
    
    // 提前5分钟判断为过期，用于自动刷新
    const bufferTime = 5 * 60 * 1000
    
    return (expireTime - currentTime) <= bufferTime
  }

  /**
   * 获取令牌剩余有效时间（毫秒）
   */
  getTokenRemainingTime() {
    if (!this.tokenExpireAt) {
      return 0
    }
    
    const expireTime = new Date(this.tokenExpireAt).getTime()
    const currentTime = Date.now()
    
    return Math.max(0, expireTime - currentTime)
  }

  /**
   * 检查令牌是否即将过期（30分钟内）
   */
  isTokenExpiringSoon() {
    const remainingTime = this.getTokenRemainingTime()
    const thirtyMinutes = 30 * 60 * 1000
    
    return remainingTime > 0 && remainingTime <= thirtyMinutes
  }

  /**
   * 获取当前有效的令牌
   */
  getValidToken() {
    // 如果内存中没有令牌，尝试从存储中加载
    if (!this.token) {
      this.loadTokens()
    }
    
    // 检查令牌是否有效
    if (!this.token || this.isTokenExpired()) {
      return null
    }
    
    return this.token
  }

  /**
   * 解析JWT令牌载荷
   * @param {string} token - JWT令牌
   */
  parseTokenPayload(token) {
    try {
      if (!token) return null
      
      const parts = token.split('.')
      if (parts.length !== 3) return null
      
      const payload = parts[1]
      const decoded = JSON.parse(atob(payload))
      
      return decoded
    } catch (error) {
      console.error('解析令牌失败:', error)
      return null
    }
  }

  /**
   * 获取令牌中的用户信息
   */
  getTokenUserInfo() {
    const token = this.getValidToken()
    if (!token) return null
    
    const payload = this.parseTokenPayload(token)
    if (!payload) return null
    
    return {
      userId: payload.sub || payload.user_id,
      username: payload.username,
      email: payload.email,
      exp: payload.exp,
      iat: payload.iat
    }
  }

  /**
   * 验证令牌格式
   * @param {string} token - 要验证的令牌
   */
  validateTokenFormat(token) {
    if (!token || typeof token !== 'string') {
      return false
    }
    
    // JWT令牌应该有三个部分，用点分隔
    const parts = token.split('.')
    if (parts.length !== 3) {
      return false
    }
    
    // 检查每个部分是否为有效的base64字符串
    try {
      for (const part of parts) {
        atob(part)
      }
      return true
    } catch (error) {
      return false
    }
  }

  /**
   * 获取令牌状态信息
   */
  getTokenStatus() {
    const hasToken = this.hasToken()
    const isExpired = this.isTokenExpired()
    const isExpiringSoon = this.isTokenExpiringSoon()
    const remainingTime = this.getTokenRemainingTime()
    
    return {
      hasToken,
      isValid: hasToken && !isExpired,
      isExpired,
      isExpiringSoon,
      remainingTime,
      remainingTimeFormatted: this.formatRemainingTime(remainingTime)
    }
  }

  /**
   * 格式化剩余时间显示
   * @param {number} milliseconds - 毫秒数
   */
  formatRemainingTime(milliseconds) {
    if (milliseconds <= 0) {
      return '已过期'
    }
    
    const seconds = Math.floor(milliseconds / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)
    
    if (days > 0) {
      return `${days}天${hours % 24}小时`
    } else if (hours > 0) {
      return `${hours}小时${minutes % 60}分钟`
    } else if (minutes > 0) {
      return `${minutes}分钟`
    } else {
      return `${seconds}秒`
    }
  }

  /**
   * 设置令牌过期监听器
   * @param {Function} callback - 过期回调函数
   */
  setTokenExpirationListener(callback) {
    const checkExpiration = () => {
      if (this.hasToken() && this.isTokenExpired()) {
        callback && callback()
      }
    }
    
    // 每分钟检查一次
    return setInterval(checkExpiration, 60 * 1000)
  }

  /**
   * 保存登录状态信息
   * @param {Object} loginState - 登录状态数据
   */
  saveLoginState(loginState) {
    try {
      const state = {
        isLoggedIn: true,
        loginTime: new Date().toISOString(),
        autoLoginEnabled: loginState.autoLoginEnabled !== false,
        ...loginState
      }
      
      uni.setStorageSync(STORAGE_KEYS.LOGIN_STATE, JSON.stringify(state))
      uni.setStorageSync(STORAGE_KEYS.LAST_LOGIN_TIME, state.loginTime)
      uni.setStorageSync(STORAGE_KEYS.AUTO_LOGIN_ENABLED, state.autoLoginEnabled)
      
      console.log('登录状态保存成功')
    } catch (error) {
      console.error('登录状态保存失败:', error)
    }
  }

  /**
   * 获取登录状态信息
   */
  getLoginState() {
    try {
      const stateStr = uni.getStorageSync(STORAGE_KEYS.LOGIN_STATE)
      if (!stateStr) return null
      
      const state = JSON.parse(stateStr)
      return {
        ...state,
        lastLoginTime: uni.getStorageSync(STORAGE_KEYS.LAST_LOGIN_TIME),
        autoLoginEnabled: uni.getStorageSync(STORAGE_KEYS.AUTO_LOGIN_ENABLED) !== false
      }
    } catch (error) {
      console.error('获取登录状态失败:', error)
      return null
    }
  }

  /**
   * 清除登录状态
   */
  clearLoginState() {
    try {
      uni.removeStorageSync(STORAGE_KEYS.LOGIN_STATE)
      uni.removeStorageSync(STORAGE_KEYS.LAST_LOGIN_TIME)
      uni.removeStorageSync(STORAGE_KEYS.AUTO_LOGIN_ENABLED)
      console.log('登录状态清除成功')
    } catch (error) {
      console.error('登录状态清除失败:', error)
    }
  }

  /**
   * 检查是否启用自动登录
   */
  isAutoLoginEnabled() {
    return uni.getStorageSync(STORAGE_KEYS.AUTO_LOGIN_ENABLED) !== false
  }

  /**
   * 设置自动登录状态
   * @param {boolean} enabled - 是否启用自动登录
   */
  setAutoLoginEnabled(enabled) {
    uni.setStorageSync(STORAGE_KEYS.AUTO_LOGIN_ENABLED, enabled)
  }

  /**
   * 检查登录状态是否持久有效
   * 基于最后登录时间和token有效期判断
   */
  isPersistentLoginValid() {
    const loginState = this.getLoginState()
    if (!loginState || !loginState.isLoggedIn) {
      return false
    }

    // 检查是否启用自动登录
    if (!this.isAutoLoginEnabled()) {
      return false
    }

    // 检查最后登录时间（30天内有效）
    const lastLoginTime = new Date(loginState.lastLoginTime || loginState.loginTime)
    const now = new Date()
    const daysDiff = (now - lastLoginTime) / (1000 * 60 * 60 * 24)
    
    if (daysDiff > 30) {
      console.log('登录状态已过期（超过30天）')
      return false
    }

    // 检查是否有有效的refresh token
    if (!this.refreshToken && !uni.getStorageSync(STORAGE_KEYS.REFRESH_TOKEN)) {
      console.log('没有有效的refresh token')
      return false
    }

    return true
  }

  /**
   * 更新最后活跃时间
   */
  updateLastActiveTime() {
    try {
      const loginState = this.getLoginState()
      if (loginState) {
        loginState.lastActiveTime = new Date().toISOString()
        uni.setStorageSync(STORAGE_KEYS.LOGIN_STATE, JSON.stringify(loginState))
      }
    } catch (error) {
      console.error('更新最后活跃时间失败:', error)
    }
  }

  /**
   * 获取登录持续时间（毫秒）
   */
  getLoginDuration() {
    const loginState = this.getLoginState()
    if (!loginState || !loginState.loginTime) {
      return 0
    }

    const loginTime = new Date(loginState.loginTime)
    const now = new Date()
    return now - loginTime
  }

  /**
   * 检查是否需要重新认证
   * 基于安全策略判断是否需要用户重新输入凭据
   */
  needsReauthentication() {
    const loginState = this.getLoginState()
    if (!loginState) return true

    // 检查是否超过7天未活跃
    const lastActiveTime = loginState.lastActiveTime || loginState.loginTime
    const daysSinceActive = (new Date() - new Date(lastActiveTime)) / (1000 * 60 * 60 * 24)
    
    if (daysSinceActive > 7) {
      console.log('超过7天未活跃，需要重新认证')
      return true
    }

    // 检查登录持续时间是否超过30天
    const loginDuration = this.getLoginDuration()
    const maxLoginDuration = 30 * 24 * 60 * 60 * 1000 // 30天
    
    if (loginDuration > maxLoginDuration) {
      console.log('登录时间超过30天，需要重新认证')
      return true
    }

    return false
  }
}

// 创建单例实例
const tokenManager = new TokenManager()

export default tokenManager
export { TokenManager, STORAGE_KEYS }