"""
监控和指标收集模块
提供Prometheus指标和健康检查功能
"""

import time
import psutil
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from functools import wraps

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.logging import get_logger
from app.db.database import engine
from app.db.redis import redis_client

logger = get_logger(__name__)

# 应用信息指标
app_info = Info('app_info', 'Application information')
app_info.info({
    'version': '1.0.0',
    'name': 'content-aggregator',
    'environment': 'production'
})

# HTTP请求指标
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently being processed'
)

# 数据库指标
db_connections_active = Gauge('db_connections_active', 'Active database connections')
db_connections_idle = Gauge('db_connections_idle', 'Idle database connections')
db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['query_type']
)
db_queries_total = Counter(
    'db_queries_total',
    'Total database queries',
    ['query_type', 'status']
)

# Redis指标
redis_connections_active = Gauge('redis_connections_active', 'Active Redis connections')
redis_operations_total = Counter(
    'redis_operations_total',
    'Total Redis operations',
    ['operation', 'status']
)
redis_operation_duration_seconds = Histogram(
    'redis_operation_duration_seconds',
    'Redis operation duration in seconds',
    ['operation']
)

# Celery指标
celery_tasks_total = Counter(
    'celery_tasks_total',
    'Total Celery tasks',
    ['task_name', 'status']
)
celery_task_duration_seconds = Histogram(
    'celery_task_duration_seconds',
    'Celery task duration in seconds',
    ['task_name']
)
celery_active_tasks = Gauge('celery_active_tasks', 'Active Celery tasks')

# 业务指标
users_total = Gauge('users_total', 'Total number of users')
users_active_daily = Gauge('users_active_daily', 'Daily active users')
subscriptions_total = Gauge('subscriptions_total', 'Total number of subscriptions')
articles_total = Gauge('articles_total', 'Total number of articles')
push_notifications_total = Counter(
    'push_notifications_total',
    'Total push notifications sent',
    ['status']
)

# 系统指标
system_cpu_usage = Gauge('system_cpu_usage_percent', 'System CPU usage percentage')
system_memory_usage = Gauge('system_memory_usage_percent', 'System memory usage percentage')
system_disk_usage = Gauge('system_disk_usage_percent', 'System disk usage percentage')


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.start_time = time.time()
    
    async def collect_system_metrics(self) -> None:
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            system_cpu_usage.set(cpu_percent)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            system_memory_usage.set(memory.percent)
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            system_disk_usage.set(disk_percent)
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {str(e)}")
    
    async def collect_database_metrics(self) -> None:
        """收集数据库指标"""
        try:
            async with engine.begin() as conn:
                # 连接数统计
                result = await conn.execute(text("""
                    SELECT 
                        count(*) as total_connections,
                        count(*) FILTER (WHERE state = 'active') as active_connections,
                        count(*) FILTER (WHERE state = 'idle') as idle_connections
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                """))
                
                row = result.fetchone()
                if row:
                    db_connections_active.set(row.active_connections or 0)
                    db_connections_idle.set(row.idle_connections or 0)
                
        except Exception as e:
            logger.error(f"收集数据库指标失败: {str(e)}")
    
    async def collect_redis_metrics(self) -> None:
        """收集Redis指标"""
        try:
            if redis_client:
                info = await redis_client.info()
                redis_connections_active.set(info.get('connected_clients', 0))
                
        except Exception as e:
            logger.error(f"收集Redis指标失败: {str(e)}")
    
    async def collect_business_metrics(self) -> None:
        """收集业务指标"""
        try:
            async with engine.begin() as conn:
                # 用户总数
                result = await conn.execute(text("SELECT COUNT(*) FROM users"))
                users_total.set(result.scalar() or 0)
                
                # 日活用户（24小时内有活动）
                result = await conn.execute(text("""
                    SELECT COUNT(DISTINCT user_id) 
                    FROM push_records 
                    WHERE push_time >= NOW() - INTERVAL '24 hours'
                """))
                users_active_daily.set(result.scalar() or 0)
                
                # 订阅总数
                result = await conn.execute(text("SELECT COUNT(*) FROM subscriptions"))
                subscriptions_total.set(result.scalar() or 0)
                
                # 文章总数
                result = await conn.execute(text("SELECT COUNT(*) FROM articles"))
                articles_total.set(result.scalar() or 0)
                
        except Exception as e:
            logger.error(f"收集业务指标失败: {str(e)}")
    
    async def collect_all_metrics(self) -> None:
        """收集所有指标"""
        await asyncio.gather(
            self.collect_system_metrics(),
            self.collect_database_metrics(),
            self.collect_redis_metrics(),
            self.collect_business_metrics(),
            return_exceptions=True
        )


# 全局指标收集器实例
metrics_collector = MetricsCollector()


def monitor_http_requests(func):
    """HTTP请求监控装饰器"""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        method = request.method
        path = request.url.path
        
        # 简化路径（移除动态参数）
        endpoint = path
        for param in request.path_params.values():
            endpoint = endpoint.replace(str(param), '{id}')
        
        http_requests_in_progress.inc()
        start_time = time.time()
        
        try:
            response = await func(request, *args, **kwargs)
            status_code = getattr(response, 'status_code', 200)
            
            # 记录指标
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()
            
            return response
            
        except Exception as e:
            # 记录错误
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=500
            ).inc()
            raise
            
        finally:
            # 记录请求时长
            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            http_requests_in_progress.dec()
    
    return wrapper


def monitor_database_query(query_type: str):
    """数据库查询监控装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                db_queries_total.labels(query_type=query_type, status='success').inc()
                return result
                
            except Exception as e:
                db_queries_total.labels(query_type=query_type, status='error').inc()
                raise
                
            finally:
                duration = time.time() - start_time
                db_query_duration_seconds.labels(query_type=query_type).observe(duration)
        
        return wrapper
    return decorator


def monitor_redis_operation(operation: str):
    """Redis操作监控装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                redis_operations_total.labels(operation=operation, status='success').inc()
                return result
                
            except Exception as e:
                redis_operations_total.labels(operation=operation, status='error').inc()
                raise
                
            finally:
                duration = time.time() - start_time
                redis_operation_duration_seconds.labels(operation=operation).observe(duration)
        
        return wrapper
    return decorator


def monitor_celery_task(task_name: str):
    """Celery任务监控装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            celery_active_tasks.inc()
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                celery_tasks_total.labels(task_name=task_name, status='success').inc()
                return result
                
            except Exception as e:
                celery_tasks_total.labels(task_name=task_name, status='error').inc()
                raise
                
            finally:
                duration = time.time() - start_time
                celery_task_duration_seconds.labels(task_name=task_name).observe(duration)
                celery_active_tasks.dec()
        
        return wrapper
    return decorator


class HealthChecker:
    """健康检查器"""
    
    async def check_database(self) -> Dict[str, Any]:
        """检查数据库连接"""
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return {"status": "healthy", "response_time": 0}
            
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def check_redis(self) -> Dict[str, Any]:
        """检查Redis连接"""
        try:
            if redis_client:
                await redis_client.ping()
                return {"status": "healthy"}
            else:
                return {"status": "unhealthy", "error": "Redis client not initialized"}
                
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def check_external_apis(self) -> Dict[str, Any]:
        """检查外部API连接"""
        # 这里可以添加对微信API等外部服务的健康检查
        return {"status": "healthy", "note": "External API checks not implemented"}
    
    async def get_health_status(self) -> Dict[str, Any]:
        """获取整体健康状态"""
        checks = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            self.check_external_apis(),
            return_exceptions=True
        )
        
        db_status, redis_status, api_status = checks
        
        overall_status = "healthy"
        if (db_status.get("status") != "healthy" or 
            redis_status.get("status") != "healthy"):
            overall_status = "unhealthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": db_status,
                "redis": redis_status,
                "external_apis": api_status
            }
        }


# 全局健康检查器实例
health_checker = HealthChecker()


async def get_metrics() -> str:
    """获取Prometheus指标"""
    # 收集最新指标
    await metrics_collector.collect_all_metrics()
    
    # 返回指标数据
    return generate_latest()


def create_metrics_response() -> Response:
    """创建指标响应"""
    metrics_data = generate_latest()
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )