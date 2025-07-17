"""
推送队列管理服务
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.user import User
from app.models.push_record import PushRecord, PushStatus
from app.services.limits import limits_service
from app.db.redis import get_redis
import json

logger = logging.getLogger(__name__)


class PushQueueService:
    """推送队列管理服务"""
    
    def __init__(self):
        self.queue_key = "new_articles_queue"
        self.processing_key = "push_processing"
        self.failed_queue_key = "failed_push_queue"
        
    async def get_next_push_item(self) -> Optional[Dict[str, Any]]:
        """
        从队列中获取下一个推送项目
        
        Returns:
            推送项目数据或None
        """
        try:
            redis = await get_redis()
            if not redis:
                return None
            
            # 从队列右端弹出一个项目（FIFO）
            item_data = await redis.rpop(self.queue_key)
            
            if item_data:
                item = json.loads(item_data)
                logger.debug(f"获取推送项目: 文章ID {item.get('article_id')}")
                return item
            
            return None
            
        except Exception as e:
            logger.error(f"获取推送项目失败: {str(e)}")
            return None
    
    async def process_push_item(
        self, 
        db: AsyncSession, 
        push_item: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理推送项目
        
        Args:
            db: 数据库会话
            push_item: 推送项目数据
            
        Returns:
            处理结果
        """
        try:
            article_id = push_item.get("article_id")
            user_ids = push_item.get("user_ids", [])
            
            if not article_id or not user_ids:
                logger.warning(f"推送项目数据不完整: {push_item}")
                return {
                    "success": False,
                    "error": "推送项目数据不完整",
                    "processed_users": 0,
                    "failed_users": 0
                }
            
            processed_users = 0
            failed_users = 0
            push_records = []
            
            # 为每个用户创建推送记录
            for user_id in user_ids:
                try:
                    # 检查用户推送限制
                    can_push = await limits_service.check_push_limit(
                        user_id, db, raise_exception=False
                    )
                    
                    if not can_push["can_push"]:
                        # 创建跳过的推送记录
                        push_record = PushRecord(
                            user_id=user_id,
                            article_id=article_id,
                            push_time=datetime.now(),
                            status=PushStatus.SKIPPED.value,
                            error_message="达到推送限制"
                        )
                        push_records.append(push_record)
                        failed_users += 1
                        logger.debug(f"用户 {user_id} 达到推送限制，跳过推送")
                        continue
                    
                    # 创建待推送记录
                    push_record = PushRecord(
                        user_id=user_id,
                        article_id=article_id,
                        push_time=datetime.now(),
                        status=PushStatus.PENDING.value
                    )
                    push_records.append(push_record)
                    processed_users += 1
                    
                except Exception as e:
                    logger.error(f"处理用户 {user_id} 推送失败: {str(e)}")
                    # 创建失败的推送记录
                    push_record = PushRecord(
                        user_id=user_id,
                        article_id=article_id,
                        push_time=datetime.now(),
                        status=PushStatus.FAILED.value,
                        error_message=str(e)
                    )
                    push_records.append(push_record)
                    failed_users += 1
            
            # 批量保存推送记录
            if push_records:
                db.add_all(push_records)
                await db.commit()
            
            result = {
                "success": True,
                "article_id": article_id,
                "total_users": len(user_ids),
                "processed_users": processed_users,
                "failed_users": failed_users,
                "push_records_created": len(push_records)
            }
            
            logger.info(
                f"处理推送项目完成 - 文章ID: {article_id}, "
                f"处理用户: {processed_users}, 失败用户: {failed_users}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"处理推送项目失败: {str(e)}", exc_info=True)
            # 将失败的项目添加到失败队列
            await self._add_to_failed_queue(push_item, str(e))
            
            return {
                "success": False,
                "error": str(e),
                "processed_users": 0,
                "failed_users": len(push_item.get("user_ids", []))
            }
    
    async def get_pending_push_records(
        self, 
        db: AsyncSession, 
        limit: int = 100
    ) -> List[PushRecord]:
        """
        获取待推送的记录
        
        Args:
            db: 数据库会话
            limit: 限制数量
            
        Returns:
            待推送记录列表
        """
        try:
            query = (
                select(PushRecord)
                .where(PushRecord.status == PushStatus.PENDING.value)
                .order_by(PushRecord.push_time)
                .limit(limit)
            )
            
            result = await db.execute(query)
            records = result.scalars().all()
            
            logger.debug(f"获取到 {len(records)} 条待推送记录")
            return list(records)
            
        except Exception as e:
            logger.error(f"获取待推送记录失败: {str(e)}")
            return []
    
    async def update_push_record_status(
        self, 
        db: AsyncSession, 
        record_id: int, 
        status: PushStatus, 
        error_message: Optional[str] = None
    ) -> bool:
        """
        更新推送记录状态
        
        Args:
            db: 数据库会话
            record_id: 记录ID
            status: 新状态
            error_message: 错误信息（可选）
            
        Returns:
            是否成功
        """
        try:
            query = select(PushRecord).where(PushRecord.id == record_id)
            result = await db.execute(query)
            record = result.scalar_one_or_none()
            
            if not record:
                logger.warning(f"推送记录不存在: {record_id}")
                return False
            
            record.status = status.value
            if error_message:
                record.error_message = error_message
            
            await db.commit()
            
            logger.debug(f"更新推送记录状态: {record_id} -> {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"更新推送记录状态失败: {str(e)}")
            await db.rollback()
            return False
    
    async def get_queue_statistics(self) -> Dict[str, Any]:
        """
        获取队列统计信息
        
        Returns:
            队列统计数据
        """
        try:
            redis = await get_redis()
            if not redis:
                return {
                    "pending_queue_length": 0,
                    "failed_queue_length": 0,
                    "processing_count": 0,
                    "status": "redis_unavailable"
                }
            
            # 获取各队列长度
            pending_length = await redis.llen(self.queue_key)
            failed_length = await redis.llen(self.failed_queue_key)
            processing_count = await redis.scard(self.processing_key)
            
            stats = {
                "pending_queue_length": pending_length,
                "failed_queue_length": failed_length,
                "processing_count": processing_count,
                "status": "active",
                "timestamp": datetime.now().isoformat()
            }
            
            logger.debug(f"队列统计: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"获取队列统计失败: {str(e)}")
            return {
                "pending_queue_length": 0,
                "failed_queue_length": 0,
                "processing_count": 0,
                "status": "error",
                "error": str(e)
            }
    
    async def retry_failed_items(self, max_items: int = 10) -> Dict[str, Any]:
        """
        重试失败的推送项目
        
        Args:
            max_items: 最大重试数量
            
        Returns:
            重试结果
        """
        try:
            redis = await get_redis()
            if not redis:
                return {"success": False, "error": "Redis不可用"}
            
            retried_count = 0
            
            # 从失败队列中取出项目并重新加入主队列
            for _ in range(max_items):
                failed_item = await redis.rpop(self.failed_queue_key)
                if not failed_item:
                    break
                
                # 重新加入主队列
                await redis.lpush(self.queue_key, failed_item)
                retried_count += 1
            
            result = {
                "success": True,
                "retried_count": retried_count,
                "message": f"重试了 {retried_count} 个失败项目"
            }
            
            logger.info(f"重试失败项目完成: {retried_count} 个")
            return result
            
        except Exception as e:
            logger.error(f"重试失败项目失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "retried_count": 0
            }
    
    async def clear_all_queues(self) -> bool:
        """
        清空所有队列（用于维护）
        
        Returns:
            是否成功
        """
        try:
            redis = await get_redis()
            if not redis:
                return False
            
            # 清空所有相关队列
            await redis.delete(self.queue_key)
            await redis.delete(self.failed_queue_key)
            await redis.delete(self.processing_key)
            
            logger.info("所有推送队列已清空")
            return True
            
        except Exception as e:
            logger.error(f"清空队列失败: {str(e)}")
            return False
    
    async def _add_to_failed_queue(self, push_item: Dict[str, Any], error: str) -> None:
        """将失败的项目添加到失败队列"""
        try:
            redis = await get_redis()
            if not redis:
                return
            
            # 添加错误信息和时间戳
            failed_item = {
                **push_item,
                "failed_at": datetime.now().isoformat(),
                "error": error
            }
            
            await redis.lpush(
                self.failed_queue_key,
                json.dumps(failed_item, default=str)
            )
            
            logger.debug(f"添加失败项目到失败队列: 文章ID {push_item.get('article_id')}")
            
        except Exception as e:
            logger.error(f"添加到失败队列失败: {str(e)}")


# 创建服务实例
push_queue_service = PushQueueService()