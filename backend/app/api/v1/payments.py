"""
支付API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.core.deps import get_db, get_current_user
from app.core.logging import get_logger
from app.core.exceptions import BusinessException, NotFoundException
from app.models.user import User, MembershipLevel
from app.models.payment_order import PaymentChannel
from app.schemas.user import MembershipUpgrade
from app.schemas.common import BaseResponse
from app.services.payment import payment_service

logger = get_logger(__name__)
router = APIRouter(prefix="/payments", tags=["支付"])


@router.post("/create", response_model=BaseResponse)
async def create_payment(
    payload: MembershipUpgrade,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建会员支付订单并返回前端发起支付所需参数"""
    try:
        # 解析支付渠道
        try:
            channel = PaymentChannel(payload.channel)
        except Exception:
            # 兼容字符串
            mapping = {
                "wechat_jsapi": PaymentChannel.WECHAT_JSAPI,
                "wechat_miniprog": PaymentChannel.WECHAT_MINIPROG,
                "wechat_app": PaymentChannel.WECHAT_APP,
                "wechat_h5": PaymentChannel.WECHAT_H5,
            }
            channel = mapping.get((payload.channel or "wechat_miniprog").lower(), PaymentChannel.WECHAT_MINIPROG)

        result = await payment_service.create_membership_order(
            db=db,
            user_id=current_user.id,
            target_level=payload.level,
            duration_months=payload.duration_months,
            channel=channel,
            client_ip=payload.client_ip,
            openid=current_user.openid,
        )
        return BaseResponse(data=result, message="订单创建成功")
    except (BusinessException, NotFoundException) as e:
        raise HTTPException(status_code=getattr(e, "status_code", 400), detail=str(e))
    except Exception as e:
        logger.error(f"创建支付订单失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建支付订单失败")


@router.post("/wechat/notify")
async def wechat_notify(request: Request, db: AsyncSession = Depends(get_db)):
    """微信支付回调（必须提供公网可访问地址）"""
    try:
        headers = dict(request.headers)
        body = await request.body()
        result = await payment_service.handle_wechat_notify(db, headers, body)
        return {"code": 0, "message": "OK", "data": result}
    except (BusinessException, NotFoundException) as e:
        logger.error(f"微信回调处理失败: {str(e)}")
        return {"code": 1, "message": str(e)}
    except Exception as e:
        logger.error(f"微信回调未知异常: {str(e)}", exc_info=True)
        return {"code": 1, "message": "回调处理失败"} 