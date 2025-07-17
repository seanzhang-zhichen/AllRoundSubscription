/**
 * 页面导航工具类
 * 提供统一的页面跳转和导航管理功能
 */

/**
 * 跳转到登录页面
 */
export const navigateToLogin = () => {
  uni.navigateTo({
    url: '/pages/login/login'
  })
}

/**
 * 跳转到首页
 */
export const navigateToHome = () => {
  uni.switchTab({
    url: '/pages/index/index'
  })
}

/**
 * 跳转到搜索页面
 */
export const navigateToSearch = () => {
  uni.switchTab({
    url: '/pages/search/search'
  })
}

/**
 * 跳转到订阅页面
 */
export const navigateToSubscription = () => {
  uni.switchTab({
    url: '/pages/subscription/subscription'
  })
}

/**
 * 跳转到个人中心页面
 */
export const navigateToProfile = () => {
  uni.switchTab({
    url: '/pages/profile/profile'
  })
}

/**
 * 跳转到文章详情页面
 * @param {string|number} articleId - 文章ID
 */
export const navigateToArticleDetail = (articleId) => {
  if (!articleId) {
    console.error('文章ID不能为空')
    return
  }
  uni.navigateTo({
    url: `/pages/article/detail?id=${articleId}`
  })
}

/**
 * 返回上一页
 */
export const navigateBack = () => {
  uni.navigateBack({
    delta: 1
  })
}

/**
 * 重定向到指定页面
 * @param {string} url - 页面路径
 */
export const redirectTo = (url) => {
  uni.redirectTo({
    url
  })
}

/**
 * 关闭所有页面并跳转到指定页面
 * @param {string} url - 页面路径
 */
export const reLaunch = (url) => {
  uni.reLaunch({
    url
  })
}

/**
 * 检查用户登录状态并处理导航
 * @param {Function} callback - 登录后的回调函数
 * @param {Object} options - 配置选项
 */
export const checkLoginAndNavigate = (callback, options = {}) => {
  const { requireAuth } = require('./routeGuard')
  
  return requireAuth(callback, {
    showModal: true,
    modalTitle: '提示',
    modalContent: '请先登录后使用此功能',
    redirectAfterLogin: true,
    ...options
  })
}

/**
 * 显示页面加载错误提示
 * @param {string} message - 错误信息
 * @param {Function} retryCallback - 重试回调函数
 */
export const showPageError = (message = '页面加载失败', retryCallback) => {
  uni.showModal({
    title: '错误',
    content: message,
    showCancel: !!retryCallback,
    cancelText: '取消',
    confirmText: retryCallback ? '重试' : '确定',
    success: (res) => {
      if (res.confirm && retryCallback) {
        retryCallback()
      }
    }
  })
}

/**
 * 显示网络错误提示
 * @param {Function} retryCallback - 重试回调函数
 */
export const showNetworkError = (retryCallback) => {
  showPageError('网络连接失败，请检查网络设置', retryCallback)
}

/**
 * 显示权限不足提示
 */
export const showPermissionError = () => {
  uni.showModal({
    title: '权限不足',
    content: '您的权限不足，请升级会员或联系客服',
    showCancel: false,
    confirmText: '确定'
  })
}

/**
 * 显示功能开发中提示
 * @param {string} feature - 功能名称
 */
export const showFeatureInDevelopment = (feature = '该功能') => {
  uni.showToast({
    title: `${feature}正在开发中`,
    icon: 'none',
    duration: 2000
  })
}