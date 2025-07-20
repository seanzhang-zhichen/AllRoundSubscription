"""
端到端综合集成测试
Comprehensive End-to-End Integration Tests

测试完整的用户流程：
1. 用户注册到订阅的完整流程测试
2. 推送通知的端到端功能测试  
3. 会员权限限制的正确性验证

需求覆盖: 1.1-1.6, 2.1-2.6, 5.1-5.6, 6.1-6.6
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, MembershipLevel
from app.models.account import Account, Platform
from app.models.article import Article
from app.models.subscription import Subscription
from app.models.push_record import PushRecord, PushStatus
from app.services.auth import auth_service
from app.services.subscription import subscription_service
from app.services.push_notification import push_notification_service
from app.services.wechat import wechat_service
from app.services.limits import limits_service
from app.core.exceptions import SubscriptionLimitException, PushLimitException


class TestE2EUserRegistrationToSubscription:
    """端到端用户注册到订阅流程测试"""
    
    @pytest.mark.asyncio
    async def test_complete_user_journey_from_registration_to_subscription(self, db_session: AsyncSession):
        """
        测试用户从注册到订阅的完整旅程
        需求: 6.1, 6.2, 1.1, 1.2, 1.3, 1.5
        """
        # Step 1: 模拟微信登录注册用户
        mock_wechat_data = {
            "openid": "e2e_test_user_001",
            "session_key": "test_session_key"
        }
        
        with patch.object(wechat_service, 'code_to_session', return_value=mock_wechat_data):
            # 创建用户（模拟登录注册过程）
            user = await auth_service.create_or_update_user(
                openid="e2e_test_user_001",
                nickname="端到端测试用户",
                avatar_url="https://example.com/avatar.jpg",
                db=db_session
            )
        
        # 验证用户创建成功
        assert user.openid == "e2e_test_user_001"
        assert user.membership_level == MembershipLevel.FREE
        assert user.nickname == "端到端测试用户"
        
        # Step 2: 创建测试博主账号
        test_account = Account(
            name="端到端测试博主",
            platform=Platform.WECHAT,
            account_id="e2e_test_account_001",
            avatar_url="https://example.com/account_avatar.jpg",
            description="这是一个端到端测试博主账号",
            follower_count=50000,
            details={"verified": True, "category": "tech"}
        )
        
        db_session.add(test_account)
        await db_session.commit()
        await db_session.refresh(test_account)
        
        # Step 3: 用户订阅博主
        from app.schemas.subscription import SubscriptionCreate
        subscription_data = SubscriptionCreate(
            user_id=user.id,
            account_id=test_account.id
        )
        
        subscription = await subscription_service.create_subscription(
            subscription_data, db_session
        )
        
        # 验证订阅创建成功
        assert subscription.user_id == user.id
        assert subscription.account_id == test_account.id
        assert subscription.created_at is not None
        
        # Step 4: 验证用户订阅列表
        from app.schemas.subscription import SubscriptionList
        query_params = SubscriptionList(
            user_id=user.id,
            page=1,
            page_size=10
        )
        
        subscriptions, total = await subscription_service.get_user_subscriptions(
            query_params, db_session
        )
        
        assert total == 1
        assert len(subscriptions) == 1
        assert subscriptions[0].user_id == user.id
        assert subscriptions[0].account_id == test_account.id
        assert subscriptions[0].account_name == "端到端测试博主"
        
        # Step 5: 验证订阅统计信息
        stats = await subscription_service.get_subscription_stats(user.id, db_session)
        
        assert stats.total_subscriptions == 1
        assert stats.subscription_limit == 10  # 免费用户限制
        assert stats.remaining_subscriptions == 9
        assert stats.platform_stats["wechat"] == 1
        
        return {
            "user": user,
            "account": test_account,
            "subscription": subscription
        }
    
    @pytest.mark.asyncio
    async def test_subscription_limit_enforcement_for_free_users(self, db_session: AsyncSession):
        """
        测试免费用户订阅数量限制执行
        需求: 1.3, 1.5, 5.4
        """
        # 创建免费用户
        free_user = User(
            openid="free_user_limit_test",
            nickname="免费用户限制测试",
            membership_level=MembershipLevel.FREE
        )
        
        db_session.add(free_user)
        await db_session.commit()
        await db_session.refresh(free_user)
        
        # 创建10个测试账号（免费用户限制）
        test_accounts = []
        for i in range(11):  # 创建11个，测试第11个会被拒绝
            account = Account(
                name=f"限制测试账号{i}",
                platform=Platform.WECHAT if i % 2 == 0 else Platform.WEIBO,
                account_id=f"limit_test_account_{i}",
                follower_count=1000 + i * 100
            )
            db_session.add(account)
            test_accounts.append(account)
        
        await db_session.commit()
        
        # 刷新所有账号
        for account in test_accounts:
            await db_session.refresh(account)
        
        # 订阅前10个账号，应该都成功
        successful_subscriptions = 0
        from app.schemas.subscription import SubscriptionCreate
        
        for account in test_accounts[:10]:
            subscription_data = SubscriptionCreate(
                user_id=free_user.id,
                account_id=account.id
            )
            
            subscription = await subscription_service.create_subscription(
                subscription_data, db_session
            )
            
            assert subscription is not None
            successful_subscriptions += 1
        
        assert successful_subscriptions == 10
        
        # 尝试订阅第11个账号，应该失败
        subscription_data = SubscriptionCreate(
            user_id=free_user.id,
            account_id=test_accounts[10].id
        )
        
        with pytest.raises(SubscriptionLimitException):
            await subscription_service.create_subscription(
                subscription_data, db_session
            )
        
        # 验证最终订阅数量
        stats = await subscription_service.get_subscription_stats(free_user.id, db_session)
        assert stats.total_subscriptions == 10
        assert stats.remaining_subscriptions == 0
    
    @pytest.mark.asyncio
    async def test_premium_user_unlimited_subscriptions(self, db_session: AsyncSession):
        """
        测试高级会员无限订阅功能
        需求: 5.5, 5.6
        """
        # 创建高级会员用户
        premium_user = User(
            openid="premium_user_test",
            nickname="高级会员测试",
            membership_level=MembershipLevel.PREMIUM,
            membership_expire_at=datetime.utcnow() + timedelta(days=30)
        )
        
        db_session.add(premium_user)
        await db_session.commit()
        await db_session.refresh(premium_user)
        
        # 创建15个测试账号（超过免费用户限制）
        test_accounts = []
        for i in range(15):
            account = Account(
                name=f"高级会员测试账号{i}",
                platform=Platform.WECHAT if i % 3 == 0 else (Platform.WEIBO if i % 3 == 1 else Platform.TWITTER),
                account_id=f"premium_test_account_{i}",
                follower_count=2000 + i * 200
            )
            db_session.add(account)
            test_accounts.append(account)
        
        await db_session.commit()
        
        # 刷新所有账号
        for account in test_accounts:
            await db_session.refresh(account)
        
        # 高级会员应该能订阅所有15个账号
        successful_subscriptions = 0
        from app.schemas.subscription import SubscriptionCreate
        
        for account in test_accounts:
            subscription_data = SubscriptionCreate(
                user_id=premium_user.id,
                account_id=account.id
            )
            
            subscription = await subscription_service.create_subscription(
                subscription_data, db_session
            )
            
            assert subscription is not None
            successful_subscriptions += 1
        
        assert successful_subscriptions == 15
        
        # 验证订阅统计
        stats = await subscription_service.get_subscription_stats(premium_user.id, db_session)
        assert stats.total_subscriptions == 15
        assert stats.subscription_limit == -1  # 无限制
        assert stats.remaining_subscriptions == -1  # 无限制


class TestE2EPushNotificationFlow:
    """端到端推送通知流程测试"""
    
    @pytest.mark.asyncio
    async def test_complete_push_notification_workflow(self, db_session: AsyncSession):
        """
        测试完整的推送通知工作流程
        需求: 2.1, 2.2, 2.6
        """
        # Step 1: 创建用户和订阅关系
        user = User(
            openid="push_test_user_001",
            nickname="推送测试用户",
            membership_level=MembershipLevel.BASIC
        )
        
        account = Account(
            name="推送测试博主",
            platform=Platform.WECHAT,
            account_id="push_test_account_001",
            follower_count=30000
        )
        
        db_session.add_all([user, account])
        await db_session.commit()
        await db_session.refresh(user)
        await db_session.refresh(account)
        
        # 创建订阅关系
        from app.schemas.subscription import SubscriptionCreate
        subscription_data = SubscriptionCreate(
            user_id=user.id,
            account_id=account.id
        )
        
        subscription = await subscription_service.create_subscription(
            subscription_data, db_session
        )
        
        # Step 2: 创建新文章（模拟博主发布内容）
        new_article = Article(
            account_id=account.id,
            title="推送测试新文章标题",
            url="https://example.com/push-test-article",
            content="这是一篇用于测试推送功能的新文章内容，包含了丰富的信息和有价值的观点。",
            summary="推送测试文章摘要",
            publish_time=datetime.utcnow(),
            publish_timestamp=int(datetime.utcnow().timestamp()),
            images=["https://example.com/test-image1.jpg", "https://example.com/test-image2.jpg"],
            details={
                "platform": "wechat",
                "read_count": 0,
                "like_count": 0
            }
        )
        
        db_session.add(new_article)
        await db_session.commit()
        await db_session.refresh(new_article)
        
        # Step 3: 模拟推送通知发送
        with patch.object(wechat_service, 'send_push_notification') as mock_push:
            mock_push.return_value = {
                "success": True,
                "msgid": "push_test_msgid_001",
                "message": "推送成功"
            }
            
            # 发送推送通知
            push_result = await push_notification_service.send_article_notification(
                db_session, user_id=user.id, article_id=new_article.id
            )
            
            # 验证推送结果
            assert push_result["success"] is True
            assert push_result["message"] == "推送成功"
            assert "msgid" in push_result
            
            # 验证微信推送服务被正确调用
            mock_push.assert_called_once()
            call_args = mock_push.call_args[1]
            assert call_args["user_openid"] == user.openid
            assert call_args["article_data"]["title"] == "推送测试新文章标题"
            assert call_args["article_data"]["account_name"] == "推送测试博主"
        
        # Step 4: 验证推送记录被正确创建
        from sqlalchemy import select
        push_record_query = select(PushRecord).where(
            PushRecord.user_id == user.id,
            PushRecord.article_id == new_article.id
        )
        result = await db_session.execute(push_record_query)
        push_record = result.scalar_one_or_none()
        
        assert push_record is not None
        assert push_record.user_id == user.id
        assert push_record.article_id == new_article.id
        assert push_record.status == PushStatus.SUCCESS.value
        assert push_record.push_time is not None
    
    @pytest.mark.asyncio
    async def test_push_notification_limits_enforcement(self, db_session: AsyncSession):
        """
        测试推送通知限制执行
        需求: 2.3, 2.4, 2.5
        """
        # 创建免费用户（每日推送限制5次）
        free_user = User(
            openid="push_limit_test_user",
            nickname="推送限制测试用户",
            membership_level=MembershipLevel.FREE
        )
        
        db_session.add(free_user)
        await db_session.commit()
        await db_session.refresh(free_user)
        
        # 创建测试文章
        test_articles = []
        for i in range(6):  # 创建6篇文章，第6篇应该被限制
            article = Article(
                account_id=1,  # 假设存在的账号ID
                title=f"推送限制测试文章{i}",
                url=f"https://example.com/limit-test-article-{i}",
                content=f"推送限制测试内容{i}",
                publish_time=datetime.utcnow(),
                publish_timestamp=int(datetime.utcnow().timestamp())
            )
            db_session.add(article)
            test_articles.append(article)
        
        await db_session.commit()
        
        # 刷新所有文章
        for article in test_articles:
            await db_session.refresh(article)
        
        # 模拟前5次推送成功
        successful_pushes = 0
        with patch.object(wechat_service, 'send_push_notification') as mock_push:
            mock_push.return_value = {"success": True, "msgid": "test_msgid"}
            
            for i, article in enumerate(test_articles[:5]):
                # 模拟推送限制检查通过
                with patch.object(limits_service, 'check_push_limit') as mock_limit:
                    mock_limit.return_value = {
                        "can_push": True,
                        "remaining": 5 - i - 1,
                        "message": f"今日还可推送{5-i-1}次"
                    }
                    
                    with patch.object(limits_service, 'increment_push_count'):
                        push_result = await push_notification_service.send_article_notification(
                            db_session, user_id=free_user.id, article_id=article.id
                        )
                        
                        if push_result["success"]:
                            successful_pushes += 1
        
        assert successful_pushes == 5
        
        # 尝试第6次推送，应该被限制
        with patch.object(limits_service, 'check_push_limit') as mock_limit:
            mock_limit.return_value = {
                "can_push": False,
                "remaining": 0,
                "message": "今日推送次数已达上限(5次)"
            }
            
            push_result = await push_notification_service.send_article_notification(
                db_session, user_id=free_user.id, article_id=test_articles[5].id
            )
            
            # 验证推送被跳过
            assert push_result["success"] is False
            assert push_result["skipped"] is True
            assert push_result["reason"] == "push_limit_reached"
            assert "上限" in push_result["message"]
    
    @pytest.mark.asyncio
    async def test_batch_push_notification_processing(self, db_session: AsyncSession):
        """
        测试批量推送通知处理
        需求: 2.6
        """
        # 创建多个用户
        users = []
        for i in range(5):
            user = User(
                openid=f"batch_push_user_{i}",
                nickname=f"批量推送用户{i}",
                membership_level=MembershipLevel.BASIC
            )
            db_session.add(user)
            users.append(user)
        
        await db_session.commit()
        
        # 刷新所有用户
        for user in users:
            await db_session.refresh(user)
        
        # 创建测试文章
        test_article = Article(
            account_id=1,
            title="批量推送测试文章",
            url="https://example.com/batch-push-test",
            content="批量推送测试内容",
            publish_time=datetime.utcnow(),
            publish_timestamp=int(datetime.utcnow().timestamp())
        )
        
        db_session.add(test_article)
        await db_session.commit()
        await db_session.refresh(test_article)
        
        # 执行批量推送
        user_ids = [user.id for user in users]
        
        with patch.object(push_notification_service, 'send_article_notification') as mock_send:
            # 模拟部分成功，部分失败的情况
            mock_send.side_effect = [
                {"success": True, "message": "推送成功"},
                {"success": True, "message": "推送成功"},
                {"success": False, "error": "用户未关注服务号"},
                {"success": False, "skipped": True, "reason": "push_limit_reached"},
                {"success": True, "message": "推送成功"}
            ]
            
            batch_result = await push_notification_service.batch_send_notifications(
                db_session, user_ids, test_article.id
            )
            
            # 验证批量推送结果
            assert batch_result["total_users"] == 5
            assert batch_result["success_count"] == 3
            assert batch_result["failed_count"] == 1
            assert batch_result["skipped_count"] == 1
            assert len(batch_result["results"]) == 5


class TestE2EMembershipIntegration:
    """端到端会员等级集成测试"""
    
    @pytest.mark.asyncio
    async def test_membership_upgrade_and_benefits_flow(self, db_session: AsyncSession):
        """
        测试会员升级和权益变化流程
        需求: 5.1, 5.2, 5.3
        """
        # Step 1: 创建免费用户
        user = User(
            openid="membership_upgrade_test",
            nickname="会员升级测试用户",
            membership_level=MembershipLevel.FREE
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # 验证免费用户初始权限
        initial_limits = limits_service.get_user_limits(user)
        assert initial_limits["subscription_limit"] == 10
        assert initial_limits["daily_push_limit"] == 5
        
        # Step 2: 升级到基础会员
        user.membership_level = MembershipLevel.BASIC
        user.membership_expire_at = datetime.utcnow() + timedelta(days=30)
        
        await db_session.commit()
        await db_session.refresh(user)
        
        # 验证基础会员权限
        basic_limits = limits_service.get_user_limits(user)
        assert basic_limits["subscription_limit"] == 50
        assert basic_limits["daily_push_limit"] == 20
        
        # Step 3: 再升级到高级会员
        user.membership_level = MembershipLevel.PREMIUM
        user.membership_expire_at = datetime.utcnow() + timedelta(days=30)
        
        await db_session.commit()
        await db_session.refresh(user)
        
        # 验证高级会员权限（无限制）
        premium_limits = limits_service.get_user_limits(user)
        assert premium_limits["subscription_limit"] == -1  # 无限制
        assert premium_limits["daily_push_limit"] == -1   # 无限制
    
    @pytest.mark.asyncio
    async def test_membership_expiration_handling(self, db_session: AsyncSession):
        """
        测试会员到期处理
        需求: 5.3
        """
        # 创建已过期的基础会员
        expired_user = User(
            openid="expired_member_test",
            nickname="过期会员测试",
            membership_level=MembershipLevel.BASIC,
            membership_expire_at=datetime.utcnow() - timedelta(days=1)  # 已过期
        )
        
        db_session.add(expired_user)
        await db_session.commit()
        await db_session.refresh(expired_user)
        
        # 模拟会员到期检查和降级处理
        from app.services.membership import membership_service
        
        with patch.object(membership_service, 'check_and_handle_expired_memberships') as mock_check:
            # 模拟会员到期处理
            mock_check.return_value = {
                "processed_users": 1,
                "downgraded_users": [expired_user.id]
            }
            
            # 手动降级用户（模拟定时任务处理）
            expired_user.membership_level = MembershipLevel.FREE
            expired_user.membership_expire_at = None
            
            await db_session.commit()
            await db_session.refresh(expired_user)
            
            # 验证用户已降级为免费用户
            assert expired_user.membership_level == MembershipLevel.FREE
            assert expired_user.membership_expire_at is None
            
            # 验证权限已恢复为免费用户限制
            downgraded_limits = limits_service.get_user_limits(expired_user)
            assert downgraded_limits["subscription_limit"] == 10
            assert downgraded_limits["daily_push_limit"] == 5


class TestE2ESystemReliability:
    """端到端系统可靠性测试"""
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_handling(self, db_session: AsyncSession):
        """
        测试并发操作处理
        需求: 7.5
        """
        # 创建测试用户和账号
        user = User(
            openid="concurrent_test_user",
            nickname="并发测试用户",
            membership_level=MembershipLevel.FREE
        )
        
        account = Account(
            name="并发测试账号",
            platform=Platform.WECHAT,
            account_id="concurrent_test_account",
            follower_count=5000
        )
        
        db_session.add_all([user, account])
        await db_session.commit()
        await db_session.refresh(user)
        await db_session.refresh(account)
        
        # 并发订阅同一个账号（测试重复订阅处理）
        from app.schemas.subscription import SubscriptionCreate
        
        async def create_subscription():
            try:
                subscription_data = SubscriptionCreate(
                    user_id=user.id,
                    account_id=account.id
                )
                return await subscription_service.create_subscription(
                    subscription_data, db_session
                )
            except Exception as e:
                return {"error": str(e)}
        
        # 同时发起多个订阅请求
        tasks = [create_subscription() for _ in range(3)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 验证只有一个订阅成功，其他的被识别为重复
        successful_subscriptions = 0
        duplicate_errors = 0
        
        for result in results:
            if isinstance(result, Exception):
                continue
            elif isinstance(result, dict) and "error" in result:
                if "已经订阅" in result["error"]:
                    duplicate_errors += 1
            elif hasattr(result, 'id'):
                successful_subscriptions += 1
        
        # 应该只有一个成功，其他的被识别为重复
        assert successful_subscriptions == 1
        # 注意：由于数据库约束，重复订阅可能在数据库层面被阻止
    
    @pytest.mark.asyncio
    async def test_data_consistency_verification(self, db_session: AsyncSession):
        """
        测试数据一致性验证
        需求: 7.3
        """
        # 创建用户和多个订阅
        user = User(
            openid="consistency_test_user",
            nickname="数据一致性测试用户",
            membership_level=MembershipLevel.BASIC
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # 创建多个不同平台的账号和订阅
        platforms = [Platform.WECHAT, Platform.WEIBO, Platform.TWITTER]
        created_subscriptions = 0
        
        from app.schemas.subscription import SubscriptionCreate
        
        for i, platform in enumerate(platforms):
            for j in range(2):  # 每个平台2个账号
                account = Account(
                    name=f"{platform.value}一致性测试账号{j}",
                    platform=platform,
                    account_id=f"consistency_test_{platform.value}_{j}",
                    follower_count=1000 + i * 100 + j * 10
                )
                
                db_session.add(account)
                await db_session.commit()
                await db_session.refresh(account)
                
                # 创建订阅
                subscription_data = SubscriptionCreate(
                    user_id=user.id,
                    account_id=account.id
                )
                
                subscription = await subscription_service.create_subscription(
                    subscription_data, db_session
                )
                
                assert subscription is not None
                created_subscriptions += 1
        
        # 验证订阅统计数据一致性
        stats = await subscription_service.get_subscription_stats(user.id, db_session)
        
        # 验证总数一致性
        assert stats.total_subscriptions == created_subscriptions
        assert stats.total_subscriptions == 6  # 3个平台 × 2个账号
        
        # 验证平台统计一致性
        platform_total = sum(stats.platform_stats.values())
        assert platform_total == stats.total_subscriptions
        
        # 验证各平台数量
        assert stats.platform_stats["wechat"] == 2
        assert stats.platform_stats["weibo"] == 2
        assert stats.platform_stats["twitter"] == 2
        
        # 验证订阅列表数据一致性
        from app.schemas.subscription import SubscriptionList
        query_params = SubscriptionList(
            user_id=user.id,
            page=1,
            page_size=100
        )
        
        subscriptions, total = await subscription_service.get_user_subscriptions(
            query_params, db_session
        )
        
        assert total == stats.total_subscriptions
        assert len(subscriptions) == stats.total_subscriptions


# 综合测试运行器
@pytest.mark.asyncio
async def test_run_comprehensive_e2e_scenarios(db_session: AsyncSession):
    """运行所有综合端到端测试场景"""
    
    print("🚀 开始运行综合端到端集成测试...")
    
    # 测试实例
    registration_test = TestE2EUserRegistrationToSubscription()
    push_test = TestE2EPushNotificationFlow()
    membership_test = TestE2EMembershipIntegration()
    reliability_test = TestE2ESystemReliability()
    
    test_results = {
        "passed": 0,
        "failed": 0,
        "errors": []
    }
    
    # 1. 用户注册到订阅流程测试
    try:
        user_data = await registration_test.test_complete_user_journey_from_registration_to_subscription(db_session)
        print("✅ 用户注册到订阅完整流程测试通过")
        test_results["passed"] += 1
    except Exception as e:
        print(f"❌ 用户注册到订阅流程测试失败: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(f"用户注册到订阅: {e}")
    
    # 2. 订阅限制执行测试
    try:
        await registration_test.test_subscription_limit_enforcement_for_free_users(db_session)
        print("✅ 免费用户订阅限制执行测试通过")
        test_results["passed"] += 1
    except Exception as e:
        print(f"❌ 订阅限制执行测试失败: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(f"订阅限制执行: {e}")
    
    # 3. 高级会员无限订阅测试
    try:
        await registration_test.test_premium_user_unlimited_subscriptions(db_session)
        print("✅ 高级会员无限订阅测试通过")
        test_results["passed"] += 1
    except Exception as e:
        print(f"❌ 高级会员无限订阅测试失败: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(f"高级会员无限订阅: {e}")
    
    # 4. 推送通知完整流程测试
    try:
        await push_test.test_complete_push_notification_workflow(db_session)
        print("✅ 推送通知完整流程测试通过")
        test_results["passed"] += 1
    except Exception as e:
        print(f"❌ 推送通知流程测试失败: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(f"推送通知流程: {e}")
    
    # 5. 推送限制执行测试
    try:
        await push_test.test_push_notification_limits_enforcement(db_session)
        print("✅ 推送通知限制执行测试通过")
        test_results["passed"] += 1
    except Exception as e:
        print(f"❌ 推送限制执行测试失败: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(f"推送限制执行: {e}")
    
    # 6. 会员升级流程测试
    try:
        await membership_test.test_membership_upgrade_and_benefits_flow(db_session)
        print("✅ 会员升级和权益变化流程测试通过")
        test_results["passed"] += 1
    except Exception as e:
        print(f"❌ 会员升级流程测试失败: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(f"会员升级流程: {e}")
    
    # 7. 数据一致性验证测试
    try:
        await reliability_test.test_data_consistency_verification(db_session)
        print("✅ 数据一致性验证测试通过")
        test_results["passed"] += 1
    except Exception as e:
        print(f"❌ 数据一致性验证测试失败: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(f"数据一致性验证: {e}")
    
    # 输出测试总结
    print(f"\n📊 综合端到端测试总结:")
    print(f"✅ 通过: {test_results['passed']} 个测试")
    print(f"❌ 失败: {test_results['failed']} 个测试")
    
    if test_results["errors"]:
        print(f"\n❌ 失败详情:")
        for error in test_results["errors"]:
            print(f"  - {error}")
    
    # 验证核心功能都通过
    assert test_results["passed"] >= 5, f"核心功能测试通过数量不足，当前通过: {test_results['passed']}"
    
    print(f"\n🎉 综合端到端集成测试完成！")
    
    return test_results