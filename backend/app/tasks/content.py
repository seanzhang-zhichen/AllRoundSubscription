"""
内容相关任务
"""
from celery import shared_task
from app.tasks.base import BaseTask
from app.services.content_detection import content_detection_service
from app.db.database import AsyncSessionLocal
from app.core.logging import get_logger
import asyncio

logger = get_logger(__name__)


async def _detect_new_content_async():
    """异步检测新内容"""
    try:
        async with AsyncSessionLocal() as db:
            new_articles = await content_detection_service.detect_new_content(db)
            
            return {
                "success": True,
                "new_articles_count": len(new_articles),
                "push_queue_items": len(new_articles),  # 每篇文章可能对应多个推送
                "articles": new_articles
            }
            
    except Exception as e:
        logger.error(f"异步检测新内容失败: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "new_articles_count": 0,
            "push_queue_items": 0
        }


@shared_task(base=BaseTask, bind=True)
def fetch_new_content(self):
    """获取新内容任务"""
    try:
        logger.info("开始检测新内容...")
        
        # 运行异步内容检测
        result = asyncio.run(_detect_new_content_async())
        
        if result["success"]:
            logger.info(f"新内容检测完成，发现 {result['new_articles_count']} 篇新文章")
            return {
                "status": "success", 
                "message": f"检测完成，发现 {result['new_articles_count']} 篇新文章",
                "new_articles_count": result["new_articles_count"],
                "push_queue_items": result["push_queue_items"]
            }
        else:
            logger.warning(f"新内容检测失败: {result['error']}")
            return {
                "status": "partial_success",
                "message": f"检测过程中出现问题: {result['error']}",
                "new_articles_count": 0
            }
            
    except Exception as exc:
        logger.error(f"新内容检测任务失败: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=60, max_retries=3)


async def _get_notifications_async(user_id: int):
    """异步获取通知"""
    try:
        async with AsyncSessionLocal() as db:
            notifications = await content_detection_service.get_content_change_notifications(
                db, user_id
            )
            
            return {
                "success": True,
                "notification_count": len(notifications),
                "notifications": notifications
            }
            
    except Exception as e:
        logger.error(f"异步获取通知失败: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "notification_count": 0,
            "notifications": []
        }


@shared_task(base=BaseTask, bind=True)
def get_content_change_notifications(self, user_id: int):
    """获取用户内容变更通知任务"""
    try:
        logger.info(f"获取用户 {user_id} 的内容变更通知...")
        
        result = asyncio.run(_get_notifications_async(user_id))
        
        if result["success"]:
            logger.info(f"获取用户 {user_id} 的通知完成，共 {result['notification_count']} 条")
            return {
                "status": "success",
                "message": f"获取通知完成，共 {result['notification_count']} 条",
                "notification_count": result["notification_count"],
                "notifications": result["notifications"]
            }
        else:
            logger.error(f"获取用户通知失败: {result['error']}")
            return {
                "status": "failed",
                "message": f"获取通知失败: {result['error']}",
                "notification_count": 0
            }
            
    except Exception as exc:
        logger.error(f"获取内容变更通知任务失败: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=30, max_retries=2)


async def _get_queue_status_async():
    """异步获取队列状态"""
    try:
        return await content_detection_service.get_push_queue_status()
    except Exception as e:
        logger.error(f"异步获取队列状态失败: {str(e)}", exc_info=True)
        return {"queue_length": 0, "status": "error", "error": str(e)}


@shared_task(base=BaseTask, bind=True)
def get_push_queue_status(self):
    """获取推送队列状态任务"""
    try:
        logger.info("获取推送队列状态...")
        
        result = asyncio.run(_get_queue_status_async())
        
        logger.info(f"推送队列状态: {result}")
        return {
            "status": "success",
            "message": "获取队列状态完成",
            "queue_status": result
        }
        
    except Exception as exc:
        logger.error(f"获取推送队列状态失败: {str(exc)}")
        return {
            "status": "failed",
            "message": f"获取队列状态失败: {str(exc)}",
            "queue_status": {"queue_length": 0, "status": "error"}
        }