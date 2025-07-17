"""
内容服务测试
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.content import content_service
from app.models.user import User, MembershipLevel
from app.models.account import Account, Platform
from app.models.article import Article
from app.models.subscription import Subscription
from app.schemas.article import ArticleWithAccount, ArticleDetail, ArticleStats
from app.schemas.common import PaginatedResponse
from app.core.exceptions import BusinessException


class TestContentService:
    """内容服务测试类"""
    
    @pytest.fixture
    async def sample_user(self, db_session: AsyncSession):
        """创建测试用户"""
        user = User(
            openid="test_openid_content",
            nickname="测试用户",
            avatar_url="https://example.com/avatar.jpg",
            membership_level=MembershipLevel.FREE
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user
    
    @pytest.fixture
    async def sample_accounts(self, db_session: AsyncSession):
        """创建测试账号"""
        accounts = []
        
        # 微博账号
        weibo_account = Account(
            name="测试微博博主",
            platform=Platform.WEIBO,
            account_id="weibo_123",
            avatar_url="https://example.com/weibo_avatar.jpg",
            description="测试微博账号",
            follower_count=10000
        )
        db_session.add(weibo_account)
        accounts.append(weibo_account)
        
        # 微信公众号
        wechat_account = Account(
            name="测试公众号",
            platform=Platform.WECHAT,
            account_id="wechat_123",
            avatar_url="https://example.com/wechat_avatar.jpg",
            description="测试微信公众号",
            follower_count=5000
        )
        db_session.add(wechat_account)
        accounts.append(wechat_account)
        
        await db_session.commit()
        for account in accounts:
            await db_session.refresh(account)
        
        return accounts
    
    @pytest.fixture
    async def sample_articles(self, db_session: AsyncSession, sample_accounts):
        """创建测试文章"""
        articles = []
        now = datetime.now()
        
        for i, account in enumerate(sample_accounts):
            for j in range(5):  # 每个账号创建5篇文章
                publish_time = now - timedelta(hours=i*5 + j)
                article = Article(
                    account_id=account.id,
                    title=f"测试文章 {account.name} - {j+1}",
                    url=f"https://example.com/article_{account.id}_{j+1}",
                    content=f"这是来自 {account.name} 的测试文章内容 {j+1}",
                    summary=f"文章摘要 {j+1}",
                    publish_time=publish_time,
                    publish_timestamp=int(publish_time.timestamp()),
                    images=[f"https://example.com/image_{j+1}.jpg"] if j % 2 == 0 else None,
                    details={"platform_specific": f"data_{j+1}"}
                )
                db_session.add(article)
                articles.append(article)
        
        await db_session.commit()
        for article in articles:
            await db_session.refresh(article)
        
        return articles
    
    @pytest.fixture
    async def sample_subscriptions(self, db_session: AsyncSession, sample_user, sample_accounts):
        """创建测试订阅关系"""
        subscriptions = []
        
        for account in sample_accounts:
            subscription = Subscription(
                user_id=sample_user.id,
                account_id=account.id
            )
            db_session.add(subscription)
            subscriptions.append(subscription)
        
        await db_session.commit()
        for subscription in subscriptions:
            await db_session.refresh(subscription)
        
        return subscriptions
    
    async def test_get_user_feed_success(
        self, 
        db_session: AsyncSession, 
        sample_user, 
        sample_accounts, 
        sample_articles, 
        sample_subscriptions
    ):
        """测试获取用户动态流成功"""
        result = await content_service.get_user_feed(
            db=db_session,
            user_id=sample_user.id,
            page=1,
            page_size=5
        )
        
        assert isinstance(result, PaginatedResponse)
        assert len(result.data) == 5
        assert result.total == 10  # 总共10篇文章
        assert result.page == 1
        assert result.page_size == 5
        assert result.total_pages == 2
        
        # 验证文章按时间倒序排列
        for i in range(len(result.data) - 1):
            assert result.data[i].publish_timestamp >= result.data[i+1].publish_timestamp
        
        # 验证文章包含账号信息
        first_article = result.data[0]
        assert isinstance(first_article, ArticleWithAccount)
        assert first_article.account_name is not None
        assert first_article.account_platform is not None
        assert first_article.platform_display_name is not None
    
    async def test_get_user_feed_no_subscriptions(self, db_session: AsyncSession, sample_user):
        """测试用户没有订阅时获取动态流"""
        result = await content_service.get_user_feed(
            db=db_session,
            user_id=sample_user.id,
            page=1,
            page_size=10
        )
        
        assert isinstance(result, PaginatedResponse)
        assert len(result.data) == 0
        assert result.total == 0
        assert result.total_pages == 0
    
    async def test_get_user_feed_pagination(
        self, 
        db_session: AsyncSession, 
        sample_user, 
        sample_accounts, 
        sample_articles, 
        sample_subscriptions
    ):
        """测试动态流分页"""
        # 第一页
        page1 = await content_service.get_user_feed(
            db=db_session,
            user_id=sample_user.id,
            page=1,
            page_size=3
        )
        
        assert len(page1.data) == 3
        assert page1.page == 1
        assert page1.total_pages == 4  # 10篇文章，每页3篇，共4页
        
        # 第二页
        page2 = await content_service.get_user_feed(
            db=db_session,
            user_id=sample_user.id,
            page=2,
            page_size=3
        )
        
        assert len(page2.data) == 3
        assert page2.page == 2
        
        # 验证不同页的文章不重复
        page1_ids = {article.id for article in page1.data}
        page2_ids = {article.id for article in page2.data}
        assert page1_ids.isdisjoint(page2_ids)
    
    async def test_get_article_detail_success(
        self, 
        db_session: AsyncSession, 
        sample_user, 
        sample_accounts, 
        sample_articles, 
        sample_subscriptions
    ):
        """测试获取文章详情成功"""
        article = sample_articles[0]
        
        result = await content_service.get_article_detail(
            db=db_session,
            article_id=article.id,
            user_id=sample_user.id
        )
        
        assert isinstance(result, ArticleDetail)
        assert result.id == article.id
        assert result.title == article.title
        assert result.account_name is not None
        assert result.account_platform is not None
        assert result.is_subscribed is True  # 用户已订阅该账号
        assert isinstance(result.related_articles, list)
    
    async def test_get_article_detail_not_found(self, db_session: AsyncSession, sample_user):
        """测试获取不存在的文章详情"""
        with pytest.raises(BusinessException) as exc_info:
            await content_service.get_article_detail(
                db=db_session,
                article_id=99999,
                user_id=sample_user.id
            )
        
        assert exc_info.value.message == "文章不存在"
        assert exc_info.value.status_code == 404
    
    async def test_get_article_detail_without_user(
        self, 
        db_session: AsyncSession, 
        sample_accounts, 
        sample_articles
    ):
        """测试未登录用户获取文章详情"""
        article = sample_articles[0]
        
        result = await content_service.get_article_detail(
            db=db_session,
            article_id=article.id,
            user_id=None
        )
        
        assert isinstance(result, ArticleDetail)
        assert result.id == article.id
        assert result.is_subscribed is False  # 未登录用户未订阅
    
    async def test_get_articles_by_account(
        self, 
        db_session: AsyncSession, 
        sample_accounts, 
        sample_articles
    ):
        """测试获取指定账号的文章列表"""
        account = sample_accounts[0]
        
        result = await content_service.get_articles_by_account(
            db=db_session,
            account_id=account.id,
            page=1,
            page_size=10
        )
        
        assert isinstance(result, PaginatedResponse)
        assert len(result.data) == 5  # 每个账号有5篇文章
        assert result.total == 5
        
        # 验证所有文章都属于指定账号
        for article in result.data:
            assert article.account_id == account.id
        
        # 验证按时间倒序排列
        for i in range(len(result.data) - 1):
            assert result.data[i].publish_timestamp >= result.data[i+1].publish_timestamp
    
    async def test_get_content_stats(
        self, 
        db_session: AsyncSession, 
        sample_user, 
        sample_accounts, 
        sample_articles, 
        sample_subscriptions
    ):
        """测试获取内容统计信息"""
        result = await content_service.get_content_stats(
            db=db_session,
            user_id=sample_user.id
        )
        
        assert isinstance(result, ArticleStats)
        assert result.total_articles == 10  # 总共10篇文章
        assert result.today_articles >= 0
        assert result.week_articles >= 0
        assert isinstance(result.platform_stats, dict)
        assert len(result.platform_stats) == 2  # 两个平台
        assert "weibo" in result.platform_stats
        assert "wechat" in result.platform_stats
    
    async def test_get_content_stats_no_subscriptions(self, db_session: AsyncSession, sample_user):
        """测试用户没有订阅时获取内容统计"""
        result = await content_service.get_content_stats(
            db=db_session,
            user_id=sample_user.id
        )
        
        assert isinstance(result, ArticleStats)
        assert result.total_articles == 0
        assert result.today_articles == 0
        assert result.week_articles == 0
        assert result.platform_stats == {}
    
    async def test_platform_display_name(self):
        """测试平台显示名称转换"""
        assert content_service._get_platform_display_name("wechat") == "微信公众号"
        assert content_service._get_platform_display_name("weibo") == "微博"
        assert content_service._get_platform_display_name("twitter") == "推特"
        assert content_service._get_platform_display_name("mock") == "测试平台"
        assert content_service._get_platform_display_name("unknown") == "unknown"
    
    async def test_refresh_user_feed_cache(self, sample_user):
        """测试刷新用户动态流缓存"""
        # 注意：这个测试可能需要Redis连接
        result = await content_service.refresh_user_feed_cache(sample_user.id)
        
        # 如果Redis不可用，应该返回False
        assert isinstance(result, bool)
    
    async def test_get_user_feed_with_images(
        self, 
        db_session: AsyncSession, 
        sample_user, 
        sample_accounts, 
        sample_articles, 
        sample_subscriptions
    ):
        """测试获取包含图片的动态流"""
        result = await content_service.get_user_feed(
            db=db_session,
            user_id=sample_user.id,
            page=1,
            page_size=10
        )
        
        # 验证图片相关字段
        articles_with_images = [article for article in result.data if article.has_images]
        assert len(articles_with_images) > 0
        
        for article in articles_with_images:
            assert article.image_count > 0
            assert article.thumbnail_url != ""
            assert isinstance(article.images, list)
            assert len(article.images) > 0
    
    async def test_related_articles(
        self, 
        db_session: AsyncSession, 
        sample_user, 
        sample_accounts, 
        sample_articles, 
        sample_subscriptions
    ):
        """测试相关文章功能"""
        article = sample_articles[0]
        
        result = await content_service.get_article_detail(
            db=db_session,
            article_id=article.id,
            user_id=sample_user.id
        )
        
        # 验证相关文章
        assert isinstance(result.related_articles, list)
        assert len(result.related_articles) <= 5  # 最多5篇相关文章
        
        # 验证相关文章都来自同一账号且不包含当前文章
        for related_article in result.related_articles:
            assert related_article.account_id == article.account_id
            assert related_article.id != article.id