"""
会员管理API路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.core.deps import get_current_user, get_db
from app.models.user import User, MembershipLevel
from app.services.membership import membership_service
from app.services.limits import limits_service
from app.schemas.user import MembershipUpgrade, MembershipInfo
from app.schemas.common import BaseResponse
from app.core.exceptions import BusinessException, NotFoundException
from app.core.permissions import check_membership_dependency
from app.services.payment import payment_service
from app.models.payment_order import PaymentChannel

router = APIRouter(prefix="/membership", tags=["会员管理"])


@router.get("/info", response_model=BaseResponse)
async def get_membership_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户会员信息"""
    try:
        membership_info = await membership_service.get_membership_info(current_user.id, db)
        return BaseResponse(data=membership_info, message="获取会员信息成功")
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/upgrade", response_model=BaseResponse)
async def upgrade_membership(
    upgrade_data: MembershipUpgrade,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """升级用户会员：创建支付订单并返回前端发起支付所需参数"""
    try:
        # 解析支付渠道（兼容字符串输入）
        try:
            channel = PaymentChannel(upgrade_data.channel)  # type: ignore[arg-type]
        except Exception:
            mapping = {
                "wechat_jsapi": PaymentChannel.WECHAT_JSAPI,
                "wechat_miniprog": PaymentChannel.WECHAT_MINIPROG,
                "wechat_app": PaymentChannel.WECHAT_APP,
                "wechat_h5": PaymentChannel.WECHAT_H5,
            }
            channel = mapping.get((upgrade_data.channel or "wechat_miniprog").lower(), PaymentChannel.WECHAT_MINIPROG)

        result = await payment_service.create_membership_order(
            db=db,
            user_id=current_user.id,
            target_level=upgrade_data.level,
            duration_months=upgrade_data.duration_months,
            channel=channel,
            client_ip=upgrade_data.client_ip,
            openid=current_user.openid,
        )
        return BaseResponse(data=result, message="订单创建成功，请发起支付")
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/limits", response_model=BaseResponse)
async def get_user_limits(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户权限限制信息"""
    try:
        limits_info = await limits_service.get_user_limits_summary(current_user.id, db)
        return BaseResponse(data=limits_info, message="获取限制信息成功")
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/limits/subscription", response_model=BaseResponse)
async def check_subscription_limit(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """检查订阅数量限制"""
    try:
        subscription_info = await limits_service.check_subscription_limit(current_user.id, db)
        return BaseResponse(data=subscription_info, message="订阅限制检查完成")
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/limits/push", response_model=BaseResponse)
async def check_push_limit(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """检查推送次数限制"""
    try:
        push_info = await limits_service.check_push_limit(current_user.id, db)
        return BaseResponse(data=push_info, message="推送限制检查完成")
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/benefits", response_model=BaseResponse)
async def get_membership_benefits():
    """获取所有会员等级权益对比"""
    try:
        benefits_info = await limits_service.get_all_membership_benefits()
        return BaseResponse(data=benefits_info, message="获取会员权益信息成功")
    except BusinessException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/benefits/{level}", response_model=BaseResponse)
async def get_level_benefits(level: str):
    """获取指定等级的会员权益"""
    try:
        # 验证会员等级
        try:
            membership_level = MembershipLevel(level)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的会员等级: {level}"
            )
        
        benefits_info = await limits_service.get_membership_benefits_display(membership_level)
        return BaseResponse(data=benefits_info, message="获取会员权益信息成功")
    except BusinessException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/check-expiry", response_model=BaseResponse)
async def check_membership_expiry(
    current_user: User = Depends(check_membership_dependency(MembershipLevel.PREMIUM)),
    db: AsyncSession = Depends(get_db)
):
    """检查并处理会员到期（仅管理员功能）"""
    try:
        expired_user_ids = await membership_service.check_membership_expiry(db)
        return BaseResponse(
            data={"expired_user_count": len(expired_user_ids), "expired_user_ids": expired_user_ids},
            message="会员到期检查完成"
        )
    except BusinessException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)