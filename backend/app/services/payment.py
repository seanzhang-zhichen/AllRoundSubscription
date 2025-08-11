from typing import Dict, Any, Tuple, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.logging import get_logger
from app.core.exceptions import BusinessException, ErrorCode, NotFoundException
from app.models import User, MembershipLevel
from app.models.payment_order import PaymentOrder, PaymentStatus, PaymentChannel
from app.services.membership import membership_service
from app.utils.wechatpay_helper import wechat_pay_helper

logger = get_logger(__name__)


class PaymentService:
    """会员支付服务"""

    PRICE_MAP_CENTS = {
        # 单价（分）/月
        MembershipLevel.V1.value: 690,
        MembershipLevel.V2.value: 990,
        MembershipLevel.V3.value: 1490,
        MembershipLevel.V4.value: 1990,
        MembershipLevel.V5.value: 2990,
    }

    async def create_membership_order(
        self,
        db: AsyncSession,
        user_id: int,
        target_level: MembershipLevel,
        duration_months: int,
        channel: PaymentChannel,
        client_ip: Optional[str] = None,
        openid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """创建会员支付订单并调用微信下单，返回前端支付参数"""
        if wechat_pay_helper is None:
            raise BusinessException(error_code=ErrorCode.INTERNAL_ERROR, message="支付服务未初始化")

        # 校验参数
        if target_level == MembershipLevel.FREE:
            raise BusinessException(error_code=ErrorCode.INVALID_PARAMS, message="不能购买免费会员")
        if duration_months < 1 or duration_months > 12:
            raise BusinessException(error_code=ErrorCode.INVALID_PARAMS, message="购买月数必须在1-12之间")

        # 查询用户
        user = await db.get(User, user_id)
        if not user:
            raise NotFoundException("用户不存在")

        # 计算金额
        unit = self.PRICE_MAP_CENTS.get(target_level.value)
        if unit is None:
            raise BusinessException(error_code=ErrorCode.INVALID_PARAMS, message="无效的会员等级定价")
        total_amount = unit * duration_months

        # 生成订单号（用WeChatPayHelper内部方法以保持风格一致）
        out_trade_no = wechat_pay_helper._generate_out_trade_no()  # noqa: SLF001 使用其实现

        description = f"会员升级-{target_level.value}-{duration_months}月"

        # 创建订单记录（先PENDING）
        order = PaymentOrder(
            user_id=user_id,
            target_level=target_level.value,
            duration_months=duration_months,
            out_trade_no=out_trade_no,
            channel=channel,
            status=PaymentStatus.PENDING,
            amount_total=total_amount,
            description=description,
        )
        db.add(order)
        await db.flush()

        # 调起微信统一下单
        if channel == PaymentChannel.WECHAT_MINIPROG:
            if not openid:
                raise BusinessException(error_code=ErrorCode.INVALID_PARAMS, message="缺少openid")
            code, payload = wechat_pay_helper.create_miniprog_payment(
                openid=openid,
                amount=total_amount,
                description=description,
                out_trade_no=out_trade_no,
            )
        elif channel == PaymentChannel.WECHAT_JSAPI:
            if not openid:
                raise BusinessException(error_code=ErrorCode.INVALID_PARAMS, message="缺少openid")
            code, payload = wechat_pay_helper.create_jsapi_payment(
                openid=openid,
                amount=total_amount,
                description=description,
                out_trade_no=out_trade_no,
            )
        elif channel == PaymentChannel.WECHAT_APP:
            code, payload = wechat_pay_helper.create_app_payment(
                amount=total_amount,
                description=description,
                out_trade_no=out_trade_no,
            )
        elif channel == PaymentChannel.WECHAT_H5:
            if not client_ip:
                raise BusinessException(error_code=ErrorCode.INVALID_PARAMS, message="缺少客户端IP")
            code, payload = wechat_pay_helper.create_h5_payment(
                amount=total_amount,
                description=description,
                client_ip=client_ip,
                out_trade_no=out_trade_no,
            )
        else:
            raise BusinessException(error_code=ErrorCode.INVALID_PARAMS, message="不支持的支付渠道")

        if code < 200 or code >= 300:
            raise BusinessException(error_code=ErrorCode.EXTERNAL_SERVICE_ERROR, message=payload.get("error", "微信下单失败"))

        # 保存prepay_id等
        prepay_id = payload.get("prepay_id")
        if prepay_id:
            await db.execute(
                update(PaymentOrder)
                .where(PaymentOrder.id == order.id)
                .values(prepay_id=prepay_id)
            )
        await db.commit()

        # 返回给前端的调起参数（payload内已就绪）
        return {
            "order_id": order.id,
            "out_trade_no": out_trade_no,
            "channel": channel.value,
            "pay_params": payload,
        }

    async def handle_wechat_notify(self, db: AsyncSession, headers: dict, body: bytes) -> Dict[str, Any]:
        """处理微信支付回调，验证签名并升级会员"""
        if wechat_pay_helper is None:
            raise BusinessException(error_code=ErrorCode.INTERNAL_ERROR, message="支付服务未初始化")

        data = wechat_pay_helper.process_notification(headers, body)
        if data.get("status") == "error":
            raise BusinessException(error_code=ErrorCode.EXTERNAL_SERVICE_ERROR, message=data.get("message", "回调验签失败"))

        # data 中一般包含 resource -> ciphertext 解密后的订单信息，这里按常见字段取值
        resource = data.get("resource", {}) if isinstance(data, dict) else {}
        out_trade_no = resource.get("out_trade_no") or data.get("out_trade_no")
        transaction_state = resource.get("trade_state") or data.get("trade_state")
        success = transaction_state in ("SUCCESS", "SUCCESSFUL", "SUCCESSFUL_PAYMENT")

        if not out_trade_no:
            raise BusinessException(error_code=ErrorCode.INVALID_PARAMS, message="回调缺少订单号")

        # 查询订单
        stmt = select(PaymentOrder).where(PaymentOrder.out_trade_no == out_trade_no)
        result = await db.execute(stmt)
        order: Optional[PaymentOrder] = result.scalar_one_or_none()
        if not order:
            raise NotFoundException("订单不存在")

        # 幂等处理
        if order.status == PaymentStatus.SUCCESS:
            return {"status": "success", "message": "已处理", "out_trade_no": out_trade_no}

        if success:
            # 标记成功
            await db.execute(
                update(PaymentOrder)
                .where(PaymentOrder.id == order.id)
                .values(status=PaymentStatus.SUCCESS, paid_at=datetime.utcnow())
            )
            await db.commit()

            # 升级会员
            level = MembershipLevel(order.target_level)
            await membership_service.upgrade_membership(
                user_id=order.user_id,
                target_level=level,
                duration_months=order.duration_months,
                db=db,
            )
            return {"status": "success", "message": "会员已升级", "out_trade_no": out_trade_no}
        else:
            await db.execute(
                update(PaymentOrder)
                .where(PaymentOrder.id == order.id)
                .values(status=PaymentStatus.FAILED)
            )
            await db.commit()
            return {"status": "failed", "message": "支付失败", "out_trade_no": out_trade_no}


payment_service = PaymentService() 