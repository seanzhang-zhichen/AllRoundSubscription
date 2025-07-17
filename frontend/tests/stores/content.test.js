/**
 * Content Store 单元测试
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useContentStore } from '@/stores/content'

// Mock request utility
vi.mock('@/utils/request', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn()
  }
}))

// Mock cache manager
vi.mock('@/utils/cacheManager', () => ({
  useCache: () => ({
    get: vi.fn(),
    set: vi.fn()
  })
}))

// Mock network manager
vi.mock('@/utils/networkManager', () => ({
  useNetwork: () => ({
    shouldUseCache: vi.fn(() => false),
    networkState: {
      isOnline: true
    }
  })
}))

describe('Content Store', () => {
  let store
  let mockRequest

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useContentStore()
    
    // 重置 mock
    vi.clearAllMocks()
    
    // 获取 mock 的 request
    mockRequest = require('@/utils/request').default
  })

  describe('初始状态', () => {
    it('应该有正确的初始状态', () => {
      expect(store.feedList).toEqual([])
      expect(store.loading).toBe(false)
      expect(store.refreshing).toBe(false)
      expect(store.loadingMore).toBe(false)
      expect(store.pagination.page).toBe(1)
      expect(store.pagination.size).toBe(20)
      expect(store.pagination.hasMore).toBe(true)
    })

    it('应该有空的文章缓存', () => {
      expect(store.articleCache.size).toBe(0)
    })
  })

  describe('获取动态流', () => {
    const mockFeedData = {
      items: [
        { id: 1, title: '文章1', content: '内容1' },
        { id: 2, title: '文章2', content: '内容2' }
      ],
      total: 100
    }

    it('应该能够获取动态流数据', async () => {
      mockRequest.get.mockResolvedValue(mockFeedData)

      await store.fetchFeed()

      expect(mockRequest.get).toHaveBeenCalledWith('/feed', {
        page: 1,
        size: 20
      })
      expect(store.feedList).toEqual(mockFeedData.items)
      expect(store.pagination.total).toBe(mockFeedData.total)
      expect(store.pagination.page).toBe(2)
      expect(store.loading).toBe(false)
    })

    it('应该在刷新时重置分页', async () => {
      // 先设置一些状态
      store.pagination.page = 3
      store.feedList = [{ id: 999, title: '旧数据' }]

      mockRequest.get.mockResolvedValue(mockFeedData)

      await store.fetchFeed(true)

      expect(store.pagination.page).toBe(2) // 重置为1，然后+1
      expect(store.feedList).toEqual(mockFeedData.items)
      expect(store.refreshing).toBe(false)
    })

    it('应该在加载更多时追加数据', async () => {
      // 先设置一些现有数据
      store.feedList = [{ id: 0, title: '现有数据' }]
      store.pagination.page = 2

      mockRequest.get.mockResolvedValue(mockFeedData)

      await store.fetchFeed(false)

      expect(store.feedList).toHaveLength(3) // 1个现有 + 2个新的
      expect(store.feedList[0]).toEqual({ id: 0, title: '现有数据' })
      expect(store.feedList[1]).toEqual(mockFeedData.items[0])
      expect(store.loadingMore).toBe(false)
    })

    it('应该在没有更多数据时停止加载', async () => {
      store.pagination.hasMore = false

      await store.fetchFeed(false)

      expect(mockRequest.get).not.toHaveBeenCalled()
    })

    it('应该正确处理获取失败', async () => {
      const error = new Error('网络错误')
      mockRequest.get.mockRejectedValue(error)

      await expect(store.fetchFeed()).rejects.toThrow('网络错误')
      expect(store.loading).toBe(false)
      expect(store.refreshing).toBe(false)
      expect(store.loadingMore).toBe(false)
    })
  })

  describe('获取文章详情', () => {
    const mockArticle = {
      id: 1,
      title: '测试文章',
      content: '测试内容',
      author: '测试作者'
    }

    it('应该能够获取文章详情', async () => {
      mockRequest.get.mockResolvedValue(mockArticle)

      const result = await store.fetchArticleDetail(1)

      expect(mockRequest.get).toHaveBeenCalledWith('/articles/1')
      expect(result).toEqual(mockArticle)
      expect(store.articleCache.get(1)).toEqual(mockArticle)
    })

    it('应该从缓存中获取文章详情', async () => {
      // 先设置缓存
      store.articleCache.set(1, mockArticle)

      const result = await store.fetchArticleDetail(1)

      expect(mockRequest.get).not.toHaveBeenCalled()
      expect(result).toEqual(mockArticle)
    })

    it('应该正确处理获取文章详情失败', async () => {
      const error = new Error('文章不存在')
      mockRequest.get.mockRejectedValue(error)

      await expect(store.fetchArticleDetail(1)).rejects.toThrow('文章不存在')
      expect(store.loading).toBe(false)
    })
  })

  describe('刷新和加载更多', () => {
    it('应该能够刷新动态流', async () => {
      const mockData = { items: [], total: 0 }
      mockRequest.get.mockResolvedValue(mockData)

      const result = await store.refreshFeed()

      expect(result).toEqual(mockData)
      // refreshFeed 应该调用 fetchFeed(true)
    })

    it('应该能够加载更多动态', async () => {
      const mockData = { items: [], total: 0 }
      mockRequest.get.mockResolvedValue(mockData)

      const result = await store.loadMoreFeed()

      expect(result).toEqual(mockData)
      // loadMoreFeed 应该调用 fetchFeed(false)
    })
  })

  describe('文章操作', () => {
    beforeEach(() => {
      // 设置一些测试数据
      store.feedList = [
        { id: 1, title: '文章1', is_read: false, is_favorited: false },
        { id: 2, title: '文章2', is_read: false, is_favorited: false }
      ]
    })

    it('应该能够标记文章为已读', async () => {
      mockRequest.post.mockResolvedValue({})

      await store.markArticleAsRead(1)

      expect(mockRequest.post).toHaveBeenCalledWith('/articles/1/read')
      expect(store.feedList[0].is_read).toBe(true)
    })

    it('应该能够收藏文章', async () => {
      mockRequest.post.mockResolvedValue({})

      await store.favoriteArticle(1)

      expect(mockRequest.post).toHaveBeenCalledWith('/articles/1/favorite')
      expect(store.feedList[0].is_favorited).toBe(true)
      expect(uni.showToast).toHaveBeenCalledWith({
        title: '收藏成功',
        icon: 'success'
      })
    })

    it('应该能够取消收藏文章', async () => {
      // 先设置为已收藏
      store.feedList[0].is_favorited = true
      mockRequest.delete.mockResolvedValue({})

      await store.unfavoriteArticle(1)

      expect(mockRequest.delete).toHaveBeenCalledWith('/articles/1/favorite')
      expect(store.feedList[0].is_favorited).toBe(false)
      expect(uni.showToast).toHaveBeenCalledWith({
        title: '取消收藏成功',
        icon: 'success'
      })
    })

    it('应该正确处理收藏失败', async () => {
      const error = new Error('收藏失败')
      mockRequest.post.mockRejectedValue(error)

      await expect(store.favoriteArticle(1)).rejects.toThrow('收藏失败')
      expect(uni.showToast).toHaveBeenCalledWith({
        title: '收藏失败',
        icon: 'none'
      })
    })
  })

  describe('分享功能', () => {
    const mockArticle = {
      id: 1,
      title: '测试文章',
      summary: '测试摘要',
      url: 'https://example.com/article/1',
      images: ['https://example.com/image.jpg']
    }

    beforeEach(() => {
      store.feedList = [mockArticle]
    })

    it('应该能够分享文章', async () => {
      // Mock uni.share 成功
      uni.share.mockImplementation((options) => {
        options.success()
      })
      mockRequest.post.mockResolvedValue({})

      await store.shareArticle(1)

      expect(uni.share).toHaveBeenCalledWith({
        provider: 'weixin',
        scene: 'WXSceneSession',
        type: 0,
        href: mockArticle.url,
        title: mockArticle.title,
        summary: mockArticle.summary,
        imageUrl: mockArticle.images[0],
        success: expect.any(Function),
        fail: expect.any(Function)
      })
      expect(mockRequest.post).toHaveBeenCalledWith('/articles/1/share')
    })

    it('应该正确处理分享失败', async () => {
      // Mock uni.share 失败
      uni.share.mockImplementation((options) => {
        options.fail(new Error('分享失败'))
      })

      await expect(store.shareArticle(1)).rejects.toThrow()
    })

    it('应该正确处理文章不存在的情况', async () => {
      await expect(store.shareArticle(999)).rejects.toThrow('文章不存在')
    })
  })

  describe('搜索功能', () => {
    it('应该能够搜索文章', async () => {
      const mockSearchResult = {
        items: [{ id: 1, title: '搜索结果' }],
        total: 1
      }
      mockRequest.get.mockResolvedValue(mockSearchResult)

      const result = await store.searchArticles('测试关键词', { platform: 'wechat' })

      expect(mockRequest.get).toHaveBeenCalledWith('/articles/search', {
        keyword: '测试关键词',
        platform: 'wechat'
      })
      expect(result).toEqual(mockSearchResult)
    })

    it('应该能够获取指定博主的文章', async () => {
      const mockAccountArticles = {
        items: [{ id: 1, title: '博主文章' }],
        total: 1
      }
      mockRequest.get.mockResolvedValue(mockAccountArticles)

      const result = await store.fetchAccountArticles(1, 1, 10)

      expect(mockRequest.get).toHaveBeenCalledWith('/articles', {
        account_id: 1,
        page: 1,
        size: 10
      })
      expect(result).toEqual(mockAccountArticles)
    })
  })

  describe('数据清理', () => {
    beforeEach(() => {
      // 设置一些测试数据
      store.feedList = [{ id: 1, title: '测试文章' }]
      store.articleCache.set(1, { id: 1, title: '缓存文章' })
      store.pagination.page = 3
      store.pagination.total = 100
      store.lastUpdateTime = new Date()
    })

    it('应该能够清除所有内容数据', () => {
      store.clearContent()

      expect(store.feedList).toEqual([])
      expect(store.articleCache.size).toBe(0)
      expect(store.pagination.page).toBe(1)
      expect(store.pagination.total).toBe(0)
      expect(store.pagination.hasMore).toBe(true)
      expect(store.lastUpdateTime).toBeNull()
    })

    it('应该能够清除文章缓存', () => {
      store.clearArticleCache()

      expect(store.articleCache.size).toBe(0)
      // 其他数据应该保持不变
      expect(store.feedList).toHaveLength(1)
    })
  })

  describe('Getters', () => {
    beforeEach(() => {
      store.feedList = [
        { id: 1, title: '今天的文章', publish_time: '2024-01-01T12:00:00Z' },
        { id: 2, title: '昨天的文章', publish_time: '2023-12-31T12:00:00Z' }
      ]
    })

    it('应该正确按日期分组动态流', () => {
      const feedByDate = store.feedByDate

      expect(Object.keys(feedByDate)).toHaveLength(2)
      expect(feedByDate['Mon Jan 01 2024']).toHaveLength(1)
      expect(feedByDate['Sun Dec 31 2023']).toHaveLength(1)
    })

    it('应该正确判断是否有内容', () => {
      expect(store.hasContent).toBe(true)

      store.feedList = []
      expect(store.hasContent).toBe(false)
    })
  })
})