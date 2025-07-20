/**
 * 微信登录状态监控工具
 * 用于监控和诊断微信登录问题
 */

class WechatLoginMonitor {
  constructor() {
    this.loginAttempts = []
    this.maxAttempts = 50 // 保留最近50次登录记录
    this.errorStats = {}
  }

  /**
   * 记录登录尝试
   * @param {Object} attempt - 登录尝试信息
   */
  recordLoginAttempt(attempt) {
    const record = {
      timestamp: new Date().toISOString(),
      id: this.generateAttemptId(),
      ...attempt
    }

    this.loginAttempts.unshift(record)
    
    // 保持记录数量限制
    if (this.loginAttempts.length > this.maxAttempts) {
      this.loginAttempts = this.loginAttempts.slice(0, this.maxAttempts)
    }

    // 更新错误统计
    if (attempt.success === false && attempt.error) {
      this.updateErrorStats(attempt.error)
    }

    // 保存到本地存储
    this.saveToStorage()

    console.log('登录尝试记录:', record)
  }

  /**
   * 记录成功的登录
   * @param {Object} details - 登录详情
   */
  recordSuccess(details = {}) {
    this.recordLoginAttempt({
      success: true,
      type: 'wechat_login',
      duration: details.duration || 0,
      codeLength: details.codeLength || 0,
      retryCount: details.retryCount || 0,
      mode: details.mode || 'interactive'
    })
  }

  /**
   * 记录失败的登录
   * @param {Object} details - 失败详情
   */
  recordFailure(details = {}) {
    this.recordLoginAttempt({
      success: false,
      type: 'wechat_login',
      error: details.error || 'unknown_error',
      errorCode: details.errorCode,
      errorMessage: details.errorMessage || '',
      duration: details.duration || 0,
      codeLength: details.codeLength || 0,
      retryCount: details.retryCount || 0,
      mode: details.mode || 'interactive',
      step: details.step || 'unknown' // 失败发生在哪个步骤
    })
  }

  /**
   * 记录Code获取
   * @param {Object} details - Code获取详情
   */
  recordCodeAcquisition(details = {}) {
    this.recordLoginAttempt({
      success: details.success,
      type: 'code_acquisition',
      codeLength: details.codeLength || 0,
      duration: details.duration || 0,
      error: details.error,
      errorMessage: details.errorMessage || ''
    })
  }

  /**
   * 记录API调用
   * @param {Object} details - API调用详情
   */
  recordApiCall(details = {}) {
    this.recordLoginAttempt({
      success: details.success,
      type: 'api_call',
      endpoint: details.endpoint || '/auth/login',
      statusCode: details.statusCode,
      duration: details.duration || 0,
      error: details.error,
      errorMessage: details.errorMessage || '',
      retryCount: details.retryCount || 0
    })
  }

  /**
   * 更新错误统计
   * @param {string} error - 错误类型
   */
  updateErrorStats(error) {
    if (!this.errorStats[error]) {
      this.errorStats[error] = {
        count: 0,
        firstOccurrence: new Date().toISOString(),
        lastOccurrence: new Date().toISOString()
      }
    }

    this.errorStats[error].count++
    this.errorStats[error].lastOccurrence = new Date().toISOString()
  }

  /**
   * 生成尝试ID
   */
  generateAttemptId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2)
  }

  /**
   * 获取登录统计信息
   */
  getLoginStats() {
    const total = this.loginAttempts.length
    const successful = this.loginAttempts.filter(a => a.success === true).length
    const failed = this.loginAttempts.filter(a => a.success === false).length
    const successRate = total > 0 ? (successful / total * 100).toFixed(2) : 0

    // 最近24小时的统计
    const last24Hours = new Date(Date.now() - 24 * 60 * 60 * 1000)
    const recent = this.loginAttempts.filter(a => new Date(a.timestamp) > last24Hours)
    const recentSuccessful = recent.filter(a => a.success === true).length
    const recentFailed = recent.filter(a => a.success === false).length

    return {
      total: {
        attempts: total,
        successful,
        failed,
        successRate: `${successRate}%`
      },
      last24Hours: {
        attempts: recent.length,
        successful: recentSuccessful,
        failed: recentFailed,
        successRate: recent.length > 0 ? `${(recentSuccessful / recent.length * 100).toFixed(2)}%` : '0%'
      },
      errorStats: this.errorStats,
      mostCommonErrors: this.getMostCommonErrors()
    }
  }

  /**
   * 获取最常见的错误
   */
  getMostCommonErrors() {
    const errors = Object.entries(this.errorStats)
      .sort((a, b) => b[1].count - a[1].count)
      .slice(0, 5)
      .map(([error, stats]) => ({
        error,
        count: stats.count,
        lastOccurrence: stats.lastOccurrence
      }))

    return errors
  }

  /**
   * 获取最近的登录尝试
   * @param {number} limit - 限制数量
   */
  getRecentAttempts(limit = 10) {
    return this.loginAttempts.slice(0, limit)
  }

  /**
   * 检查是否存在频繁失败
   */
  checkForFrequentFailures() {
    const recentAttempts = this.loginAttempts.slice(0, 10) // 最近10次
    const recentFailures = recentAttempts.filter(a => a.success === false)

    if (recentFailures.length >= 5) {
      return {
        hasFrequentFailures: true,
        failureCount: recentFailures.length,
        totalAttempts: recentAttempts.length,
        commonErrors: this.getCommonErrorsInAttempts(recentFailures)
      }
    }

    return {
      hasFrequentFailures: false
    }
  }

  /**
   * 获取尝试中的常见错误
   * @param {Array} attempts - 尝试记录
   */
  getCommonErrorsInAttempts(attempts) {
    const errorCounts = {}
    
    attempts.forEach(attempt => {
      if (attempt.error) {
        errorCounts[attempt.error] = (errorCounts[attempt.error] || 0) + 1
      }
    })

    return Object.entries(errorCounts)
      .sort((a, b) => b[1] - a[1])
      .map(([error, count]) => ({ error, count }))
  }

  /**
   * 生成诊断报告
   */
  generateDiagnosticReport() {
    const stats = this.getLoginStats()
    const frequentFailures = this.checkForFrequentFailures()
    const recentAttempts = this.getRecentAttempts(5)

    const report = {
      timestamp: new Date().toISOString(),
      summary: {
        totalAttempts: stats.total.attempts,
        successRate: stats.total.successRate,
        hasFrequentFailures: frequentFailures.hasFrequentFailures
      },
      statistics: stats,
      frequentFailures,
      recentAttempts,
      recommendations: this.generateRecommendations(stats, frequentFailures)
    }

    console.log('微信登录诊断报告:', report)
    return report
  }

  /**
   * 生成建议
   * @param {Object} stats - 统计信息
   * @param {Object} frequentFailures - 频繁失败信息
   */
  generateRecommendations(stats, frequentFailures) {
    const recommendations = []

    // 检查成功率
    const successRate = parseFloat(stats.total.successRate)
    if (successRate < 80) {
      recommendations.push({
        type: 'low_success_rate',
        message: '登录成功率较低，建议检查网络连接和微信配置',
        priority: 'high'
      })
    }

    // 检查常见错误
    if (stats.mostCommonErrors.length > 0) {
      const topError = stats.mostCommonErrors[0]
      if (topError.error.includes('40029') || topError.error.includes('invalid_code')) {
        recommendations.push({
          type: 'invalid_code_error',
          message: '频繁出现无效code错误，建议优化code获取和传递流程',
          priority: 'high'
        })
      }
    }

    // 检查频繁失败
    if (frequentFailures.hasFrequentFailures) {
      recommendations.push({
        type: 'frequent_failures',
        message: '最近登录失败频繁，建议暂停自动登录并检查配置',
        priority: 'critical'
      })
    }

    return recommendations
  }

  /**
   * 保存到本地存储
   */
  saveToStorage() {
    try {
      const data = {
        loginAttempts: this.loginAttempts,
        errorStats: this.errorStats,
        lastUpdated: new Date().toISOString()
      }
      
      uni.setStorageSync('wechat_login_monitor', JSON.stringify(data))
    } catch (error) {
      console.error('保存登录监控数据失败:', error)
    }
  }

  /**
   * 从本地存储加载
   */
  loadFromStorage() {
    try {
      const data = uni.getStorageSync('wechat_login_monitor')
      if (data) {
        const parsed = JSON.parse(data)
        this.loginAttempts = parsed.loginAttempts || []
        this.errorStats = parsed.errorStats || {}
      }
    } catch (error) {
      console.error('加载登录监控数据失败:', error)
    }
  }

  /**
   * 清除监控数据
   */
  clearData() {
    this.loginAttempts = []
    this.errorStats = {}
    
    try {
      uni.removeStorageSync('wechat_login_monitor')
    } catch (error) {
      console.error('清除登录监控数据失败:', error)
    }
  }

  /**
   * 导出监控数据
   */
  exportData() {
    return {
      loginAttempts: this.loginAttempts,
      errorStats: this.errorStats,
      statistics: this.getLoginStats(),
      diagnosticReport: this.generateDiagnosticReport(),
      exportTime: new Date().toISOString()
    }
  }
}

// 创建全局实例
const wechatLoginMonitor = new WechatLoginMonitor()

// 初始化时加载数据
wechatLoginMonitor.loadFromStorage()

export default wechatLoginMonitor
export { WechatLoginMonitor }