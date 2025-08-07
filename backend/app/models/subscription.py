"""
订阅相关数据模型
"""
from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, String
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Subscription(BaseModel):
    """订阅关系模型"""
    __tablename__ = "subscriptions"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="账号ID")
    platform = Column(String(50), nullable=False, index=True, comment="平台类型")
    
    # 关系定义
    user = relationship("User", back_populates="subscriptions")
    account = relationship("Account", back_populates="subscriptions")
    
    # 唯一约束：一个用户不能重复订阅同一个账号
    __table_args__ = (
        UniqueConstraint('user_id', 'account_id', name='uq_user_account_subscription'),
    )
    
    def __repr__(self):
        return f"<Subscription(id={self.id}, user_id={self.user_id}, account_id={self.account_id}, platform={self.platform})>"