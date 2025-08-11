"""
订阅相关数据模型
"""
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, DateTime, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Subscription(Base):
    """订阅关系模型"""
    __tablename__ = "subscriptions"
    
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
    
    # Subscription特有属性
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    account_id = Column(String(200), ForeignKey("accounts.account_id"), nullable=False, index=True, comment="账号ID")
    platform = Column(String(50), nullable=False, index=True, comment="平台类型")
    
    # 关系定义
    user = relationship("User", back_populates="subscriptions")
    account = relationship("Account", back_populates="subscriptions", primaryjoin="Subscription.account_id == Account.account_id")
    
    # 唯一约束：一个用户不能重复订阅同一个账号
    __table_args__ = (
        UniqueConstraint('user_id', 'account_id', name='uq_user_account_subscription'),
    )
    
    def __repr__(self):
        return f"<Subscription(id={self.id}, user_id={self.user_id}, account_id={self.account_id}, platform={self.platform})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }