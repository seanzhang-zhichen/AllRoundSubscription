/**
 * 页面状态管理工具
 * 提供统一的页面加载状态、错误处理和重试机制
 */

import { ref, reactive, watch, nextTick } from 'vue'
import { useFeedback } from './feedbackManager'
import { useStateSync } from './stateSync'

/**
 * 创建增强的页面状态管理器
 * @param {Object} options - 配置选项
 * @returns {Object} 页面状态管理器
 */
export const createPageState = (options = {}) => {
  const {
    initialLoading = false,
    enableRetry = true,
    maxRetryCount = 3,
    retryDelay = 1000,
    pageId = '',
    enableStateSync = false,
    enableFeedback = true,
    skeletonType = 'generic'
  } = options

  // 页面状态
  const state = reactive({
    loading: initialLoading,
    error: '',
    retryCount: 0,
    isEmpty: false,
    refreshing: false,
    showSkeleton: false,
    loadingMore: false,
    hasMore: true
  })

  // 初始化反馈管理器和状态同步
  const feedback = enableFeedback ? useFeedback() : null
  const stateSync = enableStateSync && pageId ? useStateSync(pageId, state, {
    syncKeys: ['loading', 'error', 'isEmpty'],
    persistKeys: ['isEmpty'],
    autoSync: true
  }) : null

  // 设置加载状态
  const setLoading = (loading, showSkeleton = false) => {
    state.loading = loading
    state.showSkeleton = showSkeleton
    if (loading) {
      state.error = ''
    }
  }

  // 设置错误状态
  const setError = (error) => {
    const errorMessage = handleCommonError(error)
    state.error = errorMessage
    state.loading = false
    state.showSkeleton = false
    
    // 使用反馈管理器显示错误
    if (feedback && errorMessage) {
      feedback.showError(errorMessage)
    }
  }

  // 清除错误状态
  const clearError = () => {
    state.error = ''
    state.retryCount = 0
  }

  // 设置空数据状态
  const setEmpty = (isEmpty) => {
    state.isEmpty = isEmpty
  }

  // 设置刷新状态
  const setRefreshing = (refreshing) => {
    state.refreshing = refreshing
  }

  // 重试机制
  const retry = async (retryFunction) => {
    if (!enableRetry || state.retryCount >= maxRetryCount) {
      return false
    }

    state.retryCount++
    clearError()
    setLoading(true)

    try {
      // 添加延迟
      if (retryDelay > 0) {
        await new Promise(resolve => setTimeout(resolve, retryDelay))
      }

      await retryFunction()
      return true
    } catch (error) {
      setError(error.message || '重试失败')
      return false
    }
  }

  // 执行异步操作的包装器
  const executeAsync = async (asyncFunction, options = {}) => {
    const {
      showLoading = true,
      showSkeleton = false,
      errorMessage = '操作失败',
      successMessage = '',
      showSuccess = false,
      showLoadingFeedback = false,
      loadingMessage = '处理中...'
    } = options

    try {
      if (showLoading) {
        setLoading(true, showSkeleton)
      }
      
      if (showLoadingFeedback && feedback) {
        feedback.showLoading(loadingMessage)
      }
      
      clearError()

      const result = await asyncFunction()

      if (showLoadingFeedback && feedback) {
        feedback.hideLoading()
      }

      if (showSuccess && successMessage && feedback) {
        feedback.showSuccess(successMessage)
      }

      return result
    } catch (error) {
      console.error('页面操作失败:', error)
      
      if (showLoadingFeedback && feedback) {
        feedback.hideLoading()
      }
      
      setError(error)
      throw error
    } finally {
      if (showLoading) {
        setLoading(false, false)
      }
    }
  }

  // 下拉刷新处理
  const handlePullRefresh = async (refreshFunction) => {
    try {
      setRefreshing(true)
      clearError()
      await refreshFunction()
    } catch (error) {
      setError(error.message || '刷新失败')
    } finally {
      setRefreshing(false)
      // 停止下拉刷新动画
      uni.stopPullDownRefresh()
    }
  }

  // 上拉加载更多处理
  const handleLoadMore = async (loadMoreFunction) => {
    if (state.loadingMore || !state.hasMore) {
      return
    }

    try {
      state.loadingMore = true
      const result = await loadMoreFunction()
      
      // 如果返回的数据为空或少于预期，设置没有更多数据
      if (result && result.hasMore !== undefined) {
        state.hasMore = result.hasMore
      }
    } catch (error) {
      const errorMessage = handleCommonError(error)
      if (feedback) {
        feedback.showError(errorMessage)
      } else {
        uni.showToast({
          title: errorMessage,
          icon: 'none'
        })
      }
    } finally {
      state.loadingMore = false
    }
  }

  // 设置加载更多状态
  const setLoadingMore = (loading) => {
    state.loadingMore = loading
  }

  // 设置是否有更多数据
  const setHasMore = (hasMore) => {
    state.hasMore = hasMore
  }

  // 重置状态
  const reset = () => {
    state.loading = initialLoading
    state.error = ''
    state.retryCount = 0
    state.isEmpty = false
    state.refreshing = false
  }

  return {
    // 状态
    state,
    
    // 状态设置方法
    setLoading,
    setError,
    clearError,
    setEmpty,
    setRefreshing,
    
    // 操作方法
    retry,
    executeAsync,
    handlePullRefresh,
    handleLoadMore,
    reset,
    
    // 计算属性
    get isLoading() {
      return state.loading
    },
    
    get hasError() {
      return !!state.error
    },
    
    get canRetry() {
      return enableRetry && state.retryCount < maxRetryCount && !!state.error
    },
    
    get isEmpty() {
      return state.isEmpty && !state.loading && !state.error
    },
    
    get isRefreshing() {
      return state.refreshing
    }
  }
}

/**
 * 通用错误处理器
 * @param {Error} error - 错误对象
 * @returns {string} 用户友好的错误信息
 */
export const handleCommonError = (error) => {
  console.error('页面错误:', error)
  
  // 网络错误
  if (error.code === 'NETWORK_ERROR' || error.message.includes('网络')) {
    return '网络连接失败，请检查网络设置'
  }
  
  // 认证错误
  if (error.code === 'UNAUTHORIZED' || error.status === 401) {
    return '登录已过期，请重新登录'
  }
  
  // 权限错误
  if (error.code === 'FORBIDDEN' || error.status === 403) {
    return '权限不足，请联系管理员'
  }
  
  // 服务器错误
  if (error.status >= 500) {
    return '服务器繁忙，请稍后重试'
  }
  
  // 参数错误
  if (error.status === 400) {
    return error.message || '请求参数错误'
  }
  
  // 资源不存在
  if (error.status === 404) {
    return '请求的资源不存在'
  }
  
  // 默认错误信息
  return error.message || '操作失败，请重试'
}

/**
 * 页面生命周期钩子增强
 * @param {Object} pageState - 页面状态管理器
 * @param {Object} options - 配置选项
 */
export const enhancePageLifecycle = (pageState, options = {}) => {
  const {
    enablePullRefresh = false,
    enableReachBottom = false,
    autoRetryOnShow = false
  } = options

  // 页面显示时的处理
  const onShow = () => {
    if (autoRetryOnShow && pageState.hasError && pageState.canRetry) {
      // 自动重试逻辑可以在这里实现
    }
  }

  // 下拉刷新
  const onPullDownRefresh = async () => {
    if (enablePullRefresh && options.onRefresh) {
      await pageState.handlePullRefresh(options.onRefresh)
    }
  }

  // 上拉加载更多
  const onReachBottom = async () => {
    if (enableReachBottom && options.onLoadMore) {
      await pageState.handleLoadMore(options.onLoadMore)
    }
  }

  return {
    onShow,
    onPullDownRefresh,
    onReachBottom
  }
}