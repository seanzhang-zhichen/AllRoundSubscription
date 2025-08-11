"""
推送记录相关数据模型
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import relationship
from app.db.database import Base
from enum import Enum


class PushStatus(Enum):
    """推送状态枚举"""
    PENDING = "pending"      # 待推送
    SUCCESS = "success"      # 推送成功
    FAILED = "failed"        # 推送失败
    SKIPPED = "skipped"      # 跳过推送（达到限制等）


class PushRecord(Base):
    """推送记录模型"""
    __tablename__ = "push_records"
    
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
    
    # PushRecord特有属性
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False, index=True, comment="文章ID")
    push_time = Column(DateTime, nullable=False, comment="推送时间")
    status = Column(String(20), nullable=False, default=PushStatus.PENDING.value, comment="推送状态")
    error_message = Column(String(500), nullable=True, comment="错误信息")
    
    # 关系定义
    user = relationship("User", back_populates="push_records")
    article = relationship("Article", back_populates="push_records")
    
    def __repr__(self):
        return f"<PushRecord(id={self.id}, user_id={self.user_id}, article_id={self.article_id}, status={self.status})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    @property
    def is_success(self) -> bool:
        """是否推送成功"""
        return self.status == PushStatus.SUCCESS.value
    
    @property
    def is_failed(self) -> bool:
        """是否推送失败"""
        return self.status == PushStatus.FAILED.value