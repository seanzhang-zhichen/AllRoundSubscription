"""
中间件模块
"""
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time
from app.core.logging import get_logger
from typing import Dict, Optional, List
from app.db.redis import cache_service
from app.core.exceptions import BusinessException, ErrorCode, AuthenticationException
from app.core.security import jwt_manager
from app.core.monitoring import get_performance_monitor

logger = get_logger(__name__)
performance_monitor = get_performance_monitor()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls  # 允许的调用次数
        self.period = period  # 时间窗口（秒）
    
    async def dispatch(self, request: Request, call_next):
        # 获取客户端IP
        client_ip = request.client.host
        
        # 构造限流key
        rate_limit_key = f"rate_limit:{client_ip}"
        
        try:
            # 检查当前请求数
            current_calls = await cache_service.get(rate_limit_key)
            if current_calls is None:
                current_calls = 0
            
            if int(current_calls) >= self.calls:
                return JSONResponse(
                    status_code=429,
                    content={
                        "code": 429,
                        "message": "请求过于频繁，请稍后再试",
                        "timestamp": int(time.time())
                    }
                )
            
            # 增加请求计数
            await cache_service.set(rate_limit_key, int(current_calls) + 1, self.period)
            
        except Exception as e:
            logger.error(f"限流中间件错误: {str(e)}")
            # 限流失败时不阻止请求
        
        response = await call_next(request)
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 记录请求信息
        logger.info(
            "请求开始",
            extra={
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host,
                "user_agent": request.headers.get("user-agent", ""),
            }
        )
        
        try:
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录性能监控数据
            performance_monitor.record_response_time(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                response_time=process_time
            )
            
            # 记录响应信息
            logger.info(
                "请求完成",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": response.status_code,
                    "process_time": round(process_time, 4),
                }
            )
            
            # 添加响应头
            response.headers["X-Process-Time"] = str(round(process_time, 4))
            
            # 如果响应时间过长，记录警告
            if process_time > 2.0:
                logger.warning(
                    f"慢请求检测: {request.method} {request.url.path} 耗时 {process_time:.3f}s",
                    extra={
                        "slow_request": True,
                        "method": request.method,
                        "url": str(request.url),
                        "process_time": process_time
                    }
                )
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            
            # 记录异常的性能数据
            performance_monitor.record_response_time(
                endpoint=request.url.path,
                method=request.method,
                status_code=500,
                response_time=process_time
            )
            
            logger.error(
                "请求异常",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "error": str(e),
                    "process_time": round(process_time, 4),
                },
                exc_info=True
            )
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头中间件"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # 添加安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """认证中间件"""
    
    def __init__(self, app, protected_paths: Optional[List[str]] = None):
        super().__init__(app)
        # 需要认证的路径前缀
        self.protected_paths = protected_paths or [
            "/api/v1/users",
            "/api/v1/subscriptions", 
            "/api/v1/content",
            "/api/v1/articles"
        ]
        # 不需要认证的路径
        self.public_paths = [
            "/api/v1/auth/login",
            "/api/v1/auth/refresh",
            "/api/v1/search",
            "/api/v1/health",
            "/health",
            "/docs",
            "/openapi.json"
        ]
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # 检查是否为公开路径
        if any(path.startswith(public_path) for public_path in self.public_paths):
            return await call_next(request)
        
        # 检查是否为受保护路径
        if any(path.startswith(protected_path) for protected_path in self.protected_paths):
            # 获取Authorization头
            auth_header = request.headers.get("Authorization")
            
            if not auth_header:
                logger.warning(f"受保护路径缺少认证令牌: {path}")
                return JSONResponse(
                    status_code=401,
                    content={
                        "code": 401,
                        "message": "缺少认证令牌",
                        "timestamp": int(time.time())
                    }
                )
            
            # 检查Bearer格式
            if not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={
                        "code": 401,
                        "message": "无效的认证格式",
                        "timestamp": int(time.time())
                    }
                )
            
            # 提取令牌
            token = auth_header[7:]  # 移除"Bearer "前缀
            
            try:
                # 验证令牌格式（不验证用户存在性，留给具体的依赖处理）
                jwt_manager.verify_token(token, "access")
                logger.debug(f"令牌格式验证通过，路径: {path}")
                
            except AuthenticationException as e:
                logger.warning(f"令牌验证失败: {str(e)}, 路径: {path}")
                return JSONResponse(
                    status_code=401,
                    content={
                        "code": 401,
                        "message": str(e),
                        "timestamp": int(time.time())
                    }
                )
            except Exception as e:
                logger.error(f"认证中间件异常: {str(e)}, 路径: {path}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "code": 500,
                        "message": "认证服务异常",
                        "timestamp": int(time.time())
                    }
                )
        
        return await call_next(request)