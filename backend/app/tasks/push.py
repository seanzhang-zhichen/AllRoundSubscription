"""
推送相关任务
"""
from celery import shared_task
from app.tasks.base import BaseTask
from app.services.push_queue import push_queue_service
from app.db.database import AsyncSessionLocal
from app.core.logging import get_logger
import asyncio

logger = get_logger(__name__)


async def _process_push_queue_async():
    """异步处理推送队列"""
    try:
        processed_items = 0
        failed_items = 0
        
        async with AsyncSessionLocal() as db:
            # 处理队列中的项目，最多处理10个
            for _ in range(10):
                push_item = await push_queue_service.get_next_push_item()
                if not push_item:
                    break
                
                result = await push_queue_service.process_push_item(db, push_item)
                
                if result["success"]:
                    processed_items += 1
                    logger.debug(
                        f"处理推送项目成功 - 文章ID: {result.get('article_id')}, "
                        f"处理用户: {result.get('processed_users')}"
                    )
                else:
                    failed_items += 1
                    logger.warning(
                        f"处理推送项目失败: {result.get('error')}"
                    )
        
        return {
            "success": True,
            "processed_items": processed_items,
            "failed_items": failed_items,
            "total_items": processed_items + failed_items
        }
        
    except Exception as e:
        logger.error(f"异步处理推送队列失败: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "processed_items": 0,
            "failed_items": 0
        }


@shared_task(base=BaseTask, bind=True)
def send_pending_notifications(self):
    """发送待推送通知任务"""
    try:
        logger.info("开始处理推送队列...")
        
        # 运行异步推送处理
        result = asyncio.run(_process_push_queue_async())
        
        if result["success"]:
            logger.info(
                f"推送队列处理完成 - 处理: {result['processed_items']}, "
                f"失败: {result['failed_items']}"
            )
            return {
                "status": "success",
                "message": f"处理了 {result['processed_items']} 个推送项目",
                "processed_items": result["processed_items"],
                "failed_items": result["failed_items"]
            }
        else:
            logger.error(f"推送队列处理失败: {result['error']}")
            return {
                "status": "failed",
                "message": f"推送队列处理失败: {result['error']}",
                "processed_items": 0,
                "failed_items": 0
            }
            
    except Exception as exc:
        logger.error(f"推送队列处理任务失败: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=30, max_retries=5)


async def _get_queue_stats_async():
    """异步获取队列统计"""
    try:
        return await push_queue_service.get_queue_statistics()
    except Exception as e:
        logger.error(f"异步获取队列统计失败: {str(e)}", exc_info=True)
        return {"status": "error", "error": str(e)}


@shared_task(base=BaseTask, bind=True)
def get_push_queue_statistics(self):
    """获取推送队列统计任务"""
    try:
        logger.info("获取推送队列统计...")
        
        result = asyncio.run(_get_queue_stats_async())
        
        logger.info(f"推送队列统计: {result}")
        return {
            "status": "success",
            "message": "获取队列统计完成",
            "statistics": result
        }
        
    except Exception as exc:
        logger.error(f"获取推送队列统计失败: {str(exc)}", exc_info=True)
        return {
            "status": "failed",
            "message": f"获取队列统计失败: {str(exc)}",
            "statistics": {"status": "error"}
        }


async def _retry_failed_items_async(max_items: int = 10):
    """异步重试失败项目"""
    try:
        return await push_queue_service.retry_failed_items(max_items)
    except Exception as e:
        logger.error(f"异步重试失败项目失败: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


@shared_task(base=BaseTask, bind=True)
def retry_failed_push_items(self, max_items: int = 10):
    """重试失败的推送项目任务"""
    try:
        logger.info(f"开始重试失败的推送项目，最多 {max_items} 个...")
        
        result = asyncio.run(_retry_failed_items_async(max_items))
        
        if result["success"]:
            logger.info(f"重试失败项目完成: {result['retried_count']} 个")
            return {
                "status": "success",
                "message": result["message"],
                "retried_count": result["retried_count"]
            }
        else:
            logger.error(f"重试失败项目失败: {result['error']}")
            return {
                "status": "failed",
                "message": f"重试失败: {result['error']}",
                "retried_count": 0
            }
            
    except Exception as exc:
        logger.error(f"重试失败项目任务失败: {str(exc)}", exc_info=True)
        return {
            "status": "failed",
            "message": f"任务执行失败: {str(exc)}",
            "retried_count": 0
        }