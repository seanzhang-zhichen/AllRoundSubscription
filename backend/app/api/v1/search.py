"""
搜索相关API接口
"""
import time
import traceback
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, HTTPException
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
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/accounts", response_model=DataResponse[SearchResponse], summary="搜索博主账号")
async def search_accounts(
    keyword: Optional[str] = Query(None, min_length=1, max_length=100, description="搜索关键词，为空时获取所有博主"),
    platforms: Optional[str] = Query(None, description="指定平台列表，用逗号分隔"),
    page: int = Query(default=0, description="页码"),
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
        
        # 打印详细的请求参数
        print("="*50)
        print("搜索博主请求参数:")
        print(f"关键词: '{keyword}'")
        print(f"平台列表: {platforms}")
        print(f"页码: {page}, 每页大小: {page_size}")
        print(f"用户ID: {current_user.id}")
        print("="*50)
        
        # 解析平台列表
        platform_list = None
        if platforms and platforms.lower() != 'undefined':
            platform_list = [p.strip() for p in platforms.split(',') if p.strip()]
            # 验证平台有效性
            valid_platforms = [p.value for p in Platform]
            for platform in platform_list:
                if platform not in valid_platforms:
                    raise HTTPException(
                        status_code=400,
                        detail=f"不支持的平台类型: {platform}，支持的平台: {valid_platforms}"
                    )
        
        # 执行搜索或获取所有博主
        if keyword and keyword.strip():
            print(f"执行关键词搜索: '{keyword.strip()}'")
            search_result = await search_service.search_accounts(
                keyword=keyword.strip(),
                platforms=platform_list,
                page=page,
                page_size=page_size
            )
        else:
            print("获取所有博主")
            # 获取所有博主
            search_result = await search_service.get_all_accounts(
                platforms=platform_list,
                page=page,
                page_size=page_size
            )
        
        # 计算搜索耗时
        search_time_ms = int((time.time() - start_time) * 1000)
        
        # 打印详细的搜索结果
        print("="*50)
        print("搜索结果:")
        print(f"总结果数: {search_result.total}")
        print(f"当前页结果数: {len(search_result.accounts)}")
        print(f"耗时: {search_time_ms}ms")
        
        if search_result.accounts:
            print(f"首条结果: {search_result.accounts[0].name} (平台: {search_result.accounts[0].platform})")
            print("所有结果ID列表:")
            for i, account in enumerate(search_result.accounts):
                print(f"  {i+1}. ID: {account.id}, 名称: {account.name}, 平台: {account.platform}")
        else:
            print("没有找到匹配的结果!")
        print("="*50)
        
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
        
        action = "搜索博主" if keyword and keyword.strip() else "获取所有博主"
        logger.info(
            f"用户 {current_user.id} {action}: 关键词='{keyword or '无'}', "
            f"平台={platform_list}, 结果数={search_result.total}, "
            f"耗时={search_time_ms}ms"
        )
        
        return DataResponse(
            data=response,
            message=f"搜索完成，找到 {search_result.total} 个结果"
        )
        
    except BusinessException as e:
        logger.warning(f"搜索业务异常: {e.message}")
        print(f"搜索业务异常: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"搜索服务异常: {str(e)}", exc_info=True)
        print(f"搜索服务异常: {str(e)}")
        traceback.print_exc()
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
        
        return DataResponse(
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
            "weixin": "微信公众号",
            "weibo": "微博",
            "twitter": "推特",
            "bilibili": "哔哩哔哩",
            "douyin": "抖音",
            "zhihu": "知乎",
            "xiaohongshu": "小红书"
        }
        
        platform_descriptions = {
            "wechat": "微信公众号平台，支持搜索公众号账号",
            "weixin": "微信公众号平台，支持搜索公众号账号",
            "weibo": "新浪微博平台，支持搜索微博用户",
            "twitter": "推特平台，支持搜索推特用户",
            "bilibili": "哔哩哔哩平台，支持搜索UP主",
            "douyin": "抖音平台，支持搜索抖音创作者",
            "zhihu": "知乎平台，支持搜索知乎用户",
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
        
        return DataResponse(
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
        
        return DataResponse(
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
        
        return DataResponse(
            data=account,
            message="获取账号信息成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取账号信息异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取账号信息失败")


@router.get("/accounts/by-id/{account_id}", response_model=DataResponse[AccountResponse], summary="根据账号ID获取账号信息")
async def get_account_by_id(
    account_id: str = Path(..., description="账号ID"),
    platform: str = Query(None, description="平台类型，如wechat、weibo、twitter等"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    根据账号ID获取账号详细信息
    
    - **account_id**: 账号ID
    - **platform**: 平台类型，如wechat、weibo、twitter等
    - **source**: 订阅来源，如search、included
    
    返回账号详细信息
    """
    try:
        # 获取账号信息
        account = await search_service.get_account_by_id(account_id, db, platform)
        
        if not account:
            raise HTTPException(
                status_code=404,
                detail=f"未找到账号 {account_id}"
            )
        
        logger.info(
            f"用户 {current_user.id} 获取账号信息: "
            f"账号ID={account_id}, 平台={platform or '所有平台'}"
        )
        
        return DataResponse(
            data=account,
            message="获取账号信息成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取账号信息异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取账号信息失败")