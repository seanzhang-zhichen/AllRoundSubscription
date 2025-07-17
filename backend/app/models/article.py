"""
文章相关数据模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from datetime import datetime


class Article(BaseModel):
    """文章模型"""
    __tablename__ = "articles"
    
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="账号ID")
    title = Column(String(500), nullable=False, comment="文章标题")
    url = Column(String(1000), nullable=False, unique=True, comment="文章链接")
    content = Column(Text, nullable=True, comment="文章内容")
    summary = Column(Text, nullable=True, comment="文章摘要")
    publish_time = Column(DateTime, nullable=False, comment="发布时间")
    publish_timestamp = Column(BigInteger, nullable=False, index=True, comment="发布时间戳")
    images = Column(JSON, nullable=True, comment="图片链接列表")
    details = Column(JSON, nullable=True, comment="平台特定详细信息")
    
    # 关系定义
    account = relationship("Account", back_populates="articles")
    push_records = relationship("PushRecord", back_populates="article", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Article(id={self.id}, title={self.title[:50]}, account_id={self.account_id})>"
    
    @property
    def image_count(self) -> int:
        """图片数量"""
        if not self.images:
            return 0
        return len(self.images) if isinstance(self.images, list) else 0
    
    @property
    def has_images(self) -> bool:
        """是否包含图片"""
        return self.image_count > 0
    
    def get_thumbnail_url(self) -> str:
        """获取缩略图URL"""
        if self.has_images and isinstance(self.images, list):
            return self.images[0]
        return ""