"""
文章相关数据模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, BigInteger, Index, func
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime


class Article(Base):
    """文章模型"""
    __tablename__ = "articles"
    __table_args__ = (
        Index("ux_articles_url_prefix", "url", mysql_length=768, unique=True),
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
    
    # Article特有属性
    account_id = Column(String(200), ForeignKey("accounts.account_id"), nullable=False, index=True, comment="账号ID")
    title = Column(String(500), nullable=False, comment="文章标题")
    url = Column(String(1000), nullable=False, comment="文章链接")
    content = Column(MEDIUMTEXT, nullable=True, comment="文章内容")
    summary = Column(Text, nullable=True, comment="文章摘要")
    cover_url = Column(String(500), nullable=True, comment="封面图片URL")
    publish_time = Column(DateTime, nullable=False, comment="发布时间")
    details = Column(JSON, nullable=True, comment="平台特定详细信息")
    platform = Column(String(50), nullable=False, comment="平台类型")
    
    # 关系定义
    account = relationship("Account", back_populates="articles", foreign_keys=[account_id], primaryjoin="Article.account_id == Account.account_id")
    push_records = relationship("PushRecord", back_populates="article", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Article(id={self.id}, title={self.title[:50]}, account_id={self.account_id})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
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