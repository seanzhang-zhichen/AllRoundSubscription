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
        'v1': 'V1 会员',
        'v2': 'V2 会员',
        'v3': 'V3 会员',
        'v4': 'V4 会员',
        'v5': 'V5 会员',
        // 兼容旧值
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
     * 升级会员（通过支付）
     */
    async upgradeMembership(level, durationMonths = 1) {
      try {
        this.loading = true
        // 创建支付订单
        const payload = {
          level,
          duration_months: durationMonths,
          channel: 'wechat_miniprog'  // 默认使用小程序支付
        }
        const resp = await request.post('/payments/create', payload)
        const { pay_params: payParams, channel } = resp

        // 调起支付
        if (channel === 'wechat_miniprog' || channel === 'wechat_jsapi') {
          // 小程序支付
          await new Promise((resolve, reject) => {
            // #ifdef MP-WEIXIN
            wx.requestPayment({
              timeStamp: payParams.timeStamp,
              nonceStr: payParams.nonceStr,
              package: payParams.package,
              signType: payParams.signType || 'RSA',
              paySign: payParams.paySign,
              success: resolve,
              fail: reject
            })
            // #endif
            // #ifndef MP-WEIXIN
            reject(new Error('当前环境不支持小程序支付'))
            // #endif
          })
        } else if (channel === 'wechat_h5' && payParams.h5_url) {
          // H5跳转
          // #ifdef H5
          window.location.href = payParams.h5_url
          // #endif
          // #ifndef H5
          uni.navigateTo({ url: `/pages/webview/webview?url=${encodeURIComponent(payParams.h5_url)}` })
          // #endif
          // 避免未完成支付时误提示成功，这里直接返回，等待支付完成后的回调/页面再校验订单状态
          uni.showToast({ title: '已跳转至微信支付，请完成支付后返回', icon: 'none' })
          return false
        }
        
        // 支付成功，刷新用户信息与限制
        await this.fetchUserProfile()
        await this.fetchUserLimits()

        uni.showToast({ title: '支付成功，会员已升级', icon: 'success' })
        return true
      } catch (error) {
        console.error('会员升级失败:', error)
        uni.showToast({ title: '支付失败或取消', icon: 'none' })
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