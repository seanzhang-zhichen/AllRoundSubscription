"""
日志配置模块
提供结构化日志记录和监控功能
"""

import logging
import logging.config
import sys
import os
from typing import Dict, Any
from datetime import datetime
import json
import traceback
from pathlib import Path

import structlog
from pythonjsonlogger import jsonlogger
from prometheus_client import Counter, Histogram, Gauge

# Prometheus监控指标
log_counter = Counter('app_log_messages_total', 'Total log messages', ['level', 'module'])
error_counter = Counter('app_errors_total', 'Total errors', ['error_type', 'module'])
request_duration = Histogram('app_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
active_connections = Gauge('app_active_connections', 'Active database connections')


class StructuredFormatter(jsonlogger.JsonFormatter):
    """结构化JSON日志格式化器"""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        
        # 添加时间戳
        log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # 添加日志级别
        log_record['level'] = record.levelname
        
        # 添加模块信息
        log_record['module'] = record.name
        
        # 添加文件和行号信息
        log_record['file'] = record.filename
        log_record['line'] = record.lineno
        
        # 添加进程和线程信息
        log_record['process_id'] = os.getpid()
        log_record['thread_id'] = record.thread
        
        # 如果有异常信息，添加堆栈跟踪
        if record.exc_info:
            log_record['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }


class PrometheusLogHandler(logging.Handler):
    """Prometheus指标收集日志处理器"""
    
    def emit(self, record: logging.LogRecord) -> None:
        # 记录日志数量
        log_counter.labels(level=record.levelname, module=record.name).inc()
        
        # 记录错误
        if record.levelno >= logging.ERROR:
            error_type = getattr(record, 'error_type', 'unknown')
            error_counter.labels(error_type=error_type, module=record.name).inc()


class RequestContextFilter(logging.Filter):
    """请求上下文过滤器"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        # 尝试从上下文中获取请求信息
        try:
            from contextvars import copy_context
            ctx = copy_context()
            
            # 添加请求ID（如果存在）
            request_id = ctx.get('request_id', None)
            if request_id:
                record.request_id = request_id
                
            # 添加用户ID（如果存在）
            user_id = ctx.get('user_id', None)
            if user_id:
                record.user_id = user_id
                
        except Exception:
            pass
            
        return True


def setup_logging(
    log_level: str = "INFO",
    log_file: str = None,
    enable_json: bool = True,
    enable_prometheus: bool = True
) -> None:
    """
    设置应用日志配置
    
    Args:
        log_level: 日志级别
        log_file: 日志文件路径
        enable_json: 是否启用JSON格式
        enable_prometheus: 是否启用Prometheus指标收集
    """
    
    # 创建日志目录
    if log_file:
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
    
    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    if enable_json:
        console_formatter = StructuredFormatter(
            fmt='%(timestamp)s %(level)s %(module)s %(message)s'
        )
    else:
        console_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(RequestContextFilter())
    root_logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        from logging.handlers import RotatingFileHandler
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=10
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        
        if enable_json:
            file_formatter = StructuredFormatter(
                fmt='%(timestamp)s %(level)s %(module)s %(message)s'
            )
        else:
            file_formatter = logging.Formatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(RequestContextFilter())
        root_logger.addHandler(file_handler)
    
    # Prometheus指标处理器
    if enable_prometheus:
        prometheus_handler = PrometheusLogHandler()
        prometheus_handler.setLevel(logging.INFO)
        root_logger.addHandler(prometheus_handler)
    
    # 配置第三方库日志级别
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('celery').setLevel(logging.INFO)
    logging.getLogger('redis').setLevel(logging.WARNING)
    
    # 配置structlog
    if enable_json:
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )


def get_logger(name: str) -> logging.Logger:
    """获取日志器实例"""
    return logging.getLogger(name)


def log_performance(func_name: str, duration: float, **kwargs) -> None:
    """记录性能指标"""
    logger = get_logger('performance')
    logger.info(
        f"Performance metric",
        extra={
            'function': func_name,
            'duration': duration,
            'metric_type': 'performance',
            **kwargs
        }
    )


def log_business_event(event_type: str, **kwargs) -> None:
    """记录业务事件"""
    logger = get_logger('business')
    logger.info(
        f"Business event: {event_type}",
        extra={
            'event_type': event_type,
            'metric_type': 'business',
            **kwargs
        }
    )


def log_security_event(event_type: str, severity: str = 'info', **kwargs) -> None:
    """记录安全事件"""
    logger = get_logger('security')
    
    log_func = getattr(logger, severity.lower(), logger.info)
    log_func(
        f"Security event: {event_type}",
        extra={
            'event_type': event_type,
            'severity': severity,
            'metric_type': 'security',
            **kwargs
        }
    )


class LoggerMixin:
    """日志器混入类"""
    
    @property
    def logger(self) -> logging.Logger:
        return get_logger(self.__class__.__module__ + '.' + self.__class__.__name__)