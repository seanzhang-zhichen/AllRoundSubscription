"""
订阅相关Pydantic模型
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


class SubscriptionBase(BaseModel):
    """订阅基础模型"""
    user_id: int = Field(..., description="用户ID")
    account_id: str = Field(..., description="账号ID")


class SubscriptionCreate(SubscriptionBase):
    """订阅创建模型"""
    platform: str = Field(..., description="账号平台")


class SubscriptionResponse(SubscriptionBase):
    """订阅响应模型"""
    id: int = Field(description="订阅ID")
    created_at: datetime = Field(description="订阅时间")
    platform: str = Field(description="平台类型")
    
    class Config:
        from_attributes = True


class SubscriptionWithAccount(SubscriptionResponse):
    """带账号信息的订阅模型"""
    account_name: str = Field(description="账号名称")
    account_platform: str = Field(description="账号平台")
    account_avatar_url: Optional[str] = Field(None, description="账号头像")
    account_description: Optional[str] = Field(None, description="账号描述")
    account_follower_count: int = Field(description="账号粉丝数")
    platform_display_name: str = Field(description="平台显示名称")
    latest_article_time: Optional[datetime] = Field(None, description="最新文章时间")
    article_count: int = Field(default=0, description="文章数量")


class SubscriptionList(BaseModel):
    """订阅列表查询模型"""
    user_id: int = Field(..., description="用户ID")
    platform: Optional[str] = Field(None, description="平台筛选")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小")
    order_by: str = Field(default="created_at", description="排序字段")
    order_desc: bool = Field(default=True, description="是否降序")
    
    @validator('order_by')
    def validate_order_by(cls, v):
        allowed_fields = ['created_at', 'account_name', 'latest_article_time']
        if v not in allowed_fields:
            raise ValueError(f'不支持的排序字段: {v}，支持的字段: {allowed_fields}')
        return v


class SubscriptionStats(BaseModel):
    """订阅统计模型"""
    total_subscriptions: int = Field(description="总订阅数")
    subscription_limit: int = Field(description="订阅限制")
    remaining_subscriptions: int = Field(description="剩余可订阅数")
    platform_stats: dict = Field(description="各平台订阅统计")
    recent_subscriptions: List[SubscriptionWithAccount] = Field(description="最近订阅")


class BatchSubscriptionCreate(BaseModel):
    """批量订阅创建模型"""
    user_id: int = Field(..., description="用户ID")
    platform: str = Field(..., description="平台类型")
    account_ids: List[int] = Field(..., min_items=1, max_items=10, description="账号ID列表")
    
    @validator('account_ids')
    def validate_account_ids(cls, v):
        if len(set(v)) != len(v):
            raise ValueError('账号ID列表中存在重复项')
        return v


class BatchSubscriptionResponse(BaseModel):
    """批量订阅响应模型"""
    success_count: int = Field(description="成功订阅数量")
    failed_count: int = Field(description="失败订阅数量")
    success_accounts: List[int] = Field(description="成功订阅的账号ID")
    failed_accounts: List[dict] = Field(description="失败订阅的账号信息")
    message: str = Field(description="操作结果消息")