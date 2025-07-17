"""
订阅管理功能简单测试
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, MembershipLevel
from app.models.account import Account, Platform
from app.services.subscription import subscription_service
from app.schemas.subscription import SubscriptionCreate
from app.core.exceptions import NotFoundException, SubscriptionLimitException, DuplicateException


class TestSubscriptionServiceSimple:
    """订阅服务简单测试类"""
    
    @pytest.mark.asyncio
    async def test_create_subscription_success(self, db_session: AsyncSession):
        """测试成功创建订阅"""
        # 创建测试用户
        user = User(
            openid="test_user_openid",
            nickname="测试用户",
            membership_level=MembershipLevel.BASIC,
            membership_expire_at=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # 创建测试账号
        account = Account(
            name="测试公众号",
            platform=Platform.WECHAT,
            account_id="test_wechat_account",
            follower_count=10000
        )
        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(account)
        
        # 创建订阅
        subscription_data = SubscriptionCreate(
            user_id=user.id,
            account_id=account.id
        )
        
        result = await subscription_service.create_subscription(subscription_data, db_session)
        
        assert result.user_id == user.id
        assert result.account_id == account.id
        assert result.id is not None
        assert result.created_at is not None
    
    @pytest.mark.asyncio
    async def test_create_subscription_user_not_found(self, db_session: AsyncSession):
        """测试用户不存在时创建订阅"""
        # 创建测试账号
        account = Account(
            name="测试公众号",
            platform=Platform.WECHAT,
            account_id="test_wechat_account",
            follower_count=10000
        )
        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(account)
        
        subscription_data = SubscriptionCreate(
            user_id=99999,  # 不存在的用户ID
            account_id=account.id
        )
        
        with pytest.raises(NotFoundException, match="用户不存在"):
            await subscription_service.create_subscription(subscription_data, db_session)
    
    @pytest.mark.asyncio
    async def test_create_subscription_account_not_found(self, db_session: AsyncSession):
        """测试账号不存在时创建订阅"""
        # 创建测试用户
        user = User(
            openid="test_user_openid",
            nickname="测试用户",
            membership_level=MembershipLevel.BASIC,
            membership_expire_at=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        subscription_data = SubscriptionCreate(
            user_id=user.id,
            account_id=99999  # 不存在的账号ID
        )
        
        with pytest.raises(NotFoundException, match="账号不存在"):
            await subscription_service.create_subscription(subscription_data, db_session)
    
    @pytest.mark.asyncio
    async def test_delete_subscription_success(self, db_session: AsyncSession):
        """测试成功删除订阅"""
        # 创建测试用户
        user = User(
            openid="test_user_openid",
            nickname="测试用户",
            membership_level=MembershipLevel.BASIC,
            membership_expire_at=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # 创建测试账号
        account = Account(
            name="测试公众号",
            platform=Platform.WECHAT,
            account_id="test_wechat_account",
            follower_count=10000
        )
        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(account)
        
        # 先创建订阅
        subscription_data = SubscriptionCreate(
            user_id=user.id,
            account_id=account.id
        )
        await subscription_service.create_subscription(subscription_data, db_session)
        
        # 删除订阅
        result = await subscription_service.delete_subscription(
            user.id, account.id, db_session
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_subscription_not_found(self, db_session: AsyncSession):
        """测试删除不存在的订阅"""
        # 创建测试用户
        user = User(
            openid="test_user_openid",
            nickname="测试用户",
            membership_level=MembershipLevel.BASIC,
            membership_expire_at=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # 创建测试账号
        account = Account(
            name="测试公众号",
            platform=Platform.WECHAT,
            account_id="test_wechat_account",
            follower_count=10000
        )
        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(account)
        
        with pytest.raises(NotFoundException, match="订阅关系不存在"):
            await subscription_service.delete_subscription(
                user.id, account.id, db_session
            )
    
    @pytest.mark.asyncio
    async def test_check_subscription_status(self, db_session: AsyncSession):
        """测试检查订阅状态"""
        # 创建测试用户
        user = User(
            openid="test_user_openid",
            nickname="测试用户",
            membership_level=MembershipLevel.BASIC,
            membership_expire_at=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # 创建测试账号
        account = Account(
            name="测试公众号",
            platform=Platform.WECHAT,
            account_id="test_wechat_account",
            follower_count=10000
        )
        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(account)
        
        # 检查未订阅状态
        status = await subscription_service.check_subscription_status(
            user.id, account.id, db_session
        )
        
        assert status["is_subscribed"] is False
        assert status["subscription_id"] is None
        assert status["can_subscribe"] is True
        
        # 创建订阅
        subscription_data = SubscriptionCreate(
            user_id=user.id,
            account_id=account.id
        )
        subscription = await subscription_service.create_subscription(subscription_data, db_session)
        
        # 检查已订阅状态
        status = await subscription_service.check_subscription_status(
            user.id, account.id, db_session
        )
        
        assert status["is_subscribed"] is True
        assert status["subscription_id"] == subscription.id
        assert status["subscription_time"] is not None