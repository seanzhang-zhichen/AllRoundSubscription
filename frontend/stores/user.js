/**
 * 用户状态管理
 */
import { defineStore } from 'pinia'
import request from '../utils/request'

export const useUserStore = defineStore('user', {
  state: () => ({
    // 用户基本信息
    userInfo: {
      id: null,
      openid: '',
      nickname: '',
      avatar_url: '',
      membership_level: 'free',
      membership_expire_at: null,
      created_at: null
    },
    
    // 用户权限限制
    userLimits: {
      subscription_limit: 10,
      push_limit: 5,
      current_subscriptions: 0,
      today_pushes: 0
    },
    
    // 用户偏好设置
    userSettings: {
      push_enabled: true,
      push_time_start: '09:00',
      push_time_end: '22:00'
    },
    
    // 加载状态
    loading: false
  }),
  
  getters: {
    // 是否已登录
    isLoggedIn: (state) => !!state.userInfo.id,
    
    // 会员等级显示名称
    membershipLevelName: (state) => {
      const levelMap = {
        'free': '免费用户',
        'basic': '基础会员',
        'premium': '高级会员'
      }
      return levelMap[state.userInfo.membership_level] || '未知'
    },
    
    // 是否为付费会员
    isPaidMember: (state) => {
      return ['basic', 'premium'].includes(state.userInfo.membership_level)
    },
    
    // 订阅是否已达上限
    isSubscriptionLimitReached: (state) => {
      return state.userLimits.current_subscriptions >= state.userLimits.subscription_limit
    },
    
    // 今日推送是否已达上限
    isPushLimitReached: (state) => {
      return state.userLimits.today_pushes >= state.userLimits.push_limit
    }
  },
  
  actions: {
    /**
     * 获取用户信息
     */
    async fetchUserProfile() {
      try {
        this.loading = true
        const data = await request.get('/users/profile')
        this.userInfo = data
        return data
      } catch (error) {
        console.error('获取用户信息失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    /**
     * 更新用户信息
     */
    async updateUserProfile(profileData) {
      try {
        this.loading = true
        const data = await request.put('/users/profile', profileData)
        this.userInfo = { ...this.userInfo, ...data }
        return data
      } catch (error) {
        console.error('更新用户信息失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    /**
     * 获取用户权限限制
     */
    async fetchUserLimits() {
      try {
        const data = await request.get('/users/limits')
        // 将后端返回的字段映射到前端期望的字段
        this.userLimits = {
          ...data,
          current_subscriptions: data.subscription_used || 0,
          today_pushes: data.daily_push_used || 0,
          subscription_limit: data.subscription_limit || 10,
          push_limit: data.daily_push_limit || 5
        }
        return data
      } catch (error) {
        console.error('获取用户限制失败:', error)
        throw error
      }
    },
    
    /**
     * 获取会员信息
     */
    async fetchMembershipInfo() {
      try {
        const data = await request.get('/users/membership')
        this.userInfo.membership_level = data.level
        this.userInfo.membership_expire_at = data.expire_at
        return data
      } catch (error) {
        console.error('获取会员信息失败:', error)
        throw error
      }
    },
    
    /**
     * 升级会员
     */
    async upgradeMembership(level) {
      try {
        this.loading = true
        const data = await request.post('/users/membership', { level })
        this.userInfo.membership_level = data.level
        this.userInfo.membership_expire_at = data.expire_at
        
        // 更新用户限制
        await this.fetchUserLimits()
        
        uni.showToast({
          title: '会员升级成功',
          icon: 'success'
        })
        
        return data
      } catch (error) {
        console.error('会员升级失败:', error)
        uni.showToast({
          title: '升级失败，请稍后重试',
          icon: 'none'
        })
        throw error
      } finally {
        this.loading = false
      }
    },
    
    /**
     * 更新用户设置
     */
    async updateUserSettings(settings) {
      try {
        this.userSettings = { ...this.userSettings, ...settings }
        
        // 保存到本地存储
        uni.setStorageSync('userSettings', this.userSettings)
        
        // 这里可以调用API保存到服务器
        // await request.put('/users/settings', this.userSettings)
        
        return this.userSettings
      } catch (error) {
        console.error('更新用户设置失败:', error)
        throw error
      }
    },
    
    /**
     * 从本地存储加载用户设置
     */
    loadUserSettings() {
      try {
        const settings = uni.getStorageSync('userSettings')
        if (settings) {
          this.userSettings = { ...this.userSettings, ...settings }
        }
      } catch (error) {
        console.error('加载用户设置失败:', error)
      }
    },
    
    /**
     * 清除用户数据
     */
    clearUserData() {
      this.userInfo = {
        id: null,
        openid: '',
        nickname: '',
        avatar_url: '',
        membership_level: 'free',
        membership_expire_at: null,
        created_at: null
      }
      
      this.userLimits = {
        subscription_limit: 10,
        push_limit: 5,
        current_subscriptions: 0,
        today_pushes: 0
      }
      
      // 清除本地存储
      uni.removeStorageSync('userSettings')
    }
  }
})