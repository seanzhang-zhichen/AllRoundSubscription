"""
账号相关Pydantic模型
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from app.models.account import Platform


class AccountBase(BaseModel):
    """账号基础模型"""
    name: str = Field(..., max_length=200, description="账号名称")
    platform: str = Field(..., max_length=50, description="平台类型")
    account_id: str = Field(..., max_length=200, description="平台账号ID")
    avatar_url: Optional[str] = Field(None, max_length=500, description="头像URL")
    description: Optional[str] = Field(None, description="账号描述")
    follower_count: int = Field(default=0, ge=0, description="粉丝数量")
    details: Optional[Dict[str, Any]] = Field(None, description="平台特定详细信息")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('账号名称不能为空')
        return v.strip()
    
    @validator('platform')
    def validate_platform(cls, v):
        valid_platforms = [p.value for p in Platform]
        if v not in valid_platforms:
            raise ValueError(f'不支持的平台类型: {v}，支持的平台: {valid_platforms}')
        return v
    
    @validator('account_id')
    def validate_account_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('平台账号ID不能为空')
        return v.strip()


class AccountCreate(AccountBase):
    """账号创建模型"""
    pass


class AccountUpdate(BaseModel):
    """账号更新模型"""
    name: Optional[str] = Field(None, max_length=200, description="账号名称")
    avatar_url: Optional[str] = Field(None, max_length=500, description="头像URL")
    description: Optional[str] = Field(None, description="账号描述")
    follower_count: Optional[int] = Field(None, ge=0, description="粉丝数量")
    details: Optional[Dict[str, Any]] = Field(None, description="平台特定详细信息")


class AccountResponse(AccountBase):
    """账号响应模型"""
    id: Union[int, str] = Field(..., description="账号ID")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    platform_display_name: str = Field(description="平台显示名称")
    
    class Config:
        from_attributes = True


class AccountSearch(BaseModel):
    """账号搜索模型"""
    keyword: str = Field(..., min_length=1, max_length=100, description="搜索关键词")
    platforms: Optional[List[str]] = Field(None, description="指定平台列表")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小")
    
    @validator('keyword')
    def validate_keyword(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('搜索关键词不能为空')
        return v.strip()
    
    @validator('platforms')
    def validate_platforms(cls, v):
        if v is not None:
            valid_platforms = [p.value for p in Platform]
            for platform in v:
                if platform not in valid_platforms:
                    raise ValueError(f'不支持的平台类型: {platform}')
        return v


class AccountWithStats(AccountResponse):
    """带统计信息的账号模型"""
    article_count: int = Field(default=0, description="文章数量")
    subscriber_count: int = Field(default=0, description="订阅者数量")
    latest_article_time: Optional[datetime] = Field(None, description="最新文章时间")


class PlatformInfo(BaseModel):
    """平台信息模型"""
    platform: str = Field(description="平台标识")
    display_name: str = Field(description="平台显示名称")
    is_supported: bool = Field(description="是否支持")
    description: Optional[str] = Field(None, description="平台描述")