/**
 * 搜索状态管理
 */
import { defineStore } from 'pinia'
import request from '../utils/request'
import { useAppStore } from './app'

export const useSearchStore = defineStore('search', {
  state: () => ({
    // 搜索结果
    searchResults: [],
    
    // 当前搜索关键词
    currentKeyword: '',
    
    // 选中的平台筛选
    selectedPlatforms: [],
    
    // 加载状态
    loading: false,
    searching: false,
    
    // 分页信息
    pagination: {
      page: 0, // 修改为从0开始
      size: 20,
      total: 0,
      hasMore: true
    },
    
    // 搜索统计
    searchStats: {
      totalResults: 0,
      platformResults: {}
    }
  }),
  
  getters: {
    // 按平台分组的搜索结果
    resultsByPlatform: (state) => {
      const grouped = {}
      state.searchResults.forEach(account => {
        if (!grouped[account.platform]) {
          grouped[account.platform] = []
        }
        grouped[account.platform].push(account)
      })
      return grouped
    },
    
    // 是否有搜索结果
    hasResults: (state) => state.searchResults.length > 0,
    
    // 是否正在搜索
    isSearching: (state) => state.searching || state.loading,
    
    // 获取平台搜索结果数量
    getPlatformResultCount: (state) => (platform) => {
      return state.searchResults.filter(account => account.platform === platform).length
    }
  },
  
  actions: {
    /**
     * 搜索博主或获取所有博主
     */
    async searchAccounts(keyword, platforms = [], refresh = false) {
      try {
        const trimmedKeyword = keyword ? keyword.trim() : ''
        
        if (refresh) {
          this.pagination.page = 0 // 刷新时重置为0
          this.pagination.hasMore = true
        } else {
          if (!this.pagination.hasMore) {
            return
          }
        }
        
        this.searching = true
        this.loading = true
        this.currentKeyword = trimmedKeyword
        this.selectedPlatforms = platforms
        
        // 只有在有关键词时才添加到搜索历史
        if (trimmedKeyword) {
          const appStore = useAppStore()
          appStore.addSearchHistory(trimmedKeyword)
        }
        
        // 构建请求参数
        const params = {
          platforms: platforms.length > 0 ? platforms.join(',') : undefined,
          page: this.pagination.page,
          page_size: this.pagination.size
        }
        
        // 只有在有关键词时才添加keyword参数
        if (trimmedKeyword) {
          params.keyword = trimmedKeyword
        }
        
        const response = await request.get('/search/accounts', params)
        const data = response.data || response // 处理可能的嵌套数据结构
        
        // 添加详细的日志打印
        console.log('===== 后端搜索结果 =====')
        console.log('关键词:', trimmedKeyword)
        console.log('平台:', platforms.join(',') || '全部')
        console.log('页码:', this.pagination.page)
        console.log('每页数量:', this.pagination.size)
        console.log('总结果数:', data.total)
        console.log('返回账号数量:', (data.accounts || []).length)
        if (data.accounts && data.accounts.length > 0) {
          console.log('第一个结果:', {
            id: data.accounts[0].id,
            name: data.accounts[0].name,
            platform: data.accounts[0].platform,
            follower_count: data.accounts[0].follower_count
          })
        }
        console.log('查询耗时:', data.search_time_ms, 'ms')
        console.log('完整响应数据:', data)
        console.log('========================')
        
        if (refresh) {
          this.searchResults = data.accounts || []
        } else {
          this.searchResults.push(...(data.accounts || []))
        }
        
        // 更新分页信息
        this.pagination.total = data.total || 0
        this.pagination.hasMore = (data.accounts || []).length === this.pagination.size
        this.pagination.page += 1
        
        // 更新搜索统计
        this.updateSearchStats(data)
        
        return data
        
      } catch (error) {
        console.error('搜索博主失败:', error)
        throw error
      } finally {
        this.searching = false
        this.loading = false
      }
    },
    
    /**
     * 刷新搜索结果
     */
    async refreshSearch() {
      return this.searchAccounts(this.currentKeyword, this.selectedPlatforms, true)
    },
    
    /**
     * 加载更多搜索结果
     */
    async loadMoreResults() {
      return this.searchAccounts(this.currentKeyword, this.selectedPlatforms, false)
    },
    
    /**
     * 按平台筛选搜索
     */
    async filterByPlatforms(platforms) {
      this.selectedPlatforms = platforms
      // 无论是否有关键词，都重新搜索
      return this.searchAccounts(this.currentKeyword, platforms, true)
    },
    
    /**
     * 获取支持的平台列表
     */
    async fetchSupportedPlatforms() {
      try {
        this.loading = true
        
        const data = await request.get('/search/platforms')
        
        return data
        
      } catch (error) {
        console.error('获取平台列表失败:', error)
        // 返回默认平台列表
        const appStore = useAppStore()
        return appStore.supportedPlatforms
      } finally {
        this.loading = false
      }
    },
    
    /**
     * 获取搜索建议
     */
    async getSearchSuggestions(keyword) {
      try {
        if (!keyword || keyword.trim() === '') {
          return []
        }
        
        const data = await request.get('/search/suggestions', {
          keyword: keyword.trim()
        })
        
        return data.suggestions || []
        
      } catch (error) {
        console.error('获取搜索建议失败:', error)
        return []
      }
    },
    
    /**
     * 更新搜索统计
     */
    updateSearchStats(data) {
      this.searchStats.totalResults = data.total || 0
      this.searchStats.platformResults = data.platform_stats || {}
      
      // 如果没有平台统计数据，根据当前结果计算
      if (!data.platform_stats && this.searchResults.length > 0) {
        const platformCounts = {}
        this.searchResults.forEach(account => {
          platformCounts[account.platform] = (platformCounts[account.platform] || 0) + 1
        })
        this.searchStats.platformResults = platformCounts
      }
    },
    
    /**
     * 清除搜索结果
     */
    clearSearchResults() {
      this.searchResults = []
      this.currentKeyword = ''
      this.selectedPlatforms = []
      this.pagination = {
        page: 0, // 修改为从0开始
        size: 20,
        total: 0,
        hasMore: true
      }
      this.searchStats = {
        totalResults: 0,
        platformResults: {}
      }
    },
    
    /**
     * 重置搜索状态
     */
    resetSearchState() {
      this.clearSearchResults()
      this.loading = false
      this.searching = false
    }
  }
})