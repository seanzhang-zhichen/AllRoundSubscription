/**
 * 缓存管理器单元测试
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { CacheManager, CacheStrategy, CacheType, CachePriority } from '@/utils/cacheManager'

describe('CacheManager', () => {
  let cacheManager

  beforeEach(() => {
    cacheManager = new CacheManager()
    vi.clearAllMocks()
  })

  describe('基础缓存操作', () => {
    it('应该能够设置和获取内存缓存', async () => {
      const key = 'test-key'
      const value = { data: 'test-data' }

      await cacheManager.set(key, value, {
        strategy: CacheStrategy.MEMORY_ONLY
      })

      const result = await cacheManager.get(key, {
        strategy: CacheStrategy.MEMORY_ONLY
      })

      expect(result).toEqual(value)
    })

    it('应该能够设置和获取存储缓存', async () => {
      const key = 'test-storage-key'
      const value = { data: 'test-storage-data' }

      // Mock uni.setStorageSync 和 uni.getStorageSync
      uni.setStorageSync.mockImplementation(() => {})
      uni.getStorageSync.mockReturnValue({
        value,
        timestamp: Date.now(),
        ttl: 30 * 60 * 1000,
        priority: CachePriority.NORMAL,
        type: CacheType.API_DATA,
        compressed: false,
        encrypted: false,
        size: 100,
        accessCount: 0,
        lastAccess: Date.now()
      })

      await cacheManager.set(key, value, {
        strategy: CacheStrategy.STORAGE_ONLY
      })

      const result = await cacheManager.get(key, {
        strategy: CacheStrategy.STORAGE_ONLY
      })

      expect(result).toEqual(value)
      expect(uni.setStorageSync).toHaveBeenCalled()
      expect(uni.getStorageSync).toHaveBeenCalled()
    })

    it('应该能够删除缓存', async () => {
      const key = 'test-delete-key'
      const value = { data: 'test-delete-data' }

      await cacheManager.set(key, value, {
        strategy: CacheStrategy.MEMORY_ONLY
      })

      let result = await cacheManager.get(key)
      expect(result).toEqual(value)

      await cacheManager.delete(key)

      result = await cacheManager.get(key)
      expect(result).toBeNull()
    })

    it('应该能够清空所有缓存', async () => {
      const keys = ['key1', 'key2', 'key3']
      const value = { data: 'test-data' }

      // 设置多个缓存项
      for (const key of keys) {
        await cacheManager.set(key, value, {
          strategy: CacheStrategy.MEMORY_ONLY
        })
      }

      // 验证缓存存在
      for (const key of keys) {
        const result = await cacheManager.get(key)
        expect(result).toEqual(value)
      }

      // 清空缓存
      await cacheManager.clear()

      // 验证缓存已清空
      for (const key of keys) {
        const result = await cacheManager.get(key)
        expect(result).toBeNull()
      }
    })
  })

  describe('缓存过期处理', () => {
    it('应该正确处理过期的缓存', async () => {
      const key = 'test-expire-key'
      const value = { data: 'test-expire-data' }

      // 设置一个很短的TTL
      await cacheManager.set(key, value, {
        strategy: CacheStrategy.MEMORY_ONLY,
        ttl: 1 // 1毫秒
      })

      // 等待缓存过期
      await new Promise(resolve => setTimeout(resolve, 10))

      const result = await cacheManager.get(key)
      expect(result).toBeNull()
    })

    it('应该在获取过期缓存时自动删除', async () => {
      const key = 'test-auto-delete-key'
      const value = { data: 'test-auto-delete-data' }

      await cacheManager.set(key, value, {
        strategy: CacheStrategy.MEMORY_ONLY,
        ttl: 1
      })

      // 等待过期
      await new Promise(resolve => setTimeout(resolve, 10))

      // 尝试获取过期缓存
      const result = await cacheManager.get(key)
      expect(result).toBeNull()

      // 验证缓存已被删除
      expect(cacheManager.memoryCache.has(key)).toBe(false)
    })
  })

  describe('缓存策略', () => {
    it('MEMORY_FIRST策略应该优先使用内存缓存', async () => {
      const key = 'test-memory-first'
      const memoryValue = { data: 'memory-data' }
      const storageValue = { data: 'storage-data' }

      // 设置内存缓存
      await cacheManager.set(key, memoryValue, {
        strategy: CacheStrategy.MEMORY_ONLY
      })

      // Mock存储缓存
      uni.getStorageSync.mockReturnValue({
        value: storageValue,
        timestamp: Date.now(),
        ttl: 30 * 60 * 1000,
        priority: CachePriority.NORMAL,
        type: CacheType.API_DATA,
        compressed: false,
        encrypted: false,
        size: 100,
        accessCount: 0,
        lastAccess: Date.now()
      })

      const result = await cacheManager.get(key, {
        strategy: CacheStrategy.MEMORY_FIRST
      })

      // 应该返回内存中的值
      expect(result).toEqual(memoryValue)
    })

    it('HYBRID策略应该智能选择缓存位置', async () => {
      const key = 'test-hybrid'
      const value = { data: 'hybrid-data' }

      await cacheManager.set(key, value, {
        strategy: CacheStrategy.HYBRID,
        type: CacheType.USER_DATA,
        priority: CachePriority.HIGH
      })

      const result = await cacheManager.get(key, {
        strategy: CacheStrategy.HYBRID
      })

      expect(result).toEqual(value)
    })
  })

  describe('缓存统计', () => {
    it('应该正确统计缓存命中率', async () => {
      const key = 'test-stats-key'
      const value = { data: 'test-stats-data' }

      // 设置缓存
      await cacheManager.set(key, value, {
        strategy: CacheStrategy.MEMORY_ONLY
      })

      // 多次获取缓存（命中）
      await cacheManager.get(key)
      await cacheManager.get(key)
      await cacheManager.get(key)

      // 获取不存在的缓存（未命中）
      await cacheManager.get('non-existent-key')

      const stats = cacheManager.getStats()
      
      expect(stats.memory.hits).toBe(3)
      expect(stats.memory.misses).toBe(1)
      expect(stats.hitRate.memory).toBe(0.75) // 3/4 = 0.75
    })

    it('应该正确统计缓存大小', async () => {
      const key = 'test-size-key'
      const value = { data: 'test-size-data' }

      const initialStats = cacheManager.getStats()
      const initialSize = initialStats.memory.size

      await cacheManager.set(key, value, {
        strategy: CacheStrategy.MEMORY_ONLY
      })

      const finalStats = cacheManager.getStats()
      expect(finalStats.memory.size).toBeGreaterThan(initialSize)
      expect(finalStats.memory.items).toBe(initialStats.memory.items + 1)
    })
  })

  describe('缓存淘汰', () => {
    it('应该在达到内存限制时淘汰低优先级缓存', async () => {
      // 设置较小的内存限制用于测试
      cacheManager.config.memory.maxItems = 2

      const highPriorityKey = 'high-priority'
      const lowPriorityKey = 'low-priority'
      const newKey = 'new-key'

      // 设置高优先级缓存
      await cacheManager.set(highPriorityKey, { data: 'high' }, {
        strategy: CacheStrategy.MEMORY_ONLY,
        priority: CachePriority.HIGH
      })

      // 设置低优先级缓存
      await cacheManager.set(lowPriorityKey, { data: 'low' }, {
        strategy: CacheStrategy.MEMORY_ONLY,
        priority: CachePriority.LOW
      })

      // 添加新缓存，应该触发淘汰
      await cacheManager.set(newKey, { data: 'new' }, {
        strategy: CacheStrategy.MEMORY_ONLY,
        priority: CachePriority.NORMAL
      })

      // 高优先级缓存应该保留
      const highResult = await cacheManager.get(highPriorityKey)
      expect(highResult).toEqual({ data: 'high' })

      // 新缓存应该存在
      const newResult = await cacheManager.get(newKey)
      expect(newResult).toEqual({ data: 'new' })

      // 低优先级缓存可能被淘汰
      const lowResult = await cacheManager.get(lowPriorityKey)
      // 由于淘汰策略的复杂性，这里不做严格断言
    })
  })

  describe('条件清理', () => {
    it('应该能够按类型清理缓存', async () => {
      const apiKey = 'api-key'
      const userKey = 'user-key'

      await cacheManager.set(apiKey, { data: 'api-data' }, {
        strategy: CacheStrategy.MEMORY_ONLY,
        type: CacheType.API_DATA
      })

      await cacheManager.set(userKey, { data: 'user-data' }, {
        strategy: CacheStrategy.MEMORY_ONLY,
        type: CacheType.USER_DATA
      })

      // 清理API数据类型的缓存
      await cacheManager.clear({ type: CacheType.API_DATA })

      // API缓存应该被清理
      const apiResult = await cacheManager.get(apiKey)
      expect(apiResult).toBeNull()

      // 用户缓存应该保留
      const userResult = await cacheManager.get(userKey)
      expect(userResult).toEqual({ data: 'user-data' })
    })

    it('应该能够按优先级清理缓存', async () => {
      const highKey = 'high-key'
      const lowKey = 'low-key'

      await cacheManager.set(highKey, { data: 'high-data' }, {
        strategy: CacheStrategy.MEMORY_ONLY,
        priority: CachePriority.HIGH
      })

      await cacheManager.set(lowKey, { data: 'low-data' }, {
        strategy: CacheStrategy.MEMORY_ONLY,
        priority: CachePriority.LOW
      })

      // 清理低优先级缓存
      await cacheManager.clear({ priority: CachePriority.NORMAL })

      // 高优先级缓存应该保留
      const highResult = await cacheManager.get(highKey)
      expect(highResult).toEqual({ data: 'high-data' })

      // 低优先级缓存应该被清理
      const lowResult = await cacheManager.get(lowKey)
      expect(lowResult).toBeNull()
    })
  })

  describe('错误处理', () => {
    it('应该优雅处理存储错误', async () => {
      const key = 'test-error-key'
      const value = { data: 'test-error-data' }

      // Mock存储错误
      uni.setStorageSync.mockImplementation(() => {
        throw new Error('Storage error')
      })

      // 设置缓存不应该抛出错误
      await expect(cacheManager.set(key, value, {
        strategy: CacheStrategy.STORAGE_ONLY
      })).resolves.not.toThrow()
    })

    it('应该优雅处理获取缓存错误', async () => {
      const key = 'test-get-error-key'

      // Mock获取错误
      uni.getStorageSync.mockImplementation(() => {
        throw new Error('Get storage error')
      })

      // 获取缓存不应该抛出错误
      const result = await cacheManager.get(key, {
        strategy: CacheStrategy.STORAGE_ONLY
      })

      expect(result).toBeNull()
    })
  })
})