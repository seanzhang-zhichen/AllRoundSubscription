"""
Celery应用配置
"""
from celery import Celery
from app.core.config import settings

# 创建Celery应用
celery_app = Celery(
    "content_aggregator",
    broker=settings.celery_broker_url_with_auth,
    backend=settings.celery_result_backend_with_auth,
    include=["app.tasks"]
)

# Celery配置
celery_app.conf.update(
    # 任务序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # 时区设置
    timezone="Asia/Shanghai",
    enable_utc=True,
    
    # 任务路由
    task_routes={
        "app.tasks.content.*": {"queue": "content"},
        "app.tasks.push.*": {"queue": "push"},
        "app.tasks.search.*": {"queue": "search"},
    },
    
    # 任务过期时间
    task_time_limit=300,  # 5分钟
    task_soft_time_limit=240,  # 4分钟
    
    # 结果过期时间
    result_expires=3600,  # 1小时
    
    # 工作进程配置
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # 任务重试配置
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # 定时任务配置
    beat_schedule={
        "fetch-new-content": {
            "task": "app.tasks.content.fetch_new_content",
            "schedule": 300.0,  # 每5分钟执行一次
        },
        "send-push-notifications": {
            "task": "app.tasks.push.send_pending_notifications",
            "schedule": 60.0,  # 每分钟执行一次
        },
        "get-push-queue-statistics": {
            "task": "app.tasks.push.get_push_queue_statistics",
            "schedule": 600.0,  # 每10分钟执行一次
        },
        "retry-failed-push-items": {
            "task": "app.tasks.push.retry_failed_push_items",
            "schedule": 1800.0,  # 每30分钟执行一次
        },
    },
)

# 自动发现任务
celery_app.autodiscover_tasks(["app.tasks"])