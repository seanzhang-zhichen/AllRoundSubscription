"""
用户权限限制检查服务
"""
from app.core.logging import get_logger
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.user import User, MembershipLevel
from app.models.subscription import Subscription
from app.models.push_record import PushRecord, PushStatus
from app.services.membership import membership_service, MembershipConfig
from app.core.exceptions import (
    NotFoundException,
    BusinessException,
    ErrorCode,
    SubscriptionLimitException,
    PushLimitException
)
from app.db.redis import cache_service

logger = get_logger(__name__)


class LimitsService:
    """用户权限限制检查服务类"""
    
    async def check_subscription_limit(
        self, 
        user_id: int, 
        db: AsyncSession,
        raise_exception: bool = False
    ) -> Dict[str, Any]:
        """
        检查用户订阅数量限制
        
        Args:
            user_id: 用户ID
            db: 数据库会话
            raise_exception: 是否在超限时抛出异常
            
        Returns:
            订阅限制检查结果
            
        Raises:
            SubscriptionLimitException: 当raise_exception=True且超限时
        """
        try:
            # 获取用户信息
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise NotFoundException("用户不存在")
            
            # 获取有效会员等级和限制
            membership_info = await membership_service.get_membership_info(user_id, db)
            effective_level = MembershipLevel(membership_info["effective_level"])
            subscription_limit = MembershipConfig.get_subscription_limit(effective_level)
            
            # 获取当前订阅数量
            current_count = await self._get_user_subscription_count(db, user_id)
            
            # 检查是否可以继续订阅
            can_subscribe = (subscription_limit == -1) or (current_count < subscription_limit)
            
            result = {
                "user_id": user_id,
                "membership_level": user.membership_level.value,
                "effective_level": effective_level.value,
                "is_membership_active": membership_info["is_active"],
                "subscription_limit": subscription_limit,
                "subscription_used": current_count,
                "subscription_remaining": -1 if subscription_limit == -1 else max(0, subscription_limit - current_count),
                "can_subscribe": can_subscribe,
                "limit_reached": not can_subscribe,
                "upgrade_required": not can_subscribe and effective_level == MembershipLevel.FREE
            }
            
            # 如果需要抛出异常且已达限制
            if raise_exception and not can_subscribe:
                if effective_level == MembershipLevel.FREE:
                    raise SubscriptionLimitException(
                        f"免费用户订阅数量已达上限({subscription_limit}个)，请升级会员"
                    )
                else:
                    raise SubscriptionLimitException(
                        f"当前会员订阅数量已达上限({subscription_limit}个)"
                    )
            
            logger.debug(
                f"订阅限制检查完成 - 用户ID: {user_id}, "
                f"当前: {current_count}/{subscription_limit}, "
                f"可订阅: {can_subscribe}"
            )
            
            return result
            
        except (NotFoundException, SubscriptionLimitException):
            raise
        except Exception as e:
            logger.error(f"检查订阅限制失败: {str(e)}", exc_info=True)
            raise BusinessException(
                error_code=ErrorCode.DATABASE_ERROR,
                message="检查订阅限制失败"
            )
    
    async def check_push_limit(
        self, 
        user_id: int, 
        db: AsyncSession,
        raise_exception: bool = False
    ) -> Dict[str, Any]:
        """
        检查用户推送次数限制
        
        Args:
            user_id: 用户ID
            db: 数据库会话
            raise_exception: 是否在超限时抛出异常
            
        Returns:
            推送限制检查结果
            
        Raises:
            PushLimitException: 当raise_exception=True且超限时
        """
        try:
            # 获取用户信息
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise NotFoundException("用户不存在")
            
            # 获取有效会员等级和限制
            membership_info = await membership_service.get_membership_info(user_id, db)
            effective_level = MembershipLevel(membership_info["effective_level"])
            daily_push_limit = MembershipConfig.get_daily_push_limit(effective_level)
            
            # 获取今日推送数量
            today_count = await self._get_daily_push_count(db, user_id)
            
            # 检查是否可以继续推送
            can_push = (daily_push_limit == -1) or (today_count < daily_push_limit)
            
            result = {
                "user_id": user_id,
                "membership_level": user.membership_level.value,
                "effective_level": effective_level.value,
                "is_membership_active": membership_info["is_active"],
                "daily_push_limit": daily_push_limit,
                "daily_push_used": today_count,
                "daily_push_remaining": -1 if daily_push_limit == -1 else max(0, daily_push_limit - today_count),
                "can_receive_push": can_push,
                "limit_reached": not can_push,
                "upgrade_required": not can_push and effective_level == MembershipLevel.FREE,
                "reset_time": self._get_next_reset_time()
            }
            
            # 如果需要抛出异常且已达限制
            if raise_exception and not can_push:
                if effective_level == MembershipLevel.FREE:
                    raise PushLimitException(
                        f"免费用户今日推送次数已达上限({daily_push_limit}次)，请升级会员"
                    )
                else:
                    raise PushLimitException(
                        f"当前会员今日推送次数已达上限({daily_push_limit}次)"
                    )
            
            logger.debug(
                f"推送限制检查完成 - 用户ID: {user_id}, "
                f"今日: {today_count}/{daily_push_limit}, "
                f"可推送: {can_push}"
            )
            
            return result
            
        except (NotFoundException, PushLimitException):
            raise
        except Exception as e:
            logger.error(f"检查推送限制失败: {str(e)}", exc_info=True)
            raise BusinessException(
                error_code=ErrorCode.DATABASE_ERROR,
                message="检查推送限制失败"
            )
    
    async def get_user_limits_summary(self, user_id: int, db: AsyncSession) -> Dict[str, Any]:
        """
        获取用户权限限制汇总信息
        
        Args:
            user_id: 用户ID
            db: 数据库会话
            
        Returns:
            用户限制汇总信息
        """
        try:
            # 并行获取订阅和推送限制信息
            subscription_info = await self.check_subscription_limit(user_id, db)
            push_info = await self.check_push_limit(user_id, db)
            
            # 获取会员信息
            membership_info = await membership_service.get_membership_info(user_id, db)
            
            summary = {
                "user_id": user_id,
                "membership": {
                    "level": membership_info["level"],
                    "effective_level": membership_info["effective_level"],
                    "is_active": membership_info["is_active"],
                    "expire_at": membership_info["expire_at"],
                    "features": membership_info["features"],
                    "benefits": membership_info["benefits"]
                },
                "subscription": {
                    "limit": subscription_info["subscription_limit"],
                    "used": subscription_info["subscription_used"],
                    "remaining": subscription_info["subscription_remaining"],
                    "can_subscribe": subscription_info["can_subscribe"],
                    "limit_reached": subscription_info["limit_reached"]
                },
                "push": {
                    "daily_limit": push_info["daily_push_limit"],
                    "daily_used": push_info["daily_push_used"],
                    "daily_remaining": push_info["daily_push_remaining"],
                    "can_receive_push": push_info["can_receive_push"],
                    "limit_reached": push_info["limit_reached"],
                    "reset_time": push_info["reset_time"]
                },
                "upgrade_suggestions": self._get_upgrade_suggestions(
                    subscription_info, push_info, membership_info
                )
            }
            
            logger.debug(f"获取用户限制汇总成功，用户ID: {user_id}")
            return summary
            
        except Exception as e:
            logger.error(f"获取用户限制汇总失败: {str(e)}", exc_info=True)
            raise BusinessException(
                error_code=ErrorCode.DATABASE_ERROR,
                message="获取用户限制信息失败"
            )
    
    async def get_membership_benefits_display(self, level: MembershipLevel) -> Dict[str, Any]:
        """
        获取会员权益展示信息
        
        Args:
            level: 会员等级
            
        Returns:
            会员权益展示信息
        """
        try:
            benefits_info = {
                "level": level.value,
                "level_name": self._get_level_display_name(level),
                "subscription_limit": MembershipConfig.get_subscription_limit(level),
                "daily_push_limit": MembershipConfig.get_daily_push_limit(level),
                "features": MembershipConfig.get_features(level),
                "benefits": MembershipConfig.get_benefits(level),
                "feature_descriptions": self._get_feature_descriptions(level),
                "comparison": self._get_level_comparison(level)
            }
            
            logger.debug(f"获取会员权益展示信息成功，等级: {level.value}")
            return benefits_info
            
        except Exception as e:
            logger.error(f"获取会员权益展示信息失败: {str(e)}", exc_info=True)
            raise BusinessException(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="获取会员权益信息失败"
            )
    
    async def get_all_membership_benefits(self) -> Dict[str, Any]:
        """
        获取所有会员等级的权益对比信息
        
        Returns:
            所有会员等级权益对比信息
        """
        try:
            all_benefits = {}
            
            for level in MembershipLevel:
                all_benefits[level.value] = await self.get_membership_benefits_display(level)
            
            # 添加对比表格
            comparison_table = self._generate_comparison_table()
            
            result = {
                "levels": all_benefits,
                "comparison_table": comparison_table,
                "upgrade_paths": self._get_upgrade_paths()
            }
            
            logger.debug("获取所有会员权益对比信息成功")
            return result
            
        except Exception as e:
            logger.error(f"获取所有会员权益对比信息失败: {str(e)}", exc_info=True)
            raise BusinessException(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="获取会员权益对比信息失败"
            )
    
    def _get_level_display_name(self, level: MembershipLevel) -> str:
        """获取会员等级显示名称"""
        names = {
            MembershipLevel.FREE: "免费用户",
            MembershipLevel.BASIC: "基础会员",
            MembershipLevel.PREMIUM: "高级会员"
        }
        return names.get(level, "未知等级")
    
    def _get_feature_descriptions(self, level: MembershipLevel) -> Dict[str, str]:
        """获取功能详细描述"""
        all_descriptions = {
            "basic_aggregation": "基础内容聚合 - 支持主流平台内容抓取和展示",
            "advanced_search": "高级搜索功能 - 支持多条件筛选和智能推荐",
            "priority_support": "优先客服支持 - 享受专属客服通道和快速响应",
            "exclusive_features": "专属功能体验 - 抢先体验新功能和高级特性",
            "data_export": "数据导出功能 - 支持订阅数据和历史记录导出"
        }
        
        features = MembershipConfig.get_features(level)
        return {feature: all_descriptions.get(feature, "") for feature in features}
    
    def _get_level_comparison(self, current_level: MembershipLevel) -> Dict[str, Any]:
        """获取等级对比信息"""
        all_levels = [MembershipLevel.FREE, MembershipLevel.BASIC, MembershipLevel.PREMIUM]
        current_index = all_levels.index(current_level)
        
        comparison = {
            "current_level": current_level.value,
            "can_upgrade_to": [],
            "upgrade_benefits": []
        }
        
        # 可升级的等级
        for i in range(current_index + 1, len(all_levels)):
            next_level = all_levels[i]
            comparison["can_upgrade_to"].append({
                "level": next_level.value,
                "name": self._get_level_display_name(next_level),
                "subscription_limit": MembershipConfig.get_subscription_limit(next_level),
                "daily_push_limit": MembershipConfig.get_daily_push_limit(next_level)
            })
        
        # 升级后的额外权益
        if current_index < len(all_levels) - 1:
            next_level = all_levels[current_index + 1]
            current_features = set(MembershipConfig.get_features(current_level))
            next_features = set(MembershipConfig.get_features(next_level))
            new_features = next_features - current_features
            
            comparison["upgrade_benefits"] = list(new_features)
        
        return comparison
    
    def _generate_comparison_table(self) -> List[Dict[str, Any]]:
        """生成会员等级对比表格"""
        table = []
        
        features = [
            {"key": "subscription_limit", "name": "订阅数量", "type": "limit"},
            {"key": "daily_push_limit", "name": "每日推送", "type": "limit"},
            {"key": "basic_aggregation", "name": "基础聚合", "type": "feature"},
            {"key": "advanced_search", "name": "高级搜索", "type": "feature"},
            {"key": "priority_support", "name": "优先支持", "type": "feature"},
            {"key": "exclusive_features", "name": "专属功能", "type": "feature"},
            {"key": "data_export", "name": "数据导出", "type": "feature"}
        ]
        
        for feature in features:
            row = {
                "feature": feature["name"],
                "type": feature["type"],
                "free": self._get_feature_value(MembershipLevel.FREE, feature["key"], feature["type"]),
                "basic": self._get_feature_value(MembershipLevel.BASIC, feature["key"], feature["type"]),
                "premium": self._get_feature_value(MembershipLevel.PREMIUM, feature["key"], feature["type"])
            }
            table.append(row)
        
        return table
    
    def _get_feature_value(self, level: MembershipLevel, key: str, feature_type: str) -> str:
        """获取功能值的显示文本"""
        if feature_type == "limit":
            if key == "subscription_limit":
                limit = MembershipConfig.get_subscription_limit(level)
                return "无限制" if limit == -1 else f"{limit}个"
            elif key == "daily_push_limit":
                limit = MembershipConfig.get_daily_push_limit(level)
                return "无限制" if limit == -1 else f"{limit}次"
        elif feature_type == "feature":
            features = MembershipConfig.get_features(level)
            return "✓" if key in features else "✗"
        
        return ""
    
    def _get_upgrade_paths(self) -> List[Dict[str, Any]]:
        """获取升级路径信息"""
        paths = [
            {
                "from": MembershipLevel.FREE.value,
                "to": MembershipLevel.BASIC.value,
                "benefits": [
                    "订阅数量从10个增加到50个",
                    "每日推送从5次增加到20次",
                    "获得高级搜索功能",
                    "享受优先客服支持"
                ]
            },
            {
                "from": MembershipLevel.BASIC.value,
                "to": MembershipLevel.PREMIUM.value,
                "benefits": [
                    "无限订阅数量",
                    "无限推送次数",
                    "专属功能抢先体验",
                    "数据导出功能"
                ]
            },
            {
                "from": MembershipLevel.FREE.value,
                "to": MembershipLevel.PREMIUM.value,
                "benefits": [
                    "无限订阅和推送",
                    "全部高级功能",
                    "最佳用户体验"
                ]
            }
        ]
        return paths
    
    def _get_upgrade_suggestions(
        self, 
        subscription_info: Dict[str, Any], 
        push_info: Dict[str, Any],
        membership_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """获取升级建议"""
        suggestions = []
        
        current_level = MembershipLevel(membership_info["effective_level"])
        
        # 如果订阅或推送达到限制，建议升级
        if subscription_info["limit_reached"] or push_info["limit_reached"]:
            if current_level == MembershipLevel.FREE:
                suggestions.append({
                    "type": "upgrade",
                    "target_level": MembershipLevel.BASIC.value,
                    "reason": "当前限制已达上限",
                    "benefits": ["订阅数量增加到50个", "每日推送增加到20次"]
                })
            elif current_level == MembershipLevel.BASIC:
                suggestions.append({
                    "type": "upgrade",
                    "target_level": MembershipLevel.PREMIUM.value,
                    "reason": "当前限制已达上限",
                    "benefits": ["无限订阅和推送"]
                })
        
        # 如果使用量较高，建议升级
        if (subscription_info["subscription_used"] / max(subscription_info["subscription_limit"], 1) > 0.8 or
            push_info["daily_push_used"] / max(push_info["daily_push_limit"], 1) > 0.8):
            if current_level == MembershipLevel.FREE:
                suggestions.append({
                    "type": "recommendation",
                    "target_level": MembershipLevel.BASIC.value,
                    "reason": "使用量较高，建议升级获得更多配额",
                    "benefits": ["避免达到使用限制", "享受更多功能"]
                })
        
        return suggestions
    
    def _get_next_reset_time(self) -> datetime:
        """获取下次重置时间（明天0点）"""
        tomorrow = date.today() + timedelta(days=1)
        return datetime.combine(tomorrow, datetime.min.time())
    
    async def _get_user_by_id(self, db: AsyncSession, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_user_subscription_count(self, db: AsyncSession, user_id: int) -> int:
        """获取用户订阅数量"""
        stmt = select(func.count(Subscription.id)).where(Subscription.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar() or 0
    
    async def _get_daily_push_count(self, db: AsyncSession, user_id: int) -> int:
        """获取用户今日推送数量"""
        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)
        
        stmt = (
            select(func.count(PushRecord.id))
            .where(
                and_(
                    PushRecord.user_id == user_id,
                    PushRecord.push_time >= today,
                    PushRecord.push_time < tomorrow,
                    PushRecord.status == PushStatus.SUCCESS.value
                )
            )
        )
        result = await db.execute(stmt)
        return result.scalar() or 0


# 全局限制服务实例
limits_service = LimitsService()