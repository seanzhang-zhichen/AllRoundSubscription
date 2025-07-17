"""
搜索相关API接口
"""
import time
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.exceptions import BusinessException
from app.models.user import User
from app.models.account import Platform
from app.services.search.service import search_service
from app.schemas.common import DataResponse, PaginatedResponse
from app.schemas.search import (
    SearchRequest, 
    SearchResponse, 
    PlatformSearchRequest,
    PlatformStatusResponse,
    SearchStatisticsResponse,
    SupportedPlatformsResponse
)
from app.schemas.account import AccountResponse, PlatformInfo
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/accounts", response_model=DataResponse[SearchResponse], summary="搜索博主账号")
async def search_accounts(
    keyword: str = Query(..., min_length=1, max_length=100, description="搜索关键词"),
    platforms: Optional[str] = Query(None, description="指定平台列表，用逗号分隔"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页大小"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    搜索博主账号接口
    
    - **keyword**: 搜索关键词，支持博主名称、描述等
    - **platforms**: 可选，指定搜索的平台列表，用逗号分隔（如：wechat,weibo）
    - **page**: 页码，从1开始
    - **page_size**: 每页大小，最大100
    
    返回搜索结果列表，按相关性排序
    """
    try:
        start_time = time.time()
        
        # 解析平台列表
        platform_list = None
        if platforms:
            platform_list = [p.strip() for p in platforms.split(',') if p.strip()]
            # 验证平台有效性
            valid_platforms = [p.value for p in Platform]
            for platform in platform_list:
                if platform not in valid_platforms:
                    raise HTTPException(
                        status_code=400,
                        detail=f"不支持的平台类型: {platform}，支持的平台: {valid_platforms}"
                    )
        
        # 执行搜索
        search_result = await search_service.search_accounts(
            keyword=keyword.strip(),
            platforms=platform_list,
            page=page,
            page_size=page_size
        )
        
        # 计算搜索耗时
        search_time_ms = int((time.time() - start_time) * 1000)
        
        # 构建响应
        response = SearchResponse(
            accounts=search_result.accounts,
            total=search_result.total,
            page=search_result.page,
            page_size=search_result.page_size,
            platform=search_result.platform,
            has_more=search_result.has_more,
            search_time_ms=search_time_ms
        )
        
        logger.info(
            f"用户 {current_user.id} 搜索博主: 关键词='{keyword}', "
            f"平台={platform_list}, 结果数={search_result.total}, "
            f"耗时={search_time_ms}ms"
        )
        
        return DataResponse.success(
            data=response,
            message=f"搜索完成，找到 {search_result.total} 个结果"
        )
        
    except BusinessException as e:
        logger.warning(f"搜索业务异常: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"搜索服务异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="搜索服务暂时不可用")


@router.get("/platforms/{platform}/accounts", response_model=DataResponse[SearchResponse], summary="在指定平台搜索博主")
async def search_accounts_by_platform(
    platform: str,
    keyword: str = Query(..., min_length=1, max_length=100, description="搜索关键词"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页大小"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    在指定平台搜索博主账号
    
    - **platform**: 平台标识（wechat, weibo, twitter等）
    - **keyword**: 搜索关键词
    - **page**: 页码，从1开始
    - **page_size**: 每页大小，最大100
    
    返回该平台的搜索结果
    """
    try:
        start_time = time.time()
        
        # 验证平台有效性
        valid_platforms = [p.value for p in Platform]
        if platform not in valid_platforms:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的平台类型: {platform}，支持的平台: {valid_platforms}"
            )
        
        # 执行平台搜索
        search_result = await search_service.search_by_platform(
            keyword=keyword.strip(),
            platform=platform,
            page=page,
            page_size=page_size
        )
        
        # 计算搜索耗时
        search_time_ms = int((time.time() - start_time) * 1000)
        
        # 构建响应
        response = SearchResponse(
            accounts=search_result.accounts,
            total=search_result.total,
            page=search_result.page,
            page_size=search_result.page_size,
            platform=search_result.platform,
            has_more=search_result.has_more,
            search_time_ms=search_time_ms
        )
        
        logger.info(
            f"用户 {current_user.id} 在平台 {platform} 搜索博主: "
            f"关键词='{keyword}', 结果数={search_result.total}, "
            f"耗时={search_time_ms}ms"
        )
        
        return DataResponse.success(
            data=response,
            message=f"在 {platform} 平台找到 {search_result.total} 个结果"
        )
        
    except BusinessException as e:
        logger.warning(f"平台搜索业务异常: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"平台搜索服务异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="搜索服务暂时不可用")


@router.get("/platforms", response_model=DataResponse[SupportedPlatformsResponse], summary="获取支持的平台列表")
async def get_supported_platforms(
    current_user: User = Depends(get_current_user)
):
    """
    获取支持的平台列表
    
    返回系统支持的所有搜索平台信息
    """
    try:
        # 获取平台信息
        platform_names = {
            "wechat": "微信公众号",
            "weibo": "微博",
            "twitter": "推特",
            "douyin": "抖音",
            "xiaohongshu": "小红书"
        }
        
        platform_descriptions = {
            "wechat": "微信公众号平台，支持搜索公众号账号",
            "weibo": "新浪微博平台，支持搜索微博用户",
            "twitter": "推特平台，支持搜索推特用户",
            "douyin": "抖音平台，支持搜索抖音创作者",
            "xiaohongshu": "小红书平台，支持搜索小红书博主"
        }
        
        # 获取支持的平台列表
        supported_platforms = search_service.get_supported_platforms()
        
        # 构建平台信息列表
        platforms = []
        enabled_count = 0
        
        for platform_value in [p.value for p in Platform]:
            is_supported = platform_value in supported_platforms
            if is_supported:
                enabled_count += 1
            
            platform_info = PlatformInfo(
                platform=platform_value,
                display_name=platform_names.get(platform_value, platform_value),
                is_supported=is_supported,
                description=platform_descriptions.get(platform_value)
            )
            platforms.append(platform_info)
        
        response = SupportedPlatformsResponse(
            platforms=platforms,
            total=len(platforms),
            enabled_count=enabled_count
        )
        
        logger.info(f"用户 {current_user.id} 获取支持的平台列表")
        
        return DataResponse.success(
            data=response,
            message=f"获取成功，共支持 {enabled_count} 个平台"
        )
        
    except Exception as e:
        logger.error(f"获取平台列表异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取平台列表失败")


@router.get("/statistics", response_model=DataResponse[SearchStatisticsResponse], summary="获取搜索统计信息")
async def get_search_statistics(
    current_user: User = Depends(get_current_user)
):
    """
    获取搜索统计信息
    
    返回搜索服务的统计信息，包括平台状态、缓存统计等
    """
    try:
        # 获取搜索统计信息
        stats = await search_service.get_search_statistics()
        
        response = SearchStatisticsResponse(
            supported_platforms=stats["supported_platforms"],
            registered_adapters=stats["registered_adapters"],
            platform_status=stats["platform_status"],
            cache_stats=stats["cache_stats"],
            timestamp=stats["timestamp"]
        )
        
        logger.info(f"用户 {current_user.id} 获取搜索统计信息")
        
        return DataResponse.success(
            data=response,
            message="获取搜索统计信息成功"
        )
        
    except Exception as e:
        logger.error(f"获取搜索统计信息异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取统计信息失败")


@router.get("/accounts/{account_id}", response_model=DataResponse[AccountResponse], summary="根据平台账号ID获取账号信息")
async def get_account_by_platform_id(
    account_id: str,
    platform: str = Query(..., description="平台标识"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    根据平台账号ID获取账号详细信息
    
    - **account_id**: 平台账号ID
    - **platform**: 平台标识
    
    返回账号详细信息
    """
    try:
        # 验证平台有效性
        valid_platforms = [p.value for p in Platform]
        if platform not in valid_platforms:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的平台类型: {platform}，支持的平台: {valid_platforms}"
            )
        
        # 获取账号信息
        account = await search_service.get_account_by_platform_id(
            platform=platform,
            account_id=account_id
        )
        
        if not account:
            raise HTTPException(
                status_code=404,
                detail=f"在平台 {platform} 上未找到账号 {account_id}"
            )
        
        logger.info(
            f"用户 {current_user.id} 获取账号信息: "
            f"平台={platform}, 账号ID={account_id}"
        )
        
        return DataResponse.success(
            data=account,
            message="获取账号信息成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取账号信息异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取账号信息失败")