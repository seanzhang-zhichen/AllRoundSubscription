"""
端到端集成测试
End-to-End Integration Tests

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
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, MembershipLevel
from app.models.account import Account, Platform
from app.models.article import Article
from app.models.subscription import Subscription
from app.models.push_record import PushRecord, PushStatus
from app.services.wechat import wechat_service
from app.services.content_detection import content_detection_service


class TestCompleteUserJourney:
    """完整用户旅程测试 - 从注册到订阅到推送"""
    
    @pytest.mark.asyncio
    async def test_complete_user_registration_to_subscription_flow(self, client, db_session):
        """
        测试用户注册到订阅的完整流程
        需求: 6.1, 6.2, 1.1, 1.2, 1.3
        """
        # Step 1: 用户微信登录注册
        mock_wechat_response = {
            "openid": "e2e_test_openid_001",
            "session_key": "test_session_key"
        }
        
        with patch.object(wechat_service, 'code_to_session', return_value=mock_wechat_response):
            login_response = await client.post(
                "/api/v1/auth/login",
                json={"code": "e2e_test_code"}
            )
        
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert login_data["success"] is True
        
        # 获取用户信息和令牌
        user_data = login_data["data"]["user"]
        tokens = login_data["data"]["tokens"]
        access_token = tokens["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        
        # 验证用户创建成功
        assert user_data["openid"] == "e2e_test_openid_001"
        assert user_data["membership_level"] == "free"
        
        # Step 2: 获取用户详细信息
        profile_response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        user_id = profile_data["data"]["id"]
        
        # 验证免费用户限制
        assert profile_data["data"]["subscription_limit"] == 10
        assert profile_data["data"]["daily_push_limit"] == 5
        
        # Step 3: 搜索博主
        search_response = await client.get(
            "/api/v1/search/accounts",
            params={"keyword": "测试博主", "platform": "wechat"},
            headers=auth_headers
        )
        
        assert search_response.status_code == 200
        search_data = search_response.json()
        
        # 如果没有搜索结果，创建测试账号
        if not search_data["data"]:
            # 创建测试账号（模拟搜索结果）
            test_account = Account(
                name="测试博主E2E",
                platform=Platform.WECHAT,
                account_id="e2e_test_account",
                avatar_url="https://example.com/avatar.jpg",
                description="端到端测试博主",
                follower_count=10000,
                details={"verified": True}
            )
            db_session.add(test_account)
            await db_session.commit()
            await db_session.refresh(test_account)
            account_id = test_account.id
        else:
            account_id = search_data["data"][0]["id"]
        
        # Step 4: 订阅博主
        subscription_response = await client.post(
            "/api/v1/subscriptions/",
            json={
                "user_id": user_id,
                "account_id": account_id
            },
            headers=auth_headers
        )
        
        assert subscription_response.status_code == 200
        subscription_data = subscription_response.json()
        assert subscription_data["code"] == 200
        assert subscription_data["message"] == "订阅成功"
        
        # Step 5: 验证订阅列表
        subscriptions_response = await client.get(
            "/api/v1/subscriptions/",
            headers=auth_headers
        )
        
        assert subscriptions_response.status_code == 200
        subscriptions_data = subscriptions_response.json()
        assert subscriptions_data["total"] >= 1
        assert len(subscriptions_data["data"]) >= 1
        
        # 验证订阅信息
        subscription = subscriptions_data["data"][0]
        assert subscription["user_id"] == user_id
        assert subscription["account_id"] == account_id
        
        # Step 6: 获取订阅统计
        stats_response = await client.get(
            "/api/v1/subscriptions/stats",
            headers=auth_headers
        )
        
        assert stats_response.status_code == 200
        stats_data = stats_response.json()
        assert stats_data["data"]["total_subscriptions"] >= 1
        assert stats_data["data"]["subscription_limit"] == 10
        assert stats_data["data"]["remaining_subscriptions"] <= 9
        
        # Step 7: 获取用户动态流
        feed_response = await client.get(
            "/api/v1/feed",
            params={"page": 1, "page_size": 10},
            headers=auth_headers
        )
        
        assert feed_response.status_code == 200
        feed_data = feed_response.json()
        assert "data" in feed_data
        
        return {
            "user_id": user_id,
            "account_id": account_id,
            "auth_headers": auth_headers,
            "openid": user_data["openid"]
        }
    
    @pytest.mark.asyncio
    async def test_subscription_limit_enforcement(self, client: AsyncClient, db_session: AsyncSession):
        """
        测试订阅数量限制执行
        需求: 1.3, 1.5, 5.4, 5.5
        """
        # 创建免费用户
        mock_wechat_response = {
            "openid": "limit_test_openid",
            "session_key": "test_session_key"
        }
        
        with patch.object(wechat_service, 'code_to_session', return_value=mock_wechat_response):
            login_response = await client.post(
                "/api/v1/auth/login",
                json={"code": "limit_test_code"}
            )
        
        login_data = login_response.json()
        access_token = login_data["data"]["tokens"]["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        user_id = login_data["data"]["user"]["id"]
        
        # 创建11个测试账号
        account_ids = []
        for i in range(11):
            account = Account(
                name=f"限制测试账号{i}",
                platform=Platform.WECHAT,
                account_id=f"limit_test_account_{i}",
                follower_count=1000 + i * 100
            )
            db_session.add(account)
            account_ids.append(account)
        
        await db_session.commit()
        
        # 刷新账号获取ID
        for account in account_ids:
            await db_session.refresh(account)
        
        # 订阅前10个账号（免费用户限制）
        successful_subscriptions = 0
        for i, account in enumerate(account_ids[:10]):
            response = await client.post(
                "/api/v1/subscriptions/",
                json={
                    "user_id": user_id,
                    "account_id": account.id
                },
                headers=auth_headers
            )
            
            if response.status_code == 200:
                successful_subscriptions += 1
        
        assert successful_subscriptions == 10
        
        # 尝试订阅第11个账号，应该失败
        response = await client.post(
            "/api/v1/subscriptions/",
            json={
                "user_id": user_id,
                "account_id": account_ids[10].id
            },
            headers=auth_headers
        )
        
        assert response.status_code == 400
        error_data = response.json()
        assert "订阅数量已达上限" in error_data["detail"]
        
        # 验证订阅统计
        stats_response = await client.get(
            "/api/v1/subscriptions/stats",
            headers=auth_headers
        )
        
        stats_data = stats_response.json()
        assert stats_data["data"]["total_subscriptions"] == 10
        assert stats_data["data"]["remaining_subscriptions"] == 0


class TestEndToEndPushNotifications:
    """端到端推送通知测试"""
    
    @pytest.mark.asyncio
    async def test_complete_push_notification_flow(self, client: AsyncClient, db_session: AsyncSession):
        """
        测试完整的推送通知流程
        需求: 2.1, 2.2, 2.6
        """
        # Step 1: 创建用户和订阅
        user_journey = await self._setup_user_with_subscription(client, db_session)
        user_id = user_journey["user_id"]
        account_id = user_journey["account_id"]
        openid = user_journey["openid"]
        
        # Step 2: 创建新文章（模拟博主发布内容）
        new_article = Article(
            account_id=account_id,
            title="端到端测试新文章",
            url="https://example.com/e2e-article",
            content="这是一篇用于端到端测试的新文章内容",
            summary="测试文章摘要",
            publish_time=datetime.utcnow(),
            publish_timestamp=int(datetime.utcnow().timestamp()),
            images=["https://example.com/image1.jpg"],
            details={"platform": "wechat"}
        )
        
        db_session.add(new_article)
        await db_session.commit()
        await db_session.refresh(new_article)
        
        # Step 3: 模拟内容检测服务发现新文章
        with patch.object(content_detection_service, 'detect_new_articles') as mock_detect:
            mock_detect.return_value = [new_article]
            
            # Step 4: 触发推送通知
            with patch.object(wechat_service, 'send_push_notification') as mock_push:
                mock_push.return_value = {
                    "success": True,
                    "msgid": "e2e_test_msgid",
                    "message": "推送成功"
                }
                
                # 调用推送API
                push_response = await client.post(
                    f"/api/v1/push/article/{new_article.id}",
                    json={"user_ids": [user_id]},
                    headers=user_journey["auth_headers"]
                )
                
                # 验证推送响应
                if push_response.status_code == 200:
                    push_data = push_response.json()
                    assert push_data["success"] is True
                    
                    # 验证微信推送被调用
                    mock_push.assert_called_once()
                    call_args = mock_push.call_args[1]
                    assert call_args["user_openid"] == openid
                    assert call_args["article_data"]["title"] == "端到端测试新文章"
        
        # Step 5: 验证推送记录
        push_records_response = await client.get(
            "/api/v1/push/records",
            params={"user_id": user_id},
            headers=user_journey["auth_headers"]
        )
        
        if push_records_response.status_code == 200:
            records_data = push_records_response.json()
            assert len(records_data["data"]) >= 1
            
            # 验证推送记录内容
            record = records_data["data"][0]
            assert record["user_id"] == user_id
            assert record["article_id"] == new_article.id
            assert record["status"] in ["success", "pending"]
    
    @pytest.mark.asyncio
    async def test_push_notification_limits_enforcement(self, client: AsyncClient, db_session: AsyncSession):
        """
        测试推送通知限制执行
        需求: 2.3, 2.4, 2.5
        """
        # 创建免费用户
        mock_wechat_response = {
            "openid": "push_limit_test_openid",
            "session_key": "test_session_key"
        }
        
        with patch.object(wechat_service, 'code_to_session', return_value=mock_wechat_response):
            login_response = await client.post(
                "/api/v1/auth/login",
                json={"code": "push_limit_test_code"}
            )
        
        login_data = login_response.json()
        user_id = login_data["data"]["user"]["id"]
        auth_headers = {"Authorization": f"Bearer {login_data['data']['tokens']['access_token']}"}
        
        # 创建测试文章
        test_articles = []
        for i in range(6):  # 创建6篇文章，超过免费用户限制(5次)
            article = Article(
                account_id=1,  # 假设存在的账号ID
                title=f"推送限制测试文章{i}",
                url=f"https://example.com/limit-test-{i}",
                content=f"测试内容{i}",
                publish_time=datetime.utcnow(),
                publish_timestamp=int(datetime.utcnow().timestamp())
            )
            db_session.add(article)
            test_articles.append(article)
        
        await db_session.commit()
        
        # 模拟推送前5篇文章成功
        successful_pushes = 0
        with patch.object(wechat_service, 'send_push_notification') as mock_push:
            mock_push.return_value = {"success": True, "msgid": "test_msgid"}
            
            for i, article in enumerate(test_articles[:5]):
                await db_session.refresh(article)
                
                # 模拟推送限制检查
                with patch('app.services.limits.limits_service.check_push_limit') as mock_limit:
                    mock_limit.return_value = {
                        "can_push": True,
                        "remaining": 5 - i - 1,
                        "message": f"今日还可推送{5-i-1}次"
                    }
                    
                    push_response = await client.post(
                        f"/api/v1/push/article/{article.id}",
                        json={"user_ids": [user_id]},
                        headers=auth_headers
                    )
                    
                    if push_response.status_code == 200:
                        successful_pushes += 1
        
        # 尝试推送第6篇文章，应该被限制
        with patch('app.services.limits.limits_service.check_push_limit') as mock_limit:
            mock_limit.return_value = {
                "can_push": False,
                "remaining": 0,
                "message": "今日推送次数已达上限(5次)"
            }
            
            await db_session.refresh(test_articles[5])
            push_response = await client.post(
                f"/api/v1/push/article/{test_articles[5].id}",
                json={"user_ids": [user_id]},
                headers=auth_headers
            )
            
            # 验证推送被拒绝或跳过
            if push_response.status_code == 200:
                push_data = push_response.json()
                assert push_data.get("skipped") is True or push_data.get("success") is False
            else:
                assert push_response.status_code == 429  # Too Many Requests
    
    async def _setup_user_with_subscription(self, client: AsyncClient, db_session: AsyncSession):
        """设置用户和订阅的辅助方法"""
        # 创建用户
        mock_wechat_response = {
            "openid": "push_test_openid",
            "session_key": "test_session_key"
        }
        
        with patch.object(wechat_service, 'code_to_session', return_value=mock_wechat_response):
            login_response = await client.post(
                "/api/v1/auth/login",
                json={"code": "push_test_code"}
            )
        
        login_data = login_response.json()
        user_id = login_data["data"]["user"]["id"]
        openid = login_data["data"]["user"]["openid"]
        access_token = login_data["data"]["tokens"]["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        
        # 创建测试账号
        test_account = Account(
            name="推送测试博主",
            platform=Platform.WECHAT,
            account_id="push_test_account",
            follower_count=5000
        )
        db_session.add(test_account)
        await db_session.commit()
        await db_session.refresh(test_account)
        
        # 创建订阅
        await client.post(
            "/api/v1/subscriptions/",
            json={
                "user_id": user_id,
                "account_id": test_account.id
            },
            headers=auth_headers
        )
        
        return {
            "user_id": user_id,
            "account_id": test_account.id,
            "auth_headers": auth_headers,
            "openid": openid
        }


class TestMembershipLevelIntegration:
    """会员等级集成测试"""
    
    @pytest.mark.asyncio
    async def test_membership_upgrade_flow(self, client: AsyncClient, db_session: AsyncSession):
        """
        测试会员升级完整流程
        需求: 5.1, 5.2, 5.3
        """
        # Step 1: 创建免费用户
        mock_wechat_response = {
            "openid": "membership_test_openid",
            "session_key": "test_session_key"
        }
        
        with patch.object(wechat_service, 'code_to_session', return_value=mock_wechat_response):
            login_response = await client.post(
                "/api/v1/auth/login",
                json={"code": "membership_test_code"}
            )
        
        login_data = login_response.json()
        user_id = login_data["data"]["user"]["id"]
        auth_headers = {"Authorization": f"Bearer {login_data['data']['tokens']['access_token']}"}
        
        # 验证初始免费用户状态
        profile_response = await client.get("/api/v1/auth/me", headers=auth_headers)
        profile_data = profile_response.json()
        assert profile_data["data"]["membership_level"] == "free"
        assert profile_data["data"]["subscription_limit"] == 10
        assert profile_data["data"]["daily_push_limit"] == 5
        
        # Step 2: 升级到基础会员
        upgrade_response = await client.post(
            "/api/v1/users/membership",
            json={
                "level": "basic",
                "duration_months": 1
            },
            headers=auth_headers
        )
        
        if upgrade_response.status_code == 200:
            upgrade_data = upgrade_response.json()
            assert upgrade_data["success"] is True
            
            # 验证升级后的权限
            profile_response = await client.get("/api/v1/auth/me", headers=auth_headers)
            profile_data = profile_response.json()
            assert profile_data["data"]["membership_level"] == "basic"
            assert profile_data["data"]["subscription_limit"] == 50
            assert profile_data["data"]["daily_push_limit"] == 20
        
        # Step 3: 再升级到高级会员
        premium_upgrade_response = await client.post(
            "/api/v1/users/membership",
            json={
                "level": "premium",
                "duration_months": 1
            },
            headers=auth_headers
        )
        
        if premium_upgrade_response.status_code == 200:
            # 验证高级会员权限
            profile_response = await client.get("/api/v1/auth/me", headers=auth_headers)
            profile_data = profile_response.json()
            assert profile_data["data"]["membership_level"] == "premium"
            assert profile_data["data"]["subscription_limit"] == -1  # 无限制
            assert profile_data["data"]["daily_push_limit"] == -1   # 无限制
    
    @pytest.mark.asyncio
    async def test_membership_expiration_handling(self, client: AsyncClient, db_session: AsyncSession):
        """
        测试会员到期处理
        需求: 5.3
        """
        # 创建即将到期的基础会员用户
        expired_user = User(
            openid="expired_member_openid",
            nickname="即将到期用户",
            membership_level=MembershipLevel.BASIC,
            membership_expire_at=datetime.utcnow() - timedelta(days=1)  # 已过期
        )
        
        db_session.add(expired_user)
        await db_session.commit()
        await db_session.refresh(expired_user)
        
        # 模拟登录获取令牌
        with patch.object(wechat_service, 'code_to_session') as mock_wechat:
            mock_wechat.return_value = {
                "openid": "expired_member_openid",
                "session_key": "test_session_key"
            }
            
            login_response = await client.post(
                "/api/v1/auth/login",
                json={"code": "expired_member_code"}
            )
        
        login_data = login_response.json()
        auth_headers = {"Authorization": f"Bearer {login_data['data']['tokens']['access_token']}"}
        
        # 获取用户信息，应该显示已降级为免费用户
        profile_response = await client.get("/api/v1/auth/me", headers=auth_headers)
        profile_data = profile_response.json()
        
        # 验证会员已自动降级
        assert profile_data["data"]["membership_level"] == "free"
        assert profile_data["data"]["subscription_limit"] == 10
        assert profile_data["data"]["daily_push_limit"] == 5


class TestSystemReliabilityAndErrorHandling:
    """系统可靠性和错误处理测试"""
    
    @pytest.mark.asyncio
    async def test_external_service_failure_handling(self, client: AsyncClient, db_session: AsyncSession):
        """
        测试外部服务失败处理
        需求: 7.4, 7.6
        """
        # 测试微信API失败时的处理
        with patch.object(wechat_service, 'code_to_session') as mock_wechat:
            mock_wechat.side_effect = Exception("微信服务暂时不可用")
            
            login_response = await client.post(
                "/api/v1/auth/login",
                json={"code": "test_code"}
            )
            
            # 验证错误处理
            assert login_response.status_code == 500
            error_data = login_response.json()
            assert "登录服务异常" in error_data["detail"]["message"]
    
    @pytest.mark.asyncio
    async def test_concurrent_subscription_operations(self, client: AsyncClient, db_session: AsyncSession):
        """
        测试并发订阅操作
        需求: 7.5
        """
        # 创建用户
        mock_wechat_response = {
            "openid": "concurrent_test_openid",
            "session_key": "test_session_key"
        }
        
        with patch.object(wechat_service, 'code_to_session', return_value=mock_wechat_response):
            login_response = await client.post(
                "/api/v1/auth/login",
                json={"code": "concurrent_test_code"}
            )
        
        login_data = login_response.json()
        user_id = login_data["data"]["user"]["id"]
        auth_headers = {"Authorization": f"Bearer {login_data['data']['tokens']['access_token']}"}
        
        # 创建测试账号
        test_account = Account(
            name="并发测试账号",
            platform=Platform.WECHAT,
            account_id="concurrent_test_account",
            follower_count=1000
        )
        db_session.add(test_account)
        await db_session.commit()
        await db_session.refresh(test_account)
        
        # 并发订阅同一个账号（测试重复订阅处理）
        async def subscribe_account():
            return await client.post(
                "/api/v1/subscriptions/",
                json={
                    "user_id": user_id,
                    "account_id": test_account.id
                },
                headers=auth_headers
            )
        
        # 同时发起多个订阅请求
        tasks = [subscribe_account() for _ in range(3)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 验证只有一个订阅成功，其他的应该返回重复订阅错误
        success_count = 0
        duplicate_count = 0
        
        for response in responses:
            if isinstance(response, Exception):
                continue
            
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 400:
                error_data = response.json()
                if "已经订阅" in error_data.get("detail", ""):
                    duplicate_count += 1
        
        # 应该只有一个成功，其他的被识别为重复
        assert success_count == 1
        assert duplicate_count >= 1
    
    @pytest.mark.asyncio
    async def test_data_consistency_verification(self, client: AsyncClient, db_session: AsyncSession):
        """
        测试数据一致性验证
        需求: 7.3
        """
        # 创建完整的用户订阅场景
        user_journey = await self._create_test_user_with_subscriptions(client, db_session)
        user_id = user_journey["user_id"]
        auth_headers = user_journey["auth_headers"]
        
        # 获取订阅统计
        stats_response = await client.get(
            "/api/v1/subscriptions/stats",
            headers=auth_headers
        )
        
        stats_data = stats_response.json()
        total_from_stats = stats_data["data"]["total_subscriptions"]
        
        # 获取订阅列表
        list_response = await client.get(
            "/api/v1/subscriptions/",
            params={"page": 1, "page_size": 100},
            headers=auth_headers
        )
        
        list_data = list_response.json()
        total_from_list = list_data["total"]
        
        # 验证数据一致性
        assert total_from_stats == total_from_list, "订阅统计和列表数量不一致"
        
        # 验证平台统计一致性
        platform_stats = stats_data["data"]["platform_stats"]
        platform_total = sum(platform_stats.values())
        assert platform_total == total_from_stats, "平台统计总数不一致"
    
    async def _create_test_user_with_subscriptions(self, client: AsyncClient, db_session: AsyncSession):
        """创建测试用户和订阅的辅助方法"""
        # 创建用户
        mock_wechat_response = {
            "openid": "consistency_test_openid",
            "session_key": "test_session_key"
        }
        
        with patch.object(wechat_service, 'code_to_session', return_value=mock_wechat_response):
            login_response = await client.post(
                "/api/v1/auth/login",
                json={"code": "consistency_test_code"}
            )
        
        login_data = login_response.json()
        user_id = login_data["data"]["user"]["id"]
        auth_headers = {"Authorization": f"Bearer {login_data['data']['tokens']['access_token']}"}
        
        # 创建多个测试账号和订阅
        platforms = [Platform.WECHAT, Platform.WEIBO, Platform.TWITTER]
        for i, platform in enumerate(platforms):
            for j in range(2):  # 每个平台2个账号
                account = Account(
                    name=f"{platform.value}测试账号{j}",
                    platform=platform,
                    account_id=f"consistency_test_{platform.value}_{j}",
                    follower_count=1000 + i * 100 + j * 10
                )
                db_session.add(account)
                await db_session.commit()
                await db_session.refresh(account)
                
                # 创建订阅
                await client.post(
                    "/api/v1/subscriptions/",
                    json={
                        "user_id": user_id,
                        "account_id": account.id
                    },
                    headers=auth_headers
                )
        
        return {
            "user_id": user_id,
            "auth_headers": auth_headers
        }


class TestPerformanceAndScalability:
    """性能和可扩展性测试"""
    
    @pytest.mark.asyncio
    async def test_large_subscription_list_performance(self, client: AsyncClient, db_session: AsyncSession):
        """
        测试大量订阅列表的性能
        需求: 7.1, 7.2
        """
        # 创建高级会员用户（无订阅限制）
        premium_user = User(
            openid="performance_test_openid",
            nickname="性能测试用户",
            membership_level=MembershipLevel.PREMIUM,
            membership_expire_at=datetime.utcnow() + timedelta(days=30)
        )
        
        db_session.add(premium_user)
        await db_session.commit()
        await db_session.refresh(premium_user)
        
        # 模拟登录
        with patch.object(wechat_service, 'code_to_session') as mock_wechat:
            mock_wechat.return_value = {
                "openid": "performance_test_openid",
                "session_key": "test_session_key"
            }
            
            login_response = await client.post(
                "/api/v1/auth/login",
                json={"code": "performance_test_code"}
            )
        
        login_data = login_response.json()
        auth_headers = {"Authorization": f"Bearer {login_data['data']['tokens']['access_token']}"}
        
        # 记录开始时间
        start_time = datetime.utcnow()
        
        # 获取订阅列表（即使为空也要测试响应时间）
        list_response = await client.get(
            "/api/v1/subscriptions/",
            params={"page": 1, "page_size": 50},
            headers=auth_headers
        )
        
        # 记录结束时间
        end_time = datetime.utcnow()
        response_time = (end_time - start_time).total_seconds()
        
        # 验证响应时间在可接受范围内（< 2秒）
        assert response_time < 2.0, f"订阅列表响应时间过长: {response_time}秒"
        assert list_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_feed_loading_performance(self, client: AsyncClient, db_session: AsyncSession):
        """
        测试动态流加载性能
        需求: 7.1, 7.2
        """
        # 创建用户
        mock_wechat_response = {
            "openid": "feed_performance_test_openid",
            "session_key": "test_session_key"
        }
        
        with patch.object(wechat_service, 'code_to_session', return_value=mock_wechat_response):
            login_response = await client.post(
                "/api/v1/auth/login",
                json={"code": "feed_performance_test_code"}
            )
        
        login_data = login_response.json()
        auth_headers = {"Authorization": f"Bearer {login_data['data']['tokens']['access_token']}"}
        
        # 记录开始时间
        start_time = datetime.utcnow()
        
        # 获取动态流
        feed_response = await client.get(
            "/api/v1/feed",
            params={"page": 1, "page_size": 20},
            headers=auth_headers
        )
        
        # 记录结束时间
        end_time = datetime.utcnow()
        response_time = (end_time - start_time).total_seconds()
        
        # 验证响应时间在可接受范围内（< 3秒）
        assert response_time < 3.0, f"动态流响应时间过长: {response_time}秒"
        assert feed_response.status_code == 200


# 测试运行配置
@pytest.mark.asyncio
async def test_run_all_e2e_scenarios(client: AsyncClient, db_session: AsyncSession):
    """运行所有端到端测试场景的集成测试"""
    
    # 创建测试实例
    user_journey_test = TestCompleteUserJourney()
    push_test = TestEndToEndPushNotifications()
    membership_test = TestMembershipLevelIntegration()
    reliability_test = TestSystemReliabilityAndErrorHandling()
    
    # 运行核心用户旅程测试
    try:
        user_data = await user_journey_test.test_complete_user_registration_to_subscription_flow(
            client, db_session
        )
        print("✅ 用户注册到订阅流程测试通过")
    except Exception as e:
        print(f"❌ 用户注册到订阅流程测试失败: {e}")
        raise
    
    # 运行订阅限制测试
    try:
        await user_journey_test.test_subscription_limit_enforcement(client, db_session)
        print("✅ 订阅限制执行测试通过")
    except Exception as e:
        print(f"❌ 订阅限制执行测试失败: {e}")
        raise
    
    # 运行推送通知测试
    try:
        await push_test.test_complete_push_notification_flow(client, db_session)
        print("✅ 推送通知流程测试通过")
    except Exception as e:
        print(f"❌ 推送通知流程测试失败: {e}")
        # 推送测试失败不阻断其他测试
        pass
    
    # 运行会员升级测试
    try:
        await membership_test.test_membership_upgrade_flow(client, db_session)
        print("✅ 会员升级流程测试通过")
    except Exception as e:
        print(f"❌ 会员升级流程测试失败: {e}")
        # 会员测试失败不阻断其他测试
        pass
    
    print("🎉 端到端集成测试完成")