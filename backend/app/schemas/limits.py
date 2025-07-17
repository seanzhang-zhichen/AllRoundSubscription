"""
权限限制相关Pydantic模型
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.models.user import MembershipLevel


class SubscriptionLimitInfo(BaseModel):
    """订阅限制信息"""
    user_id: int = Field(description="用户ID")
    membership_level: str = Field(description="会员等级")
    effective_level: str = Field(description="有效等级")
    is_membership_active: bool = Field(description="会员是否有效")
    subscription_limit: int = Field(description="订阅限制")
    subscription_used: int = Field(description="已使用订阅数")
    subscription_remaining: int = Field(description="剩余订阅数")
    can_subscribe: bool = Field(description="是否可以继续订阅")
    limit_reached: bool = Field(description="是否达到限制")
    upgrade_required: bool = Field(description="是否需要升级")


class PushLimitInfo(BaseModel):
    """推送限制信息"""
    user_id: int = Field(description="用户ID")
    membership_level: str = Field(description="会员等级")
    effective_level: str = Field(description="有效等级")
    is_membership_active: bool = Field(description="会员是否有效")
    daily_push_limit: int = Field(description="每日推送限制")
    daily_push_used: int = Field(description="今日已推送数")
    daily_push_remaining: int = Field(description="今日剩余推送数")
    can_receive_push: bool = Field(description="是否可以接收推送")
    limit_reached: bool = Field(description="是否达到限制")
    upgrade_required: bool = Field(description="是否需要升级")
    reset_time: datetime = Field(description="重置时间")


class MembershipSummary(BaseModel):
    """会员信息汇总"""
    level: str = Field(description="会员等级")
    effective_level: str = Field(description="有效等级")
    is_active: bool = Field(description="是否有效")
    expire_at: Optional[datetime] = Field(None, description="到期时间")
    features: List[str] = Field(description="功能列表")
    benefits: List[str] = Field(description="权益列表")


class SubscriptionSummary(BaseModel):
    """订阅信息汇总"""
    limit: int = Field(description="订阅限制")
    used: int = Field(description="已使用数量")
    remaining: int = Field(description="剩余数量")
    can_subscribe: bool = Field(description="是否可以继续订阅")
    limit_reached: bool = Field(description="是否达到限制")


class PushSummary(BaseModel):
    """推送信息汇总"""
    daily_limit: int = Field(description="每日推送限制")
    daily_used: int = Field(description="今日已推送数")
    daily_remaining: int = Field(description="今日剩余推送数")
    can_receive_push: bool = Field(description="是否可以接收推送")
    limit_reached: bool = Field(description="是否达到限制")
    reset_time: datetime = Field(description="重置时间")


class UpgradeSuggestion(BaseModel):
    """升级建议"""
    type: str = Field(description="建议类型")
    target_level: str = Field(description="目标等级")
    reason: str = Field(description="建议原因")
    benefits: List[str] = Field(description="升级后的权益")


class UserLimitsSummary(BaseModel):
    """用户限制汇总信息"""
    user_id: int = Field(description="用户ID")
    membership: MembershipSummary = Field(description="会员信息")
    subscription: SubscriptionSummary = Field(description="订阅信息")
    push: PushSummary = Field(description="推送信息")
    upgrade_suggestions: List[UpgradeSuggestion] = Field(description="升级建议")


class FeatureComparison(BaseModel):
    """功能对比"""
    feature: str = Field(description="功能名称")
    type: str = Field(description="功能类型")
    free: str = Field(description="免费用户")
    basic: str = Field(description="基础会员")
    premium: str = Field(description="高级会员")


class UpgradePath(BaseModel):
    """升级路径"""
    from_level: str = Field(alias="from", description="起始等级")
    to_level: str = Field(alias="to", description="目标等级")
    benefits: List[str] = Field(description="升级权益")
    
    class Config:
        populate_by_name = True


class LevelBenefits(BaseModel):
    """等级权益信息"""
    level: str = Field(description="会员等级")
    level_name: str = Field(description="等级名称")
    subscription_limit: int = Field(description="订阅限制")
    daily_push_limit: int = Field(description="每日推送限制")
    features: List[str] = Field(description="功能列表")
    benefits: List[str] = Field(description="权益描述")
    feature_descriptions: Dict[str, str] = Field(description="功能详细描述")
    comparison: Dict[str, Any] = Field(description="等级对比信息")


class AllMembershipBenefits(BaseModel):
    """所有会员等级权益对比"""
    levels: Dict[str, LevelBenefits] = Field(description="各等级权益")
    comparison_table: List[FeatureComparison] = Field(description="对比表格")
    upgrade_paths: List[UpgradePath] = Field(description="升级路径")


class LimitCheckRequest(BaseModel):
    """限制检查请求"""
    raise_exception: bool = Field(default=False, description="是否在超限时抛出异常")


class BatchLimitCheckRequest(BaseModel):
    """批量限制检查请求"""
    user_ids: List[int] = Field(description="用户ID列表")
    check_subscription: bool = Field(default=True, description="是否检查订阅限制")
    check_push: bool = Field(default=True, description="是否检查推送限制")


class BatchLimitCheckResponse(BaseModel):
    """批量限制检查响应"""
    results: Dict[int, UserLimitsSummary] = Field(description="检查结果")
    summary: Dict[str, int] = Field(description="汇总统计")