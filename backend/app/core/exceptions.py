"""
自定义异常类
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(Enum):
    """错误码枚举"""
    SUCCESS = (200, "操作成功")
    INVALID_PARAMS = (400, "参数错误")
    UNAUTHORIZED = (401, "未授权")
    FORBIDDEN = (403, "权限不足")
    NOT_FOUND = (404, "资源不存在")
    SUBSCRIPTION_LIMIT = (4001, "订阅数量已达上限")
    PUSH_LIMIT = (4002, "推送次数已达上限")
    MEMBERSHIP_REQUIRED = (4003, "需要升级会员")
    PLATFORM_ERROR = (5001, "平台API调用失败")
    DATABASE_ERROR = (5002, "数据库操作失败")
    CACHE_ERROR = (5003, "缓存操作失败")
    INTERNAL_ERROR = (500, "服务器内部错误")
    
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


class BusinessException(Exception):
    """业务异常基类"""
    
    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code.code
        self.message = message or error_code.message
        self.details = details or {}
        self.timestamp = datetime.now()
        
        # 根据错误码设置HTTP状态码
        if error_code.code < 500:
            self.status_code = error_code.code
        else:
            self.status_code = 500
            
        super().__init__(self.message)


class ValidationException(BusinessException):
    """参数验证异常"""
    
    def __init__(self, message: str = "参数验证失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCode.INVALID_PARAMS, message, details)


class AuthenticationException(BusinessException):
    """认证异常"""
    
    def __init__(self, message: str = "认证失败"):
        super().__init__(ErrorCode.UNAUTHORIZED, message)


class AuthorizationException(BusinessException):
    """授权异常"""
    
    def __init__(self, message: str = "权限不足"):
        super().__init__(ErrorCode.FORBIDDEN, message)


class NotFoundException(BusinessException):
    """资源不存在异常"""
    
    def __init__(self, message: str = "资源不存在"):
        super().__init__(ErrorCode.NOT_FOUND, message)


class SubscriptionLimitException(BusinessException):
    """订阅限制异常"""
    
    def __init__(self, message: str = "订阅数量已达上限"):
        super().__init__(ErrorCode.SUBSCRIPTION_LIMIT, message)


class PushLimitException(BusinessException):
    """推送限制异常"""
    
    def __init__(self, message: str = "推送次数已达上限"):
        super().__init__(ErrorCode.PUSH_LIMIT, message)


class DuplicateException(BusinessException):
    """重复资源异常"""
    
    def __init__(self, message: str = "资源已存在"):
        super().__init__(ErrorCode.INVALID_PARAMS, message)