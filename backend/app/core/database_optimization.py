"""
数据库查询优化模块
"""
import time
import logging
from typing import Any, Dict, List, Optional, Callable
from functools import wraps
from sqlalchemy import text, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from app.core.monitoring import get_database_monitor

logger = logging.getLogger(__name__)
database_monitor = get_database_monitor()


class QueryOptimizer:
    """查询优化器"""
    
    def __init__(self):
        self.slow_query_threshold = 1.0  # 慢查询阈值（秒）
        self.query_cache = {}
    
    def monitor_query(self, query_type: str):
        """查询监控装饰器"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    logger.error(f"数据库查询失败: {query_type}, 错误: {str(e)}")
                    raise
                finally:
                    execution_time = time.time() - start_time
                    database_monitor.record_query(query_type, execution_time, success)
                    
                    # 记录慢查询
                    if execution_time >= self.slow_query_threshold:
                        logger.warning(
                            f"慢查询检测: {query_type} 耗时 {execution_time:.3f}s",
                            extra={
                                "slow_query": True,
                                "query_type": query_type,
                                "execution_time": execution_time
                            }
                        )
            
            return wrapper
        return decorator


class DatabaseIndexAnalyzer:
    """数据库索引分析器"""
    
    @staticmethod
    async def analyze_table_indexes(db_session, table_name: str) -> Dict[str, Any]:
        """分析表索引使用情况"""
        try:
            # SQLite索引分析
            query = text(f"PRAGMA index_list('{table_name}')")
            result = await db_session.execute(query)
            indexes = result.fetchall()
            
            index_info = []
            for index in indexes:
                index_name = index[1]
                # 获取索引详细信息
                detail_query = text(f"PRAGMA index_info('{index_name}')")
                detail_result = await db_session.execute(detail_query)
                columns = [row[2] for row in detail_result.fetchall()]
                
                index_info.append({
                    "name": index_name,
                    "unique": bool(index[2]),
                    "columns": columns
                })
            
            return {
                "table": table_name,
                "indexes": index_info,
                "index_count": len(index_info)
            }
        except Exception as e:
            logger.error(f"分析表索引失败: {table_name}, 错误: {str(e)}")
            return {"table": table_name, "error": str(e)}
    
    @staticmethod
    async def suggest_indexes(db_session, table_name: str, query_patterns: List[str]) -> List[str]:
        """根据查询模式建议索引"""
        suggestions = []
        
        # 分析常见查询模式
        common_patterns = {
            "user_id": "用户相关查询建议添加 user_id 索引",
            "created_at": "时间范围查询建议添加 created_at 索引",
            "status": "状态筛选查询建议添加 status 索引",
            "platform": "平台筛选查询建议添加 platform 索引"
        }
        
        for pattern in query_patterns:
            for field, suggestion in common_patterns.items():
                if field in pattern.lower():
                    suggestions.append(f"CREATE INDEX idx_{table_name}_{field} ON {table_name}({field});")
        
        return suggestions


class QueryPlanAnalyzer:
    """查询计划分析器"""
    
    @staticmethod
    async def explain_query(db_session, query: str) -> Dict[str, Any]:
        """分析查询执行计划"""
        try:
            explain_query = text(f"EXPLAIN QUERY PLAN {query}")
            result = await db_session.execute(explain_query)
            plan_rows = result.fetchall()
            
            plan_info = []
            for row in plan_rows:
                plan_info.append({
                    "id": row[0],
                    "parent": row[1],
                    "detail": row[3] if len(row) > 3 else str(row)
                })
            
            # 分析是否使用了索引
            uses_index = any("USING INDEX" in str(row) for row in plan_rows)
            has_scan = any("SCAN" in str(row) for row in plan_rows)
            
            return {
                "query": query,
                "plan": plan_info,
                "uses_index": uses_index,
                "has_full_scan": has_scan,
                "optimization_needed": has_scan and not uses_index
            }
        except Exception as e:
            logger.error(f"分析查询计划失败: {str(e)}")
            return {"error": str(e)}


class ConnectionPoolMonitor:
    """连接池监控"""
    
    def __init__(self):
        self.pool_stats = {
            "active_connections": 0,
            "idle_connections": 0,
            "total_connections": 0,
            "connection_errors": 0
        }
    
    def update_pool_stats(self, pool):
        """更新连接池统计"""
        try:
            if hasattr(pool, 'size'):
                self.pool_stats["total_connections"] = pool.size()
            if hasattr(pool, 'checked_in'):
                self.pool_stats["idle_connections"] = pool.checked_in()
            if hasattr(pool, 'checked_out'):
                self.pool_stats["active_connections"] = pool.checked_out()
        except Exception as e:
            logger.error(f"更新连接池统计失败: {str(e)}")
            self.pool_stats["connection_errors"] += 1
    
    def get_pool_health(self) -> Dict[str, Any]:
        """获取连接池健康状态"""
        total = self.pool_stats["total_connections"]
        active = self.pool_stats["active_connections"]
        
        if total == 0:
            utilization = 0
        else:
            utilization = active / total
        
        health_status = "healthy"
        if utilization > 0.9:
            health_status = "critical"
        elif utilization > 0.7:
            health_status = "warning"
        
        return {
            **self.pool_stats,
            "utilization": round(utilization, 2),
            "health_status": health_status
        }


# SQLAlchemy事件监听器，用于监控查询性能
@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """查询执行前的监听器"""
    context._query_start_time = time.time()


@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """查询执行后的监听器"""
    if hasattr(context, '_query_start_time'):
        execution_time = time.time() - context._query_start_time
        
        # 提取查询类型
        query_type = statement.strip().split()[0].upper()
        
        # 记录查询性能
        database_monitor.record_query(query_type, execution_time, True)
        
        # 记录慢查询
        if execution_time >= 1.0:
            logger.warning(
                f"慢查询检测: {query_type} 耗时 {execution_time:.3f}s",
                extra={
                    "slow_query": True,
                    "query_type": query_type,
                    "execution_time": execution_time,
                    "statement": statement[:200] + "..." if len(statement) > 200 else statement
                }
            )


# 全局实例
query_optimizer = QueryOptimizer()
connection_pool_monitor = ConnectionPoolMonitor()


def get_query_optimizer() -> QueryOptimizer:
    """获取查询优化器实例"""
    return query_optimizer


def get_connection_pool_monitor() -> ConnectionPoolMonitor:
    """获取连接池监控实例"""
    return connection_pool_monitor