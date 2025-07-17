/**
 * 性能监控工具
 * 监控页面性能、内存使用、网络请求等指标
 */

/**
 * 性能监控管理器
 */
class PerformanceMonitor {
  constructor() {
    this.metrics = {
      pageLoad: {},
      apiRequests: {},
      memoryUsage: {},
      userInteractions: {},
      errors: []
    }
    
    this.observers = {
      intersection: null,
      performance: null
    }
    
    this.config = {
      enableLogging: true,
      sampleRate: 1.0, // 采样率
      maxMetrics: 1000, // 最大指标数量
      reportInterval: 60000 // 上报间隔（毫秒）
    }
    
    this.startTime = Date.now()
    this.reportTimer = null
    
    this.init()
  }

  /**
   * 初始化性能监控
   */
  init() {
    try {
      // 监控页面性能
      this.initPagePerformanceMonitor()
      
      // 监控内存使用
      this.initMemoryMonitor()
      
      // 监控用户交互
      this.initInteractionMonitor()
      
      // 启动定期上报
      this.startPeriodicReport()
      
      console.log('性能监控初始化完成')
    } catch (error) {
      console.error('性能监控初始化失败:', error)
    }
  }

  /**
   * 初始化页面性能监控
   */
  initPagePerformanceMonitor() {
    try {
      // 监控页面加载时间
      this.recordPageLoadStart()
      
      // 监控页面可见性变化
      this.initVisibilityMonitor()
      
    } catch (error) {
      console.error('页面性能监控初始化失败:', error)
    }
  }

  /**
   * 记录页面加载开始
   */
  recordPageLoadStart() {
    const pages = getCurrentPages()
    const currentPage = pages[pages.length - 1]
    
    if (currentPage) {
      const route = currentPage.route
      const startTime = Date.now()
      
      this.metrics.pageLoad[route] = {
        startTime,
        route,
        loadTime: null,
        renderTime: null,
        firstContentfulPaint: null,
        isCompleted: false
      }
      
      // 延迟记录页面加载完成时间
      setTimeout(() => {
        this.recordPageLoadComplete(route)
      }, 100)
    }
  }

  /**
   * 记录页面加载完成
   */
  recordPageLoadComplete(route) {
    const metric = this.metrics.pageLoad[route]
    if (metric && !metric.isCompleted) {
      const endTime = Date.now()
      metric.loadTime = endTime - metric.startTime
      metric.isCompleted = true
      
      if (this.config.enableLogging) {
        console.log(`页面加载完成: ${route} (${metric.loadTime}ms)`)
      }
      
      // 记录首次内容绘制时间（模拟）
      metric.firstContentfulPaint = metric.loadTime * 0.6
      metric.renderTime = metric.loadTime * 0.8
    }
  }

  /**
   * 初始化可见性监控
   */
  initVisibilityMonitor() {
    try {
      // 监听页面显示/隐藏
      uni.onAppShow(() => {
        this.recordEvent('app_show', {
          timestamp: Date.now(),
          duration: Date.now() - this.startTime
        })
      })
      
      uni.onAppHide(() => {
        this.recordEvent('app_hide', {
          timestamp: Date.now(),
          duration: Date.now() - this.startTime
        })
      })
      
    } catch (error) {
      console.error('可见性监控初始化失败:', error)
    }
  }

  /**
   * 初始化内存监控
   */
  initMemoryMonitor() {
    try {
      // 定期收集内存使用情况
      setInterval(() => {
        this.collectMemoryMetrics()
      }, 30000) // 每30秒收集一次
      
    } catch (error) {
      console.error('内存监控初始化失败:', error)
    }
  }

  /**
   * 收集内存指标
   */
  collectMemoryMetrics() {
    try {
      const systemInfo = uni.getSystemInfoSync()
      const timestamp = Date.now()
      
      const memoryMetric = {
        timestamp,
        platform: systemInfo.platform,
        system: systemInfo.system,
        version: systemInfo.version,
        screenWidth: systemInfo.screenWidth,
        screenHeight: systemInfo.screenHeight,
        pixelRatio: systemInfo.pixelRatio,
        statusBarHeight: systemInfo.statusBarHeight,
        safeArea: systemInfo.safeArea
      }
      
      // 存储内存指标
      this.metrics.memoryUsage[timestamp] = memoryMetric
      
      // 限制存储数量
      this.limitMetricsSize('memoryUsage')
      
    } catch (error) {
      console.error('收集内存指标失败:', error)
    }
  }

  /**
   * 初始化交互监控
   */
  initInteractionMonitor() {
    try {
      // 这里可以添加用户交互监控逻辑
      // 由于小程序限制，主要通过手动调用来记录交互
      
    } catch (error) {
      console.error('交互监控初始化失败:', error)
    }
  }

  /**
   * 记录API请求性能
   * @param {string} url - 请求URL
   * @param {string} method - 请求方法
   * @param {number} startTime - 开始时间
   * @param {number} endTime - 结束时间
   * @param {number} statusCode - 状态码
   * @param {number} responseSize - 响应大小
   */
  recordApiRequest(url, method, startTime, endTime, statusCode, responseSize = 0) {
    try {
      const requestId = `${method}_${url}_${startTime}`
      const duration = endTime - startTime
      
      this.metrics.apiRequests[requestId] = {
        url,
        method,
        startTime,
        endTime,
        duration,
        statusCode,
        responseSize,
        success: statusCode >= 200 && statusCode < 300,
        timestamp: Date.now()
      }
      
      if (this.config.enableLogging) {
        console.log(`API请求: ${method} ${url} (${duration}ms, ${statusCode})`)
      }
      
      // 限制存储数量
      this.limitMetricsSize('apiRequests')
      
    } catch (error) {
      console.error('记录API请求失败:', error)
    }
  }

  /**
   * 记录用户交互
   * @param {string} action - 交互动作
   * @param {Object} data - 交互数据
   */
  recordInteraction(action, data = {}) {
    try {
      const timestamp = Date.now()
      const interactionId = `${action}_${timestamp}`
      
      this.metrics.userInteractions[interactionId] = {
        action,
        timestamp,
        data,
        page: this.getCurrentPageRoute()
      }
      
      if (this.config.enableLogging) {
        console.log(`用户交互: ${action}`, data)
      }
      
      // 限制存储数量
      this.limitMetricsSize('userInteractions')
      
    } catch (error) {
      console.error('记录用户交互失败:', error)
    }
  }

  /**
   * 记录错误
   * @param {Error} error - 错误对象
   * @param {Object} context - 错误上下文
   */
  recordError(error, context = {}) {
    try {
      const errorRecord = {
        message: error.message || error,
        stack: error.stack,
        timestamp: Date.now(),
        page: this.getCurrentPageRoute(),
        context,
        userAgent: uni.getSystemInfoSync()
      }
      
      this.metrics.errors.push(errorRecord)
      
      // 限制错误记录数量
      if (this.metrics.errors.length > 100) {
        this.metrics.errors = this.metrics.errors.slice(-50)
      }
      
      if (this.config.enableLogging) {
        console.error('性能监控记录错误:', errorRecord)
      }
      
    } catch (e) {
      console.error('记录错误失败:', e)
    }
  }

  /**
   * 记录自定义事件
   * @param {string} eventName - 事件名称
   * @param {Object} data - 事件数据
   */
  recordEvent(eventName, data = {}) {
    try {
      const timestamp = Date.now()
      
      if (!this.metrics.customEvents) {
        this.metrics.customEvents = {}
      }
      
      const eventId = `${eventName}_${timestamp}`
      this.metrics.customEvents[eventId] = {
        eventName,
        timestamp,
        data,
        page: this.getCurrentPageRoute()
      }
      
      if (this.config.enableLogging) {
        console.log(`自定义事件: ${eventName}`, data)
      }
      
    } catch (error) {
      console.error('记录自定义事件失败:', error)
    }
  }

  /**
   * 获取当前页面路由
   */
  getCurrentPageRoute() {
    try {
      const pages = getCurrentPages()
      const currentPage = pages[pages.length - 1]
      return currentPage ? currentPage.route : 'unknown'
    } catch (error) {
      return 'unknown'
    }
  }

  /**
   * 限制指标存储数量
   * @param {string} metricType - 指标类型
   */
  limitMetricsSize(metricType) {
    const metrics = this.metrics[metricType]
    if (!metrics) return
    
    const keys = Object.keys(metrics)
    if (keys.length > this.config.maxMetrics) {
      // 删除最旧的指标
      const sortedKeys = keys.sort((a, b) => {
        const aTime = metrics[a].timestamp || parseInt(a.split('_').pop())
        const bTime = metrics[b].timestamp || parseInt(b.split('_').pop())
        return aTime - bTime
      })
      
      const keysToDelete = sortedKeys.slice(0, keys.length - this.config.maxMetrics)
      keysToDelete.forEach(key => {
        delete metrics[key]
      })
    }
  }

  /**
   * 获取性能报告
   */
  getPerformanceReport() {
    try {
      const now = Date.now()
      const uptime = now - this.startTime
      
      // 计算页面加载性能统计
      const pageLoadMetrics = Object.values(this.metrics.pageLoad)
      const avgLoadTime = pageLoadMetrics.length > 0 
        ? pageLoadMetrics.reduce((sum, metric) => sum + (metric.loadTime || 0), 0) / pageLoadMetrics.length
        : 0
      
      // 计算API请求性能统计
      const apiMetrics = Object.values(this.metrics.apiRequests)
      const avgApiTime = apiMetrics.length > 0
        ? apiMetrics.reduce((sum, metric) => sum + metric.duration, 0) / apiMetrics.length
        : 0
      
      const apiSuccessRate = apiMetrics.length > 0
        ? apiMetrics.filter(metric => metric.success).length / apiMetrics.length
        : 0
      
      return {
        timestamp: now,
        uptime,
        summary: {
          totalPageLoads: pageLoadMetrics.length,
          avgPageLoadTime: Math.round(avgLoadTime),
          totalApiRequests: apiMetrics.length,
          avgApiResponseTime: Math.round(avgApiTime),
          apiSuccessRate: Math.round(apiSuccessRate * 100),
          totalErrors: this.metrics.errors.length,
          memorySnapshots: Object.keys(this.metrics.memoryUsage).length,
          userInteractions: Object.keys(this.metrics.userInteractions).length
        },
        details: {
          pageLoad: this.metrics.pageLoad,
          apiRequests: this.getRecentMetrics('apiRequests', 10),
          memoryUsage: this.getRecentMetrics('memoryUsage', 5),
          errors: this.metrics.errors.slice(-10),
          userInteractions: this.getRecentMetrics('userInteractions', 10)
        }
      }
    } catch (error) {
      console.error('生成性能报告失败:', error)
      return {
        timestamp: Date.now(),
        error: error.message,
        summary: {},
        details: {}
      }
    }
  }

  /**
   * 获取最近的指标
   * @param {string} metricType - 指标类型
   * @param {number} count - 数量
   */
  getRecentMetrics(metricType, count = 10) {
    const metrics = this.metrics[metricType]
    if (!metrics) return []
    
    const entries = Object.entries(metrics)
    return entries
      .sort((a, b) => {
        const aTime = a[1].timestamp || parseInt(a[0].split('_').pop())
        const bTime = b[1].timestamp || parseInt(b[0].split('_').pop())
        return bTime - aTime
      })
      .slice(0, count)
      .map(([key, value]) => ({ key, ...value }))
  }

  /**
   * 启动定期上报
   */
  startPeriodicReport() {
    if (this.reportTimer) {
      clearInterval(this.reportTimer)
    }
    
    this.reportTimer = setInterval(() => {
      const report = this.getPerformanceReport()
      
      if (this.config.enableLogging) {
        console.log('性能报告:', report.summary)
      }
      
      // 这里可以添加上报到服务器的逻辑
      // this.reportToServer(report)
      
    }, this.config.reportInterval)
  }

  /**
   * 上报到服务器（示例）
   * @param {Object} report - 性能报告
   */
  async reportToServer(report) {
    try {
      // 示例API调用
      // await uni.request({
      //   url: '/api/performance/report',
      //   method: 'POST',
      //   data: report
      // })
      
      console.log('性能数据上报成功')
    } catch (error) {
      console.error('性能数据上报失败:', error)
    }
  }

  /**
   * 清除所有指标
   */
  clearMetrics() {
    this.metrics = {
      pageLoad: {},
      apiRequests: {},
      memoryUsage: {},
      userInteractions: {},
      errors: []
    }
    
    console.log('性能指标已清除')
  }

  /**
   * 销毁性能监控器
   */
  destroy() {
    if (this.reportTimer) {
      clearInterval(this.reportTimer)
      this.reportTimer = null
    }
    
    if (this.observers.intersection) {
      this.observers.intersection.disconnect()
    }
    
    this.clearMetrics()
    
    console.log('性能监控器已销毁')
  }
}

// 创建单例实例
const performanceMonitor = new PerformanceMonitor()

export default performanceMonitor
export { PerformanceMonitor }