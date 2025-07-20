/**
 * API请求工具类
 * 提供统一的HTTP请求接口，包含拦截器和错误处理
 * 集成性能监控功能
 */

import performanceMonitor from './performanceMonitor'

// API基础配置
const API_CONFIG = {
  baseURL: (typeof process !== 'undefined' && process.env && process.env.NODE_ENV === 'production')
    ? 'https://your-production-api.com/api/v1' 
    : 'http://localhost:8000/api/v1', // 根据环境切换API地址
  timeout: 10000, // 请求超时时间
  header: {
    'Content-Type': 'application/json'
  }
}

/**
 * HTTP请求类
 */
class Request {
  constructor(config = {}) {
    this.config = { ...API_CONFIG, ...config }
    this.interceptors = {
      request: [],
      response: []
    }
    
    // 添加默认拦截器
    this.setupDefaultInterceptors()
  }
  
  /**
   * 设置默认拦截器
   */
  setupDefaultInterceptors() {
    // 请求拦截器 - 添加认证token
    this.interceptors.request.push((config) => {
      const token = uni.getStorageSync('token')
      if (token) {
        config.header = {
          ...config.header,
          'Authorization': `Bearer ${token}`
        }
        console.log('添加认证令牌到请求头')
      } else {
        console.warn('未找到认证令牌，请求可能失败')
      }
      
      // 添加请求ID用于调试
      config.header['X-Request-ID'] = this.generateRequestId()
      
      console.log('Request:', {
        url: config.url,
        method: config.method,
        hasToken: !!token,
        headers: config.header
      })
      return config
    })
    
    // 响应拦截器 - 统一错误处理
    this.interceptors.response.push([
      (response) => {
        console.log('Response:', response)
        
        // 检查HTTP状态码
        if (response.statusCode >= 200 && response.statusCode < 300) {
          const data = response.data
          
          // 检查业务状态码
          if (data && data.code === 200) {
            // 对于分页响应，返回完整的响应对象（包含data, total, page等）
            // 对于普通响应，返回data字段
            if (data.total !== undefined && data.page !== undefined) {
              return data // 返回完整的分页响应
            } else {
              return data.data // 返回数据部分
            }
          } else if (data && data.code !== undefined) {
            return Promise.reject(new Error(data.message || '请求失败'))
          } else {
            // 如果没有标准的业务状态码，直接返回数据
            return data
          }
        } else {
          return Promise.reject(new Error(`HTTP ${response.statusCode}: ${response.errMsg}`))
        }
      },
      (error) => {
        console.error('Request Error:', error)
        
        // 处理不同类型的错误
        if (error.errMsg) {
          if (error.errMsg.includes('timeout')) {
            this.showError('请求超时，请检查网络连接')
          } else if (error.errMsg.includes('fail')) {
            this.showError('网络连接失败，请检查网络设置')
          } else {
            this.showError('请求失败，请稍后重试')
          }
        }
        
        return Promise.reject(error)
      }
    ])
  }
  
  /**
   * 生成请求ID
   */
  generateRequestId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2)
  }
  
  /**
   * 显示错误提示
   */
  showError(message) {
    uni.showToast({
      title: message,
      icon: 'none',
      duration: 2000
    })
  }
  
  /**
   * 执行请求
   */
  async request(options) {
    // 合并配置
    const config = {
      ...this.config,
      ...options,
      header: {
        ...this.config.header,
        ...options.header
      }
    }
    
    // 记录请求开始时间
    const startTime = Date.now()
    const fullUrl = config.url.startsWith('http') ? config.url : `${config.baseURL || this.config.baseURL}${config.url}`
    
    try {
      // 执行请求拦截器
      let processedConfig = config
      for (const interceptor of this.interceptors.request) {
        processedConfig = interceptor(processedConfig) || processedConfig
      }
      
      // 发送请求
      const response = await new Promise((resolve, reject) => {
        uni.request({
          ...processedConfig,
          url: fullUrl, // 使用完整的URL
          success: resolve,
          fail: reject
        })
      })
      
      // 记录请求结束时间和性能指标
      const endTime = Date.now()
      const responseSize = this.calculateResponseSize(response.data)
      
      performanceMonitor.recordApiRequest(
        fullUrl,
        config.method || 'GET',
        startTime,
        endTime,
        response.statusCode,
        responseSize
      )
      
      // 执行响应拦截器
      let processedResponse = response
      for (const interceptor of this.interceptors.response) {
        try {
          // 检查拦截器格式，支持函数和数组两种格式
          if (typeof interceptor === 'function') {
            processedResponse = await interceptor(processedResponse)
          } else if (Array.isArray(interceptor) && typeof interceptor[0] === 'function') {
            processedResponse = await interceptor[0](processedResponse)
          }
          break
        } catch (error) {
          // 处理错误拦截器
          if (Array.isArray(interceptor) && typeof interceptor[1] === 'function') {
            return interceptor[1](error)
          }
          throw error
        }
      }
      
      return processedResponse
      
    } catch (error) {
      // 记录请求失败的性能指标
      const endTime = Date.now()
      performanceMonitor.recordApiRequest(
        fullUrl,
        config.method || 'GET',
        startTime,
        endTime,
        error.statusCode || 0,
        0
      )
      
      // 记录错误到性能监控
      performanceMonitor.recordError(error, {
        url: fullUrl,
        method: config.method || 'GET',
        requestData: config.data
      })
      
      // 执行错误拦截器
      for (const interceptor of this.interceptors.response) {
        if (Array.isArray(interceptor) && typeof interceptor[1] === 'function') {
          try {
            return await interceptor[1](error)
          } catch (e) {
            // 继续抛出错误
          }
        }
      }
      throw error
    }
  }

  /**
   * 计算响应大小（估算）
   * @param {*} data - 响应数据
   */
  calculateResponseSize(data) {
    try {
      return JSON.stringify(data).length * 2 // 粗略估算，每个字符2字节
    } catch (error) {
      return 0
    }
  }
  
  /**
   * GET请求
   */
  get(url, params = {}, options = {}) {
    return this.request({
      url,
      method: 'GET',
      data: params,
      ...options
    })
  }
  
  /**
   * POST请求
   */
  post(url, data = {}, options = {}) {
    return this.request({
      url,
      method: 'POST',
      data,
      ...options
    })
  }
  
  /**
   * PUT请求
   */
  put(url, data = {}, options = {}) {
    return this.request({
      url,
      method: 'PUT',
      data,
      ...options
    })
  }
  
  /**
   * DELETE请求
   */
  delete(url, params = {}, options = {}) {
    return this.request({
      url,
      method: 'DELETE',
      data: params,
      ...options
    })
  }
  
  /**
   * 添加请求拦截器
   */
  addRequestInterceptor(interceptor) {
    this.interceptors.request.push(interceptor)
  }
  
  /**
   * 添加响应拦截器
   */
  addResponseInterceptor(onFulfilled, onRejected) {
    this.interceptors.response.push([onFulfilled, onRejected])
  }
}

// 创建默认实例
const request = new Request()

// 导出实例和类
export default request
export { Request }