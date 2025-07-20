"""
用户管理API路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_logger

from app.db.database import get_db
from app.services.user import user_service
from app.schemas.user import (
    UserUpdate, UserProfile, MembershipInfo, MembershipUpgrade, UserLimits
)
from app.schemas.common import DataResponse, SuccessResponse
from app.core.deps import get_current_user
from app.core.exceptions import NotFoundException, BusinessException
from app.models.user import User

logger = get_logger(__name__)

router = APIRouter()


@router.get("/profile", response_model=DataResponse[UserProfile], summary="获取用户档案")
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户的详细档案信息
    
    包含用户基本信息、会员状态、订阅统计、推送统计等
    """
    try:
        logger.info(f"获取用户档案请求，用户ID: {current_user.id}")
        
        profile = await user_service.get_user_profile(current_user.id, db)
        
        return DataResponse(
            data=profile,
            message="获取用户档案成功"
        )
        
    except NotFoundException as e:
        logger.error(f"用户档案不存在: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail={
                "code": 404,
                "message": str(e)
            }
        )
    except BusinessException as e:
        logger.error(f"获取用户档案业务异常: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "code": e.error_code,
                "message": e.message
            }
        )
    except Exception as e:
        logger.error(f"获取用户档案未知异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "获取用户档案失败"
            }
        )


@router.put("/profile", response_model=DataResponse[UserProfile], summary="更新用户档案")
async def update_user_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新当前用户的档案信息
    
    - **nickname**: 用户昵称（可选）
    - **avatar_url**: 头像URL（可选）
    """
    try:
        logger.info(f"更新用户档案请求，用户ID: {current_user.id}")
        
        # 转换为字典，排除None值
        update_dict = update_data.model_dump(exclude_unset=True, exclude_none=True)
        
        if not update_dict:
            logger.warning(f"没有提供更新数据，用户ID: {current_user.id}")
            # 如果没有更新数据，直接返回当前档案
            profile = await user_service.get_user_profile(current_user.id, db)
            return DataResponse(
                data=profile,
                message="没有更新数据"
            )
        
        profile = await user_service.update_user_profile(current_user.id, update_dict, db)
        
        return DataResponse(
            data=profile,
            message="用户档案更新成功"
        )
        
    except NotFoundException as e:
        logger.error(f"用户不存在: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail={
                "code": 404,
                "message": str(e)
            }
        )
    except BusinessException as e:
        logger.error(f"更新用户档案业务异常: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "code": e.error_code,
                "message": e.message
            }
        )
    except Exception as e:
        logger.error(f"更新用户档案未知异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "更新用户档案失败"
            }
        )


@router.get("/membership", response_model=DataResponse[MembershipInfo], summary="获取会员信息")
async def get_membership_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户的会员信息
    
    包含会员等级、到期时间、权益列表等
    """
    try:
        logger.info(f"获取会员信息请求，用户ID: {current_user.id}")
        
        membership_info = await user_service.get_membership_info(current_user.id, db)
        
        return DataResponse(
            data=membership_info,
            message="获取会员信息成功"
        )
        
    except NotFoundException as e:
        logger.error(f"用户不存在: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail={
                "code": 404,
                "message": str(e)
            }
        )
    except BusinessException as e:
        logger.error(f"获取会员信息业务异常: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "code": e.error_code,
                "message": e.message
            }
        )
    except Exception as e:
        logger.error(f"获取会员信息未知异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "获取会员信息失败"
            }
        )


@router.post("/membership/upgrade", response_model=DataResponse[MembershipInfo], summary="升级会员")
async def upgrade_membership(
    upgrade_data: MembershipUpgrade,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    升级用户会员等级
    
    - **level**: 目标会员等级（basic/premium）
    - **duration_months**: 购买月数（1-12）
    
    注意：这里只是模拟升级，实际应用中需要集成支付系统
    """
    try:
        logger.info(f"升级会员请求，用户ID: {current_user.id}, 等级: {upgrade_data.level.value}")
        
        membership_info = await user_service.upgrade_membership(
            current_user.id, 
            upgrade_data.level, 
            upgrade_data.duration_months, 
            db
        )
        
        return DataResponse(
            data=membership_info,
            message=f"会员升级成功，等级: {upgrade_data.level.value}"
        )
        
    except NotFoundException as e:
        logger.error(f"用户不存在: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail={
                "code": 404,
                "message": str(e)
            }
        )
    except BusinessException as e:
        logger.error(f"升级会员业务异常: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "code": e.error_code,
                "message": e.message
            }
        )
    except Exception as e:
        logger.error(f"升级会员未知异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "升级会员失败"
            }
        )


@router.get("/limits", response_model=DataResponse[UserLimits], summary="获取用户限制信息")
async def get_user_limits(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户的限制信息
    
    包含订阅限制、推送限制及当前使用情况
    """
    try:
        logger.info(f"获取用户限制信息请求，用户ID: {current_user.id}")
        
        limits = await user_service.get_user_limits(current_user.id, db)
        
        return DataResponse(
            data=limits,
            message="获取用户限制信息成功"
        )
        
    except NotFoundException as e:
        logger.error(f"用户不存在: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail={
                "code": 404,
                "message": str(e)
            }
        )
    except BusinessException as e:
        logger.error(f"获取用户限制信息业务异常: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "code": e.error_code,
                "message": e.message
            }
        )
    except Exception as e:
        logger.error(f"获取用户限制信息未知异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "获取用户限制信息失败"
            }
        )


@router.delete("/account", response_model=SuccessResponse, summary="删除用户账户")
async def delete_user_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除当前用户账户
    
    警告：此操作不可逆，将删除用户的所有数据
    """
    try:
        logger.info(f"删除用户账户请求，用户ID: {current_user.id}")
        
        success = await user_service.delete_user(current_user.id, db)
        
        if success:
            return SuccessResponse(message="用户账户删除成功")
        else:
            return SuccessResponse(
                success=False,
                message="用户账户删除失败"
            )
        
    except NotFoundException as e:
        logger.error(f"用户不存在: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail={
                "code": 404,
                "message": str(e)
            }
        )
    except BusinessException as e:
        logger.error(f"删除用户账户业务异常: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "code": e.error_code,
                "message": e.message
            }
        )
    except Exception as e:
        logger.error(f"删除用户账户未知异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "删除用户账户失败"
            }
        )