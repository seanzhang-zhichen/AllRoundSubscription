"""
Celery任务基类
"""
from celery import Task
from app.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)


class BaseTask(Task):
    """Celery任务基类"""
    
    def on_success(self, retval, task_id, args, kwargs):
        """任务成功回调"""
        logger.info(f"任务 {self.name} ({task_id}) 执行成功")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败回调"""
        logger.error(f"任务 {self.name} ({task_id}) 执行失败: {str(exc)}")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """任务重试回调"""
        logger.warning(f"任务 {self.name} ({task_id}) 重试: {str(exc)}")


# 设置默认任务基类
celery_app.Task = BaseTask