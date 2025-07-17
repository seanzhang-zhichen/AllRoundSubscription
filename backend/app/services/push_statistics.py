"""
推送统计和监控服务
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from collections import defaultdict

from app.models.push_record import PushRecord, PushStatus
from app.models.user import User
from app.models.article import Article
from app.models.account import Account
from app.models.membership import MembershipLevel
from app.db.redis import get_redis
import json

logger = logging.getLogger(__name__)


class PushStatisticsService:
    """推送统计服务"""
    
    async def get_system_push_statistics(
        self, 
        db: AsyncSession,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        获取系统级推送统计
        
        Args:
            db: 数据库会话
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            系统推送统计数据
        """
        try:
            # 默认统计最近30天
            if not end_date:
                end_date = date.today()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # 构建时间条件
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            # 总体统计
            total_query = (
                select(
                    func.count(PushRecord.id).label("total"),
                    func.sum(
                        func.case((PushRecord.status == PushStatus.SUCCESS.value, 1), else_=0)
                    ).label("success"),
                    func.sum(
                        func.case((PushRecord.status == PushStatus.FAILED.value, 1), else_=0)
                    ).label("failed"),
                    func.sum(
                        func.case((PushRecord.status == PushStatus.SKIPPED.value, 1), else_=0)
                    ).label("skipped"),
                    func.sum(
                        func.case((PushRecord.status == PushStatus.PENDING.value, 1), else_=0)
                    ).label("pending")
                )
                .where(
                    and_(
                        PushRecord.push_time >= start_datetime,
                        PushRecord.push_time <= end_datetime
                    )
                )
            )
            
            total_result = await db.execute(total_query)
            total_stats = total_result.first()
            
            # 按日期统计
            daily_query = (
                select(
                    func.date(PushRecord.push_time).label("date"),
                    func.count(PushRecord.id).label("total"),
                    func.sum(
                        func.case((PushRecord.status == PushStatus.SUCCESS.value, 1), else_=0)
                    ).label("success"),
                    func.sum(
                        func.case((PushRecord.status == PushStatus.FAILED.value, 1), else_=0)
                    ).label("failed")
                )
                .where(
                    and_(
                        PushRecord.push_time >= start_datetime,
                        PushRecord.push_time <= end_datetime
                    )
                )
                .group_by(func.date(PushRecord.push_time))
                .order_by(func.date(PushRecord.push_time))
            )
            
            daily_result = await db.execute(daily_query)
            daily_stats = daily_result.all()
            
            # 按会员等级统计
            membership_query = (
                select(
                    User.membership_level,
                    func.count(PushRecord.id).label("total"),
                    func.sum(
                        func.case((PushRecord.status == PushStatus.SUCCESS.value, 1), else_=0)
                    ).label("success")
                )
                .join(User, PushRecord.user_id == User.id)
                .where(
                    and_(
                        PushRecord.push_time >= start_datetime,
                        PushRecord.push_time <= end_datetime
                    )
                )
                .group_by(User.membership_level)
            )
            
            membership_result = await db.execute(membership_query)
            membership_stats = membership_result.all()
            
            # 计算成功率
            total_pushes = total_stats.total or 0
            success_pushes = total_stats.success or 0
            success_rate = (success_pushes / total_pushes * 100) if total_pushes > 0 else 0
            
            # 格式化结果
            result = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": (end_date - start_date).days + 1
                },
                "total_statistics": {
                    "total_pushes": total_pushes,
                    "success_pushes": success_pushes,
                    "failed_pushes": total_stats.failed or 0,
                    "skipped_pushes": total_stats.skipped or 0,
                    "pending_pushes": total_stats.pending or 0,
                    "success_rate": round(success_rate, 2)
                },
                "daily_statistics": [
                    {
                        "date": stat.date.isoformat(),
                        "total": stat.total,
                        "success": stat.success,
                        "failed": stat.failed,
                        "success_rate": round((stat.success / stat.total * 100) if stat.total > 0 else 0, 2)
                    }
                    for stat in daily_stats
                ],
                "membership_statistics": [
                    {
                        "membership_level": stat.membership_level,
                        "total_pushes": stat.total,
                        "success_pushes": stat.success,
                        "success_rate": round((stat.success / stat.total * 100) if stat.total > 0 else 0, 2)
                    }
                    for stat in membership_stats
                ]
            }
            
            return result
            
        except Exception as e:
            logger.error(f"获取系统推送统计失败: {str(e)}")
            return {
                "error": str(e),
                "period": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                }
            }
    
    async def get_platform_push_statistics(
        self, 
        db: AsyncSession,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取按平台分组的推送统计
        
        Args:
            db: 数据库会话
            days: 统计天数
            
        Returns:
            平台推送统计数据
        """
        try:
            # 计算时间范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 按平台统计
            platform_query = (
                select(
                    Account.platform,
                    func.count(PushRecord.id).label("total"),
                    func.sum(
                        func.case((PushRecord.status == PushStatus.SUCCESS.value, 1), else_=0)
                    ).label("success"),
                    func.sum(
                        func.case((PushRecord.status == PushStatus.FAILED.value, 1), else_=0)
                    ).label("failed")
                )
                .join(Article, PushRecord.article_id == Article.id)
                .join(Account, Article.account_id == Account.id)
                .where(
                    and_(
                        PushRecord.push_time >= start_date,
                        PushRecord.push_time <= end_date
                    )
                )
                .group_by(Account.platform)
                .order_by(desc(func.count(PushRecord.id)))
            )
            
            platform_result = await db.execute(platform_query)
            platform_stats = platform_result.all()
            
            # 格式化结果
            platform_names = {
                "wechat": "微信公众号",
                "weibo": "微博",
                "twitter": "推特",
                "douyin": "抖音",
                "xiaohongshu": "小红书"
            }
            
            result = {
                "period_days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "platform_statistics": [
                    {
                        "platform": stat.platform,
                        "platform_name": platform_names.get(stat.platform, stat.platform),
                        "total_pushes": stat.total,
                        "success_pushes": stat.success,
                        "failed_pushes": stat.failed,
                        "success_rate": round((stat.success / stat.total * 100) if stat.total > 0 else 0, 2)
                    }
                    for stat in platform_stats
                ]
            }
            
            return result
            
        except Exception as e:
            logger.error(f"获取平台推送统计失败: {str(e)}")
            return {
                "error": str(e),
                "period_days": days
            }
    
    async def get_top_active_users(
        self, 
        db: AsyncSession,
        limit: int = 10,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        获取推送最活跃的用户
        
        Args:
            db: 数据库会话
            limit: 返回数量限制
            days: 统计天数
            
        Returns:
            活跃用户列表
        """
        try:
            # 计算时间范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 查询活跃用户
            query = (
                select(
                    User.id,
                    User.nickname,
                    User.membership_level,
                    func.count(PushRecord.id).label("total_pushes"),
                    func.sum(
                        func.case((PushRecord.status == PushStatus.SUCCESS.value, 1), else_=0)
                    ).label("success_pushes")
                )
                .join(PushRecord, User.id == PushRecord.user_id)
                .where(
                    and_(
                        PushRecord.push_time >= start_date,
                        PushRecord.push_time <= end_date
                    )
                )
                .group_by(User.id, User.nickname, User.membership_level)
                .order_by(desc(func.count(PushRecord.id)))
                .limit(limit)
            )
            
            result = await db.execute(query)
            users = result.all()
            
            # 格式化结果
            active_users = [
                {
                    "user_id": user.id,
                    "nickname": user.nickname,
                    "membership_level": user.membership_level,
                    "total_pushes": user.total_pushes,
                    "success_pushes": user.success_pushes,
                    "success_rate": round((user.success_pushes / user.total_pushes * 100) if user.total_pushes > 0 else 0, 2)
                }
                for user in users
            ]
            
            return active_users
            
        except Exception as e:
            logger.error(f"获取活跃用户失败: {str(e)}")
            return []
    
    async def get_push_failure_analysis(
        self, 
        db: AsyncSession,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取推送失败分析
        
        Args:
            db: 数据库会话
            days: 分析天数
            
        Returns:
            推送失败分析数据
        """
        try:
            # 计算时间范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 查询失败记录
            query = (
                select(
                    PushRecord.error_message,
                    func.count(PushRecord.id).label("count")
                )
                .where(
                    and_(
                        PushRecord.status == PushStatus.FAILED.value,
                        PushRecord.push_time >= start_date,
                        PushRecord.push_time <= end_date,
                        PushRecord.error_message.isnot(None)
                    )
                )
                .group_by(PushRecord.error_message)
                .order_by(desc(func.count(PushRecord.id)))
            )
            
            result = await db.execute(query)
            failure_stats = result.all()
            
            # 分类错误信息
            error_categories = defaultdict(int)
            detailed_errors = []
            
            for stat in failure_stats:
                error_msg = stat.error_message
                count = stat.count
                
                detailed_errors.append({
                    "error_message": error_msg,
                    "count": count
                })
                
                # 错误分类
                if "用户未关注" in error_msg or "43004" in error_msg:
                    error_categories["用户未关注服务号"] += count
                elif "access_token" in error_msg or "40001" in error_msg:
                    error_categories["访问令牌无效"] += count
                elif "openid" in error_msg or "40003" in error_msg:
                    error_categories["用户ID无效"] += count
                elif "超时" in error_msg or "timeout" in error_msg.lower():
                    error_categories["网络超时"] += count
                elif "限制" in error_msg or "limit" in error_msg.lower():
                    error_categories["推送限制"] += count
                else:
                    error_categories["其他错误"] += count
            
            # 格式化结果
            result = {
                "period_days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_failures": sum(stat.count for stat in failure_stats),
                "error_categories": [
                    {
                        "category": category,
                        "count": count,
                        "percentage": round((count / sum(error_categories.values()) * 100) if sum(error_categories.values()) > 0 else 0, 2)
                    }
                    for category, count in error_categories.items()
                ],
                "detailed_errors": detailed_errors[:20]  # 只返回前20个详细错误
            }
            
            return result
            
        except Exception as e:
            logger.error(f"获取推送失败分析失败: {str(e)}")
            return {
                "error": str(e),
                "period_days": days
            }
    
    async def cache_statistics(
        self, 
        key: str, 
        data: Dict[str, Any], 
        expire_seconds: int = 300
    ) -> bool:
        """
        缓存统计数据
        
        Args:
            key: 缓存键
            data: 统计数据
            expire_seconds: 过期时间（秒）
            
        Returns:
            是否成功
        """
        try:
            redis = await get_redis()
            if not redis:
                return False
            
            # 添加时间戳
            cache_data = {
                **data,
                "cached_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(seconds=expire_seconds)).isoformat()
            }
            
            await redis.setex(
                f"push_stats:{key}",
                expire_seconds,
                json.dumps(cache_data, default=str)
            )
            
            logger.debug(f"统计数据已缓存: {key}")
            return True
            
        except Exception as e:
            logger.error(f"缓存统计数据失败: {str(e)}")
            return False
    
    async def get_cached_statistics(self, key: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存的统计数据
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的统计数据或None
        """
        try:
            redis = await get_redis()
            if not redis:
                return None
            
            cached_data = await redis.get(f"push_stats:{key}")
            if cached_data:
                data = json.loads(cached_data)
                logger.debug(f"使用缓存的统计数据: {key}")
                return data
            
            return None
            
        except Exception as e:
            logger.error(f"获取缓存统计数据失败: {str(e)}")
            return None


# 创建服务实例
push_statistics_service = PushStatisticsService()