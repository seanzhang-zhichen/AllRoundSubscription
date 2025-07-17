/**
 * 网络状态管理器
 * 提供网络状态检测、离线处理和智能重连功能
 */

import { reactive, ref, watch } from 'vue'
import { useFeedback } from './feedbackManager'
import cacheManager from './cacheManager'

// 网络类型枚举
export const NetworkType = {
  WIFI: 'wifi',
  CELLULAR_2G: '2g',
  CELLULAR_3G: '3g',
  CELLULAR_4G: '4g',
  CELLULAR_5G: '5g',
  ETHERNET: 'ethernet',
  UNKNOWN: 'unknown',
  NONE: 'none'
}

// 连接质量等级
export const ConnectionQuality = {
  EXCELLENT: 'excellent', // 优秀
  GOOD: 'good',          // 良好
  FAIR: 'fair',          // 一般
  POOR: 'poor',          // 较差
  OFFLINE: 'offline'     // 离线
}

/**
 * 网络管理器类
 */
class NetworkManager {
  constructor() {
    // 网络状态
    this.networkState = reactive({
      isOnline: true,
      networkType: NetworkType.UNKNOWN,
      connectionQuality: ConnectionQuality.GOOD,
      signalStrength: 0,
      downloadSpeed: 0,
      uploadSpeed: 0,
      latency: 0,
      lastOnlineTime: Date.now(),
      lastOfflineTime: 0,
      reconnectAttempts: 0
    })

    // 配置
    this.config = reactive({
      // 网络检测配置
      detection: {
        interval: 30 * 1000, // 30秒检测一次
        timeout: 5000, // 5秒超时
        testUrls: [
          'https://www.baidu.com/favicon.ico',
          'https://cdn.jsdelivr.net/gh/jquery/jquery/dist/jquery.min.js'
        ]
      },
      
      // 重连配置
      reconnect: {
        maxAttempts: 5,
        baseDelay: 1000, // 基础延迟1秒
        maxDelay: 30000, // 最大延迟30秒
        backoffFactor: 2 // 退避因子
      },
      
      // 离线配置
      offline: {
        showNotification: true,
        cacheRequests: true,
        maxCachedRequests: 100
      },
      
      // 质量评估配置
      quality: {
        excellentThreshold: { latency: 50, speed: 10 }, // 延迟<50ms, 速度>10Mbps
        goodThreshold: { latency: 150, speed: 5 },      // 延迟<150ms, 速度>5Mbps
        fairThreshold: { latency: 500, speed: 1 },      // 延迟<500ms, 速度>1Mbps
      }
    })

    // 离线请求队列
    this.offlineQueue = []
    
    // 定时器
    this.detectionTimer = null
    this.reconnectTimer = null
    
    // 反馈管理器
    this.feedback = useFeedback()
    
    // 初始化
    this.init()
  }

  /**
   * 初始化网络管理器
   */
  async init() {
    try {
      // 获取初始网络状态
      await this.updateNetworkStatus()
      
      // 监听网络状态变化
      this.setupNetworkListeners()
      
      // 启动定期检测
      this.startPeriodicDetection()
      
      console.log('网络管理器初始化完成')
    } catch (error) {
      console.error('网络管理器初始化失败:', error)
    }
  }

  /**
   * 设置网络状态监听器
   */
  setupNetworkListeners() {
    // 监听网络状态变化
    uni.onNetworkStatusChange((res) => {
      console.log('网络状态变化:', res)
      this.handleNetworkChange(res)
    })

    // 监听应用前后台切换
    uni.onAppShow(() => {
      console.log('应用进入前台，检查网络状态')
      this.updateNetworkStatus()
    })
  }

  /**
   * 处理网络状态变化
   */
  async handleNetworkChange(networkInfo) {
    const wasOnline = this.networkState.isOnline
    const newIsOnline = networkInfo.isConnected
    
    // 更新基础网络信息
    this.networkState.isOnline = newIsOnline
    this.networkState.networkType = networkInfo.networkType || NetworkType.UNKNOWN

    if (!wasOnline && newIsOnline) {
      // 从离线恢复到在线
      await this.handleOnlineRecovery()
    } else if (wasOnline && !newIsOnline) {
      // 从在线变为离线
      await this.handleOfflineTransition()
    }

    // 更新连接质量
    await this.updateConnectionQuality()
  }

  /**
   * 更新网络状态
   */
  async updateNetworkStatus() {
    try {
      // 获取网络类型
      const networkType = await this.getNetworkType()
      this.networkState.networkType = networkType
      
      // 检测网络连通性
      const isOnline = await this.checkConnectivity()
      const wasOnline = this.networkState.isOnline
      this.networkState.isOnline = isOnline

      // 更新时间戳
      if (isOnline) {
        this.networkState.lastOnlineTime = Date.now()
        if (!wasOnline) {
          this.networkState.reconnectAttempts = 0
        }
      } else {
        this.networkState.lastOfflineTime = Date.now()
      }

      // 更新连接质量
      if (isOnline) {
        await this.updateConnectionQuality()
      } else {
        this.networkState.connectionQuality = ConnectionQuality.OFFLINE
      }

    } catch (error) {
      console.error('更新网络状态失败:', error)
      this.networkState.isOnline = false
      this.networkState.connectionQuality = ConnectionQuality.OFFLINE
    }
  }

  /**
   * 获取网络类型
   */
  async getNetworkType() {
    return new Promise((resolve) => {
      uni.getNetworkType({
        success: (res) => {
          resolve(res.networkType || NetworkType.UNKNOWN)
        },
        fail: () => {
          resolve(NetworkType.UNKNOWN)
        }
      })
    })
  }

  /**
   * 检测网络连通性
   */
  async checkConnectivity() {
    const testPromises = this.config.detection.testUrls.map(url => 
      this.testConnection(url)
    )

    try {
      // 任意一个测试成功即认为在线
      const results = await Promise.allSettled(testPromises)
      return results.some(result => result.status === 'fulfilled' && result.value)
    } catch (error) {
      console.error('网络连通性检测失败:', error)
      return false
    }
  }

  /**
   * 测试单个连接
   */
  async testConnection(url) {
    return new Promise((resolve) => {
      const startTime = Date.now()
      
      uni.request({
        url,
        method: 'HEAD',
        timeout: this.config.detection.timeout,
        success: (res) => {
          const latency = Date.now() - startTime
          this.networkState.latency = latency
          resolve(res.statusCode === 200)
        },
        fail: () => {
          resolve(false)
        }
      })
    })
  }

  /**
   * 更新连接质量
   */
  async updateConnectionQuality() {
    if (!this.networkState.isOnline) {
      this.networkState.connectionQuality = ConnectionQuality.OFFLINE
      return
    }

    // 测量网络性能
    await this.measureNetworkPerformance()

    const { latency, downloadSpeed } = this.networkState
    const { excellentThreshold, goodThreshold, fairThreshold } = this.config.quality

    if (latency <= excellentThreshold.latency && downloadSpeed >= excellentThreshold.speed) {
      this.networkState.connectionQuality = ConnectionQuality.EXCELLENT
    } else if (latency <= goodThreshold.latency && downloadSpeed >= goodThreshold.speed) {
      this.networkState.connectionQuality = ConnectionQuality.GOOD
    } else if (latency <= fairThreshold.latency && downloadSpeed >= fairThreshold.speed) {
      this.networkState.connectionQuality = ConnectionQuality.FAIR
    } else {
      this.networkState.connectionQuality = ConnectionQuality.POOR
    }
  }

  /**
   * 测量网络性能
   */
  async measureNetworkPerformance() {
    try {
      // 简单的下载速度测试
      const testUrl = this.config.detection.testUrls[0]
      const startTime = Date.now()
      
      await new Promise((resolve, reject) => {
        uni.request({
          url: testUrl,
          timeout: this.config.detection.timeout,
          success: (res) => {
            const endTime = Date.now()
            const duration = endTime - startTime
            
            // 估算下载速度（简化计算）
            const dataSize = JSON.stringify(res.data || '').length
            const speedKbps = (dataSize * 8) / (duration / 1000) / 1024
            
            this.networkState.downloadSpeed = speedKbps
            this.networkState.latency = duration
            
            resolve()
          },
          fail: reject
        })
      })
    } catch (error) {
      console.error('网络性能测量失败:', error)
      // 使用默认值
      this.networkState.downloadSpeed = 1
      this.networkState.latency = 1000
    }
  }

  /**
   * 处理在线恢复
   */
  async handleOnlineRecovery() {
    console.log('网络连接已恢复')
    
    // 显示恢复通知
    if (this.config.offline.showNotification) {
      this.feedback.showSuccess('网络连接已恢复')
    }

    // 处理离线队列
    await this.processOfflineQueue()
    
    // 重置重连计数
    this.networkState.reconnectAttempts = 0
  }

  /**
   * 处理离线转换
   */
  async handleOfflineTransition() {
    console.log('网络连接已断开')
    
    // 显示离线通知
    if (this.config.offline.showNotification) {
      this.feedback.showWarning('网络连接已断开，部分功能可能受限')
    }

    // 启动重连尝试
    this.startReconnectAttempts()
  }

  /**
   * 启动重连尝试
   */
  startReconnectAttempts() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
    }

    const attempt = () => {
      if (this.networkState.reconnectAttempts >= this.config.reconnect.maxAttempts) {
        console.log('达到最大重连次数，停止重连')
        return
      }

      this.networkState.reconnectAttempts++
      console.log(`尝试重连 (${this.networkState.reconnectAttempts}/${this.config.reconnect.maxAttempts})`)

      this.updateNetworkStatus().then(() => {
        if (!this.networkState.isOnline) {
          // 计算下次重连延迟（指数退避）
          const delay = Math.min(
            this.config.reconnect.baseDelay * 
            Math.pow(this.config.reconnect.backoffFactor, this.networkState.reconnectAttempts - 1),
            this.config.reconnect.maxDelay
          )

          this.reconnectTimer = setTimeout(attempt, delay)
        }
      })
    }

    // 立即尝试第一次重连
    setTimeout(attempt, this.config.reconnect.baseDelay)
  }

  /**
   * 启动定期检测
   */
  startPeriodicDetection() {
    this.detectionTimer = setInterval(() => {
      this.updateNetworkStatus()
    }, this.config.detection.interval)
  }

  /**
   * 停止定期检测
   */
  stopPeriodicDetection() {
    if (this.detectionTimer) {
      clearInterval(this.detectionTimer)
      this.detectionTimer = null
    }
  }

  /**
   * 添加离线请求到队列
   */
  addToOfflineQueue(request) {
    if (!this.config.offline.cacheRequests) {
      return false
    }

    if (this.offlineQueue.length >= this.config.offline.maxCachedRequests) {
      // 移除最旧的请求
      this.offlineQueue.shift()
    }

    this.offlineQueue.push({
      ...request,
      timestamp: Date.now(),
      retryCount: 0
    })

    console.log(`请求已添加到离线队列，当前队列长度: ${this.offlineQueue.length}`)
    return true
  }

  /**
   * 处理离线队列
   */
  async processOfflineQueue() {
    if (this.offlineQueue.length === 0) {
      return
    }

    console.log(`开始处理离线队列，共 ${this.offlineQueue.length} 个请求`)

    const processedRequests = []
    
    for (const request of this.offlineQueue) {
      try {
        // 重新发送请求
        await this.retryRequest(request)
        processedRequests.push(request)
        console.log('离线请求重发成功:', request.url)
      } catch (error) {
        console.error('离线请求重发失败:', request.url, error)
        
        // 增加重试次数
        request.retryCount++
        
        // 如果重试次数过多，从队列中移除
        if (request.retryCount >= 3) {
          processedRequests.push(request)
        }
      }
    }

    // 从队列中移除已处理的请求
    this.offlineQueue = this.offlineQueue.filter(
      request => !processedRequests.includes(request)
    )

    if (processedRequests.length > 0) {
      this.feedback.showInfo(`已处理 ${processedRequests.length} 个离线请求`)
    }
  }

  /**
   * 重试请求
   */
  async retryRequest(request) {
    return new Promise((resolve, reject) => {
      uni.request({
        ...request,
        success: resolve,
        fail: reject
      })
    })
  }

  /**
   * 获取网络状态
   */
  getNetworkState() {
    return { ...this.networkState }
  }

  /**
   * 获取连接质量描述
   */
  getQualityDescription() {
    const descriptions = {
      [ConnectionQuality.EXCELLENT]: '网络状况优秀',
      [ConnectionQuality.GOOD]: '网络状况良好',
      [ConnectionQuality.FAIR]: '网络状况一般',
      [ConnectionQuality.POOR]: '网络状况较差',
      [ConnectionQuality.OFFLINE]: '网络已断开'
    }
    
    return descriptions[this.networkState.connectionQuality] || '网络状况未知'
  }

  /**
   * 获取网络类型描述
   */
  getNetworkTypeDescription() {
    const descriptions = {
      [NetworkType.WIFI]: 'WiFi',
      [NetworkType.CELLULAR_2G]: '2G网络',
      [NetworkType.CELLULAR_3G]: '3G网络',
      [NetworkType.CELLULAR_4G]: '4G网络',
      [NetworkType.CELLULAR_5G]: '5G网络',
      [NetworkType.ETHERNET]: '以太网',
      [NetworkType.UNKNOWN]: '未知网络',
      [NetworkType.NONE]: '无网络连接'
    }
    
    return descriptions[this.networkState.networkType] || '未知网络'
  }

  /**
   * 检查是否应该使用缓存
   */
  shouldUseCache() {
    return !this.networkState.isOnline || 
           this.networkState.connectionQuality === ConnectionQuality.POOR
  }

  /**
   * 检查是否应该预加载
   */
  shouldPreload() {
    return this.networkState.isOnline && 
           this.networkState.connectionQuality >= ConnectionQuality.GOOD &&
           this.networkState.networkType === NetworkType.WIFI
  }

  /**
   * 获取推荐的图片质量
   */
  getRecommendedImageQuality() {
    if (!this.networkState.isOnline) {
      return 'low'
    }

    switch (this.networkState.connectionQuality) {
      case ConnectionQuality.EXCELLENT:
        return 'high'
      case ConnectionQuality.GOOD:
        return 'medium'
      case ConnectionQuality.FAIR:
        return 'low'
      case ConnectionQuality.POOR:
        return 'low'
      default:
        return 'medium'
    }
  }

  /**
   * 更新配置
   */
  updateConfig(newConfig) {
    Object.assign(this.config, newConfig)
  }

  /**
   * 销毁网络管理器
   */
  destroy() {
    this.stopPeriodicDetection()
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    
    this.offlineQueue = []
    
    console.log('网络管理器已销毁')
  }
}

// 创建全局网络管理器实例
const networkManager = new NetworkManager()

/**
 * 网络管理 Hook
 */
export const useNetwork = () => {
  return {
    networkState: networkManager.networkState,
    getNetworkState: () => networkManager.getNetworkState(),
    getQualityDescription: () => networkManager.getQualityDescription(),
    getNetworkTypeDescription: () => networkManager.getNetworkTypeDescription(),
    shouldUseCache: () => networkManager.shouldUseCache(),
    shouldPreload: () => networkManager.shouldPreload(),
    getRecommendedImageQuality: () => networkManager.getRecommendedImageQuality(),
    addToOfflineQueue: (request) => networkManager.addToOfflineQueue(request),
    updateConfig: (config) => networkManager.updateConfig(config)
  }
}

export default networkManager
export { NetworkManager, NetworkType, ConnectionQuality }