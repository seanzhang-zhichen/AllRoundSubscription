"""
监控和健康检查API端点
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from typing import Dict, Any

from app.core.monitoring import health_checker, metrics_collector, create_metrics_response
from app.core.alerts import alert_manager
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    健康检查端点
    返回系统各组件的健康状态
    """
    try:
        health_status = await health_checker.get_health_status()
        
        # 如果系统不健康，返回503状态码
        if health_status["status"] != "healthy":
            raise HTTPException(status_code=503, detail=health_status)
        
        return health_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "健康检查执行失败",
                "error": str(e)
            }
        )


@router.get("/health/simple")
async def simple_health_check() -> Dict[str, str]:
    """
    简单健康检查端点
    用于负载均衡器等快速检查
    """
    return {"status": "ok"}


@router.get("/metrics")
async def get_metrics() -> Response:
    """
    Prometheus指标端点
    返回所有监控指标
    """
    try:
        return create_metrics_response()
    except Exception as e:
        logger.error(f"获取指标失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"message": "获取指标失败", "error": str(e)}
        )


@router.get("/alerts")
async def get_alerts() -> Dict[str, Any]:
    """
    获取当前报警信息
    """
    try:
        active_alerts = alert_manager.get_active_alerts()
        alert_summary = alert_manager.get_alert_summary()
        
        return {
            "summary": alert_summary,
            "active_alerts": [
                {
                    "id": alert.id,
                    "level": alert.level.value,
                    "type": alert.type.value,
                    "title": alert.title,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat(),
                    "metadata": alert.metadata
                }
                for alert in active_alerts
            ]
        }
        
    except Exception as e:
        logger.error(f"获取报警信息失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"message": "获取报警信息失败", "error": str(e)}
        )


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str) -> Dict[str, str]:
    """
    解决指定的报警
    """
    try:
        await alert_manager.resolve_alert(alert_id)
        return {"message": f"报警 {alert_id} 已解决"}
        
    except Exception as e:
        logger.error(f"解决报警失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"message": "解决报警失败", "error": str(e)}
        )


@router.get("/system/info")
async def get_system_info() -> Dict[str, Any]:
    """
    获取系统信息
    """
    try:
        # 收集系统指标
        await metrics_collector.collect_all_metrics()
        
        return {
            "application": {
                "name": "content-aggregator",
                "version": "1.0.0",
                "environment": "production"
            },
            "status": "running",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
    except Exception as e:
        logger.error(f"获取系统信息失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"message": "获取系统信息失败", "error": str(e)}
        )