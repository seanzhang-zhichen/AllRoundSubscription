/**
 * 微信小程序分享功能工具
 * 提供文章分享、分享统计和追踪功能
 */

/**
 * 微信分享管理器
 */
class WechatShareManager {
  constructor() {
    this.shareConfig = {
      defaultTitle: '内容聚合 - 一站式多平台内容订阅',
      defaultPath: 'pages/index/index',
      defaultImageUrl: '/static/share-logo.png'
    }
    
    this.shareStats = {
      totalShares: 0,
      articleShares: {},
      shareHistory: []
    }
    
    // 加载分享统计数据
    this.loadShareStats()
  }

  /**
   * 配置文章分享参数
   * @param {Object} article - 文章对象
   * @param {Object} options - 分享选项
   */
  configureArticleShare(article, options = {}) {
    const {
      customTitle = '',
      customPath = '',
      customImageUrl = '',
      shareSource = 'article_detail'
    } = options

    // 生成分享标题
    const shareTitle = customTitle || 
      (article.title ? `${article.title} - 内容聚合` : this.shareConfig.defaultTitle)

    // 生成分享路径，包含文章ID和分享来源
    const sharePath = customPath || 
      `pages/article/detail?id=${article.id}&share_source=${shareSource}&share_time=${Date.now()}`

    // 生成分享图片
    const shareImageUrl = customImageUrl || 
      (article.images && article.images.length > 0 ? article.images[0] : this.shareConfig.defaultImageUrl)

    return {
      title: shareTitle,
      path: sharePath,
      imageUrl: shareImageUrl,
      article: article,
      shareSource: shareSource,
      shareTime: new Date().toISOString()
    }
  }

  /**
   * 配置页面分享参数
   * @param {string} pageName - 页面名称
   * @param {Object} options - 分享选项
   */
  configurePageShare(pageName, options = {}) {
    const {
      customTitle = '',
      customPath = '',
      customImageUrl = '',
      shareParams = {}
    } = options

    const pageShareConfig = {
      'index': {
        title: '内容聚合 - 发现精彩内容',
        path: 'pages/index/index'
      },
      'search': {
        title: '内容聚合 - 搜索你感兴趣的博主',
        path: 'pages/search/search'
      },
      'subscription': {
        title: '内容聚合 - 管理你的订阅',
        path: 'pages/subscription/subscription'
      },
      'profile': {
        title: '内容聚合 - 个人中心',
        path: 'pages/profile/profile'
      }
    }

    const config = pageShareConfig[pageName] || {
      title: this.shareConfig.defaultTitle,
      path: this.shareConfig.defaultPath
    }

    // 添加分享参数
    let finalPath = customPath || config.path
    if (Object.keys(shareParams).length > 0) {
      const params = new URLSearchParams(shareParams).toString()
      finalPath += (finalPath.includes('?') ? '&' : '?') + params
    }

    return {
      title: customTitle || config.title,
      path: finalPath,
      imageUrl: customImageUrl || this.shareConfig.defaultImageUrl,
      pageName: pageName,
      shareTime: new Date().toISOString()
    }
  }

  /**
   * 处理分享到微信好友
   * @param {Object} shareData - 分享数据
   */
  async shareToFriend(shareData) {
    try {
      // 记录分享统计
      this.recordShare('friend', shareData)

      // 微信小程序中，分享到好友通过onShareAppMessage实现
      // 这里主要是记录分享意图和统计
      console.log('准备分享到微信好友:', shareData)

      // 返回分享配置，供onShareAppMessage使用
      return {
        title: shareData.title,
        path: shareData.path,
        imageUrl: shareData.imageUrl,
        success: () => {
          this.onShareSuccess('friend', shareData)
        },
        fail: (error) => {
          this.onShareFail('friend', shareData, error)
        }
      }
    } catch (error) {
      console.error('分享到好友失败:', error)
      throw error
    }
  }

  /**
   * 处理分享到朋友圈
   * @param {Object} shareData - 分享数据
   */
  async shareToTimeline(shareData) {
    try {
      // 记录分享统计
      this.recordShare('timeline', shareData)

      // 微信小程序中，分享到朋友圈通过onShareTimeline实现
      console.log('准备分享到朋友圈:', shareData)

      // 返回分享配置，供onShareTimeline使用
      return {
        title: shareData.title,
        query: this.extractQueryFromPath(shareData.path),
        imageUrl: shareData.imageUrl,
        success: () => {
          this.onShareSuccess('timeline', shareData)
        },
        fail: (error) => {
          this.onShareFail('timeline', shareData, error)
        }
      }
    } catch (error) {
      console.error('分享到朋友圈失败:', error)
      throw error
    }
  }

  /**
   * 从路径中提取查询参数
   * @param {string} path - 页面路径
   */
  extractQueryFromPath(path) {
    const queryIndex = path.indexOf('?')
    if (queryIndex === -1) return ''
    
    const queryString = path.substring(queryIndex + 1)
    const params = new URLSearchParams(queryString)
    const query = {}
    
    for (const [key, value] of params) {
      query[key] = value
    }
    
    return query
  }

  /**
   * 记录分享统计
   * @param {string} shareType - 分享类型 ('friend' | 'timeline')
   * @param {Object} shareData - 分享数据
   */
  recordShare(shareType, shareData) {
    try {
      this.shareStats.totalShares++
      
      // 记录文章分享统计
      if (shareData.article && shareData.article.id) {
        const articleId = shareData.article.id
        if (!this.shareStats.articleShares[articleId]) {
          this.shareStats.articleShares[articleId] = {
            article: shareData.article,
            totalShares: 0,
            friendShares: 0,
            timelineShares: 0,
            firstShareTime: new Date().toISOString()
          }
        }
        
        this.shareStats.articleShares[articleId].totalShares++
        this.shareStats.articleShares[articleId][shareType + 'Shares']++
      }
      
      // 记录分享历史
      const shareRecord = {
        id: Date.now().toString(),
        shareType,
        shareTime: new Date().toISOString(),
        title: shareData.title,
        path: shareData.path,
        articleId: shareData.article ? shareData.article.id : null,
        pageName: shareData.pageName || null,
        shareSource: shareData.shareSource || 'unknown'
      }
      
      this.shareStats.shareHistory.unshift(shareRecord)
      
      // 只保留最近100条分享记录
      if (this.shareStats.shareHistory.length > 100) {
        this.shareStats.shareHistory = this.shareStats.shareHistory.slice(0, 100)
      }
      
      // 保存统计数据
      this.saveShareStats()
      
      console.log('分享统计记录成功:', shareRecord)
    } catch (error) {
      console.error('记录分享统计失败:', error)
    }
  }

  /**
   * 分享成功回调
   * @param {string} shareType - 分享类型
   * @param {Object} shareData - 分享数据
   */
  onShareSuccess(shareType, shareData) {
    console.log(`分享到${shareType === 'friend' ? '好友' : '朋友圈'}成功`)
    
    // 显示成功提示
    uni.showToast({
      title: '分享成功',
      icon: 'success',
      duration: 2000
    })
    
    // 可以在这里添加分享成功的额外逻辑
    // 比如发送分享成功事件到后端
    this.reportShareSuccess(shareType, shareData)
  }

  /**
   * 分享失败回调
   * @param {string} shareType - 分享类型
   * @param {Object} shareData - 分享数据
   * @param {Object} error - 错误信息
   */
  onShareFail(shareType, shareData, error) {
    console.error(`分享到${shareType === 'friend' ? '好友' : '朋友圈'}失败:`, error)
    
    // 显示失败提示
    uni.showToast({
      title: '分享失败，请重试',
      icon: 'none',
      duration: 2000
    })
  }

  /**
   * 上报分享成功事件到后端
   * @param {string} shareType - 分享类型
   * @param {Object} shareData - 分享数据
   */
  async reportShareSuccess(shareType, shareData) {
    try {
      // 这里可以调用后端API记录分享事件
      const reportData = {
        share_type: shareType,
        article_id: shareData.article ? shareData.article.id : null,
        page_name: shareData.pageName || null,
        share_source: shareData.shareSource || 'unknown',
        share_time: shareData.shareTime,
        user_agent: uni.getSystemInfoSync()
      }
      
      // 暂时只记录到控制台，实际项目中应该调用API
      console.log('分享事件上报数据:', reportData)
      
      // 示例API调用（需要根据实际后端接口调整）
      // await request.post('/analytics/share', reportData)
      
    } catch (error) {
      console.error('上报分享事件失败:', error)
    }
  }

  /**
   * 获取分享统计数据
   */
  getShareStats() {
    return {
      ...this.shareStats,
      topSharedArticles: this.getTopSharedArticles(5),
      recentShares: this.shareStats.shareHistory.slice(0, 10)
    }
  }

  /**
   * 获取最受欢迎的分享文章
   * @param {number} limit - 返回数量限制
   */
  getTopSharedArticles(limit = 5) {
    const articles = Object.values(this.shareStats.articleShares)
    return articles
      .sort((a, b) => b.totalShares - a.totalShares)
      .slice(0, limit)
      .map(item => ({
        article: item.article,
        totalShares: item.totalShares,
        friendShares: item.friendShares,
        timelineShares: item.timelineShares,
        firstShareTime: item.firstShareTime
      }))
  }

  /**
   * 保存分享统计数据到本地存储
   */
  saveShareStats() {
    try {
      uni.setStorageSync('shareStats', JSON.stringify(this.shareStats))
    } catch (error) {
      console.error('保存分享统计失败:', error)
    }
  }

  /**
   * 从本地存储加载分享统计数据
   */
  loadShareStats() {
    try {
      const statsStr = uni.getStorageSync('shareStats')
      if (statsStr) {
        this.shareStats = {
          ...this.shareStats,
          ...JSON.parse(statsStr)
        }
      }
    } catch (error) {
      console.error('加载分享统计失败:', error)
    }
  }

  /**
   * 清除分享统计数据
   */
  clearShareStats() {
    this.shareStats = {
      totalShares: 0,
      articleShares: {},
      shareHistory: []
    }
    
    try {
      uni.removeStorageSync('shareStats')
    } catch (error) {
      console.error('清除分享统计失败:', error)
    }
  }

  /**
   * 处理分享链接点击
   * @param {Object} query - 页面查询参数
   */
  handleShareLinkClick(query) {
    try {
      if (query.share_source && query.share_time) {
        console.log('用户通过分享链接进入:', query)
        
        // 记录分享链接点击事件
        const clickEvent = {
          shareSource: query.share_source,
          shareTime: query.share_time,
          clickTime: new Date().toISOString(),
          articleId: query.id || null,
          userAgent: uni.getSystemInfoSync()
        }
        
        // 保存点击事件
        this.recordShareClick(clickEvent)
        
        // 可以在这里添加特殊的欢迎逻辑
        // 比如显示欢迎消息或者特殊的引导
        this.showShareWelcome(query)
      }
    } catch (error) {
      console.error('处理分享链接点击失败:', error)
    }
  }

  /**
   * 记录分享链接点击事件
   * @param {Object} clickEvent - 点击事件数据
   */
  recordShareClick(clickEvent) {
    try {
      let shareClicks = uni.getStorageSync('shareClicks') || []
      shareClicks.unshift(clickEvent)
      
      // 只保留最近50条点击记录
      if (shareClicks.length > 50) {
        shareClicks = shareClicks.slice(0, 50)
      }
      
      uni.setStorageSync('shareClicks', shareClicks)
    } catch (error) {
      console.error('记录分享点击失败:', error)
    }
  }

  /**
   * 显示分享欢迎信息
   * @param {Object} query - 查询参数
   */
  showShareWelcome(query) {
    // 延迟显示，避免与页面加载冲突
    setTimeout(() => {
      if (query.share_source === 'article_detail') {
        uni.showToast({
          title: '欢迎通过分享进入',
          icon: 'none',
          duration: 2000
        })
      }
    }, 1000)
  }
}

// 创建单例实例
const wechatShareManager = new WechatShareManager()

export default wechatShareManager
export { WechatShareManager }