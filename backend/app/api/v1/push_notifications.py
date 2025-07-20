"""
推送通知管理API端点
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime, date

from app.db.database import get_db
from app.services.push_notification import push_notification_service
from app.services.push_queue import push_queue_service
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import DataResponse, PaginatedResponse
from app.models.push_record import PushStatus
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/push-notifications", tags=["推送通知"])


@router.post("/send", response_model=DataResponse[Dict[str, Any]])
async def send_push_notification(
    user_id: int,
    article_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    手动发送推送通知
    
    Args:
        user_id: 目标用户ID
        article_id: 文章ID
    """
    try:
        result = await push_notification_service.send_article_notification(
            db, user_id, article_id
        )
        
        if result["success"]:
            return DataResponse(
                data=result,
                message="推送发送成功"
            )
        else:
            return DataResponse(
                data=result,
                message=result.get("error", "推送发送失败")
            )
        
    except Exception as e:
        logger.error(f"发送推送通知失败: {str(e)}")
        raise HTTPException(status_code=500, detail="发送推送通知失败")


@router.post("/batch-send", response_model=DataResponse[Dict[str, Any]])
async def batch_send_notifications(
    user_ids: List[int],
    article_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    批量发送推送通知
    
    Args:
        user_ids: 目标用户ID列表
        article_id: 文章ID
    """
    try:
        if len(user_ids) > 100:
            raise HTTPException(status_code=400, detail="批量推送用户数量不能超过100个")
        
        result = await push_notification_service.batch_send_notifications(
            db, user_ids, article_id
        )
        
        return DataResponse(
            data=result,
            message=f"批量推送完成，成功: {result['success_count']}, 失败: {result['failed_count']}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量发送推送通知失败: {str(e)}")
        raise HTTPException(status_code=500, detail="批量发送推送通知失败")


@router.get("/statistics", response_model=DataResponse[Dict[str, Any]])
async def get_push_statistics(
    user_id: Optional[int] = Query(None, description="用户ID，不传则获取当前用户统计"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取推送统计信息
    
    Args:
        user_id: 用户ID，不传则获取当前用户统计
    """
    try:
        target_user_id = user_id if user_id else current_user.id
        
        statistics = await push_notification_service.get_user_push_statistics(
            db, target_user_id
        )
        
        return DataResponse(
            data=statistics,
            message="获取推送统计成功"
        )
        
    except Exception as e:
        logger.error(f"获取推送统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取推送统计失败")


@router.get("/records", response_model=PaginatedResponse[Dict[str, Any]])
async def get_push_records(
    user_id: Optional[int] = Query(None, description="用户ID筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取推送记录列表
    
    Args:
        user_id: 用户ID筛选
        status: 状态筛选 (pending/success/failed/skipped)
        start_date: 开始日期
        end_date: 结束日期
        page: 页码
        page_size: 每页大小
    """
    try:
        # 验证状态参数
        if status and status not in [s.value for s in PushStatus]:
            raise HTTPException(status_code=400, detail="无效的状态参数")
        
        # 转换日期为datetime
        start_time = datetime.combine(start_date, datetime.min.time()) if start_date else None
        end_time = datetime.combine(end_date, datetime.max.time()) if end_date else None
        
        result = await push_notification_service.get_push_records(
            db=db,
            user_id=user_id,
            status=status,
            start_time=start_time,
            end_time=end_time,
            page=page,
            page_size=page_size
        )
        
        return PaginatedResponse(
            data=result["records"],
            pagination=result["pagination"],
            message=f"获取到 {len(result['records'])} 条推送记录"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取推送记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取推送记录失败")


@router.post("/retry/{push_record_id}", response_model=DataResponse[Dict[str, Any]])
async def retry_push_notification(
    push_record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    重试失败的推送通知
    
    Args:
        push_record_id: 推送记录ID
    """
    try:
        result = await push_notification_service.retry_failed_push(
            db, push_record_id
        )
        
        if result["success"]:
            return DataResponse(
                data=result,
                message="推送重试成功"
            )
        else:
            return DataResponse(
                data=result,
                message=result.get("error", "推送重试失败")
            )
        
    except Exception as e:
        logger.error(f"重试推送通知失败: {str(e)}")
        raise HTTPException(status_code=500, detail="重试推送通知失败")


@router.get("/queue/status", response_model=DataResponse[Dict[str, Any]])
async def get_push_queue_status(
    current_user: User = Depends(get_current_user)
):
    """
    获取推送队列状态
    """
    try:
        status = await push_queue_service.get_queue_statistics()
        
        return DataResponse(
            data=status,
            message="获取队列状态成功"
        )
        
    except Exception as e:
        logger.error(f"获取队列状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取队列状态失败")


@router.post("/queue/retry", response_model=DataResponse[Dict[str, Any]])
async def retry_failed_queue_items(
    max_items: int = Query(10, ge=1, le=100, description="最大重试数量"),
    current_user: User = Depends(get_current_user)
):
    """
    重试失败队列中的项目
    
    Args:
        max_items: 最大重试数量
    """
    try:
        result = await push_queue_service.retry_failed_items(max_items)
        
        return DataResponse(
            data=result,
            message=result.get("message", "重试完成")
        )
        
    except Exception as e:
        logger.error(f"重试失败队列项目失败: {str(e)}")
        raise HTTPException(status_code=500, detail="重试失败队列项目失败")


@router.delete("/queue/clear", response_model=DataResponse[Dict[str, Any]])
async def clear_push_queues(
    current_user: User = Depends(get_current_user)
):
    """
    清空推送队列（管理员功能）
    """
    try:
        success = await push_queue_service.clear_all_queues()
        
        if success:
            logger.info(f"用户 {current_user.id} 清空了推送队列")
            return DataResponse(
                data={"cleared": True},
                message="推送队列已清空"
            )
        else:
            return DataResponse(
                data={"cleared": False},
                message="清空推送队列失败"
            )
        
    except Exception as e:
        logger.error(f"清空推送队列失败: {str(e)}")
        raise HTTPException(status_code=500, detail="清空推送队列失败")


@router.get("/templates/test", response_model=DataResponse[Dict[str, Any]])
async def test_template_message(
    current_user: User = Depends(get_current_user)
):
    """
    测试模板消息发送
    """
    try:
        from app.services.wechat import wechat_service
        
        # 发送测试消息
        test_article_data = {
            "id": 999999,
            "title": "这是一条测试推送消息",
            "account_name": "测试博主",
            "platform_display_name": "测试平台"
        }
        
        result = await wechat_service.send_push_notification(
            user_openid=current_user.openid,
            article_data=test_article_data
        )
        
        return DataResponse(
            data=result,
            message="测试消息发送完成"
        )
        
    except Exception as e:
        logger.error(f"测试模板消息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="测试模板消息失败")


@router.get("/limits", response_model=DataResponse[Dict[str, Any]])
async def get_push_limits(
    user_id: Optional[int] = Query(None, description="用户ID，不传则获取当前用户限制"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户推送限制信息
    
    Args:
        user_id: 用户ID，不传则获取当前用户限制
    """
    try:
        from app.services.limits import limits_service
        
        target_user_id = user_id if user_id else current_user.id
        
        limits_info = await limits_service.get_user_limits(target_user_id, db)
        push_check = await limits_service.check_push_limit(
            target_user_id, db, raise_exception=False
        )
        
        result = {
            **limits_info,
            "push_check": push_check
        }
        
        return DataResponse(
            data=result,
            message="获取推送限制信息成功"
        )
        
    except Exception as e:
        logger.error(f"获取推送限制信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取推送限制信息失败")


@router.get("/statistics/system", response_model=DataResponse[Dict[str, Any]])
async def get_system_push_statistics(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    use_cache: bool = Query(True, description="是否使用缓存"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取系统级推送统计
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        use_cache: 是否使用缓存
    """
    try:
        from app.services.push_statistics import push_statistics_service
        
        # 生成缓存键
        cache_key = f"system_{start_date}_{end_date}"
        
        # 尝试从缓存获取
        if use_cache:
            cached_data = await push_statistics_service.get_cached_statistics(cache_key)
            if cached_data:
                return DataResponse(
                    data=cached_data,
                    message="获取系统推送统计成功（缓存）"
                )
        
        # 从数据库获取
        statistics = await push_statistics_service.get_system_push_statistics(
            db, start_date, end_date
        )
        
        # 缓存结果
        if use_cache and "error" not in statistics:
            await push_statistics_service.cache_statistics(cache_key, statistics)
        
        return DataResponse(
            data=statistics,
            message="获取系统推送统计成功"
        )
        
    except Exception as e:
        logger.error(f"获取系统推送统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取系统推送统计失败")


@router.get("/statistics/platform", response_model=DataResponse[Dict[str, Any]])
async def get_platform_push_statistics(
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    use_cache: bool = Query(True, description="是否使用缓存"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取按平台分组的推送统计
    
    Args:
        days: 统计天数
        use_cache: 是否使用缓存
    """
    try:
        from app.services.push_statistics import push_statistics_service
        
        # 生成缓存键
        cache_key = f"platform_{days}"
        
        # 尝试从缓存获取
        if use_cache:
            cached_data = await push_statistics_service.get_cached_statistics(cache_key)
            if cached_data:
                return DataResponse(
                    data=cached_data,
                    message="获取平台推送统计成功（缓存）"
                )
        
        # 从数据库获取
        statistics = await push_statistics_service.get_platform_push_statistics(
            db, days
        )
        
        # 缓存结果
        if use_cache and "error" not in statistics:
            await push_statistics_service.cache_statistics(cache_key, statistics, 600)  # 10分钟缓存
        
        return DataResponse(
            data=statistics,
            message="获取平台推送统计成功"
        )
        
    except Exception as e:
        logger.error(f"获取平台推送统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取平台推送统计失败")


@router.get("/statistics/active-users", response_model=DataResponse[List[Dict[str, Any]]])
async def get_top_active_users(
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    days: int = Query(30, ge=1, le=90, description="统计天数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取推送最活跃的用户
    
    Args:
        limit: 返回数量
        days: 统计天数
    """
    try:
        from app.services.push_statistics import push_statistics_service
        
        active_users = await push_statistics_service.get_top_active_users(
            db, limit, days
        )
        
        return DataResponse(
            data=active_users,
            message=f"获取到 {len(active_users)} 个活跃用户"
        )
        
    except Exception as e:
        logger.error(f"获取活跃用户失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取活跃用户失败")


@router.get("/statistics/failure-analysis", response_model=DataResponse[Dict[str, Any]])
async def get_push_failure_analysis(
    days: int = Query(7, ge=1, le=30, description="分析天数"),
    use_cache: bool = Query(True, description="是否使用缓存"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取推送失败分析
    
    Args:
        days: 分析天数
        use_cache: 是否使用缓存
    """
    try:
        from app.services.push_statistics import push_statistics_service
        
        # 生成缓存键
        cache_key = f"failure_analysis_{days}"
        
        # 尝试从缓存获取
        if use_cache:
            cached_data = await push_statistics_service.get_cached_statistics(cache_key)
            if cached_data:
                return DataResponse(
                    data=cached_data,
                    message="获取推送失败分析成功（缓存）"
                )
        
        # 从数据库获取
        analysis = await push_statistics_service.get_push_failure_analysis(
            db, days
        )
        
        # 缓存结果
        if use_cache and "error" not in analysis:
            await push_statistics_service.cache_statistics(cache_key, analysis, 1800)  # 30分钟缓存
        
        return DataResponse(
            data=analysis,
            message="获取推送失败分析成功"
        )
        
    except Exception as e:
        logger.error(f"获取推送失败分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取推送失败分析失败")