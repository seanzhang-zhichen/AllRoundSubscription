"""
错误报警和恢复机制模块
提供错误监控、报警和自动恢复功能
"""

import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class AlertLevel(Enum):
    """报警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """报警类型"""
    SYSTEM = "system"
    DATABASE = "database"
    REDIS = "redis"
    API = "api"
    BUSINESS = "business"
    SECURITY = "security"


@dataclass
class Alert:
    """报警信息"""
    id: str
    level: AlertLevel
    type: AlertType
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class AlertManager:
    """报警管理器"""
    
    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.alert_handlers: List[Callable] = []
        self.recovery_handlers: Dict[str, Callable] = {}
        
        # 报警阈值配置
        self.thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'error_rate': 5.0,  # 每分钟错误数
            'response_time': 5.0,  # 秒
            'db_connections': 180,  # 最大连接数的90%
        }
        
        # 报警抑制配置（避免重复报警）
        self.suppression_windows = {
            AlertLevel.INFO: timedelta(minutes=30),
            AlertLevel.WARNING: timedelta(minutes=15),
            AlertLevel.ERROR: timedelta(minutes=5),
            AlertLevel.CRITICAL: timedelta(minutes=1),
        }
    
    def add_alert_handler(self, handler: Callable) -> None:
        """添加报警处理器"""
        self.alert_handlers.append(handler)
    
    def add_recovery_handler(self, alert_type: str, handler: Callable) -> None:
        """添加恢复处理器"""
        self.recovery_handlers[alert_type] = handler
    
    async def create_alert(
        self,
        alert_id: str,
        level: AlertLevel,
        alert_type: AlertType,
        title: str,
        message: str,
        metadata: Dict[str, Any] = None
    ) -> None:
        """创建报警"""
        
        # 检查是否需要抑制报警
        if self._should_suppress_alert(alert_id, level):
            logger.debug(f"报警被抑制: {alert_id}")
            return
        
        alert = Alert(
            id=alert_id,
            level=level,
            type=alert_type,
            title=title,
            message=message,
            metadata=metadata or {}
        )
        
        self.alerts[alert_id] = alert
        
        logger.warning(f"创建报警: {alert_id} - {title}")
        
        # 触发报警处理器
        for handler in self.alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"报警处理器执行失败: {str(e)}")
    
    async def resolve_alert(self, alert_id: str) -> None:
        """解决报警"""
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            
            logger.info(f"报警已解决: {alert_id}")
            
            # 触发恢复处理器
            recovery_handler = self.recovery_handlers.get(alert.type.value)
            if recovery_handler:
                try:
                    await recovery_handler(alert)
                except Exception as e:
                    logger.error(f"恢复处理器执行失败: {str(e)}")
    
    def _should_suppress_alert(self, alert_id: str, level: AlertLevel) -> bool:
        """检查是否应该抑制报警"""
        if alert_id not in self.alerts:
            return False
        
        last_alert = self.alerts[alert_id]
        if last_alert.resolved:
            return False
        
        suppression_window = self.suppression_windows.get(level, timedelta(minutes=5))
        time_since_last = datetime.utcnow() - last_alert.timestamp
        
        return time_since_last < suppression_window
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃的报警"""
        return [alert for alert in self.alerts.values() if not alert.resolved]
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """获取报警摘要"""
        active_alerts = self.get_active_alerts()
        
        summary = {
            'total_alerts': len(self.alerts),
            'active_alerts': len(active_alerts),
            'resolved_alerts': len(self.alerts) - len(active_alerts),
            'alerts_by_level': {},
            'alerts_by_type': {}
        }
        
        for alert in active_alerts:
            # 按级别统计
            level_key = alert.level.value
            summary['alerts_by_level'][level_key] = summary['alerts_by_level'].get(level_key, 0) + 1
            
            # 按类型统计
            type_key = alert.type.value
            summary['alerts_by_type'][type_key] = summary['alerts_by_type'].get(type_key, 0) + 1
        
        return summary


class EmailAlertHandler:
    """邮件报警处理器"""
    
    def __init__(self, smtp_config: Dict[str, Any]):
        self.smtp_host = smtp_config.get('host')
        self.smtp_port = smtp_config.get('port', 587)
        self.smtp_user = smtp_config.get('user')
        self.smtp_password = smtp_config.get('password')
        self.from_email = smtp_config.get('from_email', self.smtp_user)
        self.to_emails = smtp_config.get('to_emails', [])
    
    async def __call__(self, alert: Alert) -> None:
        """发送邮件报警"""
        if not self.smtp_host or not self.to_emails:
            logger.warning("邮件配置不完整，跳过邮件报警")
            return
        
        try:
            # 创建邮件内容
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = f"[{alert.level.value.upper()}] {alert.title}"
            
            # 邮件正文
            body = self._create_email_body(alert)
            msg.attach(MIMEText(body, 'html'))
            
            # 发送邮件
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                
                text = msg.as_string()
                server.sendmail(self.from_email, self.to_emails, text)
            
            logger.info(f"邮件报警发送成功: {alert.id}")
            
        except Exception as e:
            logger.error(f"发送邮件报警失败: {str(e)}")
    
    def _create_email_body(self, alert: Alert) -> str:
        """创建邮件正文"""
        color_map = {
            AlertLevel.INFO: '#17a2b8',
            AlertLevel.WARNING: '#ffc107',
            AlertLevel.ERROR: '#dc3545',
            AlertLevel.CRITICAL: '#dc3545'
        }
        
        color = color_map.get(alert.level, '#6c757d')
        
        return f"""
        <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: {color}; color: white; padding: 20px; text-align: center;">
                    <h1>{alert.title}</h1>
                    <p>级别: {alert.level.value.upper()}</p>
                </div>
                
                <div style="padding: 20px; background-color: #f8f9fa;">
                    <h3>报警详情</h3>
                    <p><strong>类型:</strong> {alert.type.value}</p>
                    <p><strong>时间:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                    <p><strong>消息:</strong> {alert.message}</p>
                    
                    {self._format_metadata(alert.metadata)}
                </div>
                
                <div style="padding: 20px; text-align: center; color: #6c757d;">
                    <p>此邮件由内容聚合系统自动发送</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _format_metadata(self, metadata: Dict[str, Any]) -> str:
        """格式化元数据"""
        if not metadata:
            return ""
        
        html = "<h4>附加信息</h4><ul>"
        for key, value in metadata.items():
            html += f"<li><strong>{key}:</strong> {value}</li>"
        html += "</ul>"
        
        return html


class SystemMonitor:
    """系统监控器"""
    
    def __init__(self, alert_manager: AlertManager):
        self.alert_manager = alert_manager
        self.monitoring = False
    
    async def start_monitoring(self) -> None:
        """开始监控"""
        self.monitoring = True
        logger.info("系统监控已启动")
        
        while self.monitoring:
            try:
                await self._check_system_health()
                await asyncio.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"系统监控检查失败: {str(e)}")
                await asyncio.sleep(60)
    
    def stop_monitoring(self) -> None:
        """停止监控"""
        self.monitoring = False
        logger.info("系统监控已停止")
    
    async def _check_system_health(self) -> None:
        """检查系统健康状态"""
        # 这里可以集成之前创建的监控指标
        # 检查CPU、内存、磁盘使用率等
        
        # 示例：检查错误率
        # error_rate = await self._get_error_rate()
        # if error_rate > self.alert_manager.thresholds['error_rate']:
        #     await self.alert_manager.create_alert(
        #         alert_id="high_error_rate",
        #         level=AlertLevel.ERROR,
        #         alert_type=AlertType.SYSTEM,
        #         title="错误率过高",
        #         message=f"当前错误率: {error_rate}/分钟",
        #         metadata={"error_rate": error_rate}
        #     )
        pass


# 全局报警管理器实例
alert_manager = AlertManager()

# 配置邮件报警处理器
if hasattr(settings, 'SMTP_HOST') and settings.SMTP_HOST:
    email_handler = EmailAlertHandler({
        'host': settings.SMTP_HOST,
        'port': getattr(settings, 'SMTP_PORT', 587),
        'user': getattr(settings, 'SMTP_USER', ''),
        'password': getattr(settings, 'SMTP_PASSWORD', ''),
        'from_email': getattr(settings, 'SMTP_USER', ''),
        'to_emails': [getattr(settings, 'ALERT_EMAIL', '')]
    })
    alert_manager.add_alert_handler(email_handler)

# 系统监控器实例
system_monitor = SystemMonitor(alert_manager)