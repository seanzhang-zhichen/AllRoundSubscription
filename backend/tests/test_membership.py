"""
会员等级管理服务测试
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, MembershipLevel
from app.models.subscription import Subscription
from app.models.push_record import PushRecord, PushStatus
from app.models.account import Account, Platform
from app.services.membership import membership_service, MembershipConfig
from app.core.exceptions import (
    NotFoundException, 
    BusinessException, 
    SubscriptionLimitException,
    PushLimitException
)


class TestMembershipConfig:
    """会员配置测试"""
    
    def test_get_subscription_limit(self):
        """测试获取订阅限制"""
        assert MembershipConfig.get_subscription_limit(MembershipLevel.FREE) == 10
        assert MembershipConfig.get_subscription_limit(MembershipLevel.BASIC) == 50
        assert MembershipConfig.get_subscription_limit(MembershipLevel.PREMIUM) == -1
    
    def test_get_daily_push_limit(self):
        """测试获取推送限制"""
        assert MembershipConfig.get_daily_push_limit(MembershipLevel.FREE) == 5
        assert MembershipConfig.get_daily_push_limit(MembershipLevel.BASIC) == 20
        assert MembershipConfig.get_daily_push_limit(MembershipLevel.PREMIUM) == -1
    
    def test_get_features(self):
        """测试获取功能列表"""
        free_features = MembershipConfig.get_features(MembershipLevel.FREE)
        assert "basic_aggregation" in free_features
        
        basic_features = MembershipConfig.get_features(MembershipLevel.BASIC)
        assert "basic_aggregation" in basic_features
        assert "advanced_search" in basic_features
        
        premium_features = MembershipConfig.get_features(MembershipLevel.PREMIUM)
        assert "exclusive_features" in premium_features
        assert "data_export" in premium_features
    
    def test_get_benefits(self):
        """测试获取权益描述"""
        free_benefits = MembershipConfig.get_benefits(MembershipLevel.FREE)
        assert len(free_benefits) > 0
        assert any("10个博主" in benefit for benefit in free_benefits)
        
        premium_benefits = MembershipConfig.get_benefits(MembershipLevel.PREMIUM)
        assert any("无限" in benefit for benefit in premium_benefits)


class TestMembershipService:
    """会员服务测试"""
    
    @pytest.fixture
    async def test_user(self, db_session: AsyncSession):
        """创建测试用户"""
        user = User(
            openid="test_openid_123",
            nickname="测试用户",
            membership_level=MembershipLevel.FREE
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
            openid="premium_openid_123",
            nickname="高级用户",
            membership_level=MembershipLevel.PREMIUM,
            membership_expire_at=expire_time
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user
    
    @pytest.fixture
    async def expired_user(self, db_session: AsyncSession):
        """创建过期会员用户"""
        expire_time = datetime.utcnow() - timedelta(days=1)
        user = User(
            openid="expired_openid_123",
            nickname="过期用户",
            membership_level=MembershipLevel.BASIC,
            membership_expire_at=expire_time
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user
    
    @pytest.fixture
    async def test_account(self, db_session: AsyncSession):
        """创建测试账号"""
        account = Account(
            name="测试博主",
            platform=Platform.WEIBO,
            account_id="test_account_123",
            avatar_url="http://example.com/avatar.jpg",
            description="测试博主描述",
            follower_count=1000
        )
        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(account)
        return account
    
    async def test_upgrade_membership_success(self, test_user: User, db_session: AsyncSession):
        """测试成功升级会员"""
        # 升级到基础会员
        result = await membership_service.upgrade_membership(
            test_user.id, MembershipLevel.BASIC, 3, db_session
        )
        
        assert result["level"] == MembershipLevel.BASIC.value
        assert result["is_active"] is True
        assert result["subscription_limit"] == 50
        assert result["daily_push_limit"] == 20
        
        # 验证数据库中的数据
        await db_session.refresh(test_user)
        assert test_user.membership_level == MembershipLevel.BASIC
        assert test_user.membership_expire_at is not None
    
    async def test_upgrade_membership_invalid_level(self, test_user: User, db_session: AsyncSession):
        """测试升级到无效等级"""
        with pytest.raises(BusinessException) as exc_info:
            await membership_service.upgrade_membership(
                test_user.id, MembershipLevel.FREE, 1, db_session
            )
        assert "不能升级到免费等级" in str(exc_info.value)
    
    async def test_upgrade_membership_invalid_duration(self, test_user: User, db_session: AsyncSession):
        """测试无效的购买时长"""
        with pytest.raises(BusinessException) as exc_info:
            await membership_service.upgrade_membership(
                test_user.id, MembershipLevel.BASIC, 15, db_session
            )
        assert "购买月数必须在1-12个月之间" in str(exc_info.value)
    
    async def test_upgrade_membership_user_not_found(self, db_session: AsyncSession):
        """测试用户不存在的情况"""
        with pytest.raises(NotFoundException):
            await membership_service.upgrade_membership(
                99999, MembershipLevel.BASIC, 1, db_session
            )
    
    async def test_get_membership_info(self, premium_user: User, db_session: AsyncSession):
        """测试获取会员信息"""
        result = await membership_service.get_membership_info(premium_user.id, db_session)
        
        assert result["level"] == MembershipLevel.PREMIUM.value
        assert result["effective_level"] == MembershipLevel.PREMIUM.value
        assert result["is_active"] is True
        assert result["subscription_limit"] == -1
        assert result["daily_push_limit"] == -1
        assert "exclusive_features" in result["features"]
    
    async def test_get_membership_info_expired(self, expired_user: User, db_session: AsyncSession):
        """测试获取过期会员信息"""
        result = await membership_service.get_membership_info(expired_user.id, db_session)
        
        assert result["level"] == MembershipLevel.BASIC.value
        assert result["effective_level"] == MembershipLevel.FREE.value
        assert result["is_active"] is False
        assert result["subscription_limit"] == 10  # 降级为免费用户限制
        assert result["daily_push_limit"] == 5
    
    async def test_check_subscription_limit_free_user(
        self, 
        test_user: User, 
        test_account: Account,
        db_session: AsyncSession
    ):
        """测试免费用户订阅限制检查"""
        # 创建9个订阅（免费用户限制10个）
        for i in range(9):
            account = Account(
                name=f"博主{i}",
                platform=Platform.WEIBO,
                account_id=f"account_{i}",
                avatar_url="http://example.com/avatar.jpg",
                description=f"博主{i}描述",
                follower_count=1000
            )
            db_session.add(account)
            await db_session.flush()
            
            subscription = Subscription(user_id=test_user.id, account_id=account.id)
            db_session.add(subscription)
        
        await db_session.commit()
        
        # 应该还可以订阅1个
        can_subscribe = await membership_service.check_subscription_limit(test_user.id, db_session)
        assert can_subscribe is True
        
        # 再添加1个订阅，达到限制
        subscription = Subscription(user_id=test_user.id, account_id=test_account.id)
        db_session.add(subscription)
        await db_session.commit()
        
        # 现在应该不能再订阅
        can_subscribe = await membership_service.check_subscription_limit(test_user.id, db_session)
        assert can_subscribe is False
    
    async def test_check_subscription_limit_premium_user(
        self, 
        premium_user: User, 
        test_account: Account,
        db_session: AsyncSession
    ):
        """测试高级会员订阅限制检查（无限制）"""
        # 创建大量订阅
        for i in range(100):
            account = Account(
                name=f"博主{i}",
                platform=Platform.WEIBO,
                account_id=f"account_{i}",
                avatar_url="http://example.com/avatar.jpg",
                description=f"博主{i}描述",
                follower_count=1000
            )
            db_session.add(account)
            await db_session.flush()
            
            subscription = Subscription(user_id=premium_user.id, account_id=account.id)
            db_session.add(subscription)
        
        await db_session.commit()
        
        # 高级会员应该仍然可以订阅
        can_subscribe = await membership_service.check_subscription_limit(premium_user.id, db_session)
        assert can_subscribe is True
    
    async def test_check_push_limit_free_user(self, test_user: User, db_session: AsyncSession):
        """测试免费用户推送限制检查"""
        # 创建4条今日推送记录（免费用户限制5次）
        today = datetime.utcnow()
        for i in range(4):
            push_record = PushRecord(
                user_id=test_user.id,
                article_id=i + 1,
                push_time=today,
                status=PushStatus.SUCCESS
            )
            db_session.add(push_record)
        
        await db_session.commit()
        
        # 应该还可以推送1次
        can_push = await membership_service.check_push_limit(test_user.id, db_session)
        assert can_push is True
        
        # 再添加1条推送记录，达到限制
        push_record = PushRecord(
            user_id=test_user.id,
            article_id=5,
            push_time=today,
            status=PushStatus.SUCCESS
        )
        db_session.add(push_record)
        await db_session.commit()
        
        # 现在应该不能再推送
        can_push = await membership_service.check_push_limit(test_user.id, db_session)
        assert can_push is False
    
    async def test_check_push_limit_premium_user(self, premium_user: User, db_session: AsyncSession):
        """测试高级会员推送限制检查（无限制）"""
        # 创建大量今日推送记录
        today = datetime.utcnow()
        for i in range(100):
            push_record = PushRecord(
                user_id=premium_user.id,
                article_id=i + 1,
                push_time=today,
                status=PushStatus.SUCCESS
            )
            db_session.add(push_record)
        
        await db_session.commit()
        
        # 高级会员应该仍然可以推送
        can_push = await membership_service.check_push_limit(premium_user.id, db_session)
        assert can_push is True
    
    async def test_get_user_limits(self, test_user: User, db_session: AsyncSession):
        """测试获取用户限制信息"""
        result = await membership_service.get_user_limits(test_user.id, db_session)
        
        assert result["membership_level"] == MembershipLevel.FREE.value
        assert result["effective_level"] == MembershipLevel.FREE.value
        assert result["is_membership_active"] is True
        assert result["subscription_limit"] == 10
        assert result["subscription_used"] == 0
        assert result["daily_push_limit"] == 5
        assert result["daily_push_used"] == 0
        assert result["can_subscribe"] is True
        assert result["can_receive_push"] is True
        assert "basic_aggregation" in result["features"]
    
    async def test_check_membership_expiry(self, expired_user: User, db_session: AsyncSession):
        """测试检查会员到期"""
        # 创建另一个未过期的用户
        future_expire = datetime.utcnow() + timedelta(days=30)
        active_user = User(
            openid="active_openid_123",
            nickname="活跃用户",
            membership_level=MembershipLevel.BASIC,
            membership_expire_at=future_expire
        )
        db_session.add(active_user)
        await db_session.commit()
        
        # 执行到期检查
        expired_user_ids = await membership_service.check_membership_expiry(db_session)
        
        # 应该只有过期用户被降级
        assert expired_user.id in expired_user_ids
        assert active_user.id not in expired_user_ids
        
        # 验证过期用户被降级为免费用户
        await db_session.refresh(expired_user)
        assert expired_user.membership_level == MembershipLevel.FREE
        assert expired_user.membership_expire_at is None
        
        # 验证活跃用户未受影响
        await db_session.refresh(active_user)
        assert active_user.membership_level == MembershipLevel.BASIC
        assert active_user.membership_expire_at == future_expire