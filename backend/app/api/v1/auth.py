"""
认证相关API路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_logger

from app.db.database import get_db
from app.services.auth import auth_service
from app.schemas.auth import (
    WeChatLoginRequest, LoginResponseV2, RefreshTokenRequest, 
    RefreshTokenResponse, LogoutResponse, AuthStatus
)
from app.schemas.common import DataResponse, SuccessResponse
from app.core.deps import get_current_user
from app.core.exceptions import AuthenticationException, BusinessException
from app.models.user import User

logger = get_logger(__name__)

router = APIRouter()


@router.post("/login", response_model=DataResponse[LoginResponseV2], summary="微信小程序登录")
async def wechat_login(
    login_data: WeChatLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    微信小程序登录接口
    
    - **code**: 微信小程序登录时获取的code
    
    返回用户信息和JWT令牌
    """
    try:
        logger.info(f"收到微信登录请求，code: {login_data.code[:10]}...")
        
        result = await auth_service.wechat_login(login_data.code, db)
        
        response_data = LoginResponseV2(
            user=result["user"],
            tokens=result["tokens"]
        )
        
        return DataResponse(
            data=response_data,
            message="登录成功"
        )
        
    except BusinessException as e:
        logger.error(f"微信登录业务异常: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "code": e.error_code,
                "message": e.message
            }
        )
    except AuthenticationException as e:
        logger.error(f"微信登录认证异常: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail={
                "code": 401,
                "message": str(e)
            }
        )
    except Exception as e:
        logger.error(f"微信登录未知异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "登录服务异常"
            }
        )


@router.post("/refresh", response_model=DataResponse[RefreshTokenResponse], summary="刷新访问令牌")
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    刷新访问令牌接口
    
    - **refresh_token**: 刷新令牌
    
    返回新的访问令牌
    """
    try:
        logger.info("收到令牌刷新请求")
        
        result = await auth_service.refresh_token(refresh_data.refresh_token, db)
        
        response_data = RefreshTokenResponse(**result)
        
        return DataResponse(
            data=response_data,
            message="令牌刷新成功"
        )
        
    except AuthenticationException as e:
        logger.error(f"令牌刷新认证异常: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail={
                "code": 401,
                "message": str(e)
            }
        )
    except Exception as e:
        logger.error(f"令牌刷新未知异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "令牌刷新服务异常"
            }
        )


@router.post("/logout", response_model=SuccessResponse, summary="用户登出")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    用户登出接口
    
    需要认证，清除用户会话信息
    """
    try:
        logger.info(f"用户登出请求，用户ID: {current_user.id}")
        
        success = await auth_service.logout(current_user.id)
        
        if success:
            return SuccessResponse(message="登出成功")
        else:
            return SuccessResponse(
                success=False,
                message="登出失败，但不影响安全性"
            )
            
    except Exception as e:
        logger.error(f"用户登出异常: {str(e)}", exc_info=True)
        # 登出失败不应该抛出异常，因为客户端可以丢弃令牌
        return SuccessResponse(
            success=False,
            message="登出处理异常，请手动清除本地令牌"
        )


@router.get("/status", response_model=DataResponse[AuthStatus], summary="获取认证状态")
async def get_auth_status(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户认证状态
    
    需要认证，返回用户基本信息和认证状态
    """
    try:
        logger.debug(f"获取认证状态，用户ID: {current_user.id}")
        
        auth_status = AuthStatus(
            is_authenticated=True,
            user_id=current_user.id,
            openid=current_user.openid,
            membership_level=current_user.membership_level.value
        )
        
        return DataResponse(
            data=auth_status,
            message="获取认证状态成功"
        )
        
    except Exception as e:
        logger.error(f"获取认证状态异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "获取认证状态失败"
            }
        )


@router.get("/verify", response_model=SuccessResponse, summary="验证访问令牌")
async def verify_token(
    current_user: User = Depends(get_current_user)
):
    """
    验证当前访问令牌是否有效
    
    需要认证，如果令牌有效则返回成功响应
    """
    try:
        logger.debug(f"验证令牌，用户ID: {current_user.id}")
        
        return SuccessResponse(
            message="令牌验证成功"
        )
        
    except Exception as e:
        logger.error(f"令牌验证异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "令牌验证失败"
            }
        )


@router.get("/me", response_model=DataResponse[dict], summary="获取当前用户信息")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前登录用户的详细信息
    
    需要认证，返回用户完整信息
    """
    try:
        logger.debug(f"获取用户信息，用户ID: {current_user.id}")
        
        user_info = {
            "id": current_user.id,
            "openid": current_user.openid,
            "nickname": current_user.nickname,
            "avatar_url": current_user.avatar_url,
            "membership_level": current_user.membership_level.value,
            "membership_expire_at": current_user.membership_expire_at,
            "is_membership_active": current_user.is_membership_active,
            "subscription_limit": current_user.get_subscription_limit(),
            "daily_push_limit": current_user.get_daily_push_limit(),
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at
        }
        
        return DataResponse(
            data=user_info,
            message="获取用户信息成功"
        )
        
    except Exception as e:
        logger.error(f"获取用户信息异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "获取用户信息失败"
            }
        )