/**
 * 页面间状态同步工具
 * 提供统一的数据传递和状态同步机制
 */

import { ref, reactive, watch, nextTick } from 'vue'
import { useAppStore } from '@/stores/app'

// 全局状态同步管理器
class StateSyncManager {
  constructor() {
    this.syncStates = new Map()
    this.eventBus = reactive({})
    this.pageStates = new Map()
    this.navigationData = reactive({})
  }

  /**
   * 注册页面状态同步
   * @param {string} pageId - 页面标识
   * @param {Object} state - 页面状态
   * @param {Object} options - 同步选项
   */
  registerPageState(pageId, state, options = {}) {
    const {
      syncKeys = [], // 需要同步的状态键
      persistKeys = [], // 需要持久化的状态键
      autoSync = true // 是否自动同步
    } = options

    this.pageStates.set(pageId, {
      state,
      syncKeys,
      persistKeys,
      autoSync,
      lastUpdate: Date.now()
    })

    // 自动同步监听
    if (autoSync && syncKeys.length > 0) {
      this.setupAutoSync(pageId, state, syncKeys)
    }

    // 持久化监听
    if (persistKeys.length > 0) {
      this.setupPersistence(pageId, state, persistKeys)
    }

    console.log(`页面状态已注册: ${pageId}`)
  }

  /**
   * 设置自动同步
   */
  setupAutoSync(pageId, state, syncKeys) {
    syncKeys.forEach(key => {
      if (state[key] !== undefined) {
        watch(
          () => state[key],
          (newValue, oldValue) => {
            if (newValue !== oldValue) {
              this.broadcastStateChange(pageId, key, newValue)
            }
          },
          { deep: true }
        )
      }
    })
  }

  /**
   * 设置状态持久化
   */
  setupPersistence(pageId, state, persistKeys) {
    // 加载持久化数据
    this.loadPersistedState(pageId, state, persistKeys)

    // 监听状态变化并持久化
    persistKeys.forEach(key => {
      if (state[key] !== undefined) {
        watch(
          () => state[key],
          (newValue) => {
            this.persistState(pageId, key, newValue)
          },
          { deep: true }
        )
      }
    })
  }

  /**
   * 广播状态变化
   */
  broadcastStateChange(sourcePageId, key, value) {
    const eventKey = `${sourcePageId}:${key}`
    this.eventBus[eventKey] = {
      value,
      timestamp: Date.now(),
      source: sourcePageId
    }

    // 通知其他页面
    this.pageStates.forEach((pageConfig, pageId) => {
      if (pageId !== sourcePageId && pageConfig.syncKeys.includes(key)) {
        this.syncStateToPage(pageId, key, value)
      }
    })
  }

  /**
   * 同步状态到指定页面
   */
  syncStateToPage(pageId, key, value) {
    const pageConfig = this.pageStates.get(pageId)
    if (pageConfig && pageConfig.state[key] !== undefined) {
      pageConfig.state[key] = value
      pageConfig.lastUpdate = Date.now()
    }
  }

  /**
   * 持久化状态
   */
  persistState(pageId, key, value) {
    try {
      const storageKey = `pageState:${pageId}:${key}`
      uni.setStorageSync(storageKey, {
        value,
        timestamp: Date.now()
      })
    } catch (error) {
      console.error(`持久化状态失败: ${pageId}:${key}`, error)
    }
  }

  /**
   * 加载持久化状态
   */
  loadPersistedState(pageId, state, persistKeys) {
    persistKeys.forEach(key => {
      try {
        const storageKey = `pageState:${pageId}:${key}`
        const persistedData = uni.getStorageSync(storageKey)
        
        if (persistedData && persistedData.value !== undefined) {
          // 检查数据是否过期（24小时）
          const isExpired = Date.now() - persistedData.timestamp > 24 * 60 * 60 * 1000
          
          if (!isExpired) {
            state[key] = persistedData.value
          } else {
            // 清除过期数据
            uni.removeStorageSync(storageKey)
          }
        }
      } catch (error) {
        console.error(`加载持久化状态失败: ${pageId}:${key}`, error)
      }
    })
  }

  /**
   * 设置页面导航数据
   * @param {string} targetPage - 目标页面
   * @param {Object} data - 传递的数据
   * @param {Object} options - 选项
   */
  setNavigationData(targetPage, data, options = {}) {
    const {
      expire = 5 * 60 * 1000, // 5分钟过期
      persistent = false // 是否持久化
    } = options

    const navigationKey = `nav:${targetPage}`
    
    this.navigationData[navigationKey] = {
      data,
      timestamp: Date.now(),
      expire,
      persistent
    }

    // 持久化导航数据
    if (persistent) {
      try {
        uni.setStorageSync(navigationKey, {
          data,
          timestamp: Date.now(),
          expire
        })
      } catch (error) {
        console.error('持久化导航数据失败:', error)
      }
    }

    console.log(`导航数据已设置: ${targetPage}`, data)
  }

  /**
   * 获取页面导航数据
   * @param {string} currentPage - 当前页面
   * @returns {Object|null} 导航数据
   */
  getNavigationData(currentPage) {
    const navigationKey = `nav:${currentPage}`
    
    // 先从内存中获取
    let navData = this.navigationData[navigationKey]
    
    // 如果内存中没有，尝试从存储中获取
    if (!navData) {
      try {
        const persistedData = uni.getStorageSync(navigationKey)
        if (persistedData) {
          navData = persistedData
        }
      } catch (error) {
        console.error('获取持久化导航数据失败:', error)
      }
    }

    if (!navData) {
      return null
    }

    // 检查是否过期
    const isExpired = Date.now() - navData.timestamp > navData.expire
    
    if (isExpired) {
      // 清除过期数据
      delete this.navigationData[navigationKey]
      try {
        uni.removeStorageSync(navigationKey)
      } catch (error) {
        console.error('清除过期导航数据失败:', error)
      }
      return null
    }

    // 清除一次性导航数据
    if (!navData.persistent) {
      delete this.navigationData[navigationKey]
    }

    return navData.data
  }

  /**
   * 清除页面导航数据
   * @param {string} page - 页面标识
   */
  clearNavigationData(page) {
    const navigationKey = `nav:${page}`
    delete this.navigationData[navigationKey]
    
    try {
      uni.removeStorageSync(navigationKey)
    } catch (error) {
      console.error('清除导航数据失败:', error)
    }
  }

  /**
   * 获取页面状态快照
   * @param {string} pageId - 页面标识
   * @returns {Object|null} 状态快照
   */
  getPageStateSnapshot(pageId) {
    const pageConfig = this.pageStates.get(pageId)
    if (!pageConfig) {
      return null
    }

    const snapshot = {}
    pageConfig.syncKeys.forEach(key => {
      if (pageConfig.state[key] !== undefined) {
        snapshot[key] = JSON.parse(JSON.stringify(pageConfig.state[key]))
      }
    })

    return {
      ...snapshot,
      _meta: {
        pageId,
        lastUpdate: pageConfig.lastUpdate,
        timestamp: Date.now()
      }
    }
  }

  /**
   * 恢复页面状态
   * @param {string} pageId - 页面标识
   * @param {Object} snapshot - 状态快照
   */
  restorePageState(pageId, snapshot) {
    const pageConfig = this.pageStates.get(pageId)
    if (!pageConfig || !snapshot) {
      return false
    }

    try {
      Object.keys(snapshot).forEach(key => {
        if (key !== '_meta' && pageConfig.state[key] !== undefined) {
          pageConfig.state[key] = snapshot[key]
        }
      })

      pageConfig.lastUpdate = Date.now()
      console.log(`页面状态已恢复: ${pageId}`)
      return true
    } catch (error) {
      console.error(`恢复页面状态失败: ${pageId}`, error)
      return false
    }
  }

  /**
   * 清理过期数据
   */
  cleanup() {
    const now = Date.now()
    
    // 清理过期的导航数据
    Object.keys(this.navigationData).forEach(key => {
      const navData = this.navigationData[key]
      if (navData && now - navData.timestamp > navData.expire) {
        delete this.navigationData[key]
      }
    })

    // 清理过期的持久化数据
    try {
      const storage = uni.getStorageInfoSync()
      storage.keys.forEach(key => {
        if (key.startsWith('pageState:') || key.startsWith('nav:')) {
          try {
            const data = uni.getStorageSync(key)
            if (data && data.timestamp && now - data.timestamp > 24 * 60 * 60 * 1000) {
              uni.removeStorageSync(key)
            }
          } catch (error) {
            // 忽略单个清理错误
          }
        }
      })
    } catch (error) {
      console.error('清理过期数据失败:', error)
    }
  }

  /**
   * 注销页面状态
   * @param {string} pageId - 页面标识
   */
  unregisterPageState(pageId) {
    this.pageStates.delete(pageId)
    console.log(`页面状态已注销: ${pageId}`)
  }
}

// 创建全局实例
const stateSyncManager = new StateSyncManager()

// 定期清理过期数据
setInterval(() => {
  stateSyncManager.cleanup()
}, 10 * 60 * 1000) // 每10分钟清理一次

/**
 * 页面状态同步 Hook
 * @param {string} pageId - 页面标识
 * @param {Object} state - 页面状态
 * @param {Object} options - 同步选项
 */
export const useStateSync = (pageId, state, options = {}) => {
  // 注册页面状态
  stateSyncManager.registerPageState(pageId, state, options)

  // 获取导航数据
  const navigationData = stateSyncManager.getNavigationData(pageId)

  // 页面卸载时注销状态
  const unregister = () => {
    stateSyncManager.unregisterPageState(pageId)
  }

  return {
    navigationData,
    unregister,
    setNavigationData: (targetPage, data, opts) => 
      stateSyncManager.setNavigationData(targetPage, data, opts),
    getStateSnapshot: () => 
      stateSyncManager.getPageStateSnapshot(pageId),
    restoreState: (snapshot) => 
      stateSyncManager.restorePageState(pageId, snapshot),
    clearNavigationData: (page) => 
      stateSyncManager.clearNavigationData(page)
  }
}

/**
 * 导航数据传递工具
 */
export const navigationHelper = {
  /**
   * 带数据导航到页面
   * @param {string} url - 目标页面URL
   * @param {Object} data - 传递的数据
   * @param {Object} options - 导航选项
   */
  navigateWithData(url, data = {}, options = {}) {
    const {
      navigationType = 'navigateTo',
      dataOptions = {}
    } = options

    // 提取页面路径
    const pagePath = url.split('?')[0].replace(/^\//, '')
    
    // 设置导航数据
    stateSyncManager.setNavigationData(pagePath, data, dataOptions)

    // 执行导航
    const navigateOptions = {
      url,
      ...options
    }

    delete navigateOptions.navigationType
    delete navigateOptions.dataOptions

    return uni[navigationType](navigateOptions)
  },

  /**
   * 返回上一页并传递数据
   * @param {Object} data - 传递给上一页的数据
   * @param {number} delta - 返回层数
   */
  navigateBackWithData(data = {}, delta = 1) {
    // 获取页面栈
    const pages = getCurrentPages()
    if (pages.length > delta) {
      const targetPage = pages[pages.length - delta - 1]
      const targetRoute = targetPage.route

      // 设置导航数据
      stateSyncManager.setNavigationData(targetRoute, data, {
        expire: 2 * 60 * 1000 // 2分钟过期
      })
    }

    return uni.navigateBack({ delta })
  }
}

export default stateSyncManager