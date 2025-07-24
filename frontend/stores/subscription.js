/**
 * 订阅状态管理
 */
import { defineStore } from 'pinia'
import request from '../utils/request'
import { useUserStore } from './user'

export const useSubscriptionStore = defineStore('subscription', {
  state: () => ({
    // 订阅列表
    subscriptions: [],
    
    // 加载状态
    loading: false,
    
    // 正在加载的账号ID列表
    loadingAccountIds: [],
    
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
      console.log('计算按平台分组的订阅, 当前订阅数量:', state.subscriptions.length)
      
      // 调试订阅数据结构
      if (state.subscriptions.length > 0) {
        console.log('订阅数据示例:', JSON.stringify(state.subscriptions[0], null, 2))
      } else {
        console.log('订阅列表为空，无法生成分组')
        return grouped; // 直接返回空对象
      }
      
      state.subscriptions.forEach(sub => {
        if (!sub) {
          console.warn('订阅项为null或undefined，已跳过')
          return
        }
        
        let platform = '';
        let transformedSub = null;
        
        // 处理扁平数据结构（API直接返回的格式）
        if (sub.account_platform) {
          platform = sub.account_platform
          
          // 转换扁平结构为嵌套结构，以兼容前端组件
          transformedSub = {
            ...sub,
            account: {
              id: sub.account_id || sub.id,
              name: sub.account_name || '未知账号',
              platform: sub.account_platform,
              avatar_url: sub.account_avatar_url || '/static/default-avatar.png',
              description: sub.account_description || '',
              follower_count: sub.account_follower_count || 0
            }
          }
        }
        // 保留处理嵌套数据结构的逻辑（向后兼容）
        else if (sub.account && sub.account.platform) {
          platform = sub.account.platform
          transformedSub = sub
        } 
        // 尝试自动修复缺失的数据结构
        else if (sub.id) {
          console.warn('发现不完整的订阅数据，尝试修复:', sub)
          platform = sub.platform || 'unknown'
          transformedSub = {
            ...sub,
            account: {
              id: sub.id,
              name: sub.name || '未知账号',
              platform: platform,
              avatar_url: sub.avatar_url || '/static/default-avatar.png',
              description: sub.description || '',
              follower_count: sub.follower_count || 0
            }
          }
        } else {
          console.warn('忽略无效的订阅数据:', JSON.stringify(sub))
          return
        }
        
        // 确保platform是有效的字符串
        if (!platform) {
          platform = 'unknown'
          console.warn('使用默认platform "unknown"，原始数据:', JSON.stringify(sub))
        }
        
        // 添加到分组
        if (!grouped[platform]) {
          grouped[platform] = []
        }
        
        // 确保transformedSub有效
        if (transformedSub) {
          grouped[platform].push(transformedSub)
        }
      })
      
      // 调试分组结果
      if (Object.keys(grouped).length === 0 && state.subscriptions.length > 0) {
        console.warn('严重: 分组结果为空，但有订阅数据。详细检查订阅数据:')
        state.subscriptions.forEach((sub, index) => {
          console.log(`订阅项 #${index}:`, JSON.stringify(sub))
        })
      } else {
        console.log('分组结果:', Object.keys(grouped).map(key => `${key}: ${grouped[key].length}个`))
      }
      
      return grouped
    }
  },
  
  actions: {
    /**
     * 获取订阅列表
     */
    async fetchSubscriptions(refresh = false) {
      console.log('开始获取订阅列表, refresh:', refresh, '当前页码:', this.pagination.page)
      try {
        if (refresh) {
          console.log('刷新订阅列表，重置分页信息')
          this.pagination.page = 1
          this.pagination.hasMore = true
        }
        
        if (!this.pagination.hasMore && !refresh) {
          console.log('没有更多数据且不是刷新操作，直接返回')
          return
        }
        
        this.loading = true
        console.log('发送请求获取订阅列表, 参数:', { page: this.pagination.page, page_size: this.pagination.size })
        
        const response = await request.get('/subscriptions', {
          page: this.pagination.page,
          page_size: this.pagination.size
        })
        
        // 请求工具会返回完整的分页响应对象
        console.log('订阅列表请求响应:', response)
        
        // 检查响应格式是否正确
        if (!response || typeof response !== 'object') {
          console.error('响应格式错误，期望对象类型但收到:', typeof response)
          throw new Error('响应格式错误')
        }
        
        // 兼容处理，确保data是数组
        let data = []
        
        // 如果响应是数组格式，直接使用
        if (Array.isArray(response)) {
          console.log('响应是数组格式，直接使用')
          data = response
        } 
        // 如果响应是标准分页对象格式，使用data字段
        else if (response.data && Array.isArray(response.data)) {
          console.log('响应是标准分页对象格式，使用data字段')
          data = response.data
        }
        // 其他情况，尝试获取data字段并转换为数组
        else if (response.data) {
          console.log('响应包含data字段，但非数组格式，尝试转换')
          data = Array.isArray(response.data) ? response.data : [response.data]
        }
        
        console.log('获取到订阅数据:', data.length, '条记录')
        
        // 过滤掉无效的数据
        data = data.filter(item => item && (item.id || item.account_id || (item.account && item.account.id)))
        console.log('过滤后有效订阅数据:', data.length, '条记录')
        
        // 处理每个订阅项，确保格式一致
        const processedData = data.map(sub => {
          // 如果已经是嵌套格式并且数据完整，直接返回
          if (sub.account && sub.account.id && sub.account.platform) {
            return sub;
          }
          
          // 如果是扁平格式，转换为嵌套格式
          if (sub.account_id || sub.account_platform) {
            return {
              ...sub,
              account: {
                id: sub.account_id || sub.id,
                name: sub.account_name || '未知账号',
                platform: sub.account_platform || 'unknown',
                avatar_url: sub.account_avatar_url || '/static/default-avatar.png',
                description: sub.account_description || '',
                follower_count: sub.account_follower_count || 0
              }
            };
          }
          
          // 如果数据格式不完整但有ID，尝试构建
          return {
            ...sub,
            account: {
              id: sub.id,
              name: sub.name || '未知账号',
              platform: sub.platform || 'unknown',
              avatar_url: sub.avatar_url || '/static/default-avatar.png',
              description: sub.description || '',
              follower_count: sub.follower_count || 0
            }
          };
        });
        
        if (refresh) {
          console.log('刷新模式，替换所有订阅数据')
          this.subscriptions = processedData
        } else {
          console.log('加载更多模式，追加订阅数据')
          this.subscriptions.push(...processedData)
        }
        
        // 更新分页信息
        this.pagination.total = response.total || 0
        this.pagination.hasMore = data.length === this.pagination.size
        this.pagination.page += 1
        
        console.log('更新分页信息:', { 
          total: this.pagination.total, 
          hasMore: this.pagination.hasMore,
          nextPage: this.pagination.page
        })
        
        // 检查并尝试修复分组问题
        const groupResult = this.subscriptionsByPlatform;
        if (Object.keys(groupResult).length === 0 && this.subscriptions.length > 0) {
          console.warn('订阅数据存在但无法正确分组，这可能导致UI显示问题')
        }
        
        return response
        
      } catch (error) {
        console.error('获取订阅列表失败:', error)
        console.log('错误详情:', error.message, error.stack)
        throw error
      } finally {
        this.loading = false
        console.log('获取订阅列表完成，当前列表长度:', this.subscriptions.length)
      }
    },
    
    /**
     * 订阅博主
     */
    async subscribeAccount(accountId) {
      console.log('开始订阅博主, accountId:', accountId)
      try {
        // 将账号ID添加到加载中列表
        this.loadingAccountIds.push(accountId)
        this.loading = true
        
        // 获取当前用户ID
        const userStore = useUserStore()
        
        if (!userStore.userInfo.id) {
          console.error('订阅失败: 用户未登录')
          throw new Error('用户未登录')
        }
        
        console.log('发送订阅请求, 用户ID:', userStore.userInfo.id)
        const response = await request.post('/subscriptions', {
          user_id: userStore.userInfo.id,
          account_id: accountId
        })
        
        console.log('订阅成功, 响应数据:', response)
        
        // 添加到订阅列表
        if (response && response.data) {
          // 确保数据格式一致性
          let subscriptionData = response.data;
          
          // 如果响应中没有必要的字段，尝试规范化数据结构
          if (!subscriptionData.account_id && !subscriptionData.account) {
            console.log('订阅响应数据格式不完整，尝试构建完整数据结构')
            subscriptionData = {
              ...subscriptionData,
              account_id: accountId
            }
          }
          
          this.subscriptions.unshift(subscriptionData)
          console.log('订阅数据已添加到列表, 当前列表长度:', this.subscriptions.length)
          
          // 在添加完新订阅后，重置分页并刷新订阅列表
          console.log('订阅成功后刷新订阅列表以获取完整数据')
          this.fetchSubscriptions(true).catch(err => {
            console.error('订阅后刷新列表失败:', err)
          })
        } else {
          console.warn('订阅响应数据异常:', response)
        }
        
        return response.data
        
      } catch (error) {
        console.error('订阅失败:', error)
        console.log('错误详情:', error.message)
        
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
        // 从加载中列表移除该账号ID
        const index = this.loadingAccountIds.indexOf(accountId)
        if (index > -1) {
          this.loadingAccountIds.splice(index, 1)
        }
        // 如果没有正在加载的账号，设置全局loading为false
        if (this.loadingAccountIds.length === 0) {
          this.loading = false
        }
      }
    },
    
    /**
     * 取消订阅（通过订阅ID）
     */
    async unsubscribeAccount(subscriptionId) {
      console.log('开始取消订阅, subscriptionId:', subscriptionId)
      try {
        this.loading = true
        
        // 查找订阅记录以获取account_id
        const subscription = this.subscriptions.find(sub => sub.id === subscriptionId)
        if (!subscription) {
          console.warn('未找到要取消的订阅, subscriptionId:', subscriptionId)
          throw new Error('订阅记录不存在')
        }
        
        // 使用account_id而不是subscription_id调用API
        const accountId = subscription.account_id || (subscription.account && subscription.account.id)
        if (!accountId) {
          console.error('订阅记录中没有account_id或account.id', subscription)
          throw new Error('无法获取账号ID')
        }
        
        console.log('使用account_id调用取消订阅API, accountId:', accountId)
        await request.delete(`/subscriptions/${accountId}`)
        console.log('取消订阅请求成功')
        
        // 从订阅列表中移除
        const index = this.subscriptions.findIndex(sub => sub.id === subscriptionId)
        if (index > -1) {
          console.log('从列表中移除订阅数据, 索引:', index)
          this.subscriptions.splice(index, 1)
        } else {
          console.warn('未找到要移除的订阅, subscriptionId:', subscriptionId)
        }
        
        uni.showToast({
          title: '取消订阅成功',
          icon: 'success'
        })
        
      } catch (error) {
        console.error('取消订阅失败:', error)
        console.log('错误详情:', error.message)
        uni.showToast({
          title: '取消订阅失败，请稍后重试',
          icon: 'none'
        })
        throw error
      } finally {
        this.loading = false
        console.log('取消订阅完成, 当前列表长度:', this.subscriptions.length)
      }
    },

    /**
     * 通过账号ID取消订阅
     */
    async unsubscribeByAccountId(accountId) {
      console.log('通过账号ID取消订阅, accountId:', accountId)
      try {
        // 将账号ID添加到加载中列表
        this.loadingAccountIds.push(accountId)
        this.loading = true
        
        await request.delete(`/subscriptions/${accountId}`)
        console.log('通过账号ID取消订阅请求成功')
        
        // 从订阅列表中移除
        const index = this.subscriptions.findIndex(sub => 
          (sub && sub.account && sub.account.id === accountId) || // 嵌套结构
          (sub && sub.account_id === accountId) // 扁平结构
        )
        if (index > -1) {
          console.log('从列表中移除订阅数据, 索引:', index)
          this.subscriptions.splice(index, 1)
        } else {
          console.warn('未找到要移除的订阅, accountId:', accountId)
        }
        
        // 移除不必要的提示
        // uni.showToast({
        //   title: '退订成功',
        //   icon: 'success'
        // })
        
      } catch (error) {
        console.error('退订失败:', error)
        console.log('错误详情:', error.message)
        uni.showToast({
          title: '退订失败，请稍后重试',
          icon: 'none'
        })
        throw error
      } finally {
        // 从加载中列表移除该账号ID
        const index = this.loadingAccountIds.indexOf(accountId)
        if (index > -1) {
          this.loadingAccountIds.splice(index, 1)
        }
        // 如果没有正在加载的账号，设置全局loading为false
        if (this.loadingAccountIds.length === 0) {
          this.loading = false
        }
        console.log('通过账号ID取消订阅完成, 当前列表长度:', this.subscriptions.length)
      }
    },
    
    /**
     * 检查是否已订阅某个博主
     */
    isSubscribed(accountId) {
      const result = this.subscriptions.some(sub => 
        (sub && sub.account && sub.account.id === accountId) || // 嵌套结构
        (sub && sub.account_id === accountId) // 扁平结构
      )
      console.log('检查是否已订阅, accountId:', accountId, '结果:', result)
      return result
    },
    
    /**
     * 获取订阅的博主信息
     */
    getSubscribedAccount(accountId) {
      const subscription = this.subscriptions.find(sub => 
        (sub && sub.account && sub.account.id === accountId) || // 嵌套结构
        (sub && sub.account_id === accountId) // 扁平结构
      )
      console.log('获取订阅的博主信息, accountId:', accountId, '是否找到:', !!subscription)
      
      if (!subscription) return null
      
      // 如果是嵌套结构，直接返回account对象
      if (subscription.account) {
        return subscription.account
      }
      
      // 如果是扁平结构，构建account对象
      return {
        id: subscription.account_id,
        name: subscription.account_name,
        platform: subscription.account_platform,
        avatar_url: subscription.account_avatar_url,
        description: subscription.account_description,
        follower_count: subscription.account_follower_count
      }
    },
    
    /**
     * 批量取消订阅
     */
    async batchUnsubscribe(subscriptionIds) {
      console.log('批量取消订阅, ids:', subscriptionIds)
      try {
        this.loading = true
        
        // 找到所有订阅记录并获取相应的account_id
        const subscriptionsToUnsubscribe = this.subscriptions.filter(sub => 
          subscriptionIds.includes(sub.id)
        )
        
        if (subscriptionsToUnsubscribe.length === 0) {
          console.warn('未找到任何要取消的订阅')
          throw new Error('没有找到要取消的订阅')
        }
        
        // 提取每个订阅的账号ID
        const accountIds = subscriptionsToUnsubscribe.map(sub => 
          sub.account_id || (sub.account && sub.account.id)
        ).filter(id => id) // 过滤掉无效的ID
        
        if (accountIds.length === 0) {
          console.error('无法提取账号ID')
          throw new Error('无法获取账号ID')
        }
        
        console.log('使用account_ids批量取消订阅:', accountIds)
        const promises = accountIds.map(id => 
          request.delete(`/subscriptions/${id}`)
        )
        
        await Promise.all(promises)
        console.log('批量取消订阅请求成功')
        
        // 从订阅列表中移除
        const originalLength = this.subscriptions.length
        this.subscriptions = this.subscriptions.filter(
          sub => !subscriptionIds.includes(sub.id)
        )
        console.log('从列表中移除订阅数据, 移除前:', originalLength, '移除后:', this.subscriptions.length)
        
        uni.showToast({
          title: `成功取消${subscriptionIds.length}个订阅`,
          icon: 'success'
        })
        
      } catch (error) {
        console.error('批量取消订阅失败:', error)
        console.log('错误详情:', error.message)
        uni.showToast({
          title: '批量取消订阅失败',
          icon: 'none'
        })
        throw error
      } finally {
        this.loading = false
        console.log('批量取消订阅完成, 当前列表长度:', this.subscriptions.length)
      }
    },
    
    /**
     * 清除订阅数据
     */
    clearSubscriptions() {
      console.log('清除所有订阅数据')
      this.subscriptions = []
      this.pagination = {
        page: 1,
        size: 20,
        total: 0,
        hasMore: true
      }
      console.log('订阅数据已清除, 分页信息已重置')
      
      // 立即尝试重新获取最新数据
      this.fetchSubscriptions(true).catch(err => {
        console.error('清空后重新获取订阅列表失败:', err)
      })
    },
    
    /**
     * 立即更新本地订阅状态（用于UI立即响应）
     */
    updateLocalSubscriptionState(accountId, isSubscribed) {
      console.log('立即更新本地订阅状态, accountId:', accountId, '状态:', isSubscribed ? '已订阅' : '未订阅')
      
      if (isSubscribed) {
        // 如果不存在于订阅列表中，添加一个临时订阅
        if (!this.isSubscribed(accountId)) {
          // 创建一个临时的订阅对象
          this.subscriptions.unshift({
            id: `temp_${accountId}`,
            account_id: accountId,
            status: 'active',
            created_at: new Date().toISOString()
          })
          console.log('已添加临时订阅对象')
        }
      } else {
        // 从订阅列表中移除
        const index = this.subscriptions.findIndex(sub => 
          (sub && sub.account && sub.account.id === accountId) || 
          (sub && sub.account_id === accountId)
        )
        if (index > -1) {
          this.subscriptions.splice(index, 1)
          console.log('已从列表中移除订阅, 索引:', index)
        }
      }
    },

    /**
     * 检查账号是否正在加载中
     */
    isAccountLoading(accountId) {
      return this.loadingAccountIds.includes(accountId)
    }
  }
})