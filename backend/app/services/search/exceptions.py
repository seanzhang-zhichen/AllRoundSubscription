"""
搜索服务异常定义
"""


class SearchException(Exception):
    """搜索服务基础异常"""
    def __init__(self, message: str, platform: str = None, error_code: str = None):
        self.message = message
        self.platform = platform
        self.error_code = error_code
        super().__init__(self.message)


class PlatformAPIException(SearchException):
    """平台API调用异常"""
    def __init__(self, message: str, platform: str, status_code: int = None, response_data: dict = None):
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message, platform, "PLATFORM_API_ERROR")


class PlatformUnavailableException(SearchException):
    """平台不可用异常"""
    def __init__(self, platform: str, reason: str = "平台暂时不可用"):
        super().__init__(f"{platform}平台{reason}", platform, "PLATFORM_UNAVAILABLE")


class SearchTimeoutException(SearchException):
    """搜索超时异常"""
    def __init__(self, platform: str, timeout_seconds: int):
        message = f"{platform}平台搜索超时（{timeout_seconds}秒）"
        super().__init__(message, platform, "SEARCH_TIMEOUT")


class RateLimitException(SearchException):
    """API限流异常"""
    def __init__(self, platform: str, retry_after: int = None):
        message = f"{platform}平台API限流"
        if retry_after:
            message += f"，请在{retry_after}秒后重试"
        super().__init__(message, platform, "RATE_LIMIT")


class AuthenticationException(SearchException):
    """认证异常"""
    def __init__(self, platform: str, reason: str = "认证失败"):
        super().__init__(f"{platform}平台{reason}", platform, "AUTHENTICATION_ERROR")


class DataParsingException(SearchException):
    """数据解析异常"""
    def __init__(self, platform: str, data_type: str, reason: str = "数据格式错误"):
        message = f"{platform}平台{data_type}{reason}"
        super().__init__(message, platform, "DATA_PARSING_ERROR")


class SearchQuotaExceededException(SearchException):
    """搜索配额超限异常"""
    def __init__(self, platform: str, quota_type: str = "日搜索次数"):
        message = f"{platform}平台{quota_type}已超限"
        super().__init__(message, platform, "QUOTA_EXCEEDED")