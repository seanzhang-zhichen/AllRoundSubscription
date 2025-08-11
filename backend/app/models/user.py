"""
用户相关数据模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from enum import Enum
from datetime import datetime


class MembershipLevel(Enum):
    """会员等级枚举"""
    FREE = "free"
    # 新增多等级VIP（V1-V5）
    V1 = "v1"
    V2 = "v2"
    V3 = "v3"
    V4 = "v4"
    V5 = "v5"
    # 兼容旧值
    BASIC = "basic"
    PREMIUM = "premium"


class User(BaseModel):
    """用户模型"""
    __tablename__ = "users"
    
    openid = Column(String(128), unique=True, nullable=False, index=True, comment="微信openid")
    nickname = Column(String(100), nullable=True, comment="用户昵称")
    avatar_url = Column(String(500), nullable=True, comment="头像URL")
    membership_level = Column(
        SQLEnum(MembershipLevel), 
        default=MembershipLevel.FREE, 
        nullable=False,
        comment="会员等级"
    )
    membership_expire_at = Column(DateTime, nullable=True, comment="会员到期时间")
    
    # 关系定义
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    push_records = relationship("PushRecord", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, openid={self.openid}, nickname={self.nickname})>"
    
    @property
    def is_premium(self) -> bool:
        """是否为付费会员"""
        return self.membership_level != MembershipLevel.FREE
    
    @property
    def is_membership_active(self) -> bool:
        """会员是否有效"""
        if self.membership_level == MembershipLevel.FREE:
            return True
        if self.membership_expire_at is None:
            return False
        return self.membership_expire_at > datetime.now()
    
    def get_subscription_limit(self) -> int:
        """获取订阅数量限制"""
        if not self.is_membership_active:
            return 10  # 免费用户或过期会员
        
        limits = {
            MembershipLevel.FREE: 10,
            MembershipLevel.V1: 20,
            MembershipLevel.V2: 50,
            MembershipLevel.V3: 100,
            MembershipLevel.V4: 300,
            MembershipLevel.V5: -1,
        }
        return limits.get(self.membership_level, 10)
    
    def get_daily_push_limit(self) -> int:
        """获取每日推送次数限制"""
        if not self.is_membership_active:
            return 5  # 免费用户或过期会员
        
        limits = {
            MembershipLevel.FREE: 5,
            MembershipLevel.V1: 10,
            MembershipLevel.V2: 20,
            MembershipLevel.V3: 50,
            MembershipLevel.V4: 200,
            MembershipLevel.V5: -1,
        }
        return limits.get(self.membership_level, 5)