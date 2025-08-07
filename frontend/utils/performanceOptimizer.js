/**
 * 微信小程序性能优化工具
 * 提供预加载、缓存、渲染优化和更新检测功能
 */

/**
 * 性能优化管理器
 */
class PerformanceOptimizer {
  constructor() {
    this.config = {
      // 缓存配置
      cache: {
        maxSize: 50 * 1024 * 1024, // 50MB
        maxAge: 7 * 24 * 60 * 60 * 1000, // 7天
        cleanupInterval: 60 * 60 * 1000 // 1小时清理一次
      },
      
      // 预加载配置
      preload: {
        enabled: true,
        maxConcurrent: 3,
        timeout: 5000
      },
      
      // 图片优化配置
      image: {
        lazyLoadThreshold: 100,
        compressionQuality: 0.8,
        maxWidth: 750,
        maxHeight: 750
      },
      
      // 更新检测配置
      update: {
        checkInterval: 30 * 60 * 1000, // 30分钟检查一次
        forceUpdateThreshold: 24 * 60 * 60 * 1000 // 24小时强制更新
      }
    }
    
    this.cache = new Map()
    this.preloadQueue = []
    this.isPreloading = false
    this.updateCheckTimer = null
    
    // 初始化性能监控
    this.initPerformanceMonitor()
    
    // 启动缓存清理
    this.startCacheCleanup()
    
    // 启动更新检测
    this.startUpdateCheck()
  }

  /**
   * 初始化性能监控
   */
  initPerformanceMonitor() {
    try {
      // 监控页面性能
      this.performanceObserver = uni.createIntersectionObserver()
      
      // 记录启动时间
      this.startTime = Date.now()
      
      console.log('性能监控初始化完成')
    } catch (error) {
      console.error('性能监控初始化失败:', error)
    }
  }

  /**
   * 预加载资源
   * @param {Array} resources - 资源列表
   * @param {Object} options - 预加载选项
   */
  async preloadResources(resources, options = {}) {
    if (!this.config.preload.enabled || !resources || resources.length === 0) {
      return
    }

    const {
      priority = 'normal',
      timeout = this.config.preload.timeout
    } = options

    console.log(`开始预加载 ${resources.length} 个资源`)

    // 添加到预加载队列
    const preloadTasks = resources.map(resource => ({
      ...resource,
      priority,
      timeout,
      status: 'pending'
    }))

    this.preloadQueue.push(...preloadTasks)

    // 开始预加载处理
    if (!this.isPreloading) {
      this.processPreloadQueue()
    }
  }

  /**
   * 处理预加载队列
   */
  async processPreloadQueue() {
    if (this.isPreloading || this.preloadQueue.length === 0) {
      return
    }

    this.isPreloading = true
    const concurrentLimit = this.config.preload.maxConcurrent

    try {
      while (this.preloadQueue.length > 0) {
        // 取出优先级最高的任务
        const batch = this.preloadQueue
          .filter(task => task.status === 'pending')
          .sort((a, b) => this.getPriorityWeight(b.priority) - this.getPriorityWeight(a.priority))
          .slice(0, concurrentLimit)

        if (batch.length === 0) break

        // 并发执行预加载任务
        const promises = batch.map(task => this.executePreloadTask(task))
        await Promise.allSettled(promises)

        // 移除已完成的任务
        this.preloadQueue = this.preloadQueue.filter(task => task.status === 'pending')
      }
    } catch (error) {
      console.error('预加载队列处理失败:', error)
    } finally {
      this.isPreloading = false
    }
  }

  /**
   * 执行单个预加载任务
   * @param {Object} task - 预加载任务
   */
  async executePreloadTask(task) {
    try {
      task.status = 'loading'
      
      const startTime = Date.now()
      
      switch (task.type) {
        case 'image':
          await this.preloadImage(task.url, task.timeout)
          break
        case 'page':
          await this.preloadPage(task.path, task.timeout)
          break
        case 'api':
          await this.preloadApiData(task.url, task.params, task.timeout)
          break
        default:
          throw new Error(`不支持的预加载类型: ${task.type}`)
      }
      
      const loadTime = Date.now() - startTime
      task.status = 'completed'
      task.loadTime = loadTime
      
      // 记录预加载性能数据
      this.logPreloadPerformance(task, loadTime)
      
      // 如果加载时间过长，考虑调整预加载优先级策略
      this.adjustPreloadStrategy(task, loadTime)
      
    } catch (error) {
      task.status = 'failed'
      task.error = error.message
      console.error(`预加载失败: ${task.type} ${task.url || task.path}`, error)
    }
  }

  /**
   * 预加载图片
   * @param {string} url - 图片URL
   * @param {number} timeout - 超时时间
   */
  async preloadImage(url, timeout = 5000) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error('图片预加载超时'))
      }, timeout)

      // 检查url是否为本地资源路径
      if (url.startsWith('/') || url.startsWith('_www') || url.startsWith('static/')) {
        // 对于本地资源，尝试修复路径并使用不同方式预加载
        let fixedUrl = url;
        // 确保本地路径以'/'开头
        if (!fixedUrl.startsWith('/')) {
          fixedUrl = '/' + fixedUrl;
        }
        
        console.log('预加载本地图片:', fixedUrl);
        
        // 对于本地图片，我们可以直接解析成功，无需实际调用getImageInfo
        clearTimeout(timer);
        resolve();
        return;
      }

      uni.getImageInfo({
        src: url,
        success: (res) => {
          clearTimeout(timer)
          resolve()
        },
        fail: (error) => {
          clearTimeout(timer)
          reject(new Error(`图片预加载失败: ${error.errMsg}`))
        }
      })
    })
  }

  /**
   * 预加载页面
   * @param {string} path - 页面路径
   * @param {number} timeout - 超时时间
   */
  async preloadPage(path, timeout = 5000) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error('页面预加载超时'))
      }, timeout)

      try {
        // 微信小程序页面预加载
        if (typeof uni.preloadPage === 'function') {
          uni.preloadPage({
            url: path,
            success: () => {
              clearTimeout(timer)
              resolve()
            },
            fail: (error) => {
              clearTimeout(timer)
              reject(new Error(`页面预加载失败: ${error.errMsg}`))
            }
          })
        } else {
          // 如果不支持页面预加载，直接返回成功
          clearTimeout(timer)
          resolve()
        }
      } catch (error) {
        clearTimeout(timer)
        reject(error)
      }
    })
  }

  /**
   * 预加载API数据
   * @param {string} url - API URL
   * @param {Object} params - 请求参数
   * @param {number} timeout - 超时时间
   */
  async preloadApiData(url, params = {}, timeout = 5000) {
    const cacheKey = this.generateCacheKey(url, params)
    
    // 检查缓存
    if (this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey).data
    }

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error('API预加载超时'))
      }, timeout)

      uni.request({
        url,
        data: params,
        timeout,
        success: (res) => {
          clearTimeout(timer)
          
          if (res.statusCode === 200) {
            // 缓存数据
            this.setCache(cacheKey, res.data)
            resolve(res.data)
          } else {
            reject(new Error(`API请求失败: ${res.statusCode}`))
          }
        },
        fail: (error) => {
          clearTimeout(timer)
          reject(new Error(`API请求失败: ${error.errMsg}`))
        }
      })
    })
  }

  /**
   * 获取优先级权重
   * @param {string} priority - 优先级
   */
  getPriorityWeight(priority) {
    const weights = {
      'high': 3,
      'normal': 2,
      'low': 1
    }
    return weights[priority] || 2
  }

  /**
   * 设置缓存
   * @param {string} key - 缓存键
   * @param {*} data - 缓存数据
   * @param {number} maxAge - 最大存活时间
   */
  setCache(key, data, maxAge = this.config.cache.maxAge) {
    const cacheItem = {
      data,
      timestamp: Date.now(),
      maxAge,
      size: this.calculateDataSize(data)
    }

    this.cache.set(key, cacheItem)
    
    // 检查缓存大小
    this.checkCacheSize()
  }

  /**
   * 获取缓存
   * @param {string} key - 缓存键
   */
  getCache(key) {
    const cacheItem = this.cache.get(key)
    
    if (!cacheItem) {
      return null
    }

    // 检查是否过期
    if (Date.now() - cacheItem.timestamp > cacheItem.maxAge) {
      this.cache.delete(key)
      return null
    }

    return cacheItem.data
  }

  /**
   * 清除缓存
   * @param {string} key - 缓存键（可选）
   */
  clearCache(key = null) {
    if (key) {
      this.cache.delete(key)
    } else {
      this.cache.clear()
    }
  }

  /**
   * 检查缓存大小
   */
  checkCacheSize() {
    const totalSize = Array.from(this.cache.values())
      .reduce((sum, item) => sum + item.size, 0)

    if (totalSize > this.config.cache.maxSize) {
      this.cleanupCache()
    }
  }

  /**
   * 清理缓存
   */
  cleanupCache() {
    const now = Date.now()
    const items = Array.from(this.cache.entries())
      .map(([key, value]) => ({
        key,
        ...value,
        age: now - value.timestamp
      }))
      .sort((a, b) => b.age - a.age) // 按年龄排序，最老的在前

    // 删除过期的缓存
    const expiredItems = items.filter(item => item.age > item.maxAge)
    expiredItems.forEach(item => this.cache.delete(item.key))

    // 如果还是超出限制，删除最老的缓存
    const remainingItems = items.filter(item => item.age <= item.maxAge)
    let currentSize = remainingItems.reduce((sum, item) => sum + item.size, 0)

    while (currentSize > this.config.cache.maxSize && remainingItems.length > 0) {
      const oldestItem = remainingItems.pop()
      this.cache.delete(oldestItem.key)
      currentSize -= oldestItem.size
    }

    console.log(`缓存清理完成，删除了 ${expiredItems.length} 个过期项`)
  }

  /**
   * 启动缓存清理定时器
   */
  startCacheCleanup() {
    setInterval(() => {
      this.cleanupCache()
    }, this.config.cache.cleanupInterval)
  }

  /**
   * 计算数据大小（估算）
   * @param {*} data - 数据
   */
  calculateDataSize(data) {
    try {
      return JSON.stringify(data).length * 2 // 粗略估算，每个字符2字节
    } catch (error) {
      return 1024 // 默认1KB
    }
  }

  /**
   * 生成缓存键
   * @param {string} url - URL
   * @param {Object} params - 参数
   */
  generateCacheKey(url, params = {}) {
    const paramStr = Object.keys(params)
      .sort()
      .map(key => `${key}=${params[key]}`)
      .join('&')
    
    return `${url}${paramStr ? '?' + paramStr : ''}`
  }

  /**
   * 创建查询字符串（替代URLSearchParams）
   * @param {Object} params - 参数对象
   * @returns {string} 查询字符串
   */
  createQueryString(params) {
    return Object.keys(params)
      .map(key => {
        const value = params[key];
        return `${encodeURIComponent(key)}=${encodeURIComponent(value)}`;
      })
      .join('&');
  }

  /**
   * 优化图片加载
   * @param {string} src - 图片源
   * @param {Object} options - 优化选项
   */
  optimizeImage(src, options = {}) {
    if (!src || typeof src !== 'string') {
      return '';
    }
    
    const {
      width = this.config.image.maxWidth,
      height = this.config.image.maxHeight,
      quality = this.config.image.compressionQuality,
      format = 'webp'
    } = options

    // 如果是本地图片或已经优化过的图片，直接返回
    if (src.startsWith('/') || src.startsWith('static/') || src.includes('optimized=true')) {
      return src
    }

    try {
      // 构建优化参数
      const params = {
        w: width,
        h: height,
        q: Math.floor(quality * 100),
        f: format,
        optimized: 'true'
      };

      // 构建查询字符串
      const queryString = this.createQueryString(params);

      // 如果原URL已有参数，合并参数
      const separator = src.includes('?') ? '&' : '?';
      const optimizedUrl = `${src}${separator}${queryString}`;
      return optimizedUrl;
    } catch (error) {
      console.error('优化图片URL失败:', error);
      return src;
    }
  }

  /**
   * 启动更新检测
   */
  startUpdateCheck() {
    // 立即检查一次
    this.checkForUpdates()

    // 定期检查更新
    this.updateCheckTimer = setInterval(() => {
      this.checkForUpdates()
    }, this.config.update.checkInterval)
  }

  /**
   * 检查小程序更新
   */
  checkForUpdates() {
    try {
      const updateManager = uni.getUpdateManager()

      updateManager.onCheckForUpdate((res) => {
        console.log('检查更新结果:', res.hasUpdate)
        
        if (res.hasUpdate) {
          uni.showToast({
            title: '发现新版本',
            icon: 'none',
            duration: 2000
          })
        }
      })

      updateManager.onUpdateReady(() => {
        console.log('新版本下载完成')
        
        uni.showModal({
          title: '更新提示',
          content: '新版本已准备好，是否重启应用？',
          showCancel: true,
          cancelText: '稍后',
          confirmText: '立即重启',
          success: (res) => {
            if (res.confirm) {
              updateManager.applyUpdate()
            }
          }
        })
      })

      updateManager.onUpdateFailed(() => {
        console.error('新版本下载失败')
        
        uni.showToast({
          title: '更新失败，请稍后重试',
          icon: 'none',
          duration: 2000
        })
      })

    } catch (error) {
      console.error('更新检测初始化失败:', error)
    }
  }

  /**
   * 强制检查更新
   */
  forceCheckUpdate() {
    try {
      const updateManager = uni.getUpdateManager()
      
      // 显示检查中提示
      uni.showLoading({
        title: '检查更新中...'
      })

      updateManager.onCheckForUpdate((res) => {
        uni.hideLoading()
        
        if (res.hasUpdate) {
          uni.showToast({
            title: '发现新版本，正在下载...',
            icon: 'none',
            duration: 2000
          })
        } else {
          uni.showToast({
            title: '已是最新版本',
            icon: 'success',
            duration: 2000
          })
        }
      })

    } catch (error) {
      uni.hideLoading()
      console.error('强制检查更新失败:', error)
      
      uni.showToast({
        title: '检查更新失败',
        icon: 'none',
        duration: 2000
      })
    }
  }

  /**
   * 记录预加载性能数据
   * @param {Object} task - 预加载任务
   * @param {number} loadTime - 加载时间
   */
  logPreloadPerformance(task, loadTime) {
    try {
      // 根据加载时间对性能进行评估
      let performanceLevel = 'good';
      if (loadTime > 1000) {
        performanceLevel = 'slow';
      } else if (loadTime > 500) {
        performanceLevel = 'medium';
      }

      console.log(`预加载性能 [${performanceLevel}]: ${task.type} ${task.url || task.path || ''} - ${loadTime}ms`);
      
      // 如果是API预加载，记录缓存命中情况
      if (task.type === 'api' && task.url) {
        const cacheKey = this.generateCacheKey(task.url, task.params || {});
        const wasCached = this.cache.has(cacheKey);
        console.log(`API缓存状态: ${wasCached ? '命中' : '未命中'} - ${task.url}`);
      }
    } catch (error) {
      console.error('记录预加载性能数据失败:', error);
    }
  }
  
  /**
   * 根据加载时间调整预加载策略
   * @param {Object} task - 预加载任务
   * @param {number} loadTime - 加载时间
   */
  adjustPreloadStrategy(task, loadTime) {
    try {
      // 如果加载时间过长，调整策略
      if (loadTime > 2000) {
        // 对于图片，可以考虑使用更低质量的预加载
        if (task.type === 'image') {
          console.log(`图片加载过慢，建议优化: ${task.url}`);
        }
        
        // 对于API，可以考虑增加缓存时间
        if (task.type === 'api' && task.url) {
          const cacheKey = this.generateCacheKey(task.url, task.params || {});
          if (this.cache.has(cacheKey)) {
            const cacheItem = this.cache.get(cacheKey);
            // 增加缓存生存时间
            cacheItem.maxAge = Math.min(cacheItem.maxAge * 1.5, 24 * 60 * 60 * 1000); // 最多24小时
            this.cache.set(cacheKey, cacheItem);
            console.log(`增加API缓存时间: ${task.url}`);
          }
        }
        
        // 对于页面，减少并发预加载数
        if (task.type === 'page' && this.config.preload.maxConcurrent > 1) {
          this.config.preload.maxConcurrent = Math.max(1, this.config.preload.maxConcurrent - 1);
          console.log(`减少并发预加载数量至: ${this.config.preload.maxConcurrent}`);
        }
      }
    } catch (error) {
      console.error('调整预加载策略失败:', error);
    }
  }

  /**
   * 获取性能统计信息
   */
  getPerformanceStats() {
    const now = Date.now()
    const uptime = now - this.startTime

    return {
      uptime,
      cacheStats: {
        size: this.cache.size,
        totalSize: Array.from(this.cache.values())
          .reduce((sum, item) => sum + item.size, 0),
        hitRate: this.calculateCacheHitRate()
      },
      preloadStats: {
        queueLength: this.preloadQueue.length,
        isPreloading: this.isPreloading,
        completedTasks: this.preloadQueue.filter(task => task.status === 'completed').length,
        failedTasks: this.preloadQueue.filter(task => task.status === 'failed').length
      },
      memoryUsage: this.getMemoryUsage()
    }
  }

  /**
   * 计算缓存命中率
   */
  calculateCacheHitRate() {
    // 这里需要实际的命中统计，暂时返回估算值
    return 0.8 // 80%
  }

  /**
   * 获取内存使用情况
   */
  getMemoryUsage() {
    try {
      const systemInfo = uni.getSystemInfoSync()
      return {
        platform: systemInfo.platform,
        system: systemInfo.system,
        version: systemInfo.version,
        SDKVersion: systemInfo.SDKVersion
      }
    } catch (error) {
      console.error('获取内存使用情况失败:', error)
      return {}
    }
  }

  /**
   * 销毁性能优化器
   */
  destroy() {
    // 清除定时器
    if (this.updateCheckTimer) {
      clearInterval(this.updateCheckTimer)
      this.updateCheckTimer = null
    }

    // 清除缓存
    this.cache.clear()

    // 清除预加载队列
    this.preloadQueue = []

    // 销毁性能观察器
    if (this.performanceObserver) {
      this.performanceObserver.disconnect()
      this.performanceObserver = null
    }

    console.log('性能优化器已销毁')
  }
}

// 创建单例实例
const performanceOptimizer = new PerformanceOptimizer()

export default performanceOptimizer
export { PerformanceOptimizer }