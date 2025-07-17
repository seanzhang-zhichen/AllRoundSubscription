/**
 * 通用工具函数
 */

/**
 * 格式化时间
 * @param {string|Date} time 时间
 * @param {string} format 格式 'YYYY-MM-DD HH:mm:ss'
 * @returns {string} 格式化后的时间字符串
 */
export function formatTime(time, format = 'YYYY-MM-DD HH:mm:ss') {
  const date = new Date(time)
  
  if (isNaN(date.getTime())) {
    return ''
  }
  
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  
  return format
    .replace('YYYY', year)
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds)
}

/**
 * 相对时间格式化
 * @param {string|Date} time 时间
 * @returns {string} 相对时间字符串
 */
export function formatRelativeTime(time) {
  const date = new Date(time)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  if (isNaN(date.getTime())) {
    return ''
  }
  
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  const week = 7 * day
  const month = 30 * day
  const year = 365 * day
  
  if (diff < minute) {
    return '刚刚'
  } else if (diff < hour) {
    return `${Math.floor(diff / minute)}分钟前`
  } else if (diff < day) {
    return `${Math.floor(diff / hour)}小时前`
  } else if (diff < week) {
    return `${Math.floor(diff / day)}天前`
  } else if (diff < month) {
    return `${Math.floor(diff / week)}周前`
  } else if (diff < year) {
    return `${Math.floor(diff / month)}个月前`
  } else {
    return `${Math.floor(diff / year)}年前`
  }
}

/**
 * 防抖函数
 * @param {Function} func 要防抖的函数
 * @param {number} delay 延迟时间
 * @returns {Function} 防抖后的函数
 */
export function debounce(func, delay = 300) {
  let timeoutId
  return function (...args) {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => func.apply(this, args), delay)
  }
}

/**
 * 节流函数
 * @param {Function} func 要节流的函数
 * @param {number} delay 延迟时间
 * @returns {Function} 节流后的函数
 */
export function throttle(func, delay = 300) {
  let lastTime = 0
  return function (...args) {
    const now = Date.now()
    if (now - lastTime >= delay) {
      lastTime = now
      func.apply(this, args)
    }
  }
}

/**
 * 深拷贝
 * @param {any} obj 要拷贝的对象
 * @returns {any} 拷贝后的对象
 */
export function deepClone(obj) {
  if (obj === null || typeof obj !== 'object') {
    return obj
  }
  
  if (obj instanceof Date) {
    return new Date(obj.getTime())
  }
  
  if (obj instanceof Array) {
    return obj.map(item => deepClone(item))
  }
  
  if (typeof obj === 'object') {
    const cloned = {}
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        cloned[key] = deepClone(obj[key])
      }
    }
    return cloned
  }
  
  return obj
}

/**
 * 生成随机字符串
 * @param {number} length 长度
 * @returns {string} 随机字符串
 */
export function generateRandomString(length = 8) {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  let result = ''
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

/**
 * 验证手机号
 * @param {string} phone 手机号
 * @returns {boolean} 是否有效
 */
export function validatePhone(phone) {
  const phoneRegex = /^1[3-9]\d{9}$/
  return phoneRegex.test(phone)
}

/**
 * 验证邮箱
 * @param {string} email 邮箱
 * @returns {boolean} 是否有效
 */
export function validateEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

/**
 * 格式化文件大小
 * @param {number} bytes 字节数
 * @returns {string} 格式化后的大小
 */
export function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/**
 * 获取URL参数
 * @param {string} name 参数名
 * @param {string} url URL字符串
 * @returns {string|null} 参数值
 */
export function getUrlParam(name, url = window.location.href) {
  const regex = new RegExp('[?&]' + name + '=([^&#]*)', 'i')
  const match = regex.exec(url)
  return match ? decodeURIComponent(match[1]) : null
}

/**
 * 设置页面标题
 * @param {string} title 标题
 */
export function setPageTitle(title) {
  uni.setNavigationBarTitle({
    title: title
  })
}

/**
 * 复制到剪贴板
 * @param {string} text 要复制的文本
 * @returns {Promise<boolean>} 是否成功
 */
export function copyToClipboard(text) {
  return new Promise((resolve) => {
    uni.setClipboardData({
      data: text,
      success: () => {
        uni.showToast({
          title: '复制成功',
          icon: 'success'
        })
        resolve(true)
      },
      fail: () => {
        uni.showToast({
          title: '复制失败',
          icon: 'none'
        })
        resolve(false)
      }
    })
  })
}

/**
 * 预览图片
 * @param {string|Array} urls 图片URL或URL数组
 * @param {number} current 当前图片索引
 */
export function previewImage(urls, current = 0) {
  const urlArray = Array.isArray(urls) ? urls : [urls]
  
  uni.previewImage({
    urls: urlArray,
    current: current
  })
}

/**
 * 拨打电话
 * @param {string} phoneNumber 电话号码
 */
export function makePhoneCall(phoneNumber) {
  uni.makePhoneCall({
    phoneNumber: phoneNumber
  })
}

/**
 * 获取当前页面路径
 * @returns {string} 页面路径
 */
export function getCurrentPagePath() {
  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1]
  return currentPage ? currentPage.route : ''
}

/**
 * 页面跳转
 * @param {string} url 页面路径
 * @param {string} type 跳转类型 navigate|redirect|reLaunch|switchTab
 */
export function navigateTo(url, type = 'navigate') {
  const methods = {
    navigate: uni.navigateTo,
    redirect: uni.redirectTo,
    reLaunch: uni.reLaunch,
    switchTab: uni.switchTab
  }
  
  const method = methods[type] || uni.navigateTo
  method({ url })
}

/**
 * 显示加载提示
 * @param {string} title 提示文字
 * @param {boolean} mask 是否显示透明蒙层
 */
export function showLoading(title = '加载中...', mask = true) {
  uni.showLoading({
    title,
    mask
  })
}

/**
 * 隐藏加载提示
 */
export function hideLoading() {
  uni.hideLoading()
}

/**
 * 显示消息提示
 * @param {string} title 提示文字
 * @param {string} icon 图标类型
 * @param {number} duration 显示时长
 */
export function showToast(title, icon = 'none', duration = 2000) {
  uni.showToast({
    title,
    icon,
    duration
  })
}

/**
 * 存储数据
 * @param {string} key 键名
 * @param {any} data 数据
 * @returns {boolean} 是否成功
 */
export function setStorage(key, data) {
  try {
    uni.setStorageSync(key, data)
    return true
  } catch (error) {
    console.error('存储数据失败:', error)
    return false
  }
}

/**
 * 获取存储数据
 * @param {string} key 键名
 * @param {any} defaultValue 默认值
 * @returns {any} 数据
 */
export function getStorage(key, defaultValue = null) {
  try {
    const data = uni.getStorageSync(key)
    return data !== '' ? data : defaultValue
  } catch (error) {
    console.error('获取存储数据失败:', error)
    return defaultValue
  }
}

/**
 * 删除存储数据
 * @param {string} key 键名
 * @returns {boolean} 是否成功
 */
export function removeStorage(key) {
  try {
    uni.removeStorageSync(key)
    return true
  } catch (error) {
    console.error('删除存储数据失败:', error)
    return false
  }
}