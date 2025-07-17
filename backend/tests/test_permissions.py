"""
权限检查装饰器测试
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.user import User, MembershipLevel
from app.models.subscription import Subscription
from app.models.push_record import PushRecord, PushStatus
from app.models.account import Account, Platform
from app.core.permissions import (
    PermissionChecker,
    require_membership,
    require_subscription_permission,
    require_push_permission,
    require_feature,
    check_membership_dependency,
    check_subscription_dependency,
    check_push_dependency,
    check_feature_dependency
)
from app.core.exceptions import (
    AuthorizationException,
    SubscriptionLimitException,
    PushLimitException
)


class TestPermissionChecker:
    """权限检查器测试"""
    
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
    async def expired_user(self, db_session: AsyncSession):
        """创建过期会员用户"""
        expire_time = datetime.utcnow() - timedelta(days=1)
        user = User(
            openid="expired_user_123",
            nickname="过期用户",
            membership_level=MembershipLevel.BASIC,
            membership_expire_at=expire_time
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user
    
    async def test_check_membership_level_success(
        self, 
        basic_user: User, 
        premium_user: User,
        db_session: AsyncSession
    ):
        """测试会员等级检查成功"""
        # 基础会员可以访问免费功能
        result = await PermissionChecker.check_membership_level(
            basic_user, MembershipLevel.FREE, db_session
        )
        assert result is True
        
        # 基础会员可以访问基础功能
        result = await PermissionChecker.check_membership_level(
            basic_user, MembershipLevel.BASIC, db_session
        )
        assert result is True
        
        # 高级会员可以访问所有功能
        result = await PermissionChecker.check_membership_level(
            premium_user, MembershipLevel.PREMIUM, db_session
        )
        assert result is True
    
    async def test_check_membership_level_failure(
        self, 
        free_user: User, 
        basic_user: User,
        db_session: AsyncSession
    ):
        """测试会员等级检查失败"""
        # 免费用户不能访问基础功能
        result = await PermissionChecker.check_membership_level(
            free_user, MembershipLevel.BASIC, db_session
        )
        assert result is False
        
        # 基础会员不能访问高级功能
        result = await PermissionChecker.check_membership_level(
            basic_user, MembershipLevel.PREMIUM, db_session
        )
        assert result is False
    
    async def test_check_membership_level_expired(
        self, 
        expired_user: User,
        db_session: AsyncSession
    ):
        """测试过期会员等级检查"""
        # 过期会员应该被当作免费用户
        result = await PermissionChecker.check_membership_level(
            expired_user, MembershipLevel.BASIC, db_session
        )
        assert result is False
        
        # 过期会员可以访问免费功能
        result = await PermissionChecker.check_membership_level(
            expired_user, MembershipLevel.FREE, db_session
        )
        assert result is True
    
    async def test_check_subscription_permission(
        self, 
        free_user: User, 
        premium_user: User,
        db_session: AsyncSession
    ):
        """测试订阅权限检查"""
        # 免费用户初始状态可以订阅
        result = await PermissionChecker.check_subscription_permission(free_user, db_session)
        assert result is True
        
        # 高级会员总是可以订阅
        result = await PermissionChecker.check_subscription_permission(premium_user, db_session)
        assert result is True
        
        # 为免费用户创建10个订阅（达到限制）
        for i in range(10):
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
            
            subscription = Subscription(user_id=free_user.id, account_id=account.id)
            db_session.add(subscription)
        
        await db_session.commit()
        
        # 现在免费用户不能再订阅
        result = await PermissionChecker.check_subscription_permission(free_user, db_session)
        assert result is False
    
    async def test_check_push_permission(
        self, 
        free_user: User, 
        premium_user: User,
        db_session: AsyncSession
    ):
        """测试推送权限检查"""
        # 免费用户初始状态可以接收推送
        result = await PermissionChecker.check_push_permission(free_user, db_session)
        assert result is True
        
        # 高级会员总是可以接收推送
        result = await PermissionChecker.check_push_permission(premium_user, db_session)
        assert result is True
        
        # 为免费用户创建5条今日推送记录（达到限制）
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
        
        # 现在免费用户不能再接收推送
        result = await PermissionChecker.check_push_permission(free_user, db_session)
        assert result is False
    
    async def test_check_feature_permission(
        self, 
        free_user: User, 
        premium_user: User,
        db_session: AsyncSession
    ):
        """测试功能权限检查"""
        # 免费用户可以使用基础功能
        result = await PermissionChecker.check_feature_permission(
            free_user, "basic_aggregation", db_session
        )
        assert result is True
        
        # 免费用户不能使用高级功能
        result = await PermissionChecker.check_feature_permission(
            free_user, "exclusive_features", db_session
        )
        assert result is False
        
        # 高级会员可以使用所有功能
        result = await PermissionChecker.check_feature_permission(
            premium_user, "exclusive_features", db_session
        )
        assert result is True


class TestPermissionDecorators:
    """权限装饰器测试"""
    
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
    
    async def test_require_membership_decorator_success(
        self, 
        premium_user: User,
        db_session: AsyncSession
    ):
        """测试会员等级装饰器成功"""
        @require_membership(MembershipLevel.PREMIUM)
        async def premium_function(current_user, db):
            return "success"
        
        result = await premium_function(current_user=premium_user, db=db_session)
        assert result == "success"
    
    async def test_require_membership_decorator_failure(
        self, 
        free_user: User,
        db_session: AsyncSession
    ):
        """测试会员等级装饰器失败"""
        @require_membership(MembershipLevel.PREMIUM)
        async def premium_function(current_user, db):
            return "success"
        
        with pytest.raises(AuthorizationException) as exc_info:
            await premium_function(current_user=free_user, db=db_session)
        
        assert "需要premium等级会员权限" in str(exc_info.value)
    
    async def test_require_subscription_permission_decorator_success(
        self, 
        free_user: User,
        db_session: AsyncSession
    ):
        """测试订阅权限装饰器成功"""
        @require_subscription_permission()
        async def subscribe_function(current_user, db):
            return "success"
        
        result = await subscribe_function(current_user=free_user, db=db_session)
        assert result == "success"
    
    async def test_require_subscription_permission_decorator_failure(
        self, 
        free_user: User,
        db_session: AsyncSession
    ):
        """测试订阅权限装饰器失败"""
        # 为用户创建10个订阅（达到限制）
        for i in range(10):
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
            
            subscription = Subscription(user_id=free_user.id, account_id=account.id)
            db_session.add(subscription)
        
        await db_session.commit()
        
        @require_subscription_permission()
        async def subscribe_function(current_user, db):
            return "success"
        
        with pytest.raises(SubscriptionLimitException) as exc_info:
            await subscribe_function(current_user=free_user, db=db_session)
        
        assert "订阅数量已达上限" in str(exc_info.value)
    
    async def test_require_push_permission_decorator_success(
        self, 
        free_user: User,
        db_session: AsyncSession
    ):
        """测试推送权限装饰器成功"""
        @require_push_permission()
        async def push_function(current_user, db):
            return "success"
        
        result = await push_function(current_user=free_user, db=db_session)
        assert result == "success"
    
    async def test_require_push_permission_decorator_failure(
        self, 
        free_user: User,
        db_session: AsyncSession
    ):
        """测试推送权限装饰器失败"""
        # 为用户创建5条今日推送记录（达到限制）
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
        
        @require_push_permission()
        async def push_function(current_user, db):
            return "success"
        
        with pytest.raises(PushLimitException) as exc_info:
            await push_function(current_user=free_user, db=db_session)
        
        assert "推送次数已达上限" in str(exc_info.value)
    
    async def test_require_feature_decorator_success(
        self, 
        premium_user: User,
        db_session: AsyncSession
    ):
        """测试功能权限装饰器成功"""
        @require_feature("exclusive_features")
        async def exclusive_function(current_user, db):
            return "success"
        
        result = await exclusive_function(current_user=premium_user, db=db_session)
        assert result == "success"
    
    async def test_require_feature_decorator_failure(
        self, 
        free_user: User,
        db_session: AsyncSession
    ):
        """测试功能权限装饰器失败"""
        @require_feature("exclusive_features")
        async def exclusive_function(current_user, db):
            return "success"
        
        with pytest.raises(AuthorizationException) as exc_info:
            await exclusive_function(current_user=free_user, db=db_session)
        
        assert "需要exclusive_features功能权限" in str(exc_info.value)