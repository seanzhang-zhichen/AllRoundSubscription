"""
订阅管理API路由
"""
from app.core.logging import get_logger
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.subscription import subscription_service
from app.schemas.subscription import (
    SubscriptionCreate, SubscriptionResponse, SubscriptionWithAccount,
    SubscriptionList, SubscriptionStats, BatchSubscriptionCreate,
    BatchSubscriptionResponse
)
from app.schemas.common import BaseResponse, DataResponse, PaginatedResponse
from app.core.exceptions import (
    NotFoundException, BusinessException, SubscriptionLimitException,
    DuplicateException
)

logger = get_logger(__name__)

router = APIRouter()


@router.post("/", response_model=DataResponse[SubscriptionResponse])
async def create_subscription(
    subscription_data: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建订阅关系
    
    - **user_id**: 用户ID（必须与当前登录用户一致）
    - **account_id**: 要订阅的账号ID
    """
    try:
        # 验证用户权限
        if subscription_data.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="只能为自己创建订阅"
            )
        
        result = await subscription_service.create_subscription(subscription_data, db)
        
        return DataResponse(
            code=200,
            message="订阅成功",
            data=result
        )
        
    except SubscriptionLimitException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DuplicateException as e:
        raise HTTPException(status_code=409, detail=str(e))
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"创建订阅失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建订阅失败")


@router.delete("/{account_id}", response_model=DataResponse[bool])
async def delete_subscription(
    account_id: int = Path(..., description="账号ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取消订阅
    
    - **account_id**: 要取消订阅的账号ID
    """
    try:
        result = await subscription_service.delete_subscription(
            current_user.id, account_id, db
        )
        
        return DataResponse(
            code=200,
            message="取消订阅成功",
            data=result
        )
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"取消订阅失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="取消订阅失败")


@router.get("/", response_model=PaginatedResponse[SubscriptionWithAccount])
async def get_user_subscriptions(
    platform: str = Query(None, description="平台筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    order_by: str = Query("created_at", description="排序字段"),
    order_desc: bool = Query(True, description="是否降序"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户订阅列表
    
    - **platform**: 平台筛选（可选）
    - **page**: 页码，从1开始
    - **page_size**: 每页大小，最大100
    - **order_by**: 排序字段（created_at, account_name, latest_article_time）
    - **order_desc**: 是否降序排列
    """
    try:
        query_params = SubscriptionList(
            user_id=current_user.id,
            platform=platform,
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_desc=order_desc
        )
        
        subscriptions, total = await subscription_service.get_user_subscriptions(
            query_params, db
        )
        
        return PaginatedResponse(
            code=200,
            message="获取订阅列表成功",
            data=subscriptions,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )
        
    except BusinessException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取订阅列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取订阅列表失败")


@router.get("/stats", response_model=DataResponse[SubscriptionStats])
async def get_subscription_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户订阅统计信息
    
    包括：
    - 总订阅数和限制
    - 各平台订阅统计
    - 最近订阅列表
    """
    try:
        stats = await subscription_service.get_subscription_stats(
            current_user.id, db
        )
        
        return DataResponse(
            code=200,
            message="获取订阅统计成功",
            data=stats
        )
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取订阅统计失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取订阅统计失败")


@router.post("/batch", response_model=DataResponse[BatchSubscriptionResponse])
async def batch_create_subscriptions(
    batch_data: BatchSubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    批量创建订阅
    
    - **user_id**: 用户ID（必须与当前登录用户一致）
    - **account_ids**: 要订阅的账号ID列表（最多10个）
    """
    try:
        # 验证用户权限
        if batch_data.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="只能为自己创建订阅"
            )
        
        result = await subscription_service.batch_create_subscriptions(batch_data, db)
        
        return DataResponse(
            code=200,
            message="批量订阅完成",
            data=result
        )
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"批量订阅失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="批量订阅失败")


@router.get("/status/{account_id}", response_model=DataResponse[Dict[str, Any]])
async def check_subscription_status(
    account_id: int = Path(..., description="账号ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    检查订阅状态
    
    - **account_id**: 要检查的账号ID
    
    返回订阅状态信息，包括是否已订阅、是否可以订阅等
    """
    try:
        status = await subscription_service.check_subscription_status(
            current_user.id, account_id, db
        )
        
        return DataResponse(
            code=200,
            message="获取订阅状态成功",
            data=status
        )
        
    except Exception as e:
        logger.error(f"检查订阅状态失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="检查订阅状态失败")