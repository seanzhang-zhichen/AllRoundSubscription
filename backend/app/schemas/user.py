"""
用户相关Pydantic模型
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from app.models.user import MembershipLevel


class UserBase(BaseModel):
    """用户基础模型"""
    nickname: Optional[str] = Field(None, max_length=100, description="用户昵称")
    avatar_url: Optional[str] = Field(None, max_length=500, description="头像URL")


class UserCreate(UserBase):
    """用户创建模型"""
    openid: str = Field(..., max_length=128, description="微信openid")
    
    @validator('openid')
    def validate_openid(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('openid不能为空')
        return v.strip()


class UserUpdate(UserBase):
    """用户更新模型"""
    pass


class UserResponse(UserBase):
    """用户响应模型"""
    id: int = Field(description="用户ID")
    openid: str = Field(description="微信openid")
    membership_level: MembershipLevel = Field(description="会员等级")
    membership_expire_at: Optional[datetime] = Field(None, description="会员到期时间")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    
    class Config:
        from_attributes = True


class UserProfile(UserResponse):
    """用户档案模型"""
    subscription_count: int = Field(default=0, description="订阅数量")
    subscription_limit: int = Field(description="订阅限制")
    daily_push_limit: int = Field(description="每日推送限制")
    is_membership_active: bool = Field(description="会员是否有效")
    
    class Config:
        from_attributes = True


class MembershipInfo(BaseModel):
    """会员信息模型"""
    level: MembershipLevel = Field(description="会员等级")
    expire_at: Optional[datetime] = Field(None, description="到期时间")
    is_active: bool = Field(description="是否有效")
    subscription_limit: int = Field(description="订阅限制")
    daily_push_limit: int = Field(description="每日推送限制")
    
    class Config:
        from_attributes = True


class MembershipUpgrade(BaseModel):
    """会员升级模型"""
    level: MembershipLevel = Field(description="目标会员等级")
    duration_months: int = Field(ge=1, le=12, description="购买月数")
    
    @validator('level')
    def validate_level(cls, v):
        if v == MembershipLevel.FREE:
            raise ValueError('不能升级到免费等级')
        return v


class UserLimits(BaseModel):
    """用户限制信息"""
    subscription_limit: int = Field(description="订阅限制")
    subscription_used: int = Field(description="已使用订阅数")
    daily_push_limit: int = Field(description="每日推送限制")
    daily_push_used: int = Field(description="今日已推送数")
    can_subscribe: bool = Field(description="是否可以继续订阅")
    can_receive_push: bool = Field(description="是否可以接收推送")