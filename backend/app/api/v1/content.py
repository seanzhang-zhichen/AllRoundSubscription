"""
内容相关API路由
"""
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db.database import get_db
from app.services.content import content_service
from app.schemas.article import ArticleWithAccount, ArticleDetail, ArticleStats
from app.schemas.common import PaginatedResponse
from app.core.deps import get_current_user
from app.models.user import User
from app.services.image import image_service
from app.services.platform import platform_service
from app.services.refresh import refresh_service
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/feed", response_model=PaginatedResponse[ArticleWithAccount])
async def get_user_feed(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=50, description="每页大小"),
    refresh: bool = Query(default=False, description="是否刷新缓存"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户动态流
    
    获取当前用户订阅的所有博主的最新动态，支持分页加载和缓存优化。
    
    - **page**: 页码，从1开始
    - **page_size**: 每页大小，最大50
    - **refresh**: 是否刷新缓存获取最新内容
    """
    logger.info(f"用户 {current_user.id} 获取动态流，页码: {page}")
    
    result = await content_service.get_user_feed(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        refresh=refresh
    )
    
    return result


@router.get("/articles/{article_id}", response_model=ArticleDetail)
async def get_article_detail(
    article_id: int = Path(..., description="文章ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取文章详情
    
    获取指定文章的详细信息，包括相关文章和订阅状态。
    
    - **article_id**: 文章ID
    """
    logger.info(f"用户 {current_user.id} 获取文章详情: {article_id}")
    
    result = await content_service.get_article_detail(
        db=db,
        article_id=article_id,
        user_id=current_user.id
    )
    
    return result


@router.get("/accounts/{account_id}/articles", response_model=PaginatedResponse[ArticleWithAccount])
async def get_articles_by_account(
    account_id: int = Path(..., description="账号ID"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=50, description="每页大小"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定账号的文章列表
    
    获取指定博主账号的所有文章，按发布时间倒序排列。
    
    - **account_id**: 账号ID
    - **page**: 页码，从1开始
    - **page_size**: 每页大小，最大50
    """
    logger.info(f"用户 {current_user.id} 获取账号 {account_id} 的文章列表")
    
    result = await content_service.get_articles_by_account(
        db=db,
        account_id=account_id,
        page=page,
        page_size=page_size
    )
    
    return result


@router.get("/stats", response_model=ArticleStats)
async def get_content_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取内容统计信息
    
    获取当前用户订阅内容的统计信息，包括总数、今日数量、本周数量和各平台分布。
    """
    logger.info(f"用户 {current_user.id} 获取内容统计")
    
    result = await content_service.get_content_stats(
        db=db,
        user_id=current_user.id
    )
    
    return result


@router.post("/feed/refresh")
async def refresh_feed_cache(
    current_user: User = Depends(get_current_user)
):
    """
    刷新动态流缓存
    
    手动刷新当前用户的动态流缓存，强制获取最新内容。
    """
    logger.info(f"用户 {current_user.id} 刷新动态流缓存")
    
    success = await content_service.refresh_user_feed_cache(current_user.id)
    
    return {
        "success": success,
        "message": "缓存刷新成功" if success else "缓存刷新失败"
    }


@router.get("/platforms")
async def get_supported_platforms():
    """
    获取支持的平台列表
    
    获取所有支持的内容平台信息，包括平台标识、显示名称、图标等。
    """
    platforms = platform_service.get_supported_platforms()
    
    return {
        "success": True,
        "data": platforms,
        "total": len(platforms)
    }


@router.get("/platforms/{platform}/info")
async def get_platform_info(
    platform: str = Path(..., description="平台标识")
):
    """
    获取指定平台的详细信息
    
    获取平台的配置信息，包括显示名称、颜色、特性等。
    
    - **platform**: 平台标识 (wechat, weibo, twitter, etc.)
    """
    platform_info = platform_service.get_platform_info(platform)
    
    return {
        "success": True,
        "data": platform_info,
        "platform": platform
    }


@router.post("/articles/{article_id}/read")
async def mark_article_as_read(
    article_id: int = Path(..., description="文章ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    标记文章为已读
    
    - **article_id**: 文章ID
    """
    logger.info(f"用户 {current_user.id} 标记文章 {article_id} 为已读")
    
    result = await content_service.mark_article_as_read(
        db=db,
        article_id=article_id,
        user_id=current_user.id
    )
    
    return {
        "success": True,
        "message": "标记成功"
    }


@router.post("/articles/{article_id}/favorite")
async def favorite_article(
    article_id: int = Path(..., description="文章ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    收藏文章
    
    - **article_id**: 文章ID
    """
    logger.info(f"用户 {current_user.id} 收藏文章 {article_id}")
    
    result = await content_service.favorite_article(
        db=db,
        article_id=article_id,
        user_id=current_user.id
    )
    
    return {
        "success": True,
        "message": "收藏成功"
    }


@router.delete("/articles/{article_id}/favorite")
async def unfavorite_article(
    article_id: int = Path(..., description="文章ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取消收藏文章
    
    - **article_id**: 文章ID
    """
    logger.info(f"用户 {current_user.id} 取消收藏文章 {article_id}")
    
    result = await content_service.unfavorite_article(
        db=db,
        article_id=article_id,
        user_id=current_user.id
    )
    
    return {
        "success": True,
        "message": "取消收藏成功"
    }


@router.post("/articles/{article_id}/share")
async def share_article(
    article_id: int = Path(..., description="文章ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    记录文章分享统计
    
    - **article_id**: 文章ID
    """
    logger.info(f"用户 {current_user.id} 分享文章 {article_id}")
    
    result = await content_service.share_article(
        db=db,
        article_id=article_id,
        user_id=current_user.id
    )
    
    return {
        "success": True,
        "message": "分享记录成功"
    }


@router.get("/articles/search")
async def search_articles(
    keyword: str = Query(..., description="搜索关键词"),
    platform: Optional[str] = Query(None, description="平台筛选"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=50, description="每页大小"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    搜索文章
    
    - **keyword**: 搜索关键词
    - **platform**: 平台筛选（可选）
    - **page**: 页码，从1开始
    - **page_size**: 每页大小，最大50
    """
    logger.info(f"用户 {current_user.id} 搜索文章: {keyword}")
    
    result = await content_service.search_articles(
        db=db,
        keyword=keyword,
        platform=platform,
        page=page,
        page_size=page_size,
        user_id=current_user.id
    )
    
    return result


@router.post("/articles/{article_id}/images/optimize")
async def optimize_article_images(
    article_id: int = Path(..., description="文章ID"),
    lazy_load: bool = Query(default=True, description="是否启用懒加载"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    优化文章图片显示
    
    为指定文章的图片生成优化配置，包括缩略图、响应式尺寸等。
    
    - **article_id**: 文章ID
    - **lazy_load**: 是否启用懒加载
    """
    # 获取文章信息
    article_detail = await content_service.get_article_detail(
        db=db,
        article_id=article_id,
        user_id=current_user.id
    )
    
    if not article_detail.images:
        return {
            "success": True,
            "message": "文章无图片",
            "optimized_images": []
        }
    
    # 处理图片
    processed_images = image_service.process_article_images(
        article_detail.images, 
        article_detail.account_platform
    )
    
    # 优化图片加载
    optimized_images = image_service.optimize_image_loading(
        article_detail.images, 
        lazy_load
    )
    
    return {
        "success": True,
        "article_id": article_id,
        "processed_images": processed_images,
        "optimized_images": optimized_images
    }


@router.post("/refresh")
async def refresh_user_content(
    force: bool = Query(default=False, description="是否强制刷新"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    刷新用户内容
    
    刷新当前用户订阅的所有账号的最新内容。
    
    - **force**: 是否强制刷新，忽略频率限制
    """
    logger.info(f"用户 {current_user.id} 请求刷新内容，强制: {force}")
    
    result = await refresh_service.refresh_user_content(
        db=db,
        user_id=current_user.id,
        force=force
    )
    
    return result


@router.get("/refresh/status")
async def get_refresh_status(
    current_user: User = Depends(get_current_user)
):
    """
    获取刷新状态
    
    获取当前用户的内容刷新状态信息。
    """
    status = await refresh_service.get_refresh_status(current_user.id)
    
    return {
        "success": True,
        "data": status
    }


@router.post("/accounts/{account_id}/refresh")
async def refresh_account_content(
    account_id: int = Path(..., description="账号ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    刷新指定账号内容
    
    刷新指定博主账号的最新内容。
    
    - **account_id**: 账号ID
    """
    logger.info(f"用户 {current_user.id} 请求刷新账号 {account_id} 的内容")
    
    result = await refresh_service.refresh_account_content(
        db=db,
        account_id=account_id
    )
    
    return result