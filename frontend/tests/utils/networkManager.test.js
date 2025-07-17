/**
 * 网络管理器单元测试
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useNetwork, NetworkType, ConnectionQuality } from '@/utils/networkManager'

describe('NetworkManager', () => {
  let network

  beforeEach(() => {
    network = useNetwork()
    vi.clearAllMocks()
  })

  describe('网络状态检测', () => {
    it('应该能够获取网络类型', () => {
      // Mock网络类型为WiFi
      uni.getNetworkType.mockImplementation((options) => {
        options.success({ networkType: 'wifi' })
      })

      const networkType = network.getNetworkTypeDescription()
      expect(networkType).toBe('WiFi')
    })

    it('应该能够检测网络连接状态', () => {
      expect(network.networkState).toBeDefined()
      expect(typeof network.networkState.isOnline).toBe('boolean')
    })

    it('应该能够获取连接质量描述', () => {
      const description = network.getQualityDescription()
      expect(typeof description).toBe('string')
      expect(description.length).toBeGreaterThan(0)
    })
  })

  describe('网络质量评估', () => {
    it('应该根据网络状况推荐图片质量', () => {
      // 模拟优秀网络
      network.networkState.isOnline = true
      network.networkState.connectionQuality = ConnectionQuality.EXCELLENT
      
      const quality = network.getRecommendedImageQuality()
      expect(quality).toBe('high')
    })

    it('应该在网络较差时推荐低质量图片', () => {
      // 模拟较差网络
      network.networkState.isOnline = true
      network.networkState.connectionQuality = ConnectionQuality.POOR
      
      const quality = network.getRecommendedImageQuality()
      expect(quality).toBe('low')
    })

    it('应该在离线时推荐低质量图片', () => {
      // 模拟离线状态
      network.networkState.isOnline = false
      
      const quality = network.getRecommendedImageQuality()
      expect(quality).toBe('low')
    })
  })

  describe('缓存策略建议', () => {
    it('应该在网络良好时建议不使用缓存', () => {
      network.networkState.isOnline = true
      network.networkState.connectionQuality = ConnectionQuality.GOOD
      
      const shouldUseCache = network.shouldUseCache()
      expect(shouldUseCache).toBe(false)
    })

    it('应该在网络较差时建议使用缓存', () => {
      network.networkState.isOnline = true
      network.networkState.connectionQuality = ConnectionQuality.POOR
      
      const shouldUseCache = network.shouldUseCache()
      expect(shouldUseCache).toBe(true)
    })

    it('应该在离线时建议使用缓存', () => {
      network.networkState.isOnline = false
      
      const shouldUseCache = network.shouldUseCache()
      expect(shouldUseCache).toBe(true)
    })
  })

  describe('预加载策略建议', () => {
    it('应该在WiFi且网络良好时建议预加载', () => {
      network.networkState.isOnline = true
      network.networkState.networkType = NetworkType.WIFI
      network.networkState.connectionQuality = ConnectionQuality.GOOD
      
      const shouldPreload = network.shouldPreload()
      expect(shouldPreload).toBe(true)
    })

    it('应该在移动网络时不建议预加载', () => {
      network.networkState.isOnline = true
      network.networkState.networkType = NetworkType.CELLULAR_4G
      network.networkState.connectionQuality = ConnectionQuality.GOOD
      
      const shouldPreload = network.shouldPreload()
      expect(shouldPreload).toBe(false)
    })

    it('应该在网络较差时不建议预加载', () => {
      network.networkState.isOnline = true
      network.networkState.networkType = NetworkType.WIFI
      network.networkState.connectionQuality = ConnectionQuality.POOR
      
      const shouldPreload = network.shouldPreload()
      expect(shouldPreload).toBe(false)
    })

    it('应该在离线时不建议预加载', () => {
      network.networkState.isOnline = false
      
      const shouldPreload = network.shouldPreload()
      expect(shouldPreload).toBe(false)
    })
  })

  describe('离线请求队列', () => {
    it('应该能够添加请求到离线队列', () => {
      const request = {
        url: '/api/test',
        method: 'GET',
        data: { test: 'data' }
      }
      
      const result = network.addToOfflineQueue(request)
      expect(result).toBe(true)
    })

    it('应该在禁用离线缓存时拒绝添加请求', () => {
      // 更新配置禁用离线缓存
      network.updateConfig({
        offline: {
          cacheRequests: false
        }
      })
      
      const request = {
        url: '/api/test',
        method: 'GET'
      }
      
      const result = network.addToOfflineQueue(request)
      expect(result).toBe(false)
    })
  })

  describe('网络类型描述', () => {
    it('应该正确描述WiFi网络', () => {
      network.networkState.networkType = NetworkType.WIFI
      const description = network.getNetworkTypeDescription()
      expect(description).toBe('WiFi')
    })

    it('应该正确描述4G网络', () => {
      network.networkState.networkType = NetworkType.CELLULAR_4G
      const description = network.getNetworkTypeDescription()
      expect(description).toBe('4G网络')
    })

    it('应该正确描述5G网络', () => {
      network.networkState.networkType = NetworkType.CELLULAR_5G
      const description = network.getNetworkTypeDescription()
      expect(description).toBe('5G网络')
    })

    it('应该正确描述未知网络', () => {
      network.networkState.networkType = NetworkType.UNKNOWN
      const description = network.getNetworkTypeDescription()
      expect(description).toBe('未知网络')
    })

    it('应该正确描述无网络连接', () => {
      network.networkState.networkType = NetworkType.NONE
      const description = network.getNetworkTypeDescription()
      expect(description).toBe('无网络连接')
    })
  })

  describe('连接质量描述', () => {
    it('应该正确描述优秀连接', () => {
      network.networkState.connectionQuality = ConnectionQuality.EXCELLENT
      const description = network.getQualityDescription()
      expect(description).toBe('网络状况优秀')
    })

    it('应该正确描述良好连接', () => {
      network.networkState.connectionQuality = ConnectionQuality.GOOD
      const description = network.getQualityDescription()
      expect(description).toBe('网络状况良好')
    })

    it('应该正确描述一般连接', () => {
      network.networkState.connectionQuality = ConnectionQuality.FAIR
      const description = network.getQualityDescription()
      expect(description).toBe('网络状况一般')
    })

    it('应该正确描述较差连接', () => {
      network.networkState.connectionQuality = ConnectionQuality.POOR
      const description = network.getQualityDescription()
      expect(description).toBe('网络状况较差')
    })

    it('应该正确描述离线状态', () => {
      network.networkState.connectionQuality = ConnectionQuality.OFFLINE
      const description = network.getQualityDescription()
      expect(description).toBe('网络已断开')
    })
  })

  describe('网络状态获取', () => {
    it('应该能够获取完整的网络状态', () => {
      const networkState = network.getNetworkState()
      
      expect(networkState).toHaveProperty('isOnline')
      expect(networkState).toHaveProperty('networkType')
      expect(networkState).toHaveProperty('connectionQuality')
      expect(networkState).toHaveProperty('lastOnlineTime')
      expect(networkState).toHaveProperty('reconnectAttempts')
    })

    it('应该返回网络状态的副本而不是引用', () => {
      const networkState1 = network.getNetworkState()
      const networkState2 = network.getNetworkState()
      
      expect(networkState1).not.toBe(networkState2)
      expect(networkState1).toEqual(networkState2)
    })
  })

  describe('配置更新', () => {
    it('应该能够更新网络管理器配置', () => {
      const newConfig = {
        detection: {
          interval: 60000, // 1分钟
          timeout: 10000   // 10秒
        }
      }
      
      expect(() => network.updateConfig(newConfig)).not.toThrow()
    })
  })
})