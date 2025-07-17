/**
 * 反馈管理器单元测试
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useFeedback, FeedbackType, FeedbackPriority } from '@/utils/feedbackManager'

describe('FeedbackManager', () => {
  let feedback

  beforeEach(() => {
    feedback = useFeedback()
    vi.clearAllMocks()
  })

  describe('基础反馈功能', () => {
    it('应该能够显示成功提示', () => {
      const message = '操作成功'
      
      feedback.showSuccess(message)
      
      expect(uni.showToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: message,
          icon: 'success'
        })
      )
    })

    it('应该能够显示错误提示', () => {
      const message = '操作失败'
      
      feedback.showError(message)
      
      expect(uni.showToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: message,
          icon: 'none'
        })
      )
    })

    it('应该能够显示警告提示', () => {
      const message = '警告信息'
      
      feedback.showWarning(message)
      
      expect(uni.showToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: message,
          icon: 'none'
        })
      )
    })

    it('应该能够显示信息提示', () => {
      const message = '提示信息'
      
      feedback.showInfo(message)
      
      expect(uni.showToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: message,
          icon: 'none'
        })
      )
    })

    it('应该能够显示加载提示', () => {
      const message = '加载中...'
      
      feedback.showLoading(message)
      
      expect(uni.showLoading).toHaveBeenCalledWith(
        expect.objectContaining({
          title: message,
          mask: true
        })
      )
    })

    it('应该能够隐藏加载提示', () => {
      feedback.hideLoading()
      
      expect(uni.hideLoading).toHaveBeenCalled()
    })
  })

  describe('确认对话框', () => {
    it('应该能够显示确认对话框并返回结果', async () => {
      const title = '确认操作'
      const content = '确定要执行此操作吗？'
      
      // Mock用户点击确认
      uni.showModal.mockImplementation((options) => {
        options.success({ confirm: true, cancel: false })
      })
      
      const result = await feedback.showConfirm(title, content)
      
      expect(uni.showModal).toHaveBeenCalledWith(
        expect.objectContaining({
          title,
          content,
          showCancel: true
        })
      )
      
      expect(result.confirmed).toBe(true)
      expect(result.cancelled).toBe(false)
    })

    it('应该能够处理用户取消确认对话框', async () => {
      const title = '确认操作'
      const content = '确定要执行此操作吗？'
      
      // Mock用户点击取消
      uni.showModal.mockImplementation((options) => {
        options.success({ confirm: false, cancel: true })
      })
      
      const result = await feedback.showConfirm(title, content)
      
      expect(result.confirmed).toBe(false)
      expect(result.cancelled).toBe(true)
    })

    it('应该能够处理确认对话框失败', async () => {
      const title = '确认操作'
      const content = '确定要执行此操作吗？'
      
      // Mock对话框失败
      uni.showModal.mockImplementation((options) => {
        options.fail()
      })
      
      const result = await feedback.showConfirm(title, content)
      
      expect(result.confirmed).toBe(false)
      expect(result.cancelled).toBe(true)
    })
  })

  describe('操作菜单', () => {
    it('应该能够显示操作菜单并返回选择结果', async () => {
      const items = ['选项1', '选项2', '选项3']
      const selectedIndex = 1
      
      // Mock用户选择
      uni.showActionSheet.mockImplementation((options) => {
        options.success({ tapIndex: selectedIndex })
      })
      
      const result = await feedback.showActionSheet(items)
      
      expect(uni.showActionSheet).toHaveBeenCalledWith(
        expect.objectContaining({
          itemList: items
        })
      )
      
      expect(result.selectedIndex).toBe(selectedIndex)
      expect(result.selectedItem).toBe(items[selectedIndex])
      expect(result.cancelled).toBe(false)
    })

    it('应该能够处理用户取消操作菜单', async () => {
      const items = ['选项1', '选项2', '选项3']
      
      // Mock用户取消
      uni.showActionSheet.mockImplementation((options) => {
        options.fail()
      })
      
      const result = await feedback.showActionSheet(items)
      
      expect(result.selectedIndex).toBe(-1)
      expect(result.selectedItem).toBeNull()
      expect(result.cancelled).toBe(true)
    })
  })

  describe('错误消息解析', () => {
    it('应该能够解析字符串错误', () => {
      const errorMessage = '网络连接失败'
      
      feedback.showError(errorMessage)
      
      expect(uni.showToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: errorMessage
        })
      )
    })

    it('应该能够解析Error对象', () => {
      const error = new Error('操作失败')
      
      feedback.showError(error)
      
      expect(uni.showToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: error.message
        })
      )
    })

    it('应该能够解析HTTP错误状态码', () => {
      const error = { status: 404 }
      
      feedback.showError(error)
      
      expect(uni.showToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: '请求的资源不存在'
        })
      )
    })

    it('应该能够解析网络错误', () => {
      const error = { errMsg: 'request:fail timeout' }
      
      feedback.showError(error)
      
      expect(uni.showToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: '网络请求超时，请检查网络连接'
        })
      )
    })

    it('应该为未知错误提供默认消息', () => {
      const error = {}
      
      feedback.showError(error)
      
      expect(uni.showToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: '操作失败，请重试'
        })
      )
    })
  })

  describe('触觉反馈', () => {
    it('应该在成功提示时触发轻微震动', () => {
      feedback.showSuccess('操作成功', { vibrate: true })
      
      expect(uni.vibrateShort).toHaveBeenCalledWith({ type: 'light' })
    })

    it('应该在错误提示时触发强烈震动', () => {
      feedback.showError('操作失败', { vibrate: true })
      
      expect(uni.vibrateShort).toHaveBeenCalledWith({ type: 'heavy' })
    })

    it('应该在警告提示时触发中等震动', () => {
      feedback.showWarning('警告信息', { vibrate: true })
      
      expect(uni.vibrateShort).toHaveBeenCalledWith({ type: 'medium' })
    })
  })

  describe('反馈队列管理', () => {
    it('应该能够清空反馈队列', () => {
      feedback.showLoading('加载中...')
      feedback.clearQueue()
      
      expect(uni.hideLoading).toHaveBeenCalled()
    })

    it('应该能够更新配置', () => {
      const newConfig = {
        maxQueueSize: 20,
        defaultDuration: 3000
      }
      
      feedback.updateConfig(newConfig)
      
      // 配置更新不会抛出错误
      expect(() => feedback.updateConfig(newConfig)).not.toThrow()
    })
  })

  describe('自定义选项', () => {
    it('应该支持自定义持续时间', () => {
      const message = '自定义持续时间'
      const duration = 5000
      
      feedback.showSuccess(message, { duration })
      
      expect(uni.showToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: message,
          duration
        })
      )
    })

    it('应该支持自定义图标', () => {
      const message = '自定义图标'
      const icon = 'loading'
      
      feedback.showInfo(message, { icon })
      
      expect(uni.showToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: message,
          icon
        })
      )
    })

    it('应该支持遮罩层', () => {
      const message = '带遮罩的提示'
      
      feedback.showSuccess(message, { mask: true })
      
      expect(uni.showToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: message,
          mask: true
        })
      )
    })
  })
})