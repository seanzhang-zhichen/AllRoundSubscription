/**
 * 应用状态管理
 */
import { defineStore } from 'pinia'

export const useAppStore = defineStore('app', {
  state: () => ({
    // 应用信息
    appInfo: {
      version: '1.0.0',
      name: '多平台内容聚合',
      description: '一站式内容聚合平台'
    },
    
    // 系统信息
    systemInfo: {},
    
    // 网络状态
    networkStatus: {
      isConnected: true,
      networkType: 'unknown'
    },
    
    // 全局加载状态
    globalLoading: false,
    
    // 主题设置
    theme: {
      mode: 'light', // light | dark
      primaryColor: '#3cc51f'
    },
    
    // 搜索历史
    searchHistory: [],
    
    // 支持的平台列表
    supportedPlatforms: [
      {
        key: 'wechat',
        name: '微信公众号',
        icon: '/static/platform-wechat.png',
        color: '#07c160'
      }
    ]
  }),
  
  getters: {
    // 获取平台信息
    getPlatformInfo: (state) => (platformKey) => {
      return state.supportedPlatforms.find(p => p.key === platformKey)
    },
    
    // 是否为暗色主题
    isDarkMode: (state) => state.theme.mode === 'dark'
  },
  
  actions: {
    /**
     * 初始化应用
     */
    async initApp() {
      try {
        // 获取系统信息
        await this.getSystemInfo()
        
        // 监听网络状态
        this.watchNetworkStatus()
        
        // 加载本地设置
        this.loadLocalSettings()
        
        console.log('应用初始化完成')
        
      } catch (error) {
        console.error('应用初始化失败:', error)
      }
    },
    
    /**
     * 获取系统信息
     */
    async getSystemInfo() {
      try {
        const systemInfo = await new Promise((resolve, reject) => {
          uni.getSystemInfo({
            success: resolve,
            fail: reject
          })
        })
        
        this.systemInfo = systemInfo
        return systemInfo
        
      } catch (error) {
        console.error('获取系统信息失败:', error)
      }
    },
    
    /**
     * 监听网络状态
     */
    watchNetworkStatus() {
      // 获取当前网络状态
      uni.getNetworkType({
        success: (res) => {
          this.networkStatus.networkType = res.networkType
          this.networkStatus.isConnected = res.networkType !== 'none'
        }
      })
      
      // 监听网络状态变化
      uni.onNetworkStatusChange((res) => {
        this.networkStatus.isConnected = res.isConnected
        this.networkStatus.networkType = res.networkType
        
        if (!res.isConnected) {
          uni.showToast({
            title: '网络连接已断开',
            icon: 'none'
          })
        } else {
          uni.showToast({
            title: '网络连接已恢复',
            icon: 'success'
          })
        }
      })
    },
    
    /**
     * 加载本地设置
     */
    loadLocalSettings() {
      try {
        // 加载主题设置
        const theme = uni.getStorageSync('theme')
        if (theme) {
          this.theme = { ...this.theme, ...theme }
        }
        
        // 加载搜索历史
        const searchHistory = uni.getStorageSync('searchHistory')
        if (searchHistory) {
          this.searchHistory = searchHistory
        }
        
      } catch (error) {
        console.error('加载本地设置失败:', error)
      }
    },
    
    /**
     * 设置全局加载状态
     */
    setGlobalLoading(loading) {
      this.globalLoading = loading
      
      if (loading) {
        uni.showLoading({
          title: '加载中...',
          mask: true
        })
      } else {
        uni.hideLoading()
      }
    },
    
    /**
     * 切换主题
     */
    toggleTheme() {
      this.theme.mode = this.theme.mode === 'light' ? 'dark' : 'light'
      
      // 保存到本地存储
      uni.setStorageSync('theme', this.theme)
      
      uni.showToast({
        title: `已切换到${this.theme.mode === 'light' ? '浅色' : '深色'}主题`,
        icon: 'success'
      })
    },
    
    /**
     * 添加搜索历史
     */
    addSearchHistory(keyword) {
      if (!keyword || keyword.trim() === '') return
      
      const trimmedKeyword = keyword.trim()
      
      // 移除重复项
      this.searchHistory = this.searchHistory.filter(item => item !== trimmedKeyword)
      
      // 添加到开头
      this.searchHistory.unshift(trimmedKeyword)
      
      // 限制历史记录数量
      if (this.searchHistory.length > 20) {
        this.searchHistory = this.searchHistory.slice(0, 20)
      }
      
      // 保存到本地存储
      uni.setStorageSync('searchHistory', this.searchHistory)
    },
    
    /**
     * 清除搜索历史
     */
    clearSearchHistory() {
      this.searchHistory = []
      uni.removeStorageSync('searchHistory')
      
      uni.showToast({
        title: '搜索历史已清除',
        icon: 'success'
      })
    },
    
    /**
     * 删除单个搜索历史
     */
    removeSearchHistory(keyword) {
      this.searchHistory = this.searchHistory.filter(item => item !== keyword)
      uni.setStorageSync('searchHistory', this.searchHistory)
    },
    
    /**
     * 显示错误提示
     */
    showError(message, duration = 2000) {
      uni.showToast({
        title: message,
        icon: 'none',
        duration
      })
    },
    
    /**
     * 显示成功提示
     */
    showSuccess(message, duration = 1500) {
      uni.showToast({
        title: message,
        icon: 'success',
        duration
      })
    },
    
    /**
     * 显示确认对话框
     */
    async showConfirm(title, content) {
      return new Promise((resolve) => {
        uni.showModal({
          title,
          content,
          success: (res) => {
            resolve(res.confirm)
          },
          fail: () => {
            resolve(false)
          }
        })
      })
    },
    
    /**
     * 检查应用更新
     */
    async checkUpdate() {
      try {
        // 这里可以调用API检查是否有新版本
        // const updateInfo = await request.get('/app/update')
        
        // 暂时返回无更新
        return {
          hasUpdate: false,
          version: this.appInfo.version
        }
        
      } catch (error) {
        console.error('检查更新失败:', error)
        return {
          hasUpdate: false,
          version: this.appInfo.version
        }
      }
    }
  }
})