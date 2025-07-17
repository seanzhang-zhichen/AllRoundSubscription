"""
搜索相关任务
"""
from celery import shared_task
from app.tasks.base import BaseTask
import logging

logger = logging.getLogger(__name__)


@shared_task(base=BaseTask, bind=True)
def update_search_cache(self, keyword: str):
    """更新搜索缓存任务"""
    try:
        logger.info(f"开始更新搜索缓存: {keyword}")
        # 实现搜索缓存更新逻辑
        import asyncio
        from app.services.search.cache import search_cache
        
        async def _invalidate_cache():
            await search_cache.invalidate_search_cache(keyword)
        
        asyncio.run(_invalidate_cache())
        logger.info(f"搜索缓存更新完成: {keyword}")
        return {"status": "success", "message": f"搜索缓存更新完成: {keyword}"}
    except Exception as exc:
        logger.error(f"更新搜索缓存失败: {str(exc)}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)