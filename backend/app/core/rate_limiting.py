"""
增强的限流模块
"""
import time
import logging
from typing import Dict, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass
from app.db.redis import cache_service
from app.core.monitoring import get_performance_monitor

logger = logging.getLogger(__name__)
performance_monitor = get_performance_monitor()


class RateLimitStrategy(Enum):
    """限流策略枚举"""
    FIXED_WINDOW = "fixed_window"      # 固定窗口
    SLIDING_WINDOW = "sliding_window"  # 滑动窗口
    TOKEN_BUCKET = "token_bucket"      # 令牌桶
    LEAKY_BUCKET = "leaky_bucket"      # 漏桶


@dataclass
class RateLimitRule:
    """限流规则"""
    key: str                    # 限流键
    limit: int                  # 限制次数
    window: int                 # 时间窗口（秒）
    strategy: RateLimitStrategy # 限流策略
    burst_limit: Optional[int] = None  # 突发限制


@dataclass
class RateLimitResult:
    """限流结果"""
    allowed: bool              # 是否允许
    remaining: int             # 剩余次数
    reset_time: int           # 重置时间
    retry_after: Optional[int] = None  # 重试等待时间


class RateLimiter:
    """增强的限流器"""
    
    def __init__(self):
        self.default_rules = {
            "api": RateLimitRule("api", 100, 60, RateLimitStrategy.SLIDING_WINDOW),
            "auth": RateLimitRule("auth", 10, 60, RateLimitStrategy.FIXED_WINDOW),
            "search": RateLimitRule("search", 50, 60, RateLimitStrategy.TOKEN_BUCKET, burst_limit=10),
            "subscription": RateLimitRule("subscription", 20, 60, RateLimitStrategy.SLIDING_WINDOW)
        }
    
    async def check_rate_limit(self, identifier: str, rule_name: str = "api") -> RateLimitResult:
        """检查限流状态"""
        rule = self.default_rules.get(rule_name)
        if not rule:
            logger.warning(f"未找到限流规则: {rule_name}")
            return RateLimitResult(True, 999, int(time.time()) + 60)
        
        rate_limit_key = f"rate_limit:{rule_name}:{identifier}"
        
        try:
            if rule.strategy == RateLimitStrategy.FIXED_WINDOW:
                return await self._fixed_window_check(rate_limit_key, rule)
            elif rule.strategy == RateLimitStrategy.SLIDING_WINDOW:
                return await self._sliding_window_check(rate_limit_key, rule)
            elif rule.strategy == RateLimitStrategy.TOKEN_BUCKET:
                return await self._token_bucket_check(rate_limit_key, rule)
            else:
                return await self._fixed_window_check(rate_limit_key, rule)
        except Exception as e:
            logger.error(f"限流检查失败: {str(e)}")
            # 限流服务异常时允许请求通过
            return RateLimitResult(True, rule.limit, int(time.time()) + rule.window)
    
    async def _fixed_window_check(self, key: str, rule: RateLimitRule) -> RateLimitResult:
        """固定窗口限流检查"""
        current_time = int(time.time())
        window_start = current_time - (current_time % rule.window)
        window_key = f"{key}:{window_start}"
        
        # 获取当前窗口的请求数
        current_count = await cache_service.get(window_key) or 0
        current_count = int(current_count)
        
        if current_count >= rule.limit:
            # 超出限制
            reset_time = window_start + rule.window
            retry_after = reset_time - current_time
            performance_monitor.record_metric("rate_limit.blocked", 1, {"rule": rule.key})
            return RateLimitResult(False, 0, reset_time, retry_after)
        
        # 增加计数
        new_count = current_count + 1
        await cache_service.set(window_key, new_count, rule.window)
        
        remaining = rule.limit - new_count
        reset_time = window_start + rule.window
        performance_monitor.record_metric("rate_limit.allowed", 1, {"rule": rule.key})
        
        return RateLimitResult(True, remaining, reset_time)
    
    async def _sliding_window_check(self, key: str, rule: RateLimitRule) -> RateLimitResult:
        """滑动窗口限流检查"""
        current_time = time.time()
        window_start = current_time - rule.window
        
        # 使用Redis的有序集合实现滑动窗口
        redis_client = await cache_service._get_redis()
        
        # 清理过期的记录
        await redis_client.zremrangebyscore(key, 0, window_start)
        
        # 获取当前窗口内的请求数
        current_count = await redis_client.zcard(key)
        
        if current_count >= rule.limit:
            # 超出限制
            performance_monitor.record_metric("rate_limit.blocked", 1, {"rule": rule.key})
            return RateLimitResult(False, 0, int(current_time + rule.window), rule.window)
        
        # 添加当前请求
        await redis_client.zadd(key, {str(current_time): current_time})
        await redis_client.expire(key, rule.window)
        
        remaining = rule.limit - current_count - 1
        performance_monitor.record_metric("rate_limit.allowed", 1, {"rule": rule.key})
        
        return RateLimitResult(True, remaining, int(current_time + rule.window))
    
    async def _token_bucket_check(self, key: str, rule: RateLimitRule) -> RateLimitResult:
        """令牌桶限流检查"""
        current_time = time.time()
        bucket_key = f"{key}:bucket"
        
        # 获取桶状态
        bucket_data = await cache_service.get(bucket_key)
        if bucket_data is None:
            # 初始化桶
            bucket_data = {
                "tokens": rule.limit,
                "last_refill": current_time
            }
        
        # 计算需要补充的令牌数
        time_passed = current_time - bucket_data["last_refill"]
        tokens_to_add = int(time_passed * (rule.limit / rule.window))
        
        # 更新令牌数（不超过桶容量）
        bucket_data["tokens"] = min(rule.limit, bucket_data["tokens"] + tokens_to_add)
        bucket_data["last_refill"] = current_time
        
        if bucket_data["tokens"] < 1:
            # 没有令牌
            performance_monitor.record_metric("rate_limit.blocked", 1, {"rule": rule.key})
            retry_after = int((1 - bucket_data["tokens"]) * (rule.window / rule.limit))
            return RateLimitResult(False, 0, int(current_time + retry_after), retry_after)
        
        # 消费一个令牌
        bucket_data["tokens"] -= 1
        await cache_service.set(bucket_key, bucket_data, rule.window * 2)
        
        performance_monitor.record_metric("rate_limit.allowed", 1, {"rule": rule.key})
        return RateLimitResult(True, int(bucket_data["tokens"]), int(current_time + rule.window))
    
    async def get_rate_limit_status(self, identifier: str, rule_name: str = "api") -> Dict:
        """获取限流状态信息"""
        rule = self.default_rules.get(rule_name)
        if not rule:
            return {"error": f"未找到限流规则: {rule_name}"}
        
        rate_limit_key = f"rate_limit:{rule_name}:{identifier}"
        
        try:
            if rule.strategy == RateLimitStrategy.SLIDING_WINDOW:
                redis_client = await cache_service._get_redis()
                current_time = time.time()
                window_start = current_time - rule.window
                
                # 清理过期记录
                await redis_client.zremrangebyscore(rate_limit_key, 0, window_start)
                current_count = await redis_client.zcard(rate_limit_key)
                
                return {
                    "rule": rule_name,
                    "strategy": rule.strategy.value,
                    "limit": rule.limit,
                    "window": rule.window,
                    "current_usage": current_count,
                    "remaining": max(0, rule.limit - current_count),
                    "reset_time": int(current_time + rule.window)
                }
            else:
                # 其他策略的状态查询
                return {
                    "rule": rule_name,
                    "strategy": rule.strategy.value,
                    "limit": rule.limit,
                    "window": rule.window
                }
        except Exception as e:
            logger.error(f"获取限流状态失败: {str(e)}")
            return {"error": str(e)}
    
    def add_custom_rule(self, name: str, rule: RateLimitRule):
        """添加自定义限流规则"""
        self.default_rules[name] = rule
        logger.info(f"添加限流规则: {name} - {rule.limit}/{rule.window}s")
    
    async def reset_rate_limit(self, identifier: str, rule_name: str = "api") -> bool:
        """重置限流计数"""
        rule = self.default_rules.get(rule_name)
        if not rule:
            return False
        
        rate_limit_key = f"rate_limit:{rule_name}:{identifier}"
        
        try:
            if rule.strategy == RateLimitStrategy.SLIDING_WINDOW:
                redis_client = await cache_service._get_redis()
                await redis_client.delete(rate_limit_key)
            else:
                # 删除相关的所有键
                await cache_service.delete_pattern(f"{rate_limit_key}*")
            
            logger.info(f"重置限流计数: {identifier} - {rule_name}")
            return True
        except Exception as e:
            logger.error(f"重置限流计数失败: {str(e)}")
            return False


class AdaptiveRateLimiter(RateLimiter):
    """自适应限流器"""
    
    def __init__(self):
        super().__init__()
        self.system_load_threshold = 0.8  # 系统负载阈值
        self.error_rate_threshold = 0.1   # 错误率阈值
    
    async def adaptive_check(self, identifier: str, rule_name: str = "api") -> RateLimitResult:
        """自适应限流检查"""
        # 获取系统健康状态
        health_metrics = performance_monitor.get_health_metrics()
        
        # 根据系统状态调整限流规则
        rule = self.default_rules.get(rule_name)
        if not rule:
            return await self.check_rate_limit(identifier, rule_name)
        
        # 创建调整后的规则
        adjusted_rule = RateLimitRule(
            key=rule.key,
            limit=rule.limit,
            window=rule.window,
            strategy=rule.strategy,
            burst_limit=rule.burst_limit
        )
        
        # 根据错误率调整限制
        if health_metrics.get("error_rate", 0) > self.error_rate_threshold:
            adjusted_rule.limit = int(rule.limit * 0.5)  # 减少50%限制
            logger.warning(f"检测到高错误率，降低限流阈值: {rule_name}")
        
        # 根据响应时间调整限制
        avg_response_time = health_metrics.get("avg_response_time", 0)
        if avg_response_time > 2.0:  # 响应时间超过2秒
            adjusted_rule.limit = int(rule.limit * 0.7)  # 减少30%限制
            logger.warning(f"检测到高响应时间，降低限流阈值: {rule_name}")
        
        # 临时更新规则
        original_rule = self.default_rules[rule_name]
        self.default_rules[rule_name] = adjusted_rule
        
        try:
            result = await self.check_rate_limit(identifier, rule_name)
            return result
        finally:
            # 恢复原始规则
            self.default_rules[rule_name] = original_rule


# 全局限流器实例
rate_limiter = RateLimiter()
adaptive_rate_limiter = AdaptiveRateLimiter()


def get_rate_limiter() -> RateLimiter:
    """获取限流器实例"""
    return rate_limiter


def get_adaptive_rate_limiter() -> AdaptiveRateLimiter:
    """获取自适应限流器实例"""
    return adaptive_rate_limiter