"""
推送通知服务
"""
from app.core.logging import get_logger
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.user import User
from app.models.article import Article
from app.models.account import Account
from app.models.push_record import PushRecord, PushStatus
from app.services.wechat import wechat_service
from app.services.limits import limits_service
from app.core.exceptions import BusinessException, ErrorCode

logger = get_logger(__name__)


class PushNotificationService:
    """推送通知服务"""
    
    async def send_article_notification(
        self, 
        db: AsyncSession, 
        user_id: int, 
        article_id: int
    ) -> Dict[str, Any]:
        """
        发送文章推送通知
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            article_id: 文章ID
            
        Returns:
            推送结果
        """
        try:
            # 检查推送限制
            limit_check = await limits_service.check_push_limit(
                user_id, db, raise_exception=False
            )
            
            if not limit_check["can_push"]:
                logger.info(f"用户 {user_id} 达到推送限制，跳过推送")
                
                # 创建跳过的推送记录
                push_record = PushRecord(
                    user_id=user_id,
                    article_id=article_id,
                    push_time=datetime.now(),
                    status=PushStatus.SKIPPED.value,
                    error_message=limit_check["message"]
                )
                db.add(push_record)
                await db.commit()
                
                return {
                    "success": False,
                    "skipped": True,
                    "reason": "push_limit_reached",
                    "message": limit_check["message"],
                    "push_record_id": push_record.id
                }
            
            # 获取用户信息
            user_query = select(User).where(User.id == user_id)
            user_result = await db.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.error(f"用户不存在: {user_id}")
                return {
                    "success": False,
                    "error": "用户不存在"
                }
            
            # 获取文章和账号信息
            article_query = (
                select(Article, Account)
                .join(Account, Article.account_id == Account.id)
                .where(Article.id == article_id)
            )
            article_result = await db.execute(article_query)
            article_data = article_result.first()
            
            if not article_data:
                logger.error(f"文章不存在: {article_id}")
                return {
                    "success": False,
                    "error": "文章不存在"
                }
            
            article, account = article_data
            
            # 创建推送记录
            push_record = PushRecord(
                user_id=user_id,
                article_id=article_id,
                push_time=datetime.now(),
                status=PushStatus.PENDING.value
            )
            db.add(push_record)
            await db.flush()  # 获取ID但不提交
            
            # 准备文章数据
            article_push_data = {
                "id": article.id,
                "title": article.title,
                "account_name": account.name,
                "platform_display_name": self._get_platform_display_name(account.platform)
            }
            
            # 发送微信推送
            push_result = await wechat_service.send_push_notification(
                user_openid=user.openid,
                article_data=article_push_data
            )
            
            # 更新推送记录状态
            if push_result["success"]:
                push_record.status = PushStatus.SUCCESS.value
                logger.info(f"推送成功 - 用户: {user_id}, 文章: {article_id}")
                
                # 更新用户推送统计
                await limits_service.increment_push_count(user_id, db)
                
                result = {
                    "success": True,
                    "message": "推送成功",
                    "push_record_id": push_record.id,
                    "msgid": push_result.get("msgid")
                }
            else:
                push_record.status = PushStatus.FAILED.value
                push_record.error_message = push_result.get("error", "推送失败")
                
                logger.warning(
                    f"推送失败 - 用户: {user_id}, 文章: {article_id}, "
                    f"错误: {push_result.get('error')}"
                )
                
                result = {
                    "success": False,
                    "error": push_result.get("error", "推送失败"),
                    "error_code": push_result.get("error_code"),
                    "push_record_id": push_record.id
                }
            
            await db.commit()
            return result
            
        except Exception as e:
            logger.error(f"发送推送通知异常: {str(e)}", exc_info=True)
            await db.rollback()
            return {
                "success": False,
                "error": f"推送服务异常: {str(e)}"
            }
    
    async def batch_send_notifications(
        self, 
        db: AsyncSession, 
        user_ids: List[int], 
        article_id: int
    ) -> Dict[str, Any]:
        """
        批量发送推送通知
        
        Args:
            db: 数据库会话
            user_ids: 用户ID列表
            article_id: 文章ID
            
        Returns:
            批量推送结果
        """
        try:
            results = {
                "total_users": len(user_ids),
                "success_count": 0,
                "failed_count": 0,
                "skipped_count": 0,
                "results": []
            }
            
            for user_id in user_ids:
                try:
                    result = await self.send_article_notification(
                        db, user_id, article_id
                    )
                    
                    if result["success"]:
                        results["success_count"] += 1
                    elif result.get("skipped"):
                        results["skipped_count"] += 1
                    else:
                        results["failed_count"] += 1
                    
                    results["results"].append({
                        "user_id": user_id,
                        "result": result
                    })
                    
                except Exception as e:
                    logger.error(f"批量推送用户 {user_id} 失败: {str(e)}")
                    results["failed_count"] += 1
                    results["results"].append({
                        "user_id": user_id,
                        "result": {
                            "success": False,
                            "error": str(e)
                        }
                    })
            
            logger.info(
                f"批量推送完成 - 文章: {article_id}, 总用户: {results['total_users']}, "
                f"成功: {results['success_count']}, 失败: {results['failed_count']}, "
                f"跳过: {results['skipped_count']}"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"批量推送异常: {str(e)}", exc_info=True)
            return {
                "total_users": len(user_ids),
                "success_count": 0,
                "failed_count": len(user_ids),
                "skipped_count": 0,
                "error": str(e),
                "results": []
            }
    
    async def get_user_push_statistics(
        self, 
        db: AsyncSession, 
        user_id: int
    ) -> Dict[str, Any]:
        """
        获取用户推送统计
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            推送统计数据
        """
        try:
            today = date.today()
            
            # 获取总推送统计
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
                    ).label("skipped")
                )
                .where(PushRecord.user_id == user_id)
            )
            
            total_result = await db.execute(total_query)
            total_stats = total_result.first()
            
            # 获取今日推送统计
            today_query = (
                select(func.count(PushRecord.id))
                .where(
                    and_(
                        PushRecord.user_id == user_id,
                        func.date(PushRecord.push_time) == today,
                        PushRecord.status == PushStatus.SUCCESS.value
                    )
                )
            )
            
            today_result = await db.execute(today_query)
            today_pushes = today_result.scalar() or 0
            
            # 获取用户限制信息
            limit_info = await limits_service.get_user_limits(user_id, db)
            
            # 计算成功率
            total_pushes = total_stats.total or 0
            success_pushes = total_stats.success or 0
            success_rate = (success_pushes / total_pushes * 100) if total_pushes > 0 else 0
            
            return {
                "user_id": user_id,
                "total_pushes": total_pushes,
                "success_pushes": success_pushes,
                "failed_pushes": total_stats.failed or 0,
                "skipped_pushes": total_stats.skipped or 0,
                "success_rate": round(success_rate, 2),
                "today_pushes": today_pushes,
                "daily_limit": limit_info.get("push_limit", 0),
                "remaining_pushes": max(0, limit_info.get("push_limit", 0) - today_pushes),
                "can_push": today_pushes < limit_info.get("push_limit", 0)
            }
            
        except Exception as e:
            logger.error(f"获取用户推送统计异常: {str(e)}")
            return {
                "user_id": user_id,
                "error": str(e)
            }
    
    async def get_push_records(
        self, 
        db: AsyncSession, 
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        获取推送记录列表
        
        Args:
            db: 数据库会话
            user_id: 用户ID筛选
            status: 状态筛选
            start_time: 开始时间
            end_time: 结束时间
            page: 页码
            page_size: 每页大小
            
        Returns:
            推送记录列表和分页信息
        """
        try:
            # 构建查询条件
            conditions = []
            
            if user_id:
                conditions.append(PushRecord.user_id == user_id)
            
            if status:
                conditions.append(PushRecord.status == status)
            
            if start_time:
                conditions.append(PushRecord.push_time >= start_time)
            
            if end_time:
                conditions.append(PushRecord.push_time <= end_time)
            
            # 获取总数
            count_query = select(func.count(PushRecord.id))
            if conditions:
                count_query = count_query.where(and_(*conditions))
            
            count_result = await db.execute(count_query)
            total_count = count_result.scalar()
            
            # 获取记录列表
            query = (
                select(PushRecord, User, Article, Account)
                .join(User, PushRecord.user_id == User.id)
                .join(Article, PushRecord.article_id == Article.id)
                .join(Account, Article.account_id == Account.id)
                .order_by(PushRecord.push_time.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            
            if conditions:
                query = query.where(and_(*conditions))
            
            result = await db.execute(query)
            records_data = result.all()
            
            # 格式化记录
            records = []
            for push_record, user, article, account in records_data:
                records.append({
                    "id": push_record.id,
                    "user_id": push_record.user_id,
                    "user_nickname": user.nickname,
                    "article_id": push_record.article_id,
                    "article_title": article.title,
                    "article_url": article.url,
                    "account_name": account.name,
                    "account_platform": account.platform,
                    "platform_display_name": self._get_platform_display_name(account.platform),
                    "push_time": push_record.push_time,
                    "status": push_record.status,
                    "error_message": push_record.error_message,
                    "is_success": push_record.is_success,
                    "is_failed": push_record.is_failed
                })
            
            # 计算分页信息
            total_pages = (total_count + page_size - 1) // page_size
            
            return {
                "records": records,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
            
        except Exception as e:
            logger.error(f"获取推送记录异常: {str(e)}")
            return {
                "records": [],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_prev": False
                },
                "error": str(e)
            }
    
    async def retry_failed_push(
        self, 
        db: AsyncSession, 
        push_record_id: int
    ) -> Dict[str, Any]:
        """
        重试失败的推送
        
        Args:
            db: 数据库会话
            push_record_id: 推送记录ID
            
        Returns:
            重试结果
        """
        try:
            # 获取推送记录
            query = select(PushRecord).where(PushRecord.id == push_record_id)
            result = await db.execute(query)
            push_record = result.scalar_one_or_none()
            
            if not push_record:
                return {
                    "success": False,
                    "error": "推送记录不存在"
                }
            
            if push_record.status == PushStatus.SUCCESS.value:
                return {
                    "success": False,
                    "error": "该推送已成功，无需重试"
                }
            
            # 重新发送推送
            retry_result = await self.send_article_notification(
                db, push_record.user_id, push_record.article_id
            )
            
            return {
                "success": True,
                "message": "重试完成",
                "retry_result": retry_result
            }
            
        except Exception as e:
            logger.error(f"重试推送异常: {str(e)}")
            return {
                "success": False,
                "error": f"重试异常: {str(e)}"
            }
    
    def _get_platform_display_name(self, platform: str) -> str:
        """获取平台显示名称"""
        platform_names = {
            "wechat": "微信公众号",
            "weibo": "微博",
            "twitter": "推特",
            "douyin": "抖音",
            "xiaohongshu": "小红书"
        }
        return platform_names.get(platform, platform)


# 创建服务实例
push_notification_service = PushNotificationService()