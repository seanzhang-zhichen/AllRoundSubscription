"""
搜索相关Pydantic模型
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from app.schemas.account import AccountResponse, PlatformInfo


class SearchRequest(BaseModel):
    """搜索请求模型"""
    keyword: str = Field(..., min_length=1, max_length=100, description="搜索关键词")
    platforms: Optional[List[str]] = Field(None, description="指定平台列表")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小")
    
    @field_validator('keyword')
    @classmethod
    def validate_keyword(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('搜索关键词不能为空')
        return v.strip()
    
    @field_validator('platforms')
    @classmethod
    def validate_platforms(cls, v):
        if v is not None:
            from app.models.account import Platform
            valid_platforms = [p.value for p in Platform]
            for platform in v:
                if platform not in valid_platforms:
                    raise ValueError(f'不支持的平台类型: {platform}')
        return v


class PlatformSearchRequest(BaseModel):
    """平台搜索请求模型"""
    keyword: str = Field(..., min_length=1, max_length=100, description="搜索关键词")
    platform: str = Field(..., description="平台标识")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小")
    
    @field_validator('keyword')
    @classmethod
    def validate_keyword(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('搜索关键词不能为空')
        return v.strip()
    
    @field_validator('platform')
    @classmethod
    def validate_platform(cls, v):
        from app.models.account import Platform
        valid_platforms = [p.value for p in Platform]
        if v not in valid_platforms:
            raise ValueError(f'不支持的平台类型: {v}')
        return v


class SearchResponse(BaseModel):
    """搜索响应模型"""
    accounts: List[AccountResponse] = Field(description="搜索结果账号列表")
    total: int = Field(description="总结果数量")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页大小")
    platform: Optional[str] = Field(None, description="搜索平台（单平台搜索时）")
    has_more: bool = Field(description="是否有更多结果")
    search_time_ms: Optional[int] = Field(None, description="搜索耗时（毫秒）")
    
    class Config:
        from_attributes = True


class PlatformStatusResponse(BaseModel):
    """平台状态响应模型"""
    platform: str = Field(description="平台标识")
    platform_name: str = Field(description="平台名称")
    is_enabled: bool = Field(description="是否启用")
    is_available: bool = Field(description="是否可用")
    last_check_time: Optional[str] = Field(None, description="最后检查时间")
    error_message: Optional[str] = Field(None, description="错误信息")


class SearchStatisticsResponse(BaseModel):
    """搜索统计响应模型"""
    supported_platforms: List[str] = Field(description="支持的平台列表")
    registered_adapters: List[str] = Field(description="已注册的适配器列表")
    platform_status: Dict[str, bool] = Field(description="平台状态")
    cache_stats: Dict[str, Any] = Field(description="缓存统计信息")
    timestamp: str = Field(description="统计时间戳")


class SupportedPlatformsResponse(BaseModel):
    """支持的平台列表响应模型"""
    platforms: List[PlatformInfo] = Field(description="平台信息列表")
    total: int = Field(description="平台总数")
    enabled_count: int = Field(description="启用的平台数量")


class SearchSuggestionRequest(BaseModel):
    """搜索建议请求模型"""
    keyword: str = Field(..., min_length=1, max_length=50, description="搜索关键词")
    limit: int = Field(default=10, ge=1, le=20, description="建议数量限制")
    
    @field_validator('keyword')
    @classmethod
    def validate_keyword(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('搜索关键词不能为空')
        return v.strip()


class SearchSuggestion(BaseModel):
    """搜索建议模型"""
    keyword: str = Field(description="建议关键词")
    type: str = Field(description="建议类型")
    count: int = Field(default=0, description="相关结果数量")
    platform: Optional[str] = Field(None, description="相关平台")


class SearchSuggestionResponse(BaseModel):
    """搜索建议响应模型"""
    suggestions: List[SearchSuggestion] = Field(description="搜索建议列表")
    total: int = Field(description="建议总数")


class SearchHistoryItem(BaseModel):
    """搜索历史项模型"""
    keyword: str = Field(description="搜索关键词")
    platforms: Optional[List[str]] = Field(None, description="搜索平台")
    result_count: int = Field(description="结果数量")
    search_time: str = Field(description="搜索时间")


class SearchHistoryResponse(BaseModel):
    """搜索历史响应模型"""
    history: List[SearchHistoryItem] = Field(description="搜索历史列表")
    total: int = Field(description="历史记录总数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页大小")


class CacheStatsResponse(BaseModel):
    """缓存统计响应模型"""
    search_results: int = Field(description="搜索结果缓存数量")
    platform_results: int = Field(description="平台结果缓存数量")
    account_info: int = Field(description="账号信息缓存数量")
    platform_status: int = Field(description="平台状态缓存数量")
    total: int = Field(description="总缓存数量")
    timestamp: str = Field(description="统计时间戳")
    hit_rate: Optional[float] = Field(None, description="缓存命中率")
    
    class Config:
        from_attributes = True