/**
 * 路由守卫工具
 * 提供登录状态检查和路由保护功能
 */
import { useAuthStore } from '@/stores/auth'
import { navigateToLogin } from './navigation'

/**
 * 检查用户是否已登录
 * @returns {boolean} 登录状态
 */
export const isUserLoggedIn = () => {
  const authStore = useAuthStore()
  const token = uni.getStorageSync('token')
  
  // 优先检查本地存储的token，如果存在则视为已登录
  // 然后再检查store中的登录状态，避免因为store状态没有及时更新而导致的问题
  return !!token || (authStore.isLoggedIn && !authStore.isTokenExpired)
}

/**
 * 路由守卫 - 需要登录的页面
 * @param {Function} next - 继续执行的回调函数
 * @param {Object} options - 配置选项
 */
export const requireAuth = (next, options = {}) => {
  const {
    showModal = true,
    modalTitle = '提示',
    modalContent = '请先登录后再使用此功能',
    redirectAfterLogin = false
  } = options

  // 确保先加载令牌信息
  const authStore = useAuthStore()
  const token = uni.getStorageSync('token')
  
  // 如果本地存储中有token，确保更新authStore的状态
  if (token && !authStore.isLoggedIn) {
    authStore.token = token
    authStore.isLoggedIn = true
  }

  if (isUserLoggedIn()) {
    // 已登录，继续执行
    next && next()
    return true
  } else {
    // 未登录，显示提示并跳转到登录页
    if (showModal) {
      uni.showModal({
        title: modalTitle,
        content: modalContent,
        showCancel: true,
        cancelText: '取消',
        confirmText: '去登录',
        success: (res) => {
          if (res.confirm) {
            // 保存当前页面路径，登录后可以返回
            if (redirectAfterLogin) {
              const pages = getCurrentPages()
              const currentPage = pages[pages.length - 1]
              if (currentPage) {
                uni.setStorageSync('redirectAfterLogin', currentPage.route)
              }
            }
            navigateToLogin()
          }
        }
      })
    } else {
      navigateToLogin()
    }
    return false
  }
}

/**
 * 路由守卫 - 仅游客可访问的页面（如登录页）
 * @param {Function} next - 继续执行的回调函数
 * @param {string} redirectUrl - 已登录时重定向的页面
 */
export const requireGuest = (next, redirectUrl = '/pages/index/index') => {
  if (!isUserLoggedIn()) {
    // 未登录，继续执行
    next && next()
    return true
  } else {
    // 已登录，重定向到指定页面
    uni.switchTab({
      url: redirectUrl
    })
    return false
  }
}

/**
 * 会员权限检查
 * @param {string} requiredLevel - 需要的会员等级 ('basic' | 'premium')
 * @param {Function} next - 继续执行的回调函数
 * @param {Object} options - 配置选项
 */
export const requireMembership = (requiredLevel, next, options = {}) => {
  const {
    showModal = true,
    modalTitle = '会员权限',
    modalContent = '此功能需要会员权限，请升级会员后使用'
  } = options

  // 首先检查是否已登录
  if (!requireAuth(() => {}, { showModal: false })) {
    return false
  }

  // 动态导入stores以避免循环依赖
  const { useUserStore } = require('@/stores/user')
  const userStore = useUserStore()
  
  const membershipLevels = {
    'free': 0,
    'basic': 1,
    'premium': 2
  }
  
  const currentLevel = membershipLevels[userStore.userInfo.membership_level] || 0
  const requiredLevelValue = membershipLevels[requiredLevel] || 0
  
  if (currentLevel >= requiredLevelValue) {
    // 权限足够，继续执行
    next && next()
    return true
  } else {
    // 权限不足，显示升级提示
    if (showModal) {
      uni.showModal({
        title: modalTitle,
        content: modalContent,
        showCancel: true,
        cancelText: '取消',
        confirmText: '升级会员',
        success: (res) => {
          if (res.confirm) {
            // 跳转到会员升级页面
            uni.navigateTo({
              url: '/pages/profile/membership'
            })
          }
        }
      })
    }
    return false
  }
}

/**
 * 页面初始化时的认证检查
 * 用于页面onLoad或onShow生命周期
 */
export const initPageAuth = async () => {
  const authStore = useAuthStore()
  
  try {
    // 使用增强的登录状态检查
    await authStore.enhancedLoginCheck()
    return authStore.isLoggedIn
  } catch (error) {
    console.error('页面认证检查失败:', error)
    return false
  }
}

/**
 * 自动刷新token的守卫
 * 在token即将过期时自动刷新
 */
export const autoRefreshToken = async () => {
  const authStore = useAuthStore()
  
  if (!authStore.isLoggedIn || !authStore.token) {
    return false
  }
  
  // 检查token是否即将过期（提前5分钟刷新）
  const expireTime = new Date(authStore.tokenExpireAt).getTime()
  const currentTime = Date.now()
  const fiveMinutes = 5 * 60 * 1000
  
  if (expireTime - currentTime < fiveMinutes) {
    try {
      await authStore.refreshAccessToken()
      console.log('Token自动刷新成功')
      return true
    } catch (error) {
      console.error('Token自动刷新失败:', error)
      // 刷新失败，清除认证信息
      authStore.logout()
      return false
    }
  }
  
  return true
}

/**
 * 全局路由守卫中间件
 * 在App.vue的onShow中调用
 */
export const globalRouteGuard = async () => {
  const authStore = useAuthStore()
  
  // 使用增强的自动续期检查
  if (authStore.isLoggedIn) {
    await authStore.autoRenewalCheck()
  }
  
  // 检查当前页面是否需要登录
  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1]
  
  if (currentPage) {
    const route = currentPage.route
    
    // 定义需要登录的页面
    const protectedRoutes = [
      'pages/profile/profile',
      'pages/subscription/subscription',
      'pages/index/index'
    ]
    
    // 定义仅游客可访问的页面
    const guestOnlyRoutes = [
      'pages/login/login'
    ]
    
    if (protectedRoutes.includes(route)) {
      requireAuth(() => {}, {
        showModal: true,
        redirectAfterLogin: true
      })
    } else if (guestOnlyRoutes.includes(route)) {
      requireGuest(() => {})
    }
  }
}

/**
 * 登录后重定向处理
 */
export const handleLoginRedirect = () => {
  const redirectUrl = uni.getStorageSync('redirectAfterLogin')
  
  if (redirectUrl) {
    // 清除重定向信息
    uni.removeStorageSync('redirectAfterLogin')
    
    // 延迟跳转，确保登录状态已更新
    setTimeout(() => {
      uni.navigateTo({
        url: `/${redirectUrl}`
      })
    }, 100)
  } else {
    // 默认跳转到首页
    uni.switchTab({
      url: '/pages/index/index'
    })
  }
}