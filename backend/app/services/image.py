"""
图片处理服务
"""
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse, parse_qs
import re
import logging

logger = logging.getLogger(__name__)


class ImageService:
    """图片处理服务"""
    
    def __init__(self):
        # 支持的图片格式
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
        
        # 平台特定的缩略图规则
        self.thumbnail_rules = {
            'weibo': {
                'pattern': r'(.*?)/(.*?)\.jpg',
                'thumbnail_suffix': '_thumbnail',
                'sizes': ['small', 'medium', 'large']
            },
            'wechat': {
                'pattern': r'(.*?)/(.*?)\.jpg',
                'thumbnail_suffix': '_s',
                'sizes': ['s', 'm', 'l']
            },
            'twitter': {
                'pattern': r'(.*?)/(.*?)\.jpg',
                'thumbnail_suffix': '_small',
                'sizes': ['small', 'medium', 'large']
            }
        }
    
    def generate_thumbnail_url(self, original_url: str, platform: str = 'default', size: str = 'medium') -> str:
        """
        生成缩略图URL
        
        Args:
            original_url: 原始图片URL
            platform: 平台类型
            size: 缩略图尺寸
        
        Returns:
            缩略图URL
        """
        try:
            if not original_url or not self._is_valid_image_url(original_url):
                return original_url
            
            # 如果已经是缩略图，直接返回
            if self._is_thumbnail_url(original_url):
                return original_url
            
            # 根据平台生成缩略图URL
            if platform in self.thumbnail_rules:
                return self._generate_platform_thumbnail(original_url, platform, size)
            
            # 默认缩略图处理
            return self._generate_default_thumbnail(original_url, size)
            
        except Exception as e:
            logger.error(f"生成缩略图URL失败: {str(e)}, 原始URL: {original_url}")
            return original_url
    
    def process_article_images(self, images: List[str], platform: str = 'default') -> Dict[str, Any]:
        """
        处理文章图片列表
        
        Args:
            images: 图片URL列表
            platform: 平台类型
        
        Returns:
            处理后的图片信息
        """
        if not images:
            return {
                'original_images': [],
                'thumbnail_images': [],
                'image_count': 0,
                'has_images': False,
                'primary_thumbnail': ''
            }
        
        try:
            # 过滤有效图片
            valid_images = [img for img in images if self._is_valid_image_url(img)]
            
            # 生成缩略图
            thumbnail_images = []
            for img_url in valid_images:
                thumbnail_url = self.generate_thumbnail_url(img_url, platform, 'small')
                thumbnail_images.append({
                    'original': img_url,
                    'thumbnail': thumbnail_url,
                    'alt': self._extract_image_alt(img_url)
                })
            
            return {
                'original_images': valid_images,
                'thumbnail_images': thumbnail_images,
                'image_count': len(valid_images),
                'has_images': len(valid_images) > 0,
                'primary_thumbnail': thumbnail_images[0]['thumbnail'] if thumbnail_images else ''
            }
            
        except Exception as e:
            logger.error(f"处理文章图片失败: {str(e)}")
            return {
                'original_images': images,
                'thumbnail_images': [],
                'image_count': len(images),
                'has_images': len(images) > 0,
                'primary_thumbnail': images[0] if images else ''
            }
    
    def optimize_image_loading(self, images: List[str], lazy_load: bool = True) -> List[Dict[str, Any]]:
        """
        优化图片加载
        
        Args:
            images: 图片URL列表
            lazy_load: 是否启用懒加载
        
        Returns:
            优化后的图片配置
        """
        optimized_images = []
        
        for i, img_url in enumerate(images):
            if not self._is_valid_image_url(img_url):
                continue
            
            img_config = {
                'src': img_url,
                'alt': self._extract_image_alt(img_url),
                'loading': 'lazy' if lazy_load and i > 0 else 'eager',  # 第一张图片立即加载
                'decoding': 'async',
                'sizes': self._generate_responsive_sizes(),
                'srcset': self._generate_srcset(img_url)
            }
            
            optimized_images.append(img_config)
        
        return optimized_images
    
    def _is_valid_image_url(self, url: str) -> bool:
        """检查是否为有效的图片URL"""
        if not url:
            return False
        
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # 检查文件扩展名
            path = parsed.path.lower()
            return any(path.endswith(fmt) for fmt in self.supported_formats)
            
        except Exception:
            return False
    
    def _is_thumbnail_url(self, url: str) -> bool:
        """检查是否已经是缩略图URL"""
        thumbnail_indicators = ['_thumbnail', '_small', '_s', '_thumb', 'thumb_', 'small_']
        url_lower = url.lower()
        return any(indicator in url_lower for indicator in thumbnail_indicators)
    
    def _generate_platform_thumbnail(self, url: str, platform: str, size: str) -> str:
        """根据平台规则生成缩略图"""
        rules = self.thumbnail_rules.get(platform, {})
        pattern = rules.get('pattern')
        suffix = rules.get('thumbnail_suffix', '_thumbnail')
        
        if not pattern:
            return self._generate_default_thumbnail(url, size)
        
        try:
            match = re.match(pattern, url)
            if match:
                base_url, filename = match.groups()
                name, ext = filename.rsplit('.', 1)
                return f"{base_url}/{name}{suffix}.{ext}"
            
        except Exception as e:
            logger.error(f"平台缩略图生成失败: {str(e)}")
        
        return self._generate_default_thumbnail(url, size)
    
    def _generate_default_thumbnail(self, url: str, size: str) -> str:
        """生成默认缩略图"""
        try:
            # 简单的缩略图处理：在文件名后添加尺寸标识
            if '.' in url:
                base, ext = url.rsplit('.', 1)
                return f"{base}_thumb_{size}.{ext}"
            else:
                return f"{url}_thumb_{size}"
                
        except Exception:
            return url
    
    def _extract_image_alt(self, url: str) -> str:
        """从URL提取图片alt文本"""
        try:
            parsed = urlparse(url)
            filename = parsed.path.split('/')[-1]
            if '.' in filename:
                name = filename.rsplit('.', 1)[0]
                # 清理文件名作为alt文本
                alt = re.sub(r'[_-]', ' ', name)
                alt = re.sub(r'\d+', '', alt).strip()
                return alt if alt else '图片'
            return '图片'
            
        except Exception:
            return '图片'
    
    def _generate_responsive_sizes(self) -> str:
        """生成响应式图片尺寸"""
        return "(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
    
    def _generate_srcset(self, url: str) -> str:
        """生成srcset属性"""
        try:
            # 简单的srcset生成
            base_url = url
            if '.' in url:
                base, ext = url.rsplit('.', 1)
                return f"{base}_small.{ext} 300w, {base}_medium.{ext} 600w, {base}_large.{ext} 1200w"
            return url
            
        except Exception:
            return url


# 创建服务实例
image_service = ImageService()