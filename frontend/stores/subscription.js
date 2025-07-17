/**
 * 订阅状态管理
 */
import { defineStore } from 'pinia'
import request from '../utils/request'

export const useSubscriptionStore = defineStore('subscription', {
  state: () => ({
    // 订阅列表
    subscriptions: [],
    
    // 加载状态
    loading: false,
    
    // 分页信息
    pagination: {
      page: 1,
      size: 20,
      total: 0,
      hasMore: true
    }
  }),
  
  getters: {
    // 订阅数量
    subscriptionCount: (state) => state.subscriptions.length,
    
    // 按平台分组的订阅
    subscriptionsByPlatform: (state) => {
      const grouped = {}
      state.subscriptions.forEach(sub => {
        const platform = sub.account.platform
        if (!grouped[platform]) {
          grouped[platform] = []
        }
        grouped[platform].push(sub)
      })
      return grouped
    }
  },
  
  actions: {
    /**
     * 获取订阅列表
     */
    async fetchSubscriptions(refresh = false) {
      try {
        if (refresh) {
          this.pagination.page = 1
          this.pagination.hasMore = true
        }
        
        if (!this.pagination.hasMore && !refresh) {
          return
        }
        
        this.loading = true
        
        const data = await request.get('/subscriptions', {
          page: this.pagination.page,
          size: this.pagination.size
        })
        
        if (refresh) {
          this.subscriptions = data.items
        } else {
          this.subscriptions.push(...data.items)
        }
        
        // 更新分页信息
        this.pagination.total = data.total
        this.pagination.hasMore = data.items.length === this.pagination.size
        this.pagination.page += 1
        
        return data
        
      } catch (error) {
        console.error('获取订阅列表失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    /**
     * 订阅博主
     */
    async subscribeAccount(accountId) {
      try {
        this.loading = true
        
        const data = await request.post('/subscriptions', {
          account_id: accountId
        })
        
        // 添加到订阅列表
        this.subscriptions.unshift(data)
        
        uni.showToast({
          title: '订阅成功',
          icon: 'success'
        })
        
        return data
        
      } catch (error) {
        console.error('订阅失败:', error)
        
        if (error.message.includes('订阅数量已达上限')) {
          uni.showModal({
            title: '订阅限制',
            content: '您的订阅数量已达上限，请升级会员或取消部分订阅',
            showCancel: false
          })
        } else {
          uni.showToast({
            title: '订阅失败，请稍后重试',
            icon: 'none'
          })
        }
        
        throw error
      } finally {
        this.loading = false
      }
    },
    
    /**
     * 取消订阅
     */
    async unsubscribeAccount(subscriptionId) {
      try {
        this.loading = true
        
        await request.delete(`/subscriptions/${subscriptionId}`)
        
        // 从订阅列表中移除
        const index = this.subscriptions.findIndex(sub => sub.id === subscriptionId)
        if (index > -1) {
          this.subscriptions.splice(index, 1)
        }
        
        uni.showToast({
          title: '取消订阅成功',
          icon: 'success'
        })
        
      } catch (error) {
        console.error('取消订阅失败:', error)
        uni.showToast({
          title: '取消订阅失败，请稍后重试',
          icon: 'none'
        })
        throw error
      } finally {
        this.loading = false
      }
    },
    
    /**
     * 检查是否已订阅某个博主
     */
    isSubscribed(accountId) {
      return this.subscriptions.some(sub => sub.account.id === accountId)
    },
    
    /**
     * 获取订阅的博主信息
     */
    getSubscribedAccount(accountId) {
      const subscription = this.subscriptions.find(sub => sub.account.id === accountId)
      return subscription ? subscription.account : null
    },
    
    /**
     * 批量取消订阅
     */
    async batchUnsubscribe(subscriptionIds) {
      try {
        this.loading = true
        
        const promises = subscriptionIds.map(id => 
          request.delete(`/subscriptions/${id}`)
        )
        
        await Promise.all(promises)
        
        // 从订阅列表中移除
        this.subscriptions = this.subscriptions.filter(
          sub => !subscriptionIds.includes(sub.id)
        )
        
        uni.showToast({
          title: `成功取消${subscriptionIds.length}个订阅`,
          icon: 'success'
        })
        
      } catch (error) {
        console.error('批量取消订阅失败:', error)
        uni.showToast({
          title: '批量取消订阅失败',
          icon: 'none'
        })
        throw error
      } finally {
        this.loading = false
      }
    },
    
    /**
     * 清除订阅数据
     */
    clearSubscriptions() {
      this.subscriptions = []
      this.pagination = {
        page: 1,
        size: 20,
        total: 0,
        hasMore: true
      }
    }
  }
})