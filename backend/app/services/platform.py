"""
平台展示服务
"""
from typing import Dict, Any, Optional, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PlatformDisplayService:
    """平台展示服务"""
    
    def __init__(self):
        # 平台配置信息
        self.platform_configs = {
            'wechat': {
                'display_name': '微信公众号',
                'short_name': '微信',
                'icon': '🔥',
                'color': '#07C160',
                'background_color': '#E7F8F0',
                'url_prefix': 'https://mp.weixin.qq.com',
                'features': ['rich_text', 'images', 'videos', 'audio'],
                'max_title_length': 64,
                'description': '微信公众平台官方内容'
            },
            'weibo': {
                'display_name': '新浪微博',
                'short_name': '微博',
                'icon': '📱',
                'color': '#FF6B35',
                'background_color': '#FFF0ED',
                'url_prefix': 'https://weibo.com',
                'features': ['short_text', 'images', 'videos', 'hashtags'],
                'max_title_length': 140,
                'description': '新浪微博社交媒体内容'
            },
            'twitter': {
                'display_name': 'Twitter',
                'short_name': 'Twitter',
                'icon': '🐦',
                'color': '#1DA1F2',
                'background_color': '#E8F4FD',
                'url_prefix': 'https://twitter.com',
                'features': ['short_text', 'images', 'videos', 'hashtags', 'mentions'],
                'max_title_length': 280,
                'description': 'Twitter社交媒体内容'
            },
            'mock': {
                'display_name': '测试平台',
                'short_name': '测试',
                'icon': '🧪',
                'color': '#6C757D',
                'background_color': '#F8F9FA',
                'url_prefix': 'https://example.com',
                'features': ['all'],
                'max_title_length': 200,
                'description': '测试平台内容'
            }
        }
    
    def get_platform_info(self, platform: str) -> Dict[str, Any]:
        """
        获取平台信息
        
        Args:
            platform: 平台标识
        
        Returns:
            平台信息字典
        """
        config = self.platform_configs.get(platform.lower(), {})
        
        if not config:
            # 返回默认配置
            return {
                'display_name': platform.title(),
                'short_name': platform.title(),
                'icon': '📄',
                'color': '#6C757D',
                'background_color': '#F8F9FA',
                'url_prefix': '',
                'features': [],
                'max_title_length': 100,
                'description': f'{platform}平台内容'
            }
        
        return config.copy()
    
    def get_platform_display_name(self, platform: str) -> str:
        """获取平台显示名称"""
        config = self.get_platform_info(platform)
        return config['display_name']
    
    def get_platform_short_name(self, platform: str) -> str:
        """获取平台简短名称"""
        config = self.get_platform_info(platform)
        return config['short_name']
    
    def get_platform_icon(self, platform: str) -> str:
        """获取平台图标"""
        config = self.get_platform_info(platform)
        return config['icon']
    
    def get_platform_color(self, platform: str) -> str:
        """获取平台主色调"""
        config = self.get_platform_info(platform)
        return config['color']
    
    def get_platform_badge(self, platform: str, style: str = 'default') -> Dict[str, Any]:
        """
        获取平台徽章信息
        
        Args:
            platform: 平台标识
            style: 徽章样式 (default, compact, minimal)
        
        Returns:
            徽章配置
        """
        config = self.get_platform_info(platform)
        
        badge_config = {
            'text': config['short_name'],
            'icon': config['icon'],
            'color': config['color'],
            'background_color': config['background_color'],
            'platform': platform
        }
        
        if style == 'compact':
            badge_config['text'] = config['icon']
        elif style == 'minimal':
            badge_config = {
                'text': config['short_name'],
                'color': config['color'],
                'platform': platform
            }
        
        return badge_config
    
    def format_content_for_platform(self, content: str, platform: str) -> Dict[str, Any]:
        """
        根据平台特性格式化内容
        
        Args:
            content: 原始内容
            platform: 平台标识
        
        Returns:
            格式化后的内容信息
        """
        config = self.get_platform_info(platform)
        max_length = config['max_title_length']
        
        # 截断过长的内容
        truncated_content = content
        is_truncated = False
        
        if len(content) > max_length:
            truncated_content = content[:max_length-3] + '...'
            is_truncated = True
        
        # 提取平台特定元素
        hashtags = self._extract_hashtags(content) if 'hashtags' in config['features'] else []
        mentions = self._extract_mentions(content) if 'mentions' in config['features'] else []
        
        return {
            'original_content': content,
            'display_content': truncated_content,
            'is_truncated': is_truncated,
            'hashtags': hashtags,
            'mentions': mentions,
            'platform_features': config['features']
        }
    
    def get_supported_platforms(self) -> List[Dict[str, Any]]:
        """获取所有支持的平台列表"""
        platforms = []
        
        for platform_key, config in self.platform_configs.items():
            platform_info = {
                'key': platform_key,
                'display_name': config['display_name'],
                'short_name': config['short_name'],
                'icon': config['icon'],
                'color': config['color'],
                'description': config['description'],
                'features': config['features']
            }
            platforms.append(platform_info)
        
        return platforms
    
    def validate_platform_content(self, content: str, platform: str) -> Dict[str, Any]:
        """
        验证内容是否符合平台规范
        
        Args:
            content: 内容文本
            platform: 平台标识
        
        Returns:
            验证结果
        """
        config = self.get_platform_info(platform)
        issues = []
        
        # 检查长度限制
        if len(content) > config['max_title_length']:
            issues.append({
                'type': 'length_exceeded',
                'message': f'内容长度超过{config["max_title_length"]}字符限制',
                'current_length': len(content),
                'max_length': config['max_title_length']
            })
        
        # 检查特殊字符（根据平台特性）
        if platform == 'wechat' and self._contains_sensitive_words(content):
            issues.append({
                'type': 'sensitive_content',
                'message': '内容可能包含敏感词汇'
            })
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'platform': platform,
            'content_length': len(content)
        }
    
    def generate_platform_link(self, platform: str, account_id: str, article_id: Optional[str] = None) -> str:
        """
        生成平台链接
        
        Args:
            platform: 平台标识
            account_id: 账号ID
            article_id: 文章ID（可选）
        
        Returns:
            平台链接
        """
        config = self.get_platform_info(platform)
        base_url = config['url_prefix']
        
        if not base_url:
            return ''
        
        try:
            if platform == 'wechat':
                if article_id:
                    return f"{base_url}/s/{article_id}"
                return f"{base_url}/profile?id={account_id}"
            
            elif platform == 'weibo':
                if article_id:
                    return f"{base_url}/{account_id}/status/{article_id}"
                return f"{base_url}/u/{account_id}"
            
            elif platform == 'twitter':
                if article_id:
                    return f"{base_url}/{account_id}/status/{article_id}"
                return f"{base_url}/{account_id}"
            
            else:
                # 默认链接格式
                if article_id:
                    return f"{base_url}/{account_id}/{article_id}"
                return f"{base_url}/{account_id}"
                
        except Exception as e:
            logger.error(f"生成平台链接失败: {str(e)}")
            return base_url
    
    def _extract_hashtags(self, content: str) -> List[str]:
        """提取话题标签"""
        import re
        hashtag_pattern = r'#([^#\s]+)#?'
        matches = re.findall(hashtag_pattern, content)
        return list(set(matches))  # 去重
    
    def _extract_mentions(self, content: str) -> List[str]:
        """提取@提及"""
        import re
        mention_pattern = r'@([^\s@]+)'
        matches = re.findall(mention_pattern, content)
        return list(set(matches))  # 去重
    
    def _contains_sensitive_words(self, content: str) -> bool:
        """检查是否包含敏感词（简单实现）"""
        # 这里可以接入专业的敏感词检测服务
        sensitive_words = ['敏感词1', '敏感词2']  # 示例
        content_lower = content.lower()
        return any(word in content_lower for word in sensitive_words)


# 创建服务实例
platform_service = PlatformDisplayService()