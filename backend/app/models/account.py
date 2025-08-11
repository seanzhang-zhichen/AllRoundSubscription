"""
账号相关数据模型
"""
from sqlalchemy import Column, Integer, String, Text, JSON, Index, UniqueConstraint, DateTime, func
from sqlalchemy.orm import relationship
from app.db.database import Base
from enum import Enum


class Platform(Enum):
    """平台枚举"""
    WECHAT = "wechat"
    WEIXIN = "weixin"  # 微信公众号的另一种表示
    WEIBO = "weibo"
    TWITTER = "twitter"
    BILIBILI = "bilibili"
    DOUYIN = "douyin"
    ZHIHU = "zhihu"
    XIAOHONGSHU = "xiaohongshu"


class Account(Base):
    """账号模型 (博主)"""
    __tablename__ = "accounts"
    __table_args__ = (
        Index("ux_accounts_account_id", "account_id", unique=True),
        UniqueConstraint("platform", "account_id", name="uq_platform_account_id"),
    )
    
    # 从BaseModel继承的属性
    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="主键ID")
    created_at = Column(
        DateTime,
        default=func.now(),
        nullable=False,
        comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )
    
    # Account特有属性
    name = Column(String(200), nullable=False, comment="账号名称")
    platform = Column(String(50), nullable=False, index=True, comment="平台类型")
    account_id = Column(String(200), nullable=False, comment="平台账号ID")
    avatar_url = Column(String(500), nullable=True, comment="头像URL")
    description = Column(Text, nullable=True, comment="账号描述")
    details = Column(JSON, nullable=True, comment="平台特定详细信息")
    
    # 关系定义
    articles = relationship("Article", back_populates="account", primaryjoin="Account.account_id == Article.account_id")
    subscriptions = relationship("Subscription", back_populates="account", primaryjoin="Account.account_id == Subscription.account_id")
    
    def __repr__(self):
        return f"<Account(id={self.id}, name={self.name}, platform={self.platform})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    @property
    def platform_display_name(self) -> str:
        """平台显示名称"""
        platform_names = {
            "wechat": "微信公众号",
            "weixin": "微信公众号",
            "weibo": "微博",
            "twitter": "推特",
            "bilibili": "哔哩哔哩",
            "douyin": "抖音",
            "zhihu": "知乎",
            "xiaohongshu": "小红书"
        }
        return platform_names.get(self.platform, self.platform)