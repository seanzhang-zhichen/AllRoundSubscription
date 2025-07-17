"""
认证相关Pydantic模型
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

from app.schemas.user import UserResponse


class WeChatLoginRequest(BaseModel):
    """微信登录请求模型"""
    code: str = Field(..., min_length=1, max_length=100, description="微信小程序登录code")
    
    @validator('code')
    def validate_code(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('登录code不能为空')
        return v.strip()


class TokenInfo(BaseModel):
    """令牌信息模型"""
    access_token: str = Field(description="访问令牌")
    refresh_token: str = Field(description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(description="过期时间（秒）")


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求模型"""
    refresh_token: str = Field(..., min_length=1, description="刷新令牌")
    
    @validator('refresh_token')
    def validate_refresh_token(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('刷新令牌不能为空')
        return v.strip()


class RefreshTokenResponse(BaseModel):
    """刷新令牌响应模型"""
    access_token: str = Field(description="新的访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(description="过期时间（秒）")


class LoginResponse(BaseModel):
    """登录响应模型"""
    user: UserResponse = Field(description="用户信息")
    tokens: TokenInfo = Field(description="令牌信息")


class UserLoginInfo(BaseModel):
    """用户登录信息"""
    id: int = Field(description="用户ID")
    openid: str = Field(description="微信openid")
    nickname: Optional[str] = Field(None, description="用户昵称")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    membership_level: str = Field(description="会员等级")
    membership_expire_at: Optional[datetime] = Field(None, description="会员到期时间")
    is_membership_active: bool = Field(description="会员是否有效")
    subscription_limit: int = Field(description="订阅限制")
    daily_push_limit: int = Field(description="每日推送限制")


class LoginResponseV2(BaseModel):
    """登录响应模型V2"""
    user: UserLoginInfo = Field(description="用户信息")
    tokens: TokenInfo = Field(description="令牌信息")


class LogoutResponse(BaseModel):
    """登出响应模型"""
    success: bool = Field(default=True, description="是否成功")
    message: str = Field(default="登出成功", description="响应消息")


class TokenPayload(BaseModel):
    """令牌载荷模型"""
    sub: str = Field(description="用户ID")
    openid: str = Field(description="微信openid")
    exp: int = Field(description="过期时间戳")
    type: str = Field(description="令牌类型")


class AuthStatus(BaseModel):
    """认证状态模型"""
    is_authenticated: bool = Field(description="是否已认证")
    user_id: Optional[int] = Field(None, description="用户ID")
    openid: Optional[str] = Field(None, description="微信openid")
    membership_level: Optional[str] = Field(None, description="会员等级")
    token_expires_at: Optional[datetime] = Field(None, description="令牌过期时间")