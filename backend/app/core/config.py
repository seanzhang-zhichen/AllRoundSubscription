"""
应用配置管理
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    # 项目基本信息
    PROJECT_NAME: str = "多平台内容聚合器"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False  # 默认关闭调试模式，通过环境变量控制
    
    # 跨域配置
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # 数据库配置
    DATABASE_URL: Optional[str] = None
    SQLITE_URL: str = "sqlite+aiosqlite:///./content_aggregator.db"
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    
    # JWT配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # 微信配置
    WECHAT_APP_ID: str = ""
    WECHAT_APP_SECRET: str = ""
    
    # 微信RSS API配置
    WECHAT_RSS_API_URL: str = ""
    WECHAT_RSS_API_USERNAME: str = ""
    WECHAT_RSS_API_PASSWORD: str = ""
    
    # 微信服务号配置
    WECHAT_SERVICE_APP_ID: str = ""
    WECHAT_SERVICE_APP_SECRET: str = ""
    WECHAT_TEMPLATE_ID: str = ""  # 推送消息模板ID
    WECHAT_MINI_PROGRAM_APP_ID: str = ""  # 小程序AppID（用于跳转）
    WECHAT_MINI_PROGRAM_PATH: str = "pages/article/detail"  # 小程序跳转路径
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: Optional[str] = None
    ENABLE_SQL_LOGGING: bool = False  # 控制SQL日志输出
    
    # Celery配置
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    @property
    def redis_url_with_auth(self) -> str:
        """获取带认证的Redis URL"""
        if self.REDIS_PASSWORD:
            # 解析原始URL并添加密码
            if "://" in self.REDIS_URL:
                protocol, rest = self.REDIS_URL.split("://", 1)
                return f"{protocol}://:{self.REDIS_PASSWORD}@{rest}"
            return self.REDIS_URL
        return self.REDIS_URL
    
    @property
    def celery_broker_url_with_auth(self) -> str:
        """获取带认证的Celery Broker URL"""
        if self.REDIS_PASSWORD:
            if "://" in self.CELERY_BROKER_URL:
                protocol, rest = self.CELERY_BROKER_URL.split("://", 1)
                return f"{protocol}://:{self.REDIS_PASSWORD}@{rest}"
            return self.CELERY_BROKER_URL
        return self.CELERY_BROKER_URL
    
    @property
    def celery_result_backend_with_auth(self) -> str:
        """获取带认证的Celery Result Backend URL"""
        if self.REDIS_PASSWORD:
            if "://" in self.CELERY_RESULT_BACKEND:
                protocol, rest = self.CELERY_RESULT_BACKEND.split("://", 1)
                return f"{protocol}://:{self.REDIS_PASSWORD}@{rest}"
            return self.CELERY_RESULT_BACKEND
        return self.CELERY_RESULT_BACKEND
    
    # 监控配置
    ENABLE_MONITORING: bool = True
    ENABLE_METRICS: bool = True
    ENABLE_REDIS_METRICS: bool = False
    
    @property
    def database_url(self) -> str:
        """获取数据库连接URL"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return self.SQLITE_URL
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()