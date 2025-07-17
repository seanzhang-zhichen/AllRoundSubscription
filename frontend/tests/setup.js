/**
 * 测试环境设置文件
 */

import { vi } from 'vitest'

// Mock uni-app API
global.uni = {
  // 网络请求
  request: vi.fn(),
  
  // 存储
  setStorageSync: vi.fn(),
  getStorageSync: vi.fn(),
  removeStorageSync: vi.fn(),
  getStorageInfoSync: vi.fn(() => ({
    keys: [],
    currentSize: 0,
    limitSize: 10240
  })),
  
  // 系统信息
  getSystemInfoSync: vi.fn(() => ({
    platform: 'devtools',
    system: 'Windows 10',
    version: '8.0.5',
    SDKVersion: '3.0.0',
    screenWidth: 375,
    screenHeight: 667,
    windowWidth: 375,
    windowHeight: 667
  })),
  
  // 网络状态
  getNetworkType: vi.fn((options) => {
    options?.success?.({ networkType: 'wifi' })
  }),
  onNetworkStatusChange: vi.fn(),
  
  // 页面跳转
  navigateTo: vi.fn(),
  navigateBack: vi.fn(),
  redirectTo: vi.fn(),
  switchTab: vi.fn(),
  reLaunch: vi.fn(),
  
  // 页面滚动
  pageScrollTo: vi.fn(),
  
  // 提示框
  showToast: vi.fn(),
  hideToast: vi.fn(),
  showLoading: vi.fn(),
  hideLoading: vi.fn(),
  showModal: vi.fn(),
  showActionSheet: vi.fn(),
  
  // 图片
  previewImage: vi.fn(),
  getImageInfo: vi.fn(),
  
  // 分享
  share: vi.fn(),
  
  // 下拉刷新
  stopPullDownRefresh: vi.fn(),
  
  // 触觉反馈
  vibrateShort: vi.fn(),
  vibrateLong: vi.fn(),
  
  // 更新管理
  getUpdateManager: vi.fn(() => ({
    onCheckForUpdate: vi.fn(),
    onUpdateReady: vi.fn(),
    onUpdateFailed: vi.fn(),
    applyUpdate: vi.fn()
  })),
  
  // 交叉观察器
  createIntersectionObserver: vi.fn(() => ({
    relativeToViewport: vi.fn().mockReturnThis(),
    observe: vi.fn(),
    disconnect: vi.fn()
  })),
  
  // 应用生命周期
  onAppShow: vi.fn(),
  onAppHide: vi.fn()
}

// Mock getCurrentPages
global.getCurrentPages = vi.fn(() => [
  {
    route: 'pages/index/index',
    options: {}
  }
])

// Mock console methods for testing
global.console = {
  ...console,
  log: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
  debug: vi.fn()
}

// Mock setTimeout and setInterval for testing
vi.stubGlobal('setTimeout', vi.fn((fn, delay) => {
  return setTimeout(fn, delay)
}))

vi.stubGlobal('setInterval', vi.fn((fn, delay) => {
  return setInterval(fn, delay)
}))

vi.stubGlobal('clearTimeout', vi.fn((id) => {
  clearTimeout(id)
}))

vi.stubGlobal('clearInterval', vi.fn((id) => {
  clearInterval(id)
}))

// Mock Date for consistent testing
const mockDate = new Date('2024-01-01T00:00:00.000Z')
vi.setSystemTime(mockDate)

// Mock fetch for API testing
global.fetch = vi.fn()

// Mock ResizeObserver
global.ResizeObserver = vi.fn(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn()
}))

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn()
}))

// 测试前清理
beforeEach(() => {
  // 清理所有 mock 调用记录
  vi.clearAllMocks()
  
  // 重置存储 mock
  uni.getStorageSync.mockReturnValue(null)
  uni.getStorageInfoSync.mockReturnValue({
    keys: [],
    currentSize: 0,
    limitSize: 10240
  })
  
  // 重置网络状态 mock
  uni.getNetworkType.mockImplementation((options) => {
    options?.success?.({ networkType: 'wifi' })
  })
})

// 测试后清理
afterEach(() => {
  vi.clearAllTimers()
})