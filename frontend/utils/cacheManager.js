/**
 * 前端缓存管理器
 * 提供多层级缓存策略和智能缓存管理
 */

import { reactive, ref } from 'vue'

// 缓存策略枚举
export const CacheStrategy = {
  MEMORY_ONLY: 'memory_only',
  STORAGE_ONLY: 'storage_only',
  MEMORY_FIRST: 'memory_first',
  STORAGE_FIRST: 'storage_first',
  HYBRID: 'hybrid'
}

// 缓存优先级
export const CachePriority = {
  LOW: 1,
  NORMAL: 2,
  HIGH: 3,
  CRITICAL: 4
}

// 缓存类型
export const CacheType = {
  API_DATA: 'api_data',
  IMAGE: 'image',
  PAGE_DATA: 'page_data',
  USER_DATA: 'user_data',
  CONFIG: 'config'
}

/**
 * 缓存管理器类
 */
class CacheManager {
  constructor() {
    // 内存缓存
    this.memoryCache = new Map()
    
    // 缓存配置
    this.config = reactive({
      // 内存缓存配置
      memory: {
        maxSize: 20 * 1024 * 1024, // 20MB
        maxItems: 1000,
        defaultTTL: 30 * 60 * 1000 // 30分钟
      },
      
      // 存储缓存配置
      storage: {
        maxSize: 50 * 1024 * 1024, // 50MB
        defaultTTL: 24 * 60 * 60 * 1000, // 24小时
        keyPrefix: 'cache_'
      },
      
      // 清理配置
      cleanup: {
        interval: 10 * 60 * 1000, // 10分钟清理一次
        memoryThreshold: 0.8, // 内存使用率阈值
        storageThreshold: 0.9 // 存储使用率阈值
      }
    })
    
    // 缓存统计
    this.stats = reactive({
      memory: {
        hits: 0,
        misses: 0,
        size: 0,
        items: 0
      },
      storage: {
        hits: 0,
        misses: 0,
        size: 0,
        items: 0
      },
      operations: {
        sets: 0,
        gets: 0,
        deletes: 0,
        clears: 0
      }
    })
    
    // 启动清理定时器
    this.startCleanupTimer()
    
    // 初始化存储缓存统计
    this.initStorageStats()
  }

  /**
   * 设置缓存
   * @param {string} key - 缓存键
   * @param {*} value - 缓存值
   * @param {Object} options - 缓存选项
   */
  async set(key, value, options = {}) {
    const {
      strategy = CacheStrategy.HYBRID,
      ttl = this.config.memory.defaultTTL,
      priority = CachePriority.NORMAL,
      type = CacheType.API_DATA,
      compress = false,
      encrypt = false
    } = options

    this.stats.operations.sets++

    const cacheItem = {
      value: compress ? this.compress(value) : value,
      timestamp: Date.now(),
      ttl,
      priority,
      type,
      compressed: compress,
      encrypted: encrypt,
      size: this.calculateSize(value),
      accessCount: 0,
      lastAccess: Date.now()
    }

    // 根据策略选择缓存位置
    switch (strategy) {
      case CacheStrategy.MEMORY_ONLY:
        await this.setMemoryCache(key, cacheItem)
        break
        
      case CacheStrategy.STORAGE_ONLY:
        await this.setStorageCache(key, cacheItem)
        break
        
      case CacheStrategy.MEMORY_FIRST:
        await this.setMemoryCache(key, cacheItem)
        if (priority >= CachePriority.HIGH) {
          await this.setStorageCache(key, cacheItem)
        }
        break
        
      case CacheStrategy.STORAGE_FIRST:
        await this.setStorageCache(key, cacheItem)
        if (this.shouldCacheInMemory(cacheItem)) {
          await this.setMemoryCache(key, cacheItem)
        }
        break
        
      case CacheStrategy.HYBRID:
      default:
        // 根据数据特征智能选择
        if (this.shouldCacheInMemory(cacheItem)) {
          await this.setMemoryCache(key, cacheItem)
        }
        if (this.shouldCacheInStorage(cacheItem)) {
          await this.setStorageCache(key, cacheItem)
        }
        break
    }
  }

  /**
   * 获取缓存
   * @param {string} key - 缓存键
   * @param {Object} options - 获取选项
   */
  async get(key, options = {}) {
    const {
      strategy = CacheStrategy.HYBRID,
      updateAccess = true
    } = options

    this.stats.operations.gets++

    let cacheItem = null
    let source = null

    // 根据策略选择获取顺序
    switch (strategy) {
      case CacheStrategy.MEMORY_ONLY:
        cacheItem = await this.getMemoryCache(key)
        source = 'memory'
        break
        
      case CacheStrategy.STORAGE_ONLY:
        cacheItem = await this.getStorageCache(key)
        source = 'storage'
        break
        
      case CacheStrategy.MEMORY_FIRST:
      case CacheStrategy.HYBRID:
      default:
        // 先从内存获取
        cacheItem = await this.getMemoryCache(key)
        if (cacheItem) {
          source = 'memory'
        } else {
          // 内存中没有，从存储获取
          cacheItem = await this.getStorageCache(key)
          if (cacheItem) {
            source = 'storage'
            // 热数据提升到内存
            if (this.shouldPromoteToMemory(cacheItem)) {
              await this.setMemoryCache(key, cacheItem)
            }
          }
        }
        break
        
      case CacheStrategy.STORAGE_FIRST:
        // 先从存储获取
        cacheItem = await this.getStorageCache(key)
        if (cacheItem) {
          source = 'storage'
        } else {
          cacheItem = await this.getMemoryCache(key)
          source = 'memory'
        }
        break
    }

    if (!cacheItem) {
      this.stats[source || 'memory'].misses++
      return null
    }

    // 检查是否过期
    if (this.isExpired(cacheItem)) {
      await this.delete(key)
      this.stats[source].misses++
      return null
    }

    // 更新访问统计
    if (updateAccess) {
      cacheItem.accessCount++
      cacheItem.lastAccess = Date.now()
    }

    this.stats[source].hits++

    // 解压缩和解密
    let value = cacheItem.value
    if (cacheItem.compressed) {
      value = this.decompress(value)
    }
    if (cacheItem.encrypted) {
      value = this.decrypt(value)
    }

    return value
  }

  /**
   * 删除缓存
   * @param {string} key - 缓存键
   */
  async delete(key) {
    this.stats.operations.deletes++

    // 从内存删除
    if (this.memoryCache.has(key)) {
      const item = this.memoryCache.get(key)
      this.stats.memory.size -= item.size
      this.stats.memory.items--
      this.memoryCache.delete(key)
    }

    // 从存储删除
    try {
      const storageKey = this.getStorageKey(key)
      const item = uni.getStorageSync(storageKey)
      if (item) {
        this.stats.storage.size -= item.size || 0
        this.stats.storage.items--
        uni.removeStorageSync(storageKey)
      }
    } catch (error) {
      console.error('删除存储缓存失败:', error)
    }
  }

  /**
   * 清空缓存
   * @param {Object} options - 清空选项
   */
  async clear(options = {}) {
    const {
      type = null,
      olderThan = null,
      priority = null
    } = options

    this.stats.operations.clears++

    // 清空内存缓存
    if (type || olderThan || priority) {
      // 条件清空
      const keysToDelete = []
      
      for (const [key, item] of this.memoryCache.entries()) {
        if (this.shouldClearItem(item, { type, olderThan, priority })) {
          keysToDelete.push(key)
        }
      }
      
      keysToDelete.forEach(key => this.memoryCache.delete(key))
    } else {
      // 全部清空
      this.memoryCache.clear()
      this.stats.memory.size = 0
      this.stats.memory.items = 0
    }

    // 清空存储缓存
    try {
      const storageInfo = uni.getStorageInfoSync()
      const keysToDelete = storageInfo.keys.filter(key => 
        key.startsWith(this.config.storage.keyPrefix)
      )

      for (const key of keysToDelete) {
        if (type || olderThan || priority) {
          try {
            const item = uni.getStorageSync(key)
            if (item && this.shouldClearItem(item, { type, olderThan, priority })) {
              uni.removeStorageSync(key)
              this.stats.storage.items--
            }
          } catch (error) {
            // 忽略单个项目的错误
          }
        } else {
          uni.removeStorageSync(key)
        }
      }

      if (!type && !olderThan && !priority) {
        this.stats.storage.size = 0
        this.stats.storage.items = 0
      }
    } catch (error) {
      console.error('清空存储缓存失败:', error)
    }
  }

  /**
   * 设置内存缓存
   */
  async setMemoryCache(key, cacheItem) {
    // 检查内存限制
    if (this.stats.memory.size + cacheItem.size > this.config.memory.maxSize ||
        this.stats.memory.items >= this.config.memory.maxItems) {
      await this.evictMemoryCache()
    }

    this.memoryCache.set(key, cacheItem)
    this.stats.memory.size += cacheItem.size
    this.stats.memory.items++
  }

  /**
   * 获取内存缓存
   */
  async getMemoryCache(key) {
    return this.memoryCache.get(key) || null
  }

  /**
   * 设置存储缓存
   */
  async setStorageCache(key, cacheItem) {
    try {
      const storageKey = this.getStorageKey(key)
      
      // 检查存储限制
      const currentSize = this.getStorageSize()
      if (currentSize + cacheItem.size > this.config.storage.maxSize) {
        await this.evictStorageCache()
      }

      uni.setStorageSync(storageKey, cacheItem)
      this.stats.storage.size += cacheItem.size
      this.stats.storage.items++
    } catch (error) {
      console.error('设置存储缓存失败:', error)
    }
  }

  /**
   * 获取存储缓存
   */
  async getStorageCache(key) {
    try {
      const storageKey = this.getStorageKey(key)
      return uni.getStorageSync(storageKey) || null
    } catch (error) {
      console.error('获取存储缓存失败:', error)
      return null
    }
  }

  /**
   * 内存缓存淘汰
   */
  async evictMemoryCache() {
    const items = Array.from(this.memoryCache.entries())
      .map(([key, item]) => ({ key, ...item }))
      .sort((a, b) => {
        // 按优先级和最后访问时间排序
        if (a.priority !== b.priority) {
          return a.priority - b.priority
        }
        return a.lastAccess - b.lastAccess
      })

    // 删除25%的缓存项
    const deleteCount = Math.ceil(items.length * 0.25)
    for (let i = 0; i < deleteCount && i < items.length; i++) {
      const item = items[i]
      this.memoryCache.delete(item.key)
      this.stats.memory.size -= item.size
      this.stats.memory.items--
    }
  }

  /**
   * 存储缓存淘汰
   */
  async evictStorageCache() {
    try {
      const storageInfo = uni.getStorageInfoSync()
      const cacheKeys = storageInfo.keys.filter(key => 
        key.startsWith(this.config.storage.keyPrefix)
      )

      const items = []
      for (const key of cacheKeys) {
        try {
          const item = uni.getStorageSync(key)
          if (item) {
            items.push({ storageKey: key, ...item })
          }
        } catch (error) {
          // 忽略单个项目的错误
        }
      }

      // 按优先级和时间排序
      items.sort((a, b) => {
        if (a.priority !== b.priority) {
          return a.priority - b.priority
        }
        return a.timestamp - b.timestamp
      })

      // 删除30%的缓存项
      const deleteCount = Math.ceil(items.length * 0.3)
      for (let i = 0; i < deleteCount && i < items.length; i++) {
        const item = items[i]
        uni.removeStorageSync(item.storageKey)
        this.stats.storage.size -= item.size || 0
        this.stats.storage.items--
      }
    } catch (error) {
      console.error('存储缓存淘汰失败:', error)
    }
  }

  /**
   * 判断是否应该缓存到内存
   */
  shouldCacheInMemory(cacheItem) {
    // 高优先级数据
    if (cacheItem.priority >= CachePriority.HIGH) {
      return true
    }
    
    // 小数据
    if (cacheItem.size < 10 * 1024) { // 10KB
      return true
    }
    
    // 频繁访问的数据
    if (cacheItem.accessCount > 5) {
      return true
    }
    
    return false
  }

  /**
   * 判断是否应该缓存到存储
   */
  shouldCacheInStorage(cacheItem) {
    // 用户数据和配置数据
    if (cacheItem.type === CacheType.USER_DATA || 
        cacheItem.type === CacheType.CONFIG) {
      return true
    }
    
    // 高优先级数据
    if (cacheItem.priority >= CachePriority.HIGH) {
      return true
    }
    
    // TTL较长的数据
    if (cacheItem.ttl > 60 * 60 * 1000) { // 1小时
      return true
    }
    
    return false
  }

  /**
   * 判断是否应该提升到内存
   */
  shouldPromoteToMemory(cacheItem) {
    // 访问频率高
    if (cacheItem.accessCount > 3) {
      return true
    }
    
    // 最近访问过
    const timeSinceAccess = Date.now() - cacheItem.lastAccess
    if (timeSinceAccess < 5 * 60 * 1000) { // 5分钟内
      return true
    }
    
    return false
  }

  /**
   * 检查缓存项是否过期
   */
  isExpired(cacheItem) {
    return Date.now() - cacheItem.timestamp > cacheItem.ttl
  }

  /**
   * 判断是否应该清除缓存项
   */
  shouldClearItem(item, options) {
    const { type, olderThan, priority } = options
    
    if (type && item.type !== type) {
      return false
    }
    
    if (priority && item.priority < priority) {
      return false
    }
    
    if (olderThan && Date.now() - item.timestamp < olderThan) {
      return false
    }
    
    return true
  }

  /**
   * 获取存储键
   */
  getStorageKey(key) {
    return `${this.config.storage.keyPrefix}${key}`
  }

  /**
   * 计算数据大小
   */
  calculateSize(data) {
    try {
      return JSON.stringify(data).length * 2 // 估算字节数
    } catch (error) {
      return 1024 // 默认1KB
    }
  }

  /**
   * 获取存储大小
   */
  getStorageSize() {
    try {
      const storageInfo = uni.getStorageInfoSync()
      return storageInfo.currentSize * 1024 // 转换为字节
    } catch (error) {
      return 0
    }
  }

  /**
   * 压缩数据
   */
  compress(data) {
    // 简单的压缩实现，实际项目中可以使用更好的压缩算法
    try {
      return JSON.stringify(data)
    } catch (error) {
      return data
    }
  }

  /**
   * 解压缩数据
   */
  decompress(data) {
    try {
      return JSON.parse(data)
    } catch (error) {
      return data
    }
  }

  /**
   * 加密数据
   */
  encrypt(data) {
    // 简单的加密实现，实际项目中应使用更安全的加密算法
    return data
  }

  /**
   * 解密数据
   */
  decrypt(data) {
    return data
  }

  /**
   * 初始化存储统计
   */
  initStorageStats() {
    try {
      const storageInfo = uni.getStorageInfoSync()
      const cacheKeys = storageInfo.keys.filter(key => 
        key.startsWith(this.config.storage.keyPrefix)
      )
      
      this.stats.storage.items = cacheKeys.length
      this.stats.storage.size = this.getStorageSize()
    } catch (error) {
      console.error('初始化存储统计失败:', error)
    }
  }

  /**
   * 启动清理定时器
   */
  startCleanupTimer() {
    setInterval(() => {
      this.cleanup()
    }, this.config.cleanup.interval)
  }

  /**
   * 清理过期缓存
   */
  async cleanup() {
    const now = Date.now()
    
    // 清理内存缓存
    const memoryKeysToDelete = []
    for (const [key, item] of this.memoryCache.entries()) {
      if (this.isExpired(item)) {
        memoryKeysToDelete.push(key)
      }
    }
    
    memoryKeysToDelete.forEach(key => {
      const item = this.memoryCache.get(key)
      this.memoryCache.delete(key)
      this.stats.memory.size -= item.size
      this.stats.memory.items--
    })

    // 清理存储缓存
    try {
      const storageInfo = uni.getStorageInfoSync()
      const cacheKeys = storageInfo.keys.filter(key => 
        key.startsWith(this.config.storage.keyPrefix)
      )

      for (const key of cacheKeys) {
        try {
          const item = uni.getStorageSync(key)
          if (item && this.isExpired(item)) {
            uni.removeStorageSync(key)
            this.stats.storage.size -= item.size || 0
            this.stats.storage.items--
          }
        } catch (error) {
          // 忽略单个项目的错误
        }
      }
    } catch (error) {
      console.error('清理存储缓存失败:', error)
    }

    console.log(`缓存清理完成，删除了 ${memoryKeysToDelete.length} 个内存缓存项`)
  }

  /**
   * 获取缓存统计信息
   */
  getStats() {
    return {
      ...this.stats,
      hitRate: {
        memory: this.stats.memory.hits / (this.stats.memory.hits + this.stats.memory.misses) || 0,
        storage: this.stats.storage.hits / (this.stats.storage.hits + this.stats.storage.misses) || 0,
        overall: (this.stats.memory.hits + this.stats.storage.hits) / 
                (this.stats.memory.hits + this.stats.memory.misses + 
                 this.stats.storage.hits + this.stats.storage.misses) || 0
      },
      usage: {
        memory: this.stats.memory.size / this.config.memory.maxSize,
        storage: this.stats.storage.size / this.config.storage.maxSize
      }
    }
  }

  /**
   * 更新配置
   */
  updateConfig(newConfig) {
    Object.assign(this.config, newConfig)
  }
}

// 创建全局缓存管理器实例
const cacheManager = new CacheManager()

/**
 * 缓存管理 Hook
 */
export const useCache = () => {
  return {
    set: (key, value, options) => cacheManager.set(key, value, options),
    get: (key, options) => cacheManager.get(key, options),
    delete: (key) => cacheManager.delete(key),
    clear: (options) => cacheManager.clear(options),
    getStats: () => cacheManager.getStats(),
    updateConfig: (config) => cacheManager.updateConfig(config)
  }
}

export default cacheManager
export { CacheManager }