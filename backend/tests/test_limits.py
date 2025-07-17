"""
用户权限限制检查服务测试
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, MembershipLevel
from app.models.subscription import Subscription
from app.models.push_record import PushRecord, PushStatus
from app.models.account import Account, Platform
from app.services.limits import limits_service
from app.core.exceptions import (
    NotFoundException, 
    BusinessException, 
    SubscriptionLimitException,
    PushLimitException
)


class TestLimitsService:
    """权限限制服务测试"""
    
    @pytest.fixture
    async def free_user(self, db_session: AsyncSession):
        """创建免费用户"""
        user = User(
            openid="free_user_123",
            nickname="免费用户",
            membership_level=MembershipLevel.FREE
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user
    
    @pytest.fixture
    async def basic_user(self, db_session: AsyncSession):
        """创建基础会员用户"""
        expire_time = datetime.utcnow() + timedelta(days=30)
        user = User(
            openid="basic_user_123",
            nickname="基础用户",
            membership_level=MembershipLevel.BASIC,
            membership_expire_at=expire_time
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user
    
    @pytest.fixture
    async def premium_user(self, db_session: AsyncSession):
        """创建高级会员用户"""
        expire_time = datetime.utcnow() + timedelta(days=30)
        user = User(
            openid="premium_user_123",
            nickname="高级用户",
            membership_level=MembershipLevel.PREMIUM,
            membership_expire_at=expire_time
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user
    
    @pytest.fixture
    async def test_accounts(self, db_session: AsyncSession):
        """创建测试账号"""
        accounts = []
        for i in range(15):  # 创建15个账号用于测试
            account = Account(
                name=f"测试博主{i}",
                platform=Platform.WEIBO,
                account_id=f"test_account_{i}",
                avatar_url="http://example.com/avatar.jpg",
                description=f"测试博主{i}描述",
                follower_count=1000
            )
            db_session.add(account)
            accounts.append(account)
        
        await db_session.commit()
        for account in accounts:
            await db_session.refresh(account)
        return accounts
    
    async def test_check_subscription_limit_free_user_within_limit(
        self, 
        free_user: User, 
        test_accounts: list,
        db_session: AsyncSession
    ):
        """测试免费用户在限制内的订阅检查"""
        # 创建5个订阅（免费用户限制10个）
        for i in range(5):
            subscription = Subscription(user_id=free_user.id, account_id=test_accounts[i].id)
            db_session.add(subscription)
        await db_session.commit()
        
        result = await limits_service.check_subscription_limit(free_user.id, db_session)
        
        assert result["user_id"] == free_user.id
        assert result["membership_level"] == MembershipLevel.FREE.value
        assert result["effective_level"] == MembershipLevel.FREE.value
        assert result["subscription_limit"] == 10
        assert result["subscription_used"] == 5
        assert result["subscription_remaining"] == 5
        assert result["can_subscribe"] is True
        assert result["limit_reached"] is False
        assert result["upgrade_required"] is False
    
    async def test_check_subscription_limit_free_user_at_limit(
        self, 
        free_user: User, 
        test_accounts: list,
        db_session: AsyncSession
    ):
        """测试免费用户达到订阅限制"""
        # 创建10个订阅（免费用户限制10个）
        for i in range(10):
            subscription = Subscription(user_id=free_user.id, account_id=test_accounts[i].id)
            db_session.add(subscription)
        await db_session.commit()
        
        result = await limits_service.check_subscription_limit(free_user.id, db_session)
        
        assert result["subscription_used"] == 10
        assert result["subscription_remaining"] == 0
        assert result["can_subscribe"] is False
        assert result["limit_reached"] is True
        assert result["upgrade_required"] is True
    
    async def test_check_subscription_limit_premium_user_unlimited(
        self, 
        premium_user: User, 
        test_accounts: list,
        db_session: AsyncSession
    ):
        """测试高级会员用户无限制订阅"""
        # 创建15个订阅（超过基础会员限制）
        for i in range(15):
            subscription = Subscription(user_id=premium_user.id, account_id=test_accounts[i].id)
            db_session.add(subscription)
        await db_session.commit()
        
        result = await limits_service.check_subscription_limit(premium_user.id, db_session)
        
        assert result["subscription_limit"] == -1
        assert result["subscription_used"] == 15
        assert result["subscription_remaining"] == -1
        assert result["can_subscribe"] is True
        assert result["limit_reached"] is False
        assert result["upgrade_required"] is False
    
    async def test_check_subscription_limit_with_exception(
        self, 
        free_user: User, 
        test_accounts: list,
        db_session: AsyncSession
    ):
        """测试订阅限制检查抛出异常"""
        # 创建10个订阅达到限制
        for i in range(10):
            subscription = Subscription(user_id=free_user.id, account_id=test_accounts[i].id)
            db_session.add(subscription)
        await db_session.commit()
        
        with pytest.raises(SubscriptionLimitException) as exc_info:
            await limits_service.check_subscription_limit(
                free_user.id, db_session, raise_exception=True
            )
        
        assert "免费用户订阅数量已达上限" in str(exc_info.value)
    
    async def test_check_push_limit_free_user_within_limit(
        self, 
        free_user: User,
        db_session: AsyncSession
    ):
        """测试免费用户在推送限制内"""
        # 创建3条今日推送记录（免费用户限制5次）
        today = datetime.utcnow()
        for i in range(3):
            push_record = PushRecord(
                user_id=free_user.id,
                article_id=i + 1,
                push_time=today,
                status=PushStatus.SUCCESS
            )
            db_session.add(push_record)
        await db_session.commit()
        
        result = await limits_service.check_push_limit(free_user.id, db_session)
        
        assert result["user_id"] == free_user.id
        assert result["daily_push_limit"] == 5
        assert result["daily_push_used"] == 3
        assert result["daily_push_remaining"] == 2
        assert result["can_receive_push"] is True
        assert result["limit_reached"] is False
        assert result["upgrade_required"] is False
        assert result["reset_time"] is not None
    
    async def test_check_push_limit_free_user_at_limit(
        self, 
        free_user: User,
        db_session: AsyncSession
    ):
        """测试免费用户达到推送限制"""
        # 创建5条今日推送记录（免费用户限制5次）
        today = datetime.utcnow()
        for i in range(5):
            push_record = PushRecord(
                user_id=free_user.id,
                article_id=i + 1,
                push_time=today,
                status=PushStatus.SUCCESS
            )
            db_session.add(push_record)
        await db_session.commit()
        
        result = await limits_service.check_push_limit(free_user.id, db_session)
        
        assert result["daily_push_used"] == 5
        assert result["daily_push_remaining"] == 0
        assert result["can_receive_push"] is False
        assert result["limit_reached"] is True
        assert result["upgrade_required"] is True
    
    async def test_check_push_limit_premium_user_unlimited(
        self, 
        premium_user: User,
        db_session: AsyncSession
    ):
        """测试高级会员用户无限制推送"""
        # 创建10条今日推送记录（超过基础会员限制）
        today = datetime.utcnow()
        for i in range(10):
            push_record = PushRecord(
                user_id=premium_user.id,
                article_id=i + 1,
                push_time=today,
                status=PushStatus.SUCCESS
            )
            db_session.add(push_record)
        await db_session.commit()
        
        result = await limits_service.check_push_limit(premium_user.id, db_session)
        
        assert result["daily_push_limit"] == -1
        assert result["daily_push_used"] == 10
        assert result["daily_push_remaining"] == -1
        assert result["can_receive_push"] is True
        assert result["limit_reached"] is False
        assert result["upgrade_required"] is False
    
    async def test_check_push_limit_with_exception(
        self, 
        free_user: User,
        db_session: AsyncSession
    ):
        """测试推送限制检查抛出异常"""
        # 创建5条推送记录达到限制
        today = datetime.utcnow()
        for i in range(5):
            push_record = PushRecord(
                user_id=free_user.id,
                article_id=i + 1,
                push_time=today,
                status=PushStatus.SUCCESS
            )
            db_session.add(push_record)
        await db_session.commit()
        
        with pytest.raises(PushLimitException) as exc_info:
            await limits_service.check_push_limit(
                free_user.id, db_session, raise_exception=True
            )
        
        assert "免费用户今日推送次数已达上限" in str(exc_info.value)
    
    async def test_get_user_limits_summary(
        self, 
        basic_user: User, 
        test_accounts: list,
        db_session: AsyncSession
    ):
        """测试获取用户限制汇总信息"""
        # 创建一些订阅和推送记录
        for i in range(3):
            subscription = Subscription(user_id=basic_user.id, account_id=test_accounts[i].id)
            db_session.add(subscription)
        
        today = datetime.utcnow()
        for i in range(2):
            push_record = PushRecord(
                user_id=basic_user.id,
                article_id=i + 1,
                push_time=today,
                status=PushStatus.SUCCESS
            )
            db_session.add(push_record)
        
        await db_session.commit()
        
        result = await limits_service.get_user_limits_summary(basic_user.id, db_session)
        
        assert result["user_id"] == basic_user.id
        assert "membership" in result
        assert "subscription" in result
        assert "push" in result
        assert "upgrade_suggestions" in result
        
        # 检查会员信息
        membership = result["membership"]
        assert membership["level"] == MembershipLevel.BASIC.value
        assert membership["effective_level"] == MembershipLevel.BASIC.value
        assert membership["is_active"] is True
        
        # 检查订阅信息
        subscription = result["subscription"]
        assert subscription["limit"] == 50
        assert subscription["used"] == 3
        assert subscription["remaining"] == 47
        assert subscription["can_subscribe"] is True
        
        # 检查推送信息
        push = result["push"]
        assert push["daily_limit"] == 20
        assert push["daily_used"] == 2
        assert push["daily_remaining"] == 18
        assert push["can_receive_push"] is True
    
    async def test_get_membership_benefits_display(self):
        """测试获取会员权益展示信息"""
        result = await limits_service.get_membership_benefits_display(MembershipLevel.BASIC)
        
        assert result["level"] == MembershipLevel.BASIC.value
        assert result["level_name"] == "基础会员"
        assert result["subscription_limit"] == 50
        assert result["daily_push_limit"] == 20
        assert "features" in result
        assert "benefits" in result
        assert "feature_descriptions" in result
        assert "comparison" in result
        
        # 检查功能描述
        features = result["features"]
        assert "basic_aggregation" in features
        assert "advanced_search" in features
        
        # 检查权益列表
        benefits = result["benefits"]
        assert len(benefits) > 0
        assert any("50个博主" in benefit for benefit in benefits)
    
    async def test_get_all_membership_benefits(self):
        """测试获取所有会员等级权益对比"""
        result = await limits_service.get_all_membership_benefits()
        
        assert "levels" in result
        assert "comparison_table" in result
        assert "upgrade_paths" in result
        
        # 检查所有等级都包含在内
        levels = result["levels"]
        assert MembershipLevel.FREE.value in levels
        assert MembershipLevel.BASIC.value in levels
        assert MembershipLevel.PREMIUM.value in levels
        
        # 检查对比表格
        comparison_table = result["comparison_table"]
        assert len(comparison_table) > 0
        
        # 检查升级路径
        upgrade_paths = result["upgrade_paths"]
        assert len(upgrade_paths) > 0
        
        # 验证升级路径包含从免费到基础的路径
        free_to_basic = next(
            (path for path in upgrade_paths 
             if path["from"] == MembershipLevel.FREE.value 
             and path["to"] == MembershipLevel.BASIC.value), 
            None
        )
        assert free_to_basic is not None
        assert len(free_to_basic["benefits"]) > 0
    
    async def test_user_not_found(self, db_session: AsyncSession):
        """测试用户不存在的情况"""
        with pytest.raises(NotFoundException):
            await limits_service.check_subscription_limit(99999, db_session)
        
        with pytest.raises(NotFoundException):
            await limits_service.check_push_limit(99999, db_session)