"""
文章相关Pydantic模型
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime


class ArticleBase(BaseModel):
    """文章基础模型"""
    title: str = Field(..., max_length=500, description="文章标题")
    url: str = Field(..., max_length=1000, description="文章链接")
    content: Optional[str] = Field(None, description="文章内容")
    summary: Optional[str] = Field(None, description="文章摘要")
    publish_time: datetime = Field(..., description="发布时间")
    images: Optional[List[str]] = Field(None, description="图片链接列表")
    details: Optional[Dict[str, Any]] = Field(None, description="平台特定详细信息")
    
    @validator('title')
    def validate_title(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('文章标题不能为空')
        return v.strip()
    
    @validator('url')
    def validate_url(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('文章链接不能为空')
        # 简单的URL格式验证
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('文章链接格式不正确')
        return v.strip()
    
    @validator('images')
    def validate_images(cls, v):
        if v is not None:
            # 验证图片URL格式
            for img_url in v:
                if not (img_url.startswith('http://') or img_url.startswith('https://')):
                    raise ValueError(f'图片链接格式不正确: {img_url}')
        return v


class ArticleCreate(ArticleBase):
    """文章创建模型"""
    account_id: int = Field(..., description="账号ID")


class ArticleUpdate(BaseModel):
    """文章更新模型"""
    title: Optional[str] = Field(None, max_length=500, description="文章标题")
    content: Optional[str] = Field(None, description="文章内容")
    summary: Optional[str] = Field(None, description="文章摘要")
    images: Optional[List[str]] = Field(None, description="图片链接列表")
    details: Optional[Dict[str, Any]] = Field(None, description="平台特定详细信息")


class ArticleResponse(ArticleBase):
    """文章响应模型"""
    id: str = Field(description="文章ID")
    account_id: str = Field(description="账号ID")
    publish_timestamp: int = Field(description="发布时间戳")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    image_count: int = Field(description="图片数量")
    has_images: bool = Field(description="是否包含图片")
    thumbnail_url: str = Field(description="缩略图URL")
    
    class Config:
        from_attributes = True


class ArticleWithAccount(ArticleResponse):
    """带账号信息的文章模型"""
    account_name: str = Field(description="账号名称")
    account_platform: str = Field(description="账号平台")
    account_avatar_url: Optional[str] = Field(None, description="账号头像")
    platform_display_name: str = Field(description="平台显示名称")


class ArticleList(BaseModel):
    """文章列表查询模型"""
    user_id: Optional[int] = Field(None, description="用户ID（获取订阅内容）")
    account_id: Optional[int] = Field(None, description="账号ID（获取特定账号内容）")
    platform: Optional[str] = Field(None, description="平台筛选")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小")
    order_by: str = Field(default="publish_time", description="排序字段")
    order_desc: bool = Field(default=True, description="是否降序")
    
    @validator('order_by')
    def validate_order_by(cls, v):
        allowed_fields = ['publish_time', 'created_at', 'title']
        if v not in allowed_fields:
            raise ValueError(f'不支持的排序字段: {v}，支持的字段: {allowed_fields}')
        return v


class ArticleDetail(ArticleWithAccount):
    """文章详情模型"""
    is_subscribed: bool = Field(description="当前用户是否已订阅该账号")
    related_articles: List[ArticleResponse] = Field(default=[], description="相关文章")


class ArticleFeed(BaseModel):
    """动态流查询模型"""
    user_id: int = Field(..., description="用户ID")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=50, description="每页大小")
    refresh: bool = Field(default=False, description="是否刷新获取最新内容")


class ArticleStats(BaseModel):
    """文章统计模型"""
    total_articles: int = Field(description="总文章数")
    today_articles: int = Field(description="今日文章数")
    week_articles: int = Field(description="本周文章数")
    platform_stats: Dict[str, int] = Field(description="各平台文章统计")