"""
数据模型单元测试
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import User, Account, Article, Subscription, PushRecord
from app.models.user import MembershipLevel
from app.models.account import Platform
from app.models.push_record import PushStatus


class TestUserModel:
    """用户模型测试"""
    
    async def test_create_user(self, db_session):
        """测试创建用户"""
        user = User(
            openid="test_openid_123",
            nickname="测试用户",
            avatar_url="https://example.com/avatar.jpg",
            membership_level=MembershipLevel.FREE
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.id is not None
        assert user.openid == "test_openid_123"
        assert user.nickname == "测试用户"
        assert user.membership_level == MembershipLevel.FREE
        assert user.created_at is not None
        assert user.updated_at is not None
    
    async def test_user_unique_openid(self, db_session):
        """测试用户openid唯一性约束"""
        user1 = User(openid="duplicate_openid", nickname="用户1")
        user2 = User(openid="duplicate_openid", nickname="用户2")
        
        db_session.add(user1)
        await db_session.commit()
        
        db_session.add(user2)
        with pytest.raises(IntegrityError):
            await db_session.commit()
    
    async def test_user_membership_properties(self, db_session):
        """测试用户会员属性"""
        # 免费用户
        free_user = User(openid="free_user", membership_level=MembershipLevel.FREE)
        assert not free_user.is_premium
        assert free_user.is_membership_active
        assert free_user.get_subscription_limit() == 10
        assert free_user.get_daily_push_limit() == 5
        
        # 付费会员（有效期内）
        premium_user = User(
            openid="premium_user",
            membership_level=MembershipLevel.PREMIUM,
            membership_expire_at=datetime.now() + timedelta(days=30)
        )
        assert premium_user.is_premium
        assert premium_user.is_membership_active
        assert premium_user.get_subscription_limit() == -1  # 无限制
        assert premium_user.get_daily_push_limit() == -1  # 无限制
        
        # 付费会员（已过期）
        expired_user = User(
            openid="expired_user",
            membership_level=MembershipLevel.BASIC,
            membership_expire_at=datetime.now() - timedelta(days=1)
        )
        assert expired_user.is_premium
        assert not expired_user.is_membership_active
        assert expired_user.get_subscription_limit() == 10  # 降级到免费限制
        assert expired_user.get_daily_push_limit() == 5  # 降级到免费限制


class TestAccountModel:
    """账号模型测试"""
    
    async def test_create_account(self, db_session):
        """测试创建账号"""
        account = Account(
            name="测试博主",
            platform="weibo",
            account_id="weibo_123456",
            avatar_url="https://example.com/avatar.jpg",
            description="这是一个测试博主",
            follower_count=10000,
            details={"verified": True, "level": "VIP"}
        )
        
        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(account)
        
        assert account.id is not None
        assert account.name == "测试博主"
        assert account.platform == "weibo"
        assert account.account_id == "weibo_123456"
        assert account.follower_count == 10000
        assert account.details["verified"] is True
        assert account.platform_display_name == "微博"
    
    async def test_account_platform_display_name(self):
        """测试平台显示名称"""
        weibo_account = Account(name="微博账号", platform="weibo", account_id="123")
        assert weibo_account.platform_display_name == "微博"
        
        wechat_account = Account(name="微信账号", platform="wechat", account_id="456")
        assert wechat_account.platform_display_name == "微信公众号"
        
        twitter_account = Account(name="推特账号", platform="twitter", account_id="789")
        assert twitter_account.platform_display_name == "推特"
        
        unknown_account = Account(name="未知账号", platform="unknown", account_id="000")
        assert unknown_account.platform_display_name == "unknown"


class TestArticleModel:
    """文章模型测试"""
    
    async def test_create_article(self, db_session):
        """测试创建文章"""
        # 先创建账号
        account = Account(name="测试账号", platform="weibo", account_id="123")
        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(account)
        
        # 创建文章
        publish_time = datetime.now()
        article = Article(
            account_id=account.id,
            title="测试文章标题",
            url="https://example.com/article/123",
            content="这是文章内容",
            summary="文章摘要",
            publish_time=publish_time,
            publish_timestamp=int(publish_time.timestamp()),
            images=["https://example.com/img1.jpg", "https://example.com/img2.jpg"],
            details={"likes": 100, "comments": 50}
        )
        
        db_session.add(article)
        await db_session.commit()
        await db_session.refresh(article)
        
        assert article.id is not None
        assert article.account_id == account.id
        assert article.title == "测试文章标题"
        assert article.url == "https://example.com/article/123"
        assert article.image_count == 2
        assert article.has_images is True
        assert article.get_thumbnail_url() == "https://example.com/img1.jpg"
    
    async def test_article_unique_url(self, db_session):
        """测试文章URL唯一性约束"""
        account = Account(name="测试账号", platform="weibo", account_id="123")
        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(account)
        
        article1 = Article(
            account_id=account.id,
            title="文章1",
            url="https://example.com/duplicate",
            publish_time=datetime.now(),
            publish_timestamp=int(datetime.now().timestamp())
        )
        
        article2 = Article(
            account_id=account.id,
            title="文章2",
            url="https://example.com/duplicate",
            publish_time=datetime.now(),
            publish_timestamp=int(datetime.now().timestamp())
        )
        
        db_session.add(article1)
        await db_session.commit()
        
        db_session.add(article2)
        with pytest.raises(IntegrityError):
            await db_session.commit()
    
    async def test_article_image_properties(self):
        """测试文章图片属性"""
        # 无图片文章
        article_no_images = Article(
            account_id=1,
            title="无图文章",
            url="https://example.com/no-images",
            publish_time=datetime.now(),
            publish_timestamp=int(datetime.now().timestamp())
        )
        assert article_no_images.image_count == 0
        assert article_no_images.has_images is False
        assert article_no_images.get_thumbnail_url() == ""
        
        # 有图片文章
        article_with_images = Article(
            account_id=1,
            title="有图文章",
            url="https://example.com/with-images",
            publish_time=datetime.now(),
            publish_timestamp=int(datetime.now().timestamp()),
            images=["https://example.com/img1.jpg"]
        )
        assert article_with_images.image_count == 1
        assert article_with_images.has_images is True
        assert article_with_images.get_thumbnail_url() == "https://example.com/img1.jpg"


class TestSubscriptionModel:
    """订阅模型测试"""
    
    async def test_create_subscription(self, db_session):
        """测试创建订阅"""
        # 创建用户和账号
        user = User(openid="test_user", nickname="测试用户")
        account = Account(name="测试账号", platform="weibo", account_id="123")
        
        db_session.add(user)
        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(user)
        await db_session.refresh(account)
        
        # 创建订阅
        subscription = Subscription(user_id=user.id, account_id=account.id)
        db_session.add(subscription)
        await db_session.commit()
        await db_session.refresh(subscription)
        
        assert subscription.id is not None
        assert subscription.user_id == user.id
        assert subscription.account_id == account.id
        assert subscription.created_at is not None
    
    async def test_subscription_unique_constraint(self, db_session):
        """测试订阅唯一性约束"""
        user = User(openid="test_user", nickname="测试用户")
        account = Account(name="测试账号", platform="weibo", account_id="123")
        
        db_session.add(user)
        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(user)
        await db_session.refresh(account)
        
        # 创建第一个订阅
        subscription1 = Subscription(user_id=user.id, account_id=account.id)
        db_session.add(subscription1)
        await db_session.commit()
        
        # 尝试创建重复订阅
        subscription2 = Subscription(user_id=user.id, account_id=account.id)
        db_session.add(subscription2)
        with pytest.raises(IntegrityError):
            await db_session.commit()


class TestPushRecordModel:
    """推送记录模型测试"""
    
    async def test_create_push_record(self, db_session):
        """测试创建推送记录"""
        # 创建用户、账号和文章
        user = User(openid="test_user", nickname="测试用户")
        account = Account(name="测试账号", platform="weibo", account_id="123")
        db_session.add(user)
        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(user)
        await db_session.refresh(account)
        
        article = Article(
            account_id=account.id,
            title="测试文章",
            url="https://example.com/article",
            publish_time=datetime.now(),
            publish_timestamp=int(datetime.now().timestamp())
        )
        db_session.add(article)
        await db_session.commit()
        await db_session.refresh(article)
        
        # 创建推送记录
        push_time = datetime.now()
        push_record = PushRecord(
            user_id=user.id,
            article_id=article.id,
            push_time=push_time,
            status=PushStatus.SUCCESS.value
        )
        
        db_session.add(push_record)
        await db_session.commit()
        await db_session.refresh(push_record)
        
        assert push_record.id is not None
        assert push_record.user_id == user.id
        assert push_record.article_id == article.id
        assert push_record.status == PushStatus.SUCCESS.value
        assert push_record.is_success is True
        assert push_record.is_failed is False
    
    async def test_push_record_status_properties(self):
        """测试推送记录状态属性"""
        # 成功推送
        success_record = PushRecord(
            user_id=1,
            article_id=1,
            push_time=datetime.now(),
            status=PushStatus.SUCCESS.value
        )
        assert success_record.is_success is True
        assert success_record.is_failed is False
        
        # 失败推送
        failed_record = PushRecord(
            user_id=1,
            article_id=1,
            push_time=datetime.now(),
            status=PushStatus.FAILED.value,
            error_message="推送失败"
        )
        assert failed_record.is_success is False
        assert failed_record.is_failed is True
        
        # 待推送
        pending_record = PushRecord(
            user_id=1,
            article_id=1,
            push_time=datetime.now(),
            status=PushStatus.PENDING.value
        )
        assert pending_record.is_success is False
        assert pending_record.is_failed is False


class TestModelRelationships:
    """模型关系测试"""
    
    async def test_user_subscriptions_relationship(self, db_session):
        """测试用户-订阅关系"""
        user = User(openid="test_user", nickname="测试用户")
        account1 = Account(name="账号1", platform="weibo", account_id="123")
        account2 = Account(name="账号2", platform="wechat", account_id="456")
        
        db_session.add(user)
        db_session.add(account1)
        db_session.add(account2)
        await db_session.commit()
        await db_session.refresh(user)
        await db_session.refresh(account1)
        await db_session.refresh(account2)
        
        # 创建订阅
        subscription1 = Subscription(user_id=user.id, account_id=account1.id)
        subscription2 = Subscription(user_id=user.id, account_id=account2.id)
        db_session.add(subscription1)
        db_session.add(subscription2)
        await db_session.commit()
        
        # 查询订阅数量来验证关系
        result = await db_session.execute(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        subscriptions = result.scalars().all()
        
        # 验证关系
        assert len(subscriptions) == 2
    
    async def test_account_articles_relationship(self, db_session):
        """测试账号-文章关系"""
        account = Account(name="测试账号", platform="weibo", account_id="123")
        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(account)
        
        # 创建文章
        article1 = Article(
            account_id=account.id,
            title="文章1",
            url="https://example.com/article1",
            publish_time=datetime.now(),
            publish_timestamp=int(datetime.now().timestamp())
        )
        article2 = Article(
            account_id=account.id,
            title="文章2",
            url="https://example.com/article2",
            publish_time=datetime.now(),
            publish_timestamp=int(datetime.now().timestamp())
        )
        db_session.add(article1)
        db_session.add(article2)
        await db_session.commit()
        
        # 查询文章数量来验证关系
        result = await db_session.execute(
            select(Article).where(Article.account_id == account.id)
        )
        articles = result.scalars().all()
        
        # 验证关系
        assert len(articles) == 2