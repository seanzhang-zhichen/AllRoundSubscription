/**
 * 用户反馈管理器
 * 提供统一的错误处理、用户反馈和交互提示机制
 */

import { reactive, ref } from 'vue'
import { useAppStore } from '@/stores/app'

// 反馈类型枚举
export const FeedbackType = {
  SUCCESS: 'success',
  ERROR: 'error',
  WARNING: 'warning',
  INFO: 'info',
  LOADING: 'loading'
}

// 反馈优先级
export const FeedbackPriority = {
  LOW: 1,
  NORMAL: 2,
  HIGH: 3,
  CRITICAL: 4
}

// 全局反馈管理器
class FeedbackManager {
  constructor() {
    this.feedbackQueue = reactive([])
    this.currentFeedback = ref(null)
    this.isProcessing = ref(false)
    this.config = reactive({
      maxQueueSize: 10,
      defaultDuration: 2000,
      enableVibration: true,
      enableSound: true,
      autoHideLoading: true
    })
  }

  /**
   * 显示成功提示
   * @param {string} message - 提示消息
   * @param {Object} options - 选项
   */
  showSuccess(message, options = {}) {
    return this.addFeedback({
      type: FeedbackType.SUCCESS,
      message,
      icon: 'success',
      duration: 1500,
      ...options
    })
  }

  /**
   * 显示错误提示
   * @param {string|Error} error - 错误信息或错误对象
   * @param {Object} options - 选项
   */
  showError(error, options = {}) {
    const message = this.parseErrorMessage(error)
    
    return this.addFeedback({
      type: FeedbackType.ERROR,
      message,
      icon: 'none',
      duration: 3000,
      priority: FeedbackPriority.HIGH,
      vibrate: true,
      ...options
    })
  }

  /**
   * 显示警告提示
   * @param {string} message - 警告消息
   * @param {Object} options - 选项
   */
  showWarning(message, options = {}) {
    return this.addFeedback({
      type: FeedbackType.WARNING,
      message,
      icon: 'none',
      duration: 2500,
      priority: FeedbackPriority.NORMAL,
      ...options
    })
  }

  /**
   * 显示信息提示
   * @param {string} message - 信息消息
   * @param {Object} options - 选项
   */
  showInfo(message, options = {}) {
    return this.addFeedback({
      type: FeedbackType.INFO,
      message,
      icon: 'none',
      duration: 2000,
      ...options
    })
  }

  /**
   * 显示加载提示
   * @param {string} message - 加载消息
   * @param {Object} options - 选项
   */
  showLoading(message = '加载中...', options = {}) {
    return this.addFeedback({
      type: FeedbackType.LOADING,
      message,
      icon: 'loading',
      duration: 0, // 加载提示不自动隐藏
      mask: true,
      priority: FeedbackPriority.HIGH,
      ...options
    })
  }

  /**
   * 隐藏加载提示
   */
  hideLoading() {
    // 移除所有加载类型的反馈
    this.feedbackQueue.splice(0, this.feedbackQueue.length, 
      ...this.feedbackQueue.filter(item => item.type !== FeedbackType.LOADING)
    )

    // 如果当前显示的是加载提示，立即隐藏
    if (this.currentFeedback.value?.type === FeedbackType.LOADING) {
      uni.hideLoading()
      this.currentFeedback.value = null
      this.processQueue()
    }
  }

  /**
   * 显示确认对话框
   * @param {string} title - 标题
   * @param {string} content - 内容
   * @param {Object} options - 选项
   */
  async showConfirm(title, content, options = {}) {
    const {
      confirmText = '确定',
      cancelText = '取消',
      showCancel = true
    } = options

    return new Promise((resolve) => {
      uni.showModal({
        title,
        content,
        confirmText,
        cancelText,
        showCancel,
        success: (res) => {
          resolve({
            confirmed: res.confirm,
            cancelled: res.cancel
          })
        },
        fail: () => {
          resolve({
            confirmed: false,
            cancelled: true
          })
        }
      })
    })
  }

  /**
   * 显示操作菜单
   * @param {Array} items - 菜单项
   * @param {Object} options - 选项
   */
  async showActionSheet(items, options = {}) {
    const {
      title = '请选择操作'
    } = options

    return new Promise((resolve) => {
      uni.showActionSheet({
        itemList: items,
        title,
        success: (res) => {
          resolve({
            selectedIndex: res.tapIndex,
            selectedItem: items[res.tapIndex],
            cancelled: false
          })
        },
        fail: () => {
          resolve({
            selectedIndex: -1,
            selectedItem: null,
            cancelled: true
          })
        }
      })
    })
  }

  /**
   * 添加反馈到队列
   * @param {Object} feedback - 反馈对象
   */
  addFeedback(feedback) {
    const feedbackItem = {
      id: Date.now() + Math.random(),
      timestamp: Date.now(),
      priority: FeedbackPriority.NORMAL,
      ...feedback
    }

    // 检查队列大小
    if (this.feedbackQueue.length >= this.config.maxQueueSize) {
      // 移除优先级最低的反馈
      const lowestPriorityIndex = this.findLowestPriorityIndex()
      this.feedbackQueue.splice(lowestPriorityIndex, 1)
    }

    // 插入到合适位置（按优先级排序）
    const insertIndex = this.findInsertIndex(feedbackItem.priority)
    this.feedbackQueue.splice(insertIndex, 0, feedbackItem)

    // 处理队列
    this.processQueue()

    return feedbackItem.id
  }

  /**
   * 处理反馈队列
   */
  async processQueue() {
    if (this.isProcessing.value || this.feedbackQueue.length === 0) {
      return
    }

    this.isProcessing.value = true

    while (this.feedbackQueue.length > 0) {
      const feedback = this.feedbackQueue.shift()
      await this.showFeedback(feedback)
    }

    this.isProcessing.value = false
  }

  /**
   * 显示单个反馈
   * @param {Object} feedback - 反馈对象
   */
  async showFeedback(feedback) {
    this.currentFeedback.value = feedback

    try {
      // 触觉反馈
      if (feedback.vibrate && this.config.enableVibration) {
        this.triggerVibration(feedback.type)
      }

      // 显示反馈
      await this.displayFeedback(feedback)

    } catch (error) {
      console.error('显示反馈失败:', error)
    } finally {
      this.currentFeedback.value = null
    }
  }

  /**
   * 显示反馈内容
   * @param {Object} feedback - 反馈对象
   */
  async displayFeedback(feedback) {
    const { type, message, icon, duration, mask } = feedback

    if (type === FeedbackType.LOADING) {
      uni.showLoading({
        title: message,
        mask: mask !== false
      })

      // 如果设置了自动隐藏时间
      if (duration > 0) {
        setTimeout(() => {
          this.hideLoading()
        }, duration)
      }
    } else {
      uni.showToast({
        title: message,
        icon: icon || 'none',
        duration: duration || this.config.defaultDuration,
        mask: mask === true
      })

      // 等待提示消失
      if (duration > 0) {
        await new Promise(resolve => setTimeout(resolve, duration))
      }
    }
  }

  /**
   * 触发触觉反馈
   * @param {string} type - 反馈类型
   */
  triggerVibration(type) {
    if (!this.config.enableVibration) return

    try {
      switch (type) {
        case FeedbackType.SUCCESS:
          uni.vibrateShort({ type: 'light' })
          break
        case FeedbackType.ERROR:
          uni.vibrateShort({ type: 'heavy' })
          break
        case FeedbackType.WARNING:
          uni.vibrateShort({ type: 'medium' })
          break
        default:
          uni.vibrateShort({ type: 'light' })
      }
    } catch (error) {
      console.warn('触觉反馈失败:', error)
    }
  }

  /**
   * 解析错误消息
   * @param {string|Error|Object} error - 错误对象
   * @returns {string} 用户友好的错误消息
   */
  parseErrorMessage(error) {
    if (typeof error === 'string') {
      return error
    }

    if (error instanceof Error) {
      return error.message || '操作失败'
    }

    if (error && typeof error === 'object') {
      // API错误响应
      if (error.message) {
        return error.message
      }

      // HTTP错误
      if (error.status || error.statusCode) {
        return this.getHttpErrorMessage(error.status || error.statusCode)
      }

      // 网络错误
      if (error.errMsg) {
        return this.getNetworkErrorMessage(error.errMsg)
      }
    }

    return '操作失败，请重试'
  }

  /**
   * 获取HTTP错误消息
   * @param {number} status - HTTP状态码
   * @returns {string} 错误消息
   */
  getHttpErrorMessage(status) {
    const errorMessages = {
      400: '请求参数错误',
      401: '登录已过期，请重新登录',
      403: '权限不足',
      404: '请求的资源不存在',
      408: '请求超时',
      429: '请求过于频繁，请稍后重试',
      500: '服务器内部错误',
      502: '网关错误',
      503: '服务暂时不可用',
      504: '网关超时'
    }

    return errorMessages[status] || `请求失败 (${status})`
  }

  /**
   * 获取网络错误消息
   * @param {string} errMsg - 错误消息
   * @returns {string} 用户友好的错误消息
   */
  getNetworkErrorMessage(errMsg) {
    if (errMsg.includes('timeout')) {
      return '网络请求超时，请检查网络连接'
    }
    
    if (errMsg.includes('fail')) {
      return '网络连接失败，请检查网络设置'
    }

    if (errMsg.includes('abort')) {
      return '请求已取消'
    }

    return '网络异常，请重试'
  }

  /**
   * 查找最低优先级索引
   * @returns {number} 索引
   */
  findLowestPriorityIndex() {
    let lowestPriority = FeedbackPriority.CRITICAL
    let lowestIndex = 0

    this.feedbackQueue.forEach((item, index) => {
      if (item.priority < lowestPriority) {
        lowestPriority = item.priority
        lowestIndex = index
      }
    })

    return lowestIndex
  }

  /**
   * 查找插入位置
   * @param {number} priority - 优先级
   * @returns {number} 插入索引
   */
  findInsertIndex(priority) {
    for (let i = 0; i < this.feedbackQueue.length; i++) {
      if (this.feedbackQueue[i].priority < priority) {
        return i
      }
    }
    return this.feedbackQueue.length
  }

  /**
   * 清空反馈队列
   */
  clearQueue() {
    this.feedbackQueue.splice(0)
    
    if (this.currentFeedback.value?.type === FeedbackType.LOADING) {
      uni.hideLoading()
    }
    
    this.currentFeedback.value = null
    this.isProcessing.value = false
  }

  /**
   * 更新配置
   * @param {Object} newConfig - 新配置
   */
  updateConfig(newConfig) {
    Object.assign(this.config, newConfig)
  }
}

// 创建全局实例
const feedbackManager = new FeedbackManager()

/**
 * 反馈管理 Hook
 */
export const useFeedback = () => {
  return {
    showSuccess: (message, options) => feedbackManager.showSuccess(message, options),
    showError: (error, options) => feedbackManager.showError(error, options),
    showWarning: (message, options) => feedbackManager.showWarning(message, options),
    showInfo: (message, options) => feedbackManager.showInfo(message, options),
    showLoading: (message, options) => feedbackManager.showLoading(message, options),
    hideLoading: () => feedbackManager.hideLoading(),
    showConfirm: (title, content, options) => feedbackManager.showConfirm(title, content, options),
    showActionSheet: (items, options) => feedbackManager.showActionSheet(items, options),
    clearQueue: () => feedbackManager.clearQueue(),
    updateConfig: (config) => feedbackManager.updateConfig(config)
  }
}

/**
 * 错误处理装饰器
 * @param {Function} asyncFunction - 异步函数
 * @param {Object} options - 选项
 */
export const withErrorHandling = (asyncFunction, options = {}) => {
  const {
    showLoading = false,
    loadingMessage = '处理中...',
    successMessage = '',
    showSuccess = false,
    errorMessage = '操作失败',
    showError = true,
    retryable = false,
    maxRetries = 3
  } = options

  return async (...args) => {
    let retryCount = 0
    
    const executeWithRetry = async () => {
      try {
        if (showLoading) {
          feedbackManager.showLoading(loadingMessage)
        }

        const result = await asyncFunction(...args)

        if (showLoading) {
          feedbackManager.hideLoading()
        }

        if (showSuccess && successMessage) {
          feedbackManager.showSuccess(successMessage)
        }

        return result
      } catch (error) {
        if (showLoading) {
          feedbackManager.hideLoading()
        }

        if (retryable && retryCount < maxRetries) {
          retryCount++
          
          const shouldRetry = await feedbackManager.showConfirm(
            '操作失败',
            `${errorMessage}，是否重试？(${retryCount}/${maxRetries})`,
            {
              confirmText: '重试',
              cancelText: '取消'
            }
          )

          if (shouldRetry.confirmed) {
            return executeWithRetry()
          }
        }

        if (showError) {
          feedbackManager.showError(error, { message: errorMessage })
        }

        throw error
      }
    }

    return executeWithRetry()
  }
}

export default feedbackManager