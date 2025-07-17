"""
账号相关数据模型
"""
from sqlalchemy import Column, Integer, String, Text, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from enum import Enum


class Platform(Enum):
    """平台枚举"""
    WECHAT = "wechat"
    WEIBO = "weibo"
    TWITTER = "twitter"


class Account(BaseModel):
    """账号模型 (博主)"""
    __tablename__ = "accounts"
    
    name = Column(String(200), nullable=False, comment="账号名称")
    platform = Column(String(50), nullable=False, index=True, comment="平台类型")
    account_id = Column(String(200), nullable=False, comment="平台账号ID")
    avatar_url = Column(String(500), nullable=True, comment="头像URL")
    description = Column(Text, nullable=True, comment="账号描述")
    follower_count = Column(Integer, default=0, comment="粉丝数量")
    details = Column(JSON, nullable=True, comment="平台特定详细信息")
    
    # 关系定义
    articles = relationship("Article", back_populates="account", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="account", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Account(id={self.id}, name={self.name}, platform={self.platform})>"
    
    @property
    def platform_display_name(self) -> str:
        """平台显示名称"""
        platform_names = {
            "wechat": "微信公众号",
            "weibo": "微博",
            "twitter": "推特"
        }
        return platform_names.get(self.platform, self.platform)