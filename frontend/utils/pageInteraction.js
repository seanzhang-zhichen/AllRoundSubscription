/**
 * 页面交互增强工具
 * 提供统一的页面交互、数据传递和用户体验优化
 */

import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { createPageState } from './pageState'
import { useStateSync, navigationHelper } from './stateSync'
import { useFeedback } from './feedbackManager'

/**
 * 创建增强的页面交互管理器
 * @param {Object} options - 配置选项
 * @returns {Object} 页面交互管理器
 */
export const createPageInteraction = (options = {}) => {
  const {
    pageId,
    enableStateSync = true,
    enableFeedback = true,
    enableRetry = true,
    skeletonType = 'generic',
    cacheStrategy = 'memory', // memory | storage | none
    refreshStrategy = 'pull', // pull | button | auto
    loadMoreStrategy = 'scroll', // scroll | button | none
    errorRecovery = 'auto' // auto | manual | none
  } = options

  // 创建页面状态管理器
  const pageState = createPageState({
    pageId,
    enableStateSync,
    enableFeedback,
    enableRetry,
    skeletonType
  })

  // 状态同步管理器
  const stateSync = enableStateSync ? useStateSync(pageId, pageState.state, {
    syncKeys: ['loading', 'error', 'isEmpty', 'refreshing'],
    persistKeys: ['isEmpty'],
    autoSync: true
  }) : null

  // 反馈管理器
  const feedback = enableFeedback ? useFeedback() : null

  // 页面数据缓存
  const dataCache = reactive({
    data: null,
    timestamp: 0,
    version: 1,
    expireTime: 5 * 60 * 1000 // 5分钟过期
  })

  // 页面交互状态
  const interactionState = reactive({
    scrollTop: 0,
    showBackToTop: false,
    isVisible: true,
    networkStatus: 'online',
    lastActiveTime: Date.now()
  })

  // 数据加载配置
  const loadingConfig = reactive({
    showSkeleton: true,
    skeletonCount: 3,
    loadingText: '加载中...',
    emptyText: '暂无数据',
    errorText: '加载失败'
  })

  /**
   * 数据缓存管理
   */
  const cacheManager = {
    // 设置缓存数据
    setCache(data, options = {}) {
      const { expire = dataCache.expireTime, version = dataCache.version + 1 } = options
      
      dataCache.data = data
      dataCache.timestamp = Date.now()
      dataCache.version = version
      dataCache.expireTime = expire

      // 持久化缓存
      if (cacheStrategy === 'storage') {
        try {
          uni.setStorageSync(`pageCache:${pageId}`, {
            data,
            timestamp: dataCache.timestamp,
            version,
            expireTime: expire
          })
        } catch (error) {
          console.warn('缓存数据失败:', error)
        }
      }
    },

    // 获取缓存数据
    getCache() {
      // 检查内存缓存
      if (dataCache.data && this.isCacheValid()) {
        return dataCache.data
      }

      // 检查持久化缓存
      if (cacheStrategy === 'storage') {
        try {
          const cached = uni.getStorageSync(`pageCache:${pageId}`)
          if (cached && this.isCacheValid(cached)) {
            // 恢复到内存缓存
            Object.assign(dataCache, cached)
            return cached.data
          }
        } catch (error) {
          console.warn('获取缓存数据失败:', error)
        }
      }

      return null
    },

    // 检查缓存是否有效
    isCacheValid(cache = dataCache) {
      const now = Date.now()
      return cache.timestamp && (now - cache.timestamp) < cache.expireTime
    },

    // 清除缓存
    clearCache() {
      dataCache.data = null
      dataCache.timestamp = 0
      
      if (cacheStrategy === 'storage') {
        try {
          uni.removeStorageSync(`pageCache:${pageId}`)
        } catch (error) {
          console.warn('清除缓存失败:', error)
        }
      }
    },

    // 刷新缓存
    refreshCache(data, options = {}) {
      this.clearCache()
      this.setCache(data, options)
    }
  }

  /**
   * 数据加载管理
   */
  const dataLoader = {
    // 加载数据
    async loadData(loadFunction, options = {}) {
      const {
        useCache = cacheStrategy !== 'none',
        showSkeleton = loadingConfig.showSkeleton,
        showLoading = false,
        successMessage = '',
        forceRefresh = false
      } = options

      try {
        // 检查缓存
        if (useCache && !forceRefresh) {
          const cachedData = cacheManager.getCache()
          if (cachedData) {
            console.log('使用缓存数据')
            return cachedData
          }
        }

        // 开始加载
        pageState.setLoading(true, showSkeleton)
        pageState.clearError()

        if (showLoading && feedback) {
          feedback.showLoading(loadingConfig.loadingText)
        }

        // 执行加载函数
        const result = await loadFunction()

        // 缓存结果
        if (useCache && result) {
          cacheManager.setCache(result)
        }

        // 检查是否为空
        const isEmpty = this.checkEmpty(result)
        pageState.setEmpty(isEmpty)

        if (showLoading && feedback) {
          feedback.hideLoading()
        }

        if (successMessage && feedback) {
          feedback.showSuccess(successMessage)
        }

        return result

      } catch (error) {
        console.error('数据加载失败:', error)
        
        if (showLoading && feedback) {
          feedback.hideLoading()
        }

        pageState.setError(error)

        // 错误恢复策略
        if (errorRecovery === 'auto') {
          this.handleErrorRecovery(error, loadFunction, options)
        }

        throw error
      } finally {
        pageState.setLoading(false, false)
      }
    },

    // 刷新数据
    async refreshData(loadFunction, options = {}) {
      const refreshOptions = {
        ...options,
        useCache: false,
        forceRefresh: true,
        showSkeleton: false
      }

      try {
        pageState.setRefreshing(true)
        const result = await this.loadData(loadFunction, refreshOptions)
        
        if (feedback) {
          feedback.showSuccess('刷新成功')
        }

        return result
      } catch (error) {
        if (feedback) {
          feedback.showError('刷新失败')
        }
        throw error
      } finally {
        pageState.setRefreshing(false)
        uni.stopPullDownRefresh()
      }
    },

    // 加载更多数据
    async loadMoreData(loadFunction, options = {}) {
      return await pageState.handleLoadMore(async () => {
        const result = await loadFunction()
        
        // 检查是否还有更多数据
        if (result && typeof result === 'object') {
          if (result.hasMore !== undefined) {
            pageState.setHasMore(result.hasMore)
          }
          return result
        }

        return result
      })
    },

    // 检查数据是否为空
    checkEmpty(data) {
      if (!data) return true
      
      if (Array.isArray(data)) {
        return data.length === 0
      }
      
      if (typeof data === 'object') {
        if (data.list && Array.isArray(data.list)) {
          return data.list.length === 0
        }
        if (data.data && Array.isArray(data.data)) {
          return data.data.length === 0
        }
        return Object.keys(data).length === 0
      }
      
      return false
    },

    // 错误恢复处理
    async handleErrorRecovery(error, loadFunction, options) {
      // 网络错误自动重试
      if (error.code === 'NETWORK_ERROR' && pageState.canRetry) {
        setTimeout(async () => {
          try {
            await pageState.retry(() => this.loadData(loadFunction, options))
          } catch (retryError) {
            console.error('自动重试失败:', retryError)
          }
        }, 3000)
      }
    }
  }

  /**
   * 页面交互管理
   */
  const interactionManager = {
    // 处理页面滚动
    handlePageScroll(e) {
      interactionState.scrollTop = e.scrollTop
      interactionState.showBackToTop = e.scrollTop > 500
      interactionState.lastActiveTime = Date.now()
    },

    // 回到顶部
    scrollToTop(duration = 300) {
      uni.pageScrollTo({
        scrollTop: 0,
        duration
      })
    },

    // 处理页面可见性变化
    handleVisibilityChange(visible) {
      interactionState.isVisible = visible
      
      if (visible) {
        interactionState.lastActiveTime = Date.now()
        
        // 页面重新可见时检查数据是否需要刷新
        this.checkDataFreshness()
      }
    },

    // 检查数据新鲜度
    checkDataFreshness() {
      const now = Date.now()
      const timeSinceLastActive = now - interactionState.lastActiveTime
      
      // 如果离开页面超过5分钟，自动刷新数据
      if (timeSinceLastActive > 5 * 60 * 1000 && !cacheManager.isCacheValid()) {
        console.log('数据可能已过期，建议刷新')
        
        if (feedback) {
          feedback.showInfo('数据可能已更新，下拉刷新获取最新内容')
        }
      }
    },

    // 处理网络状态变化
    handleNetworkChange(isOnline) {
      interactionState.networkStatus = isOnline ? 'online' : 'offline'
      
      if (isOnline && feedback) {
        feedback.showSuccess('网络连接已恢复')
      } else if (feedback) {
        feedback.showWarning('网络连接已断开')
      }
    }
  }

  /**
   * 页面导航管理
   */
  const navigationManager = {
    // 带数据导航
    navigateWithData(url, data, options = {}) {
      return navigationHelper.navigateWithData(url, data, options)
    },

    // 返回并传递数据
    navigateBackWithData(data, delta = 1) {
      return navigationHelper.navigateBackWithData(data, delta)
    },

    // 获取导航数据
    getNavigationData() {
      return stateSync ? stateSync.navigationData : null
    }
  }

  // 监听网络状态变化
  onMounted(() => {
    // 监听网络状态
    uni.onNetworkStatusChange((res) => {
      interactionManager.handleNetworkChange(res.isConnected)
    })

    // 监听页面显示/隐藏
    uni.onAppShow(() => {
      interactionManager.handleVisibilityChange(true)
    })

    uni.onAppHide(() => {
      interactionManager.handleVisibilityChange(false)
    })
  })

  // 清理资源
  onUnmounted(() => {
    if (stateSync) {
      stateSync.unregister()
    }
  })

  return {
    // 状态
    ...pageState,
    interactionState,
    loadingConfig,
    
    // 数据管理
    dataLoader,
    cacheManager,
    
    // 交互管理
    interactionManager,
    navigationManager,
    
    // 工具方法
    feedback,
    stateSync,
    
    // 便捷方法
    loadData: dataLoader.loadData.bind(dataLoader),
    refreshData: dataLoader.refreshData.bind(dataLoader),
    loadMoreData: dataLoader.loadMoreData.bind(dataLoader),
    navigateWithData: navigationManager.navigateWithData,
    navigateBackWithData: navigationManager.navigateBackWithData,
    
    // 配置更新
    updateLoadingConfig(config) {
      Object.assign(loadingConfig, config)
    },
    
    // 状态计算属性
    get isOnline() {
      return interactionState.networkStatus === 'online'
    },
    
    get shouldShowBackToTop() {
      return interactionState.showBackToTop
    },
    
    get isDataFresh() {
      return cacheManager.isCacheValid()
    }
  }
}

/**
 * 页面交互 Hook（简化版）
 * @param {string} pageId - 页面标识
 * @param {Object} options - 配置选项
 */
export const usePageInteraction = (pageId, options = {}) => {
  return createPageInteraction({
    pageId,
    ...options
  })
}

/**
 * 数据加载 Hook（专用于数据加载场景）
 * @param {Function} loadFunction - 数据加载函数
 * @param {Object} options - 配置选项
 */
export const useDataLoader = (loadFunction, options = {}) => {
  const {
    immediate = true,
    ...otherOptions
  } = options

  const pageInteraction = createPageInteraction(otherOptions)

  // 立即加载数据
  if (immediate) {
    onMounted(async () => {
      try {
        await pageInteraction.loadData(loadFunction)
      } catch (error) {
        console.error('初始数据加载失败:', error)
      }
    })
  }

  return {
    ...pageInteraction,
    reload: () => pageInteraction.loadData(loadFunction, { forceRefresh: true }),
    refresh: () => pageInteraction.refreshData(loadFunction)
  }
}

export default {
  createPageInteraction,
  usePageInteraction,
  useDataLoader
}