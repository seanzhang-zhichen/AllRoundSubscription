"""
内容展示优化测试
"""
import pytest
from app.services.image import image_service
from app.services.platform import platform_service
from app.services.refresh import refresh_service


class TestImageService:
    """图片服务测试类"""
    
    def test_is_valid_image_url(self):
        """测试图片URL验证"""
        # 有效的图片URL
        assert image_service._is_valid_image_url("https://example.com/image.jpg")
        assert image_service._is_valid_image_url("https://example.com/photo.png")
        assert image_service._is_valid_image_url("http://test.com/pic.gif")
        
        # 无效的图片URL
        assert not image_service._is_valid_image_url("")
        assert not image_service._is_valid_image_url("not_a_url")
        assert not image_service._is_valid_image_url("https://example.com/document.pdf")
        assert not image_service._is_valid_image_url("ftp://example.com/image.jpg")
    
    def test_is_thumbnail_url(self):
        """测试缩略图URL识别"""
        # 缩略图URL
        assert image_service._is_thumbnail_url("https://example.com/image_thumbnail.jpg")
        assert image_service._is_thumbnail_url("https://example.com/image_small.jpg")
        assert image_service._is_thumbnail_url("https://example.com/thumb_image.jpg")
        
        # 非缩略图URL
        assert not image_service._is_thumbnail_url("https://example.com/image.jpg")
        assert not image_service._is_thumbnail_url("https://example.com/large_image.jpg")
    
    def test_generate_thumbnail_url(self):
        """测试缩略图URL生成"""
        original_url = "https://example.com/image.jpg"
        
        # 默认平台
        thumbnail = image_service.generate_thumbnail_url(original_url)
        assert thumbnail != original_url
        assert "_thumb_" in thumbnail
        
        # 微博平台
        weibo_thumbnail = image_service.generate_thumbnail_url(original_url, "weibo", "small")
        assert weibo_thumbnail != original_url
        
        # 无效URL
        invalid_thumbnail = image_service.generate_thumbnail_url("invalid_url")
        assert invalid_thumbnail == "invalid_url"
    
    def test_process_article_images(self):
        """测试文章图片处理"""
        images = [
            "https://example.com/image1.jpg",
            "https://example.com/image2.png",
            "invalid_url"
        ]
        
        result = image_service.process_article_images(images, "weibo")
        
        assert result['image_count'] == 2  # 只有2个有效图片
        assert result['has_images'] is True
        assert len(result['thumbnail_images']) == 2
        assert result['primary_thumbnail'] != ""
        
        # 测试空图片列表
        empty_result = image_service.process_article_images([])
        assert empty_result['image_count'] == 0
        assert empty_result['has_images'] is False
        assert empty_result['primary_thumbnail'] == ""
    
    def test_optimize_image_loading(self):
        """测试图片加载优化"""
        images = [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg",
            "https://example.com/image3.jpg"
        ]
        
        optimized = image_service.optimize_image_loading(images, lazy_load=True)
        
        assert len(optimized) == 3
        assert optimized[0]['loading'] == 'eager'  # 第一张图片立即加载
        assert optimized[1]['loading'] == 'lazy'   # 后续图片懒加载
        assert optimized[2]['loading'] == 'lazy'
        
        # 测试禁用懒加载
        no_lazy = image_service.optimize_image_loading(images, lazy_load=False)
        assert all(img['loading'] == 'eager' for img in no_lazy)
    
    def test_extract_image_alt(self):
        """测试图片alt文本提取"""
        url1 = "https://example.com/beautiful_sunset.jpg"
        alt1 = image_service._extract_image_alt(url1)
        assert "beautiful sunset" in alt1.lower()
        
        url2 = "https://example.com/image123.png"
        alt2 = image_service._extract_image_alt(url2)
        assert alt2 == "image"
        
        url3 = "https://example.com/"
        alt3 = image_service._extract_image_alt(url3)
        assert alt3 == "图片"


class TestPlatformService:
    """平台服务测试类"""
    
    def test_get_platform_info(self):
        """测试获取平台信息"""
        # 已知平台
        wechat_info = platform_service.get_platform_info("wechat")
        assert wechat_info['display_name'] == "微信公众号"
        assert wechat_info['short_name'] == "微信"
        assert wechat_info['color'] == "#07C160"
        
        weibo_info = platform_service.get_platform_info("weibo")
        assert weibo_info['display_name'] == "新浪微博"
        assert weibo_info['short_name'] == "微博"
        
        # 未知平台
        unknown_info = platform_service.get_platform_info("unknown")
        assert unknown_info['display_name'] == "Unknown"
        assert unknown_info['icon'] == "📄"
    
    def test_get_platform_display_name(self):
        """测试获取平台显示名称"""
        assert platform_service.get_platform_display_name("wechat") == "微信公众号"
        assert platform_service.get_platform_display_name("weibo") == "新浪微博"
        assert platform_service.get_platform_display_name("twitter") == "Twitter"
        assert platform_service.get_platform_display_name("unknown") == "Unknown"
    
    def test_get_platform_badge(self):
        """测试获取平台徽章"""
        # 默认样式
        default_badge = platform_service.get_platform_badge("wechat")
        assert default_badge['text'] == "微信"
        assert default_badge['icon'] == "🔥"
        assert default_badge['color'] == "#07C160"
        
        # 紧凑样式
        compact_badge = platform_service.get_platform_badge("wechat", "compact")
        assert compact_badge['text'] == "🔥"
        
        # 简约样式
        minimal_badge = platform_service.get_platform_badge("wechat", "minimal")
        assert 'background_color' not in minimal_badge
        assert minimal_badge['text'] == "微信"
    
    def test_format_content_for_platform(self):
        """测试平台内容格式化"""
        long_content = "这是一个很长的内容" * 20  # 超过大部分平台限制
        
        # 微信平台
        wechat_formatted = platform_service.format_content_for_platform(long_content, "wechat")
        assert wechat_formatted['is_truncated'] is True
        assert len(wechat_formatted['display_content']) <= 64 + 3  # 64字符 + "..."
        
        # 短内容
        short_content = "短内容"
        short_formatted = platform_service.format_content_for_platform(short_content, "wechat")
        assert short_formatted['is_truncated'] is False
        assert short_formatted['display_content'] == short_content
    
    def test_get_supported_platforms(self):
        """测试获取支持的平台列表"""
        platforms = platform_service.get_supported_platforms()
        
        assert len(platforms) >= 4  # 至少有4个平台
        assert any(p['key'] == 'wechat' for p in platforms)
        assert any(p['key'] == 'weibo' for p in platforms)
        assert any(p['key'] == 'twitter' for p in platforms)
        
        # 验证平台信息完整性
        for platform in platforms:
            assert 'key' in platform
            assert 'display_name' in platform
            assert 'icon' in platform
            assert 'color' in platform
    
    def test_validate_platform_content(self):
        """测试平台内容验证"""
        # 正常内容
        normal_content = "这是正常的内容"
        result = platform_service.validate_platform_content(normal_content, "wechat")
        assert result['is_valid'] is True
        assert len(result['issues']) == 0
        
        # 超长内容
        long_content = "很长的内容" * 50
        long_result = platform_service.validate_platform_content(long_content, "wechat")
        assert long_result['is_valid'] is False
        assert any(issue['type'] == 'length_exceeded' for issue in long_result['issues'])
    
    def test_generate_platform_link(self):
        """测试平台链接生成"""
        # 微信链接
        wechat_link = platform_service.generate_platform_link("wechat", "test_account", "test_article")
        assert "mp.weixin.qq.com" in wechat_link
        assert "test_article" in wechat_link
        
        # 微博链接
        weibo_link = platform_service.generate_platform_link("weibo", "test_user", "123456")
        assert "weibo.com" in weibo_link
        assert "test_user" in weibo_link
        assert "123456" in weibo_link
        
        # 只有账号ID的链接
        account_only_link = platform_service.generate_platform_link("twitter", "test_user")
        assert "twitter.com" in account_only_link
        assert "test_user" in account_only_link
    
    def test_extract_hashtags(self):
        """测试话题标签提取"""
        content = "这是一个包含 #科技# 和 #AI# 话题的内容"
        hashtags = platform_service._extract_hashtags(content)
        
        assert "科技" in hashtags
        assert "AI" in hashtags
        assert len(hashtags) == 2
    
    def test_extract_mentions(self):
        """测试@提及提取"""
        content = "感谢 @张三 和 @李四 的支持"
        mentions = platform_service._extract_mentions(content)
        
        assert "张三" in mentions
        assert "李四" in mentions
        assert len(mentions) == 2


class TestRefreshService:
    """刷新服务测试类"""
    
    async def test_get_refresh_status(self):
        """测试获取刷新状态"""
        status = await refresh_service.get_refresh_status(1)
        
        assert 'can_refresh' in status
        assert 'is_refreshing' in status
        assert 'last_refresh' in status
        assert 'min_interval' in status
        assert isinstance(status['can_refresh'], bool)
        assert isinstance(status['is_refreshing'], bool)
    
    def test_fetch_account_latest_content_mock(self):
        """测试模拟获取账号最新内容"""
        from app.models.account import Account, Platform
        
        # 创建模拟账号
        mock_account = Account(
            id=1,
            name="测试账号",
            platform=Platform.WEIBO,
            account_id="test_123"
        )
        
        # 由于这是异步方法且需要数据库，这里只测试方法存在
        assert hasattr(refresh_service, '_fetch_account_latest_content')
    
    def test_cache_key_generation(self):
        """测试缓存键生成"""
        # 测试刷新服务的缓存键前缀
        assert refresh_service.refresh_cache_prefix == "refresh:"
        assert refresh_service.last_refresh_key == "last_refresh"
        
        # 测试配置参数
        assert refresh_service.min_refresh_interval == 60
        assert refresh_service.refresh_lock_ttl == 300
        assert refresh_service.batch_size == 100


class TestContentDisplayIntegration:
    """内容展示集成测试"""
    
    def test_services_integration(self):
        """测试服务集成"""
        # 测试图片和平台服务的集成
        images = ["https://example.com/image.jpg"]
        platform = "weibo"
        
        # 处理图片
        processed = image_service.process_article_images(images, platform)
        assert processed['has_images'] is True
        
        # 获取平台信息
        platform_info = platform_service.get_platform_info(platform)
        assert platform_info['display_name'] == "新浪微博"
        
        # 验证平台特定的图片处理
        thumbnail_url = image_service.generate_thumbnail_url(images[0], platform)
        assert thumbnail_url != images[0]
    
    def test_content_optimization_workflow(self):
        """测试内容优化工作流"""
        # 模拟文章数据
        article_data = {
            'title': '测试文章标题',
            'content': '这是一篇测试文章的内容，包含了一些文本信息。',
            'images': [
                'https://example.com/image1.jpg',
                'https://example.com/image2.png'
            ],
            'platform': 'wechat'
        }
        
        # 1. 处理图片
        image_result = image_service.process_article_images(
            article_data['images'], 
            article_data['platform']
        )
        assert image_result['image_count'] == 2
        assert image_result['has_images'] is True
        
        # 2. 格式化内容
        content_result = platform_service.format_content_for_platform(
            article_data['content'], 
            article_data['platform']
        )
        assert content_result['is_truncated'] is False
        
        # 3. 获取平台徽章
        badge = platform_service.get_platform_badge(article_data['platform'])
        assert badge['text'] == "微信"
        assert badge['icon'] == "🔥"
        
        # 4. 优化图片加载
        optimized_images = image_service.optimize_image_loading(
            article_data['images'], 
            lazy_load=True
        )
        assert len(optimized_images) == 2
        assert optimized_images[0]['loading'] == 'eager'
        assert optimized_images[1]['loading'] == 'lazy'
    
    def test_platform_specific_features(self):
        """测试平台特定功能"""
        platforms = ['wechat', 'weibo', 'twitter']
        
        for platform in platforms:
            # 获取平台信息
            info = platform_service.get_platform_info(platform)
            assert info['display_name'] is not None
            assert info['color'] is not None
            assert info['icon'] is not None
            
            # 测试图片处理
            test_image = "https://example.com/test.jpg"
            thumbnail = image_service.generate_thumbnail_url(test_image, platform)
            assert thumbnail is not None
            
            # 测试内容格式化
            test_content = "测试内容"
            formatted = platform_service.format_content_for_platform(test_content, platform)
            assert formatted['display_content'] == test_content
            assert formatted['is_truncated'] is False