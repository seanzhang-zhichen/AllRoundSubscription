/**
 * 内容状态管理
 */
import { defineStore } from 'pinia'
import request from '../utils/request'
import { useCache, CacheType, CachePriority, CacheStrategy } from '../utils/cacheManager'
import { useNetwork } from '../utils/networkManager'
import { shareContent } from '../utils/common'

export const useContentStore = defineStore('content', {
  state: () => ({
    // 动态流内容
    feedList: [],

    // 文章详情缓存
    articleCache: new Map(),

    // 加载状态
    loading: false,
    refreshing: false,
    loadingMore: false,

    // 分页信息
    pagination: {
      page: 1,
      size: 20,
      total: 0,
      hasMore: true
    },

    // 最后更新时间
    lastUpdateTime: null
  }),

  getters: {
    // 按日期分组的动态流
    feedByDate: (state) => {
      const grouped = {}
      state.feedList.forEach(article => {
        const date = new Date(article.publish_time).toDateString()
        if (!grouped[date]) {
          grouped[date] = []
        }
        grouped[date].push(article)
      })
      return grouped
    },

    // 是否有内容
    hasContent: (state) => state.feedList.length > 0
  },

  actions: {
    /**
     * 获取动态流
     */
    async fetchFeed(refresh = false) {
      const cache = useCache()
      const network = useNetwork()

      try {
        if (refresh) {
          this.refreshing = true
          this.pagination.page = 1
          this.pagination.hasMore = true
        } else {
          if (!this.pagination.hasMore) {
            return
          }
          this.loadingMore = true
        }

        this.loading = true

        // 确保认证令牌可用
        const token = uni.getStorageSync('token')
        if (!token) {
          console.warn('获取动态流时未找到认证令牌')
          throw new Error('用户未登录或登录已过期')
        }

        // 生成缓存键
        const cacheKey = `feed:${this.pagination.page}:${this.pagination.size}`

        // 检查缓存（仅在非刷新且网络状况不佳时使用）
        if (!refresh && network.shouldUseCache()) {
          try {
            const cachedData = await cache.get(cacheKey, {
              strategy: CacheStrategy.MEMORY_FIRST
            })

            if (cachedData && Array.isArray(cachedData.data)) {
              
              // 检查并修复缓存的数据
              this.validateAndFixArticleData(cachedData.data);

              if (refresh) {
                this.feedList = cachedData.data || []
              } else {
                this.feedList.push(...(cachedData.data || []))
              }

              this.pagination.total = cachedData.total || 0
              this.pagination.hasMore = (this.feedList.length < cachedData.total)
              this.lastUpdateTime = cachedData.timestamp || Date.now()
              
              // 延迟一些时间后结束加载状态，避免闪烁
              setTimeout(() => {
                this.loading = false
                this.refreshing = false
                this.loadingMore = false
              }, 300)
              
              return
            }
          } catch (error) {
            console.error('获取缓存的动态流数据失败:', error)
          }
        }

        // 发起网络请求
        const result = await request.get('/content/feed', {
          page: this.pagination.page,
          size: this.pagination.size
        });

        // 检查并修复获取的数据
        this.validateAndFixArticleData(result.data);

        if (refresh) {
          this.feedList = result.data || []
        } else {
          this.feedList.push(...(result.data || []))
        }

        this.pagination.total = result.total || 0
        this.pagination.hasMore = (this.feedList.length < result.total)
        this.pagination.page++
        this.lastUpdateTime = Date.now()

        // 缓存结果
        try {
          await cache.set(cacheKey, {
            data: result.data,
            total: result.total,
            timestamp: Date.now()
          }, {
            strategy: CacheStrategy.STORAGE_FIRST,
            priority: CachePriority.HIGH,
            ttl: 30 * 60 * 1000 // 30分钟
          })
        } catch (error) {
          console.error('缓存动态流数据失败:', error)
        }

      } catch (error) {
        console.error('获取动态流失败:', error)
        throw error
      } finally {
        setTimeout(() => {
          this.loading = false
          this.refreshing = false
          this.loadingMore = false
        }, 300)
      }
    },

    /**
     * 验证并修复文章数据，确保所有必要字段存在
     */
    validateAndFixArticleData(articles) {
      if (!Array.isArray(articles)) return;
      
      articles.forEach(article => {
        if (!article) return;
        
        // 检查文章ID
        if (!article.id) {
          article.id = 'article_' + Math.random().toString(36).substring(2, 15);
        }
        
        // 检查发布时间
        if (!article.publish_time) {
          article.publish_time = new Date().toISOString();
        }
        
        // 检查文章标题
        if (!article.title) {
          article.title = '无标题内容';
        }
        
        // 检查并修复头像
        if (!article.account_avatar_url) {
          article.account_avatar_url = 'static/default-avatar.png';
        } else if (article.account_avatar_url === 'null' || article.account_avatar_url === 'undefined') {
          article.account_avatar_url = 'static/default-avatar.png';
        }
        
        // 检查账户名称
        if (!article.account_name) {
          article.account_name = '未知博主';
        }
        
        // 检查平台信息
        if (!article.account_platform) {
          article.account_platform = 'default';
        }
      });
    },

    /**
     * 获取文章详情
     */
    async fetchArticleDetail(articleId, platform) {
      try {
        if (!platform) {
          throw new Error('获取文章详情必须提供平台参数');
        }

        const cacheKey = `${articleId}-${platform}`;
        // 先检查缓存
        if (this.articleCache.has(cacheKey)) {
          return this.articleCache.get(cacheKey);
        }

        this.loading = true;

        const params = { platform };
        const data = await request.get(`/content/articles/${articleId}`, params);

        // 处理文章详情数据，确保数据一致性
        if (data) {
          // 确保account对象存在
          if (!data.account) {
            data.account = {
              name: data.account_name || '未知博主',
              avatar_url: data.account_avatar_url || 'static/default-avatar.png',
              platform: platform
            };
          }
          
          // 确保扁平字段存在
          data.account_name = data.account.name || '未知博主';
          data.account_avatar_url = data.account.avatar_url || 'static/default-avatar.png';
          data.account_platform = platform;
        }

        // 缓存文章详情
        this.articleCache.set(cacheKey, data);

        return data;

      } catch (error) {
        console.error('获取文章详情失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * 刷新动态流
     */
    async refreshFeed() {
      try {
        this.refreshing = true
        this.pagination.page = 1
        this.pagination.hasMore = true
        
        this.loading = true

        // 确保认证令牌可用
        const token = uni.getStorageSync('token')
        if (!token) {
          console.warn('获取动态流时未找到认证令牌')
          throw new Error('用户未登录或登录已过期')
        }

        const data = await request.get('/content/feed', {
          page: this.pagination.page,
          size: this.pagination.size,
          refresh: true  // 添加refresh=true参数
        })

        // 验证返回的数据结构
        if (!data || !Array.isArray(data.data)) {
          console.error('API返回数据格式错误:', data)
          throw new Error('数据格式错误')
        }

        // 处理文章数据
        const processedData = data.data.map(article => {
          // 确保扁平字段存在
          if (!article.account_name) {
            article.account_name = '未知博主';
          }
          if (!article.account_avatar_url) {
            article.account_avatar_url = 'static/default-avatar.png';
          }
          if (!article.account_platform) {
            article.account_platform = 'default';
          }
          return article;
        });

        this.feedList = processedData || []
        
        // 更新分页信息
        this.pagination.total = data.total || 0
        this.pagination.hasMore = (data.data || []).length === this.pagination.size
        this.pagination.page += 1
        this.lastUpdateTime = new Date()

        return data

      } catch (error) {
        console.error('刷新动态流失败:', error)
        throw error
      } finally {
        this.loading = false
        this.refreshing = false
      }
    },

    /**
     * 加载更多动态
     */
    async loadMoreFeed() {
      return this.fetchFeed(false)
    },

    /**
     * 获取指定博主的文章
     */
    async fetchAccountArticles(accountId, page = 1, size = 20, platform = '') {
      try {
        this.loading = true

        const data = await request.get('/content/accounts/' + accountId + '/articles', {
          page,
          page_size: size,
          platform
        })

        return data

      } catch (error) {
        console.error('获取博主文章失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * 搜索文章
     */
    async searchArticles(keyword, filters = {}) {
      try {
        this.loading = true

        const data = await request.get('/content/articles/search', {
          keyword,
          ...filters
        })

        return data

      } catch (error) {
        console.error('搜索文章失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * 标记文章为已读
     */
    async markArticleAsRead(articleId) {
      try {
        // 更新本地状态
        const article = this.feedList.find(item => item.id === articleId)
        if (article) {
          article.is_read = true
        }

        // 调用API标记已读
        await request.post(`/content/articles/${articleId}/read`)

      } catch (error) {
        console.error('标记文章已读失败:', error)
      }
    },

    /**
     * 收藏文章
     */
    async favoriteArticle(articleId) {
      try {
        await request.post(`/content/articles/${articleId}/favorite`)

        // 更新本地状态
        const article = this.feedList.find(item => item.id === articleId)
        if (article) {
          article.is_favorited = true
        }

        uni.showToast({
          title: '收藏成功',
          icon: 'success'
        })

      } catch (error) {
        console.error('收藏文章失败:', error)
        uni.showToast({
          title: '收藏失败',
          icon: 'none'
        })
        throw error
      }
    },

    /**
     * 取消收藏文章
     */
    async unfavoriteArticle(articleId) {
      try {
        await request.delete(`/content/articles/${articleId}/favorite`)

        // 更新本地状态
        const article = this.feedList.find(item => item.id === articleId)
        if (article) {
          article.is_favorited = false
        }

        uni.showToast({
          title: '取消收藏成功',
          icon: 'success'
        })

      } catch (error) {
        console.error('取消收藏失败:', error)
        uni.showToast({
          title: '取消收藏失败',
          icon: 'none'
        })
        throw error
      }
    },

    /**
     * 分享文章
     */
    async shareArticle(articleId) {
      try {
        const article = this.feedList.find(item => item.id === articleId) ||
          this.articleCache.get(articleId)

        if (!article) {
          throw new Error('文章不存在')
        }

        // 使用通用的分享功能
        await shareContent({
          title: article.title,
          summary: article.summary || article.description || article.title,
          href: article.url,
          imageUrl: (article.images && article.images[0]) || '',
          provider: 'weixin',
          scene: 'WXSceneSession'
        })

        // 记录分享统计
        await request.post(`/content/articles/${articleId}/share`)

      } catch (error) {
        console.error('分享文章失败:', error)
        throw error
      }
    },

    /**
     * 清除内容数据
     */
    clearContent() {
      this.feedList = []
      this.articleCache.clear()
      this.pagination = {
        page: 1,
        size: 20,
        total: 0,
        hasMore: true
      }
      this.lastUpdateTime = null
    },

    /**
     * 清除文章缓存
     */
    clearArticleCache() {
      this.articleCache.clear()
    }
  }
})