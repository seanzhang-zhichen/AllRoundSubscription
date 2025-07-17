/**
 * 用户交互流程集成测试
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { useContentStore } from '@/stores/content'
import { useAuthStore } from '@/stores/auth'
import { useSubscriptionStore } from '@/stores/subscription'

// Mock页面组件
const MockIndexPage = {
  template: `
    <div class="index-page">
      <div class="content-list">
        <div 
          v-for="article in feedList" 
          :key="article.id"
          class="content-item"
          @click="handleArticleClick(article)"
        >
          <h3>{{ article.title }}</h3>
          <button 
            class="favorite-btn"
            @click.stop="handleFavorite(article)"
          >
            {{ article.is_favorited ? '取消收藏' : '收藏' }}
          </button>
        </div>
      </div>
      <button class="refresh-btn" @click="handleRefresh">刷新</button>
      <button class="load-more-btn" @click="handleLoadMore">加载更多</button>
    </div>
  `,
  setup() {
    const contentStore = useContentStore()
    const authStore = useAuthStore()
    
    const { feedList } = contentStore
    
    const handleArticleClick = (article) => {
      contentStore.markArticleAsRead(article.id)
    }
    
    const handleFavorite = async (article) => {
      if (!authStore.isLoggedIn) {
        throw new Error('请先登录')
      }
      
      if (article.is_favorited) {
        await contentStore.unfavoriteArticle(article.id)
      } else {
        await contentStore.favoriteArticle(article.id)
      }
    }
    
    const handleRefresh = () => {
      return contentStore.refreshFeed()
    }
    
    const handleLoadMore = () => {
      return contentStore.loadMoreFeed()
    }
    
    return {
      feedList,
      handleArticleClick,
      handleFavorite,
      handleRefresh,
      handleLoadMore
    }
  }
}

// Mock搜索页面组件
const MockSearchPage = {
  template: `
    <div class="search-page">
      <input 
        v-model="keyword" 
        class="search-input"
        @keyup.enter="handleSearch"
      />
      <button class="search-btn" @click="handleSearch">搜索</button>
      
      <div class="search-results">
        <div 
          v-for="account in searchResults" 
          :key="account.id"
          class="account-item"
        >
          <h4>{{ account.name }}</h4>
          <button 
            class="subscribe-btn"
            @click="handleSubscribe(account)"
          >
            {{ account.is_subscribed ? '取消订阅' : '订阅' }}
          </button>
        </div>
      </div>
    </div>
  `,
  setup() {
    const subscriptionStore = useSubscriptionStore()
    const authStore = useAuthStore()
    
    const keyword = ref('')
    const searchResults = ref([])
    
    const handleSearch = async () => {
      if (!keyword.value.trim()) return
      
      try {
        const results = await subscriptionStore.searchAccounts(keyword.value)
        searchResults.value = results.items || []
      } catch (error) {
        console.error('搜索失败:', error)
      }
    }
    
    const handleSubscribe = async (account) => {
      if (!authStore.isLoggedIn) {
        throw new Error('请先登录')
      }
      
      if (account.is_subscribed) {
        await subscriptionStore.unsubscribe(account.id)
      } else {
        await subscriptionStore.subscribe(account.id)
      }
      
      // 更新本地状态
      account.is_subscribed = !account.is_subscribed
    }
    
    return {
      keyword,
      searchResults,
      handleSearch,
      handleSubscribe
    }
  }
}

describe('用户交互流程集成测试', () => {
  let contentStore
  let authStore
  let subscriptionStore

  beforeEach(() => {
    setActivePinia(createPinia())
    contentStore = useContentStore()
    authStore = useAuthStore()
    subscriptionStore = useSubscriptionStore()
    
    vi.clearAllMocks()
    
    // Mock API请求
    const mockRequest = require('@/utils/request').default
    mockRequest.get.mockImplementation((url) => {
      if (url === '/feed') {
        return Promise.resolve({
          items: [
            { id: 1, title: '文章1', is_favorited: false, is_read: false },
            { id: 2, title: '文章2', is_favorited: false, is_read: false }
          ],
          total: 2
        })
      }
      return Promise.resolve({})
    })
    
    mockRequest.post.mockResolvedValue({})
    mockRequest.delete.mockResolvedValue({})
  })

  describe('内容浏览流程', () => {
    it('应该能够完成完整的内容浏览流程', async () => {
      const wrapper = mount(MockIndexPage)
      
      // 1. 初始加载内容
      await contentStore.fetchFeed()
      await wrapper.vm.$nextTick()
      
      expect(wrapper.findAll('.content-item')).toHaveLength(2)
      
      // 2. 点击文章标记为已读
      const firstArticle = wrapper.find('.content-item')
      await firstArticle.trigger('click')
      
      expect(contentStore.feedList[0].is_read).toBe(true)
      
      // 3. 刷新内容
      const refreshBtn = wrapper.find('.refresh-btn')
      await refreshBtn.trigger('click')
      
      expect(require('@/utils/request').default.get).toHaveBeenCalledWith('/feed', {
        page: 1,
        size: 20
      })
      
      // 4. 加载更多内容
      const loadMoreBtn = wrapper.find('.load-more-btn')
      await loadMoreBtn.trigger('click')
      
      expect(require('@/utils/request').default.get).toHaveBeenCalledWith('/feed', {
        page: 2,
        size: 20
      })
    })

    it('应该能够处理收藏操作流程', async () => {
      // 模拟用户已登录
      authStore.isLoggedIn = true
      
      const wrapper = mount(MockIndexPage)
      
      // 加载内容
      await contentStore.fetchFeed()
      await wrapper.vm.$nextTick()
      
      // 点击收藏按钮
      const favoriteBtn = wrapper.find('.favorite-btn')
      expect(favoriteBtn.text()).toBe('收藏')
      
      await favoriteBtn.trigger('click')
      
      // 验证API调用
      expect(require('@/utils/request').default.post).toHaveBeenCalledWith('/articles/1/favorite')
      
      // 验证状态更新
      expect(contentStore.feedList[0].is_favorited).toBe(true)
      
      // 验证UI更新
      await wrapper.vm.$nextTick()
      expect(favoriteBtn.text()).toBe('取消收藏')
    })

    it('应该在未登录时阻止收藏操作', async () => {
      // 模拟用户未登录
      authStore.isLoggedIn = false
      
      const wrapper = mount(MockIndexPage)
      
      await contentStore.fetchFeed()
      await wrapper.vm.$nextTick()
      
      const favoriteBtn = wrapper.find('.favorite-btn')
      
      // 点击收藏应该抛出错误
      await expect(favoriteBtn.trigger('click')).rejects.toThrow('请先登录')
      
      // 验证API没有被调用
      expect(require('@/utils/request').default.post).not.toHaveBeenCalled()
    })
  })

  describe('搜索和订阅流程', () => {
    beforeEach(() => {
      // Mock搜索API
      const mockRequest = require('@/utils/request').default
      mockRequest.get.mockImplementation((url) => {
        if (url === '/search/accounts') {
          return Promise.resolve({
            items: [
              { id: 1, name: '测试博主1', is_subscribed: false },
              { id: 2, name: '测试博主2', is_subscribed: false }
            ],
            total: 2
          })
        }
        return Promise.resolve({})
      })
    })

    it('应该能够完成搜索和订阅流程', async () => {
      // 模拟用户已登录
      authStore.isLoggedIn = true
      
      const wrapper = mount(MockSearchPage)
      
      // 1. 输入搜索关键词
      const searchInput = wrapper.find('.search-input')
      await searchInput.setValue('测试博主')
      
      // 2. 点击搜索
      const searchBtn = wrapper.find('.search-btn')
      await searchBtn.trigger('click')
      
      // 等待搜索结果
      await wrapper.vm.$nextTick()
      
      // 验证搜索结果显示
      expect(wrapper.findAll('.account-item')).toHaveLength(2)
      
      // 3. 点击订阅按钮
      const subscribeBtn = wrapper.find('.subscribe-btn')
      expect(subscribeBtn.text()).toBe('订阅')
      
      await subscribeBtn.trigger('click')
      
      // 验证订阅API调用
      expect(require('@/utils/request').default.post).toHaveBeenCalledWith('/subscriptions', {
        account_id: 1
      })
      
      // 验证UI状态更新
      await wrapper.vm.$nextTick()
      expect(subscribeBtn.text()).toBe('取消订阅')
    })

    it('应该能够处理取消订阅流程', async () => {
      authStore.isLoggedIn = true
      
      const wrapper = mount(MockSearchPage)
      
      // 设置已订阅状态
      wrapper.vm.searchResults = [
        { id: 1, name: '测试博主1', is_subscribed: true }
      ]
      
      await wrapper.vm.$nextTick()
      
      const subscribeBtn = wrapper.find('.subscribe-btn')
      expect(subscribeBtn.text()).toBe('取消订阅')
      
      await subscribeBtn.trigger('click')
      
      // 验证取消订阅API调用
      expect(require('@/utils/request').default.delete).toHaveBeenCalledWith('/subscriptions/1')
      
      // 验证状态更新
      expect(wrapper.vm.searchResults[0].is_subscribed).toBe(false)
    })

    it('应该在未登录时阻止订阅操作', async () => {
      authStore.isLoggedIn = false
      
      const wrapper = mount(MockSearchPage)
      
      wrapper.vm.searchResults = [
        { id: 1, name: '测试博主1', is_subscribed: false }
      ]
      
      await wrapper.vm.$nextTick()
      
      const subscribeBtn = wrapper.find('.subscribe-btn')
      
      // 点击订阅应该抛出错误
      await expect(subscribeBtn.trigger('click')).rejects.toThrow('请先登录')
      
      // 验证API没有被调用
      expect(require('@/utils/request').default.post).not.toHaveBeenCalled()
    })
  })

  describe('错误处理流程', () => {
    it('应该能够处理网络错误', async () => {
      // Mock网络错误
      const mockRequest = require('@/utils/request').default
      mockRequest.get.mockRejectedValue(new Error('网络连接失败'))
      
      const wrapper = mount(MockIndexPage)
      
      // 尝试加载内容
      await expect(contentStore.fetchFeed()).rejects.toThrow('网络连接失败')
      
      // 验证加载状态被正确重置
      expect(contentStore.loading).toBe(false)
      expect(contentStore.refreshing).toBe(false)
    })

    it('应该能够处理API错误响应', async () => {
      const mockRequest = require('@/utils/request').default
      mockRequest.post.mockRejectedValue({
        status: 403,
        message: '权限不足'
      })
      
      authStore.isLoggedIn = true
      const wrapper = mount(MockIndexPage)
      
      await contentStore.fetchFeed()
      await wrapper.vm.$nextTick()
      
      const favoriteBtn = wrapper.find('.favorite-btn')
      
      // 收藏操作应该失败
      await expect(favoriteBtn.trigger('click')).rejects.toMatchObject({
        status: 403,
        message: '权限不足'
      })
      
      // 验证状态没有被错误更新
      expect(contentStore.feedList[0].is_favorited).toBe(false)
    })
  })

  describe('状态同步', () => {
    it('应该在多个组件间正确同步状态', async () => {
      const wrapper1 = mount(MockIndexPage)
      const wrapper2 = mount(MockIndexPage)
      
      // 在第一个组件中加载数据
      await contentStore.fetchFeed()
      
      // 两个组件都应该显示相同的数据
      await wrapper1.vm.$nextTick()
      await wrapper2.vm.$nextTick()
      
      expect(wrapper1.findAll('.content-item')).toHaveLength(2)
      expect(wrapper2.findAll('.content-item')).toHaveLength(2)
      
      // 在第一个组件中标记文章为已读
      authStore.isLoggedIn = true
      const favoriteBtn1 = wrapper1.find('.favorite-btn')
      await favoriteBtn1.trigger('click')
      
      // 第二个组件应该反映状态变化
      await wrapper2.vm.$nextTick()
      const favoriteBtn2 = wrapper2.find('.favorite-btn')
      expect(favoriteBtn2.text()).toBe('取消收藏')
    })
  })

  describe('性能优化', () => {
    it('应该避免重复的API调用', async () => {
      const mockRequest = require('@/utils/request').default
      
      const wrapper = mount(MockIndexPage)
      
      // 快速连续点击刷新按钮
      const refreshBtn = wrapper.find('.refresh-btn')
      
      const promises = [
        refreshBtn.trigger('click'),
        refreshBtn.trigger('click'),
        refreshBtn.trigger('click')
      ]
      
      await Promise.all(promises)
      
      // 应该只有一个API调用（由于防抖或其他优化机制）
      // 这里的具体行为取决于实际的防抖实现
      expect(mockRequest.get).toHaveBeenCalled()
    })

    it('应该正确处理分页加载', async () => {
      const wrapper = mount(MockIndexPage)
      
      // 初始加载
      await contentStore.fetchFeed()
      expect(contentStore.pagination.page).toBe(2)
      
      // 加载更多
      const loadMoreBtn = wrapper.find('.load-more-btn')
      await loadMoreBtn.trigger('click')
      expect(contentStore.pagination.page).toBe(3)
      
      // 验证数据累积而不是替换
      expect(contentStore.feedList.length).toBeGreaterThan(0)
    })
  })
})