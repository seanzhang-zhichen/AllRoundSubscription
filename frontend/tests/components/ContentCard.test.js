/**
 * ContentCard 组件单元测试
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ContentCard from '@/components/ContentCard.vue'

// Mock子组件
vi.mock('@/components/LazyImage.vue', () => ({
  default: {
    name: 'LazyImage',
    template: '<div class="mock-lazy-image" :src="src"></div>',
    props: ['src', 'mode', 'width', 'height', 'optimize', 'clickable']
  }
}))

describe('ContentCard', () => {
  let wrapper
  let mockArticle

  beforeEach(() => {
    mockArticle = {
      id: 1,
      title: '测试文章标题',
      summary: '这是一篇测试文章的摘要内容',
      url: 'https://example.com/article/1',
      publish_time: '2024-01-01T12:00:00Z',
      images: ['https://example.com/image1.jpg', 'https://example.com/image2.jpg'],
      is_favorited: false,
      is_read: false,
      view_count: 1000,
      like_count: 50,
      comment_count: 10,
      account: {
        id: 1,
        name: '测试博主',
        platform: 'wechat',
        avatar_url: 'https://example.com/avatar.jpg'
      }
    }

    wrapper = mount(ContentCard, {
      props: {
        article: mockArticle
      },
      global: {
        stubs: {
          LazyImage: true
        }
      }
    })
  })

  afterEach(() => {
    wrapper?.unmount()
  })

  describe('组件渲染', () => {
    it('应该正确渲染文章标题', () => {
      const title = wrapper.find('.article-title')
      expect(title.exists()).toBe(true)
      expect(title.text()).toBe(mockArticle.title)
    })

    it('应该正确渲染文章摘要', () => {
      const summary = wrapper.find('.article-summary')
      expect(summary.exists()).toBe(true)
      expect(summary.text()).toBe(mockArticle.summary)
    })

    it('应该正确渲染博主信息', () => {
      const authorName = wrapper.find('.author-name')
      expect(authorName.exists()).toBe(true)
      expect(authorName.text()).toBe(mockArticle.account.name)
    })

    it('应该正确渲染发布时间', () => {
      const publishTime = wrapper.find('.publish-time')
      expect(publishTime.exists()).toBe(true)
      expect(publishTime.text()).toBeTruthy()
    })

    it('应该正确渲染平台标签', () => {
      const platformTag = wrapper.find('.platform-tag')
      expect(platformTag.exists()).toBe(true)
      expect(platformTag.classes()).toContain('platform-wechat')
    })
  })

  describe('图片展示', () => {
    it('应该在有图片时显示图片容器', () => {
      const imagesContainer = wrapper.find('.images-container')
      expect(imagesContainer.exists()).toBe(true)
    })

    it('应该根据图片数量应用正确的网格样式', () => {
      const imageGrid = wrapper.find('.image-grid')
      expect(imageGrid.exists()).toBe(true)
      
      // 2张图片应该使用double网格
      expect(imageGrid.classes()).toContain('grid-double')
    })

    it('应该在没有图片时不显示图片容器', async () => {
      await wrapper.setProps({
        article: {
          ...mockArticle,
          images: []
        }
      })

      const imagesContainer = wrapper.find('.images-container')
      expect(imagesContainer.exists()).toBe(false)
    })

    it('应该在图片超过9张时显示更多图片提示', async () => {
      const manyImages = Array.from({ length: 12 }, (_, i) => `https://example.com/image${i}.jpg`)
      
      await wrapper.setProps({
        article: {
          ...mockArticle,
          images: manyImages
        }
      })

      const moreImages = wrapper.find('.more-images')
      expect(moreImages.exists()).toBe(true)
      expect(moreImages.find('.more-text').text()).toBe('+3')
    })
  })

  describe('统计信息', () => {
    it('应该在showStats为true时显示统计信息', () => {
      const cardFooter = wrapper.find('.card-footer')
      expect(cardFooter.exists()).toBe(true)
      
      const statsItems = wrapper.findAll('.stats-item')
      expect(statsItems).toHaveLength(3) // 浏览、点赞、评论
    })

    it('应该在showStats为false时隐藏统计信息', async () => {
      await wrapper.setProps({ showStats: false })
      
      const cardFooter = wrapper.find('.card-footer')
      expect(cardFooter.exists()).toBe(false)
    })

    it('应该正确格式化大数字', () => {
      // 测试数字格式化逻辑
      const component = wrapper.vm
      
      expect(component.formatNumber(999)).toBe('999')
      expect(component.formatNumber(1500)).toBe('1.5k')
      expect(component.formatNumber(15000)).toBe('1.5w')
      expect(component.formatNumber(150000)).toBe('15w')
    })
  })

  describe('交互功能', () => {
    it('应该在点击卡片时触发click事件', async () => {
      await wrapper.find('.content-card').trigger('click')
      
      expect(wrapper.emitted('click')).toBeTruthy()
      expect(wrapper.emitted('click')[0]).toEqual([mockArticle])
    })

    it('应该在点击收藏按钮时触发favorite事件', async () => {
      const favoriteBtn = wrapper.find('.action-btn')
      await favoriteBtn.trigger('click')
      
      expect(wrapper.emitted('favorite')).toBeTruthy()
      expect(wrapper.emitted('favorite')[0]).toEqual([mockArticle])
    })

    it('应该在点击分享按钮时触发share事件', async () => {
      const shareBtn = wrapper.findAll('.action-btn')[1]
      await shareBtn.trigger('click')
      
      expect(wrapper.emitted('share')).toBeTruthy()
      expect(wrapper.emitted('share')[0]).toEqual([mockArticle])
    })

    it('应该在点击图片时调用预览功能', async () => {
      const mockPreviewImage = vi.fn()
      uni.previewImage = mockPreviewImage
      
      const component = wrapper.vm
      component.previewImage('https://example.com/image1.jpg', mockArticle.images)
      
      expect(mockPreviewImage).toHaveBeenCalledWith({
        current: 'https://example.com/image1.jpg',
        urls: mockArticle.images
      })
    })
  })

  describe('时间格式化', () => {
    it('应该正确格式化刚刚发布的时间', () => {
      const component = wrapper.vm
      const now = new Date()
      
      const result = component.formatTime(now.toISOString())
      expect(result).toBe('刚刚')
    })

    it('应该正确格式化分钟前的时间', () => {
      const component = wrapper.vm
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000)
      
      const result = component.formatTime(fiveMinutesAgo.toISOString())
      expect(result).toBe('5分钟前')
    })

    it('应该正确格式化小时前的时间', () => {
      const component = wrapper.vm
      const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000)
      
      const result = component.formatTime(twoHoursAgo.toISOString())
      expect(result).toBe('2小时前')
    })

    it('应该正确格式化天前的时间', () => {
      const component = wrapper.vm
      const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000)
      
      const result = component.formatTime(threeDaysAgo.toISOString())
      expect(result).toBe('3天前')
    })

    it('应该正确格式化超过一周的时间', () => {
      const component = wrapper.vm
      const longTimeAgo = new Date('2023-01-01T12:00:00Z')
      
      const result = component.formatTime(longTimeAgo.toISOString())
      expect(result).toBe(longTimeAgo.toLocaleDateString())
    })
  })

  describe('平台信息', () => {
    it('应该正确获取微信平台名称', () => {
      const component = wrapper.vm
      expect(component.getPlatformName('wechat')).toBe('微信')
    })

    it('应该正确获取微博平台名称', () => {
      const component = wrapper.vm
      expect(component.getPlatformName('weibo')).toBe('微博')
    })

    it('应该正确获取推特平台名称', () => {
      const component = wrapper.vm
      expect(component.getPlatformName('twitter')).toBe('推特')
    })

    it('应该为未知平台返回默认名称', () => {
      const component = wrapper.vm
      expect(component.getPlatformName('unknown')).toBe('其他')
    })
  })

  describe('收藏状态', () => {
    it('应该在文章已收藏时显示收藏状态', async () => {
      await wrapper.setProps({
        article: {
          ...mockArticle,
          is_favorited: true
        }
      })

      const favoriteIcon = wrapper.find('.action-icon.favorited')
      expect(favoriteIcon.exists()).toBe(true)
    })

    it('应该在文章未收藏时不显示收藏状态', () => {
      const favoriteIcon = wrapper.find('.action-icon.favorited')
      expect(favoriteIcon.exists()).toBe(false)
    })
  })

  describe('边界情况处理', () => {
    it('应该处理缺少博主信息的情况', async () => {
      await wrapper.setProps({
        article: {
          ...mockArticle,
          account: null
        }
      })

      const authorName = wrapper.find('.author-name')
      expect(authorName.text()).toBe('未知博主')
    })

    it('应该处理缺少摘要的情况', async () => {
      await wrapper.setProps({
        article: {
          ...mockArticle,
          summary: null
        }
      })

      const summary = wrapper.find('.article-summary')
      expect(summary.exists()).toBe(false)
    })

    it('应该处理缺少统计数据的情况', async () => {
      await wrapper.setProps({
        article: {
          ...mockArticle,
          view_count: null,
          like_count: null,
          comment_count: null
        }
      })

      const statsItems = wrapper.findAll('.stats-text')
      statsItems.forEach(item => {
        expect(item.text()).toBe('0')
      })
    })
  })
})