"""
支付订单数据模型
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SQLEnum, DateTime
from sqlalchemy.orm import relationship
from enum import Enum
from datetime import datetime

from app.models.base import BaseModel


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


class PaymentOrder(BaseModel):
    """会员支付订单"""
    __tablename__ = "payment_orders"

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