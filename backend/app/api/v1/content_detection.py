"""
新内容检测相关API端点
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from app.db.database import get_db
from app.services.content_detection import content_detection_service
from app.services.push_queue import push_queue_service
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import DataResponse
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/content-detection", tags=["内容检测"])


@router.post("/detect", response_model=DataResponse[Dict[str, Any]])
async def detect_new_content(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    手动触发新内容检测
    
    这个端点允许管理员手动触发新内容检测过程
    """
    try:
        logger.info(f"用户 {current_user.id} 手动触发新内容检测")
        
        # 在后台任务中执行检测
        background_tasks.add_task(
            _background_detect_content, db
        )
        
        return DataResponse(
            data={
                "message": "新内容检测已启动",
                "status": "processing"
            },
            message="检测任务已启动"
        )
        
    except Exception as e:
        logger.error(f"手动触发内容检测失败: {str(e)}")
        raise HTTPException(status_code=500, detail="触发内容检测失败")


@router.get("/notifications", response_model=DataResponse[List[Dict[str, Any]]])
async def get_content_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户的内容变更通知
    
    返回用户订阅账号的最新内容变更通知
    """
    try:
        notifications = await content_detection_service.get_content_change_notifications(
            db, current_user.id
        )
        
        return DataResponse(
            data=notifications,
            message=f"获取到 {len(notifications)} 条通知"
        )
        
    except Exception as e:
        logger.error(f"获取内容通知失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取内容通知失败")


@router.get("/queue/status", response_model=DataResponse[Dict[str, Any]])
async def get_push_queue_status(
    current_user: User = Depends(get_current_user)
):
    """
    获取推送队列状态
    
    返回当前推送队列的状态信息
    """
    try:
        # 获取内容检测队列状态
        content_queue_status = await content_detection_service.get_push_queue_status()
        
        # 获取推送队列统计
        push_queue_stats = await push_queue_service.get_queue_statistics()
        
        status = {
            "content_detection_queue": content_queue_status,
            "push_queue": push_queue_stats,
            "overall_status": "active" if content_queue_status.get("status") == "active" else "inactive"
        }
        
        return DataResponse(
            data=status,
            message="获取队列状态成功"
        )
        
    except Exception as e:
        logger.error(f"获取队列状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取队列状态失败")


@router.post("/queue/clear", response_model=DataResponse[Dict[str, Any]])
async def clear_push_queue(
    current_user: User = Depends(get_current_user)
):
    """
    清空推送队列
    
    清空所有推送队列（仅管理员可用）
    """
    try:
        # 清空内容检测队列
        content_cleared = await content_detection_service.clear_push_queue()
        
        # 清空推送队列
        push_cleared = await push_queue_service.clear_all_queues()
        
        result = {
            "content_queue_cleared": content_cleared,
            "push_queue_cleared": push_cleared,
            "success": content_cleared and push_cleared
        }
        
        logger.info(f"用户 {current_user.id} 清空了推送队列")
        
        return DataResponse(
            data=result,
            message="队列清空完成"
        )
        
    except Exception as e:
        logger.error(f"清空队列失败: {str(e)}")
        raise HTTPException(status_code=500, detail="清空队列失败")


@router.post("/queue/retry", response_model=DataResponse[Dict[str, Any]])
async def retry_failed_items(
    max_items: int = 10,
    current_user: User = Depends(get_current_user)
):
    """
    重试失败的推送项目
    
    重新处理失败队列中的推送项目
    """
    try:
        result = await push_queue_service.retry_failed_items(max_items)
        
        logger.info(f"用户 {current_user.id} 重试了 {result.get('retried_count', 0)} 个失败项目")
        
        return DataResponse(
            data=result,
            message=result.get("message", "重试完成")
        )
        
    except Exception as e:
        logger.error(f"重试失败项目失败: {str(e)}")
        raise HTTPException(status_code=500, detail="重试失败项目失败")


async def _background_detect_content(db: AsyncSession):
    """后台内容检测任务"""
    try:
        await content_detection_service.detect_new_content(db)
        logger.info("后台内容检测完成")
    except Exception as e:
        logger.error(f"后台内容检测失败: {str(e)}")