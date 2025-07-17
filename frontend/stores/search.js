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
      page: 1,
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
     * 搜索博主
     */
    async searchAccounts(keyword, platforms = [], refresh = false) {
      try {
        if (!keyword || keyword.trim() === '') {
          throw new Error('搜索关键词不能为空')
        }
        
        const trimmedKeyword = keyword.trim()
        
        if (refresh) {
          this.pagination.page = 1
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
        
        // 添加到搜索历史
        const appStore = useAppStore()
        appStore.addSearchHistory(trimmedKeyword)
        
        const data = await request.get('/search/accounts', {
          keyword: trimmedKeyword,
          platforms: platforms.length > 0 ? platforms.join(',') : undefined,
          page: this.pagination.page,
          size: this.pagination.size
        })
        
        if (refresh) {
          this.searchResults = data.items || []
        } else {
          this.searchResults.push(...(data.items || []))
        }
        
        // 更新分页信息
        this.pagination.total = data.total || 0
        this.pagination.hasMore = (data.items || []).length === this.pagination.size
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
      if (!this.currentKeyword) return
      return this.searchAccounts(this.currentKeyword, this.selectedPlatforms, true)
    },
    
    /**
     * 加载更多搜索结果
     */
    async loadMoreResults() {
      if (!this.currentKeyword) return
      return this.searchAccounts(this.currentKeyword, this.selectedPlatforms, false)
    },
    
    /**
     * 按平台筛选搜索
     */
    async filterByPlatforms(platforms) {
      this.selectedPlatforms = platforms
      if (this.currentKeyword) {
        return this.searchAccounts(this.currentKeyword, platforms, true)
      }
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
    },
    
    /**
     * 清除搜索结果
     */
    clearSearchResults() {
      this.searchResults = []
      this.currentKeyword = ''
      this.selectedPlatforms = []
      this.pagination = {
        page: 1,
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