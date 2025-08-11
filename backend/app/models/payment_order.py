"""
支付订单数据模型
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SQLEnum, DateTime, func
from sqlalchemy.orm import relationship
from enum import Enum
from datetime import datetime

from app.db.database import Base


class PaymentStatus(Enum):
    PENDING = "pending"          # 已创建，待支付
    SUCCESS = "success"          # 支付成功
    FAILED = "failed"            # 支付失败
    CLOSED = "closed"            # 已关闭


class PaymentChannel(Enum):
    WECHAT_JSAPI = "wechat_jsapi"
    WECHAT_MINIPROG = "wechat_miniprog"
    WECHAT_APP = "wechat_app"
    WECHAT_H5 = "wechat_h5"


class PaymentOrder(Base):
    """会员支付订单"""
    __tablename__ = "payment_orders"

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
    
    # PaymentOrder特有属性
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    target_level = Column(String(20), nullable=False, comment="目标会员等级")
    duration_months = Column(Integer, nullable=False, comment="购买月数")

    out_trade_no = Column(String(64), unique=True, nullable=False, index=True, comment="商户订单号")
    prepay_id = Column(String(128), nullable=True, comment="预支付ID")

    channel = Column(SQLEnum(PaymentChannel), nullable=False, comment="支付渠道")
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, comment="订单状态")

    amount_total = Column(Integer, nullable=False, comment="订单总金额(分)")
    description = Column(String(128), nullable=False, comment="订单描述")

    paid_at = Column(DateTime, nullable=True, comment="支付成功时间")

    # 关系
    user = relationship("User")
    
    def __repr__(self):
        return f"<PaymentOrder(id={self.id}, user_id={self.user_id}, status={self.status})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        } 