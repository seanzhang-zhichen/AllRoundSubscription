"""
Pydantic模型验证测试
"""
import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from app.schemas.user import UserCreate, UserUpdate, MembershipUpgrade, UserLimits
from app.schemas.account import AccountCreate, AccountUpdate, AccountSearch, PlatformInfo
from app.schemas.article import ArticleCreate, ArticleUpdate, ArticleList, ArticleFeed
from app.schemas.subscription import SubscriptionCreate, SubscriptionList, BatchSubscriptionCreate
from app.schemas.push_record import PushRecordCreate, PushRecordUpdate, PushRecordList
from app.schemas.common import PaginatedResponse, ErrorResponse
from app.models.user import MembershipLevel
from app.models.push_record import PushStatus


class TestUserSchemas:
    """用户模式验证测试"""
    
    def test_user_create_valid(self):
        """测试有效的用户创建数据"""
        user_data = {
            "openid": "test_openid_123",
            "nickname": "测试用户",
            "avatar_url": "https://example.com/avatar.jpg"
        }
        user = UserCreate(**user_data)
        assert user.openid == "test_openid_123"
        assert user.nickname == "测试用户"
        assert user.avatar_url == "https://example.com/avatar.jpg"
    
    def test_user_create_invalid_openid(self):
        """测试无效的openid"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(openid="", nickname="测试用户")
        
        errors = exc_info.value.errors()
        assert any("openid不能为空" in str(error) for error in errors)
    
    def test_user_create_openid_strip(self):
        """测试openid自动去除空格"""
        user = UserCreate(openid="  test_openid  ", nickname="测试用户")
        assert user.openid == "test_openid"
    
    def test_membership_upgrade_valid(self):
        """测试有效的会员升级数据"""
        upgrade_data = {
            "level": MembershipLevel.BASIC,
            "duration_months": 6
        }
        upgrade = MembershipUpgrade(**upgrade_data)
        assert upgrade.level == MembershipLevel.BASIC
        assert upgrade.duration_months == 6
    
    def test_membership_upgrade_invalid_level(self):
        """测试无效的会员等级"""
        with pytest.raises(ValidationError) as exc_info:
            MembershipUpgrade(level=MembershipLevel.FREE, duration_months=1)
        
        errors = exc_info.value.errors()
        assert any("不能升级到免费等级" in str(error) for error in errors)
    
    def test_membership_upgrade_invalid_duration(self):
        """测试无效的购买月数"""
        with pytest.raises(ValidationError):
            MembershipUpgrade(level=MembershipLevel.BASIC, duration_months=0)
        
        with pytest.raises(ValidationError):
            MembershipUpgrade(level=MembershipLevel.BASIC, duration_months=13)


class TestAccountSchemas:
    """账号模式验证测试"""
    
    def test_account_create_valid(self):
        """测试有效的账号创建数据"""
        account_data = {
            "name": "测试博主",
            "platform": "weibo",
            "account_id": "weibo_123456",
            "avatar_url": "https://example.com/avatar.jpg",
            "description": "这是一个测试博主",
            "follower_count": 10000,
            "details": {"verified": True}
        }
        account = AccountCreate(**account_data)
        assert account.name == "测试博主"
        assert account.platform == "weibo"
        assert account.account_id == "weibo_123456"
        assert account.follower_count == 10000
    
    def test_account_create_invalid_platform(self):
        """测试无效的平台类型"""
        with pytest.raises(ValidationError) as exc_info:
            AccountCreate(
                name="测试博主",
                platform="invalid_platform",
                account_id="123"
            )
        
        errors = exc_info.value.errors()
        assert any("不支持的平台类型" in str(error) for error in errors)
    
    def test_account_create_empty_name(self):
        """测试空的账号名称"""
        with pytest.raises(ValidationError) as exc_info:
            AccountCreate(
                name="",
                platform="weibo",
                account_id="123"
            )
        
        errors = exc_info.value.errors()
        assert any("账号名称不能为空" in str(error) for error in errors)
    
    def test_account_search_valid(self):
        """测试有效的账号搜索数据"""
        search_data = {
            "keyword": "测试关键词",
            "platforms": ["weibo", "wechat"],
            "page": 1,
            "page_size": 20
        }
        search = AccountSearch(**search_data)
        assert search.keyword == "测试关键词"
        assert search.platforms == ["weibo", "wechat"]
        assert search.page == 1
        assert search.page_size == 20
    
    def test_account_search_invalid_platforms(self):
        """测试无效的平台列表"""
        with pytest.raises(ValidationError) as exc_info:
            AccountSearch(
                keyword="测试",
                platforms=["invalid_platform"]
            )
        
        errors = exc_info.value.errors()
        assert any("不支持的平台类型" in str(error) for error in errors)


class TestArticleSchemas:
    """文章模式验证测试"""
    
    def test_article_create_valid(self):
        """测试有效的文章创建数据"""
        article_data = {
            "account_id": 1,
            "title": "测试文章标题",
            "url": "https://example.com/article/123",
            "content": "这是文章内容",
            "summary": "文章摘要",
            "publish_time": datetime.now(),
            "images": ["https://example.com/img1.jpg", "https://example.com/img2.jpg"],
            "details": {"likes": 100}
        }
        article = ArticleCreate(**article_data)
        assert article.title == "测试文章标题"
        assert article.url == "https://example.com/article/123"
        assert len(article.images) == 2
    
    def test_article_create_invalid_url(self):
        """测试无效的文章链接"""
        with pytest.raises(ValidationError) as exc_info:
            ArticleCreate(
                account_id=1,
                title="测试文章",
                url="invalid_url",
                publish_time=datetime.now()
            )
        
        errors = exc_info.value.errors()
        assert any("文章链接格式不正确" in str(error) for error in errors)
    
    def test_article_create_invalid_images(self):
        """测试无效的图片链接"""
        with pytest.raises(ValidationError) as exc_info:
            ArticleCreate(
                account_id=1,
                title="测试文章",
                url="https://example.com/article",
                publish_time=datetime.now(),
                images=["invalid_image_url"]
            )
        
        errors = exc_info.value.errors()
        assert any("图片链接格式不正确" in str(error) for error in errors)
    
    def test_article_list_valid(self):
        """测试有效的文章列表查询"""
        list_data = {
            "user_id": 1,
            "platform": "weibo",
            "page": 1,
            "page_size": 20,
            "order_by": "publish_time",
            "order_desc": True
        }
        article_list = ArticleList(**list_data)
        assert article_list.user_id == 1
        assert article_list.platform == "weibo"
        assert article_list.order_by == "publish_time"
    
    def test_article_list_invalid_order_by(self):
        """测试无效的排序字段"""
        with pytest.raises(ValidationError) as exc_info:
            ArticleList(order_by="invalid_field")
        
        errors = exc_info.value.errors()
        assert any("不支持的排序字段" in str(error) for error in errors)


class TestSubscriptionSchemas:
    """订阅模式验证测试"""
    
    def test_subscription_create_valid(self):
        """测试有效的订阅创建数据"""
        subscription_data = {
            "user_id": 1,
            "account_id": 2
        }
        subscription = SubscriptionCreate(**subscription_data)
        assert subscription.user_id == 1
        assert subscription.account_id == 2
    
    def test_batch_subscription_create_valid(self):
        """测试有效的批量订阅创建数据"""
        batch_data = {
            "user_id": 1,
            "account_ids": [1, 2, 3, 4, 5]
        }
        batch_subscription = BatchSubscriptionCreate(**batch_data)
        assert batch_subscription.user_id == 1
        assert len(batch_subscription.account_ids) == 5
    
    def test_batch_subscription_create_duplicate_ids(self):
        """测试重复的账号ID"""
        with pytest.raises(ValidationError) as exc_info:
            BatchSubscriptionCreate(
                user_id=1,
                account_ids=[1, 2, 2, 3]  # 重复的ID
            )
        
        errors = exc_info.value.errors()
        assert any("账号ID列表中存在重复项" in str(error) for error in errors)
    
    def test_batch_subscription_create_too_many_ids(self):
        """测试过多的账号ID"""
        with pytest.raises(ValidationError):
            BatchSubscriptionCreate(
                user_id=1,
                account_ids=list(range(1, 12))  # 11个ID，超过限制
            )


class TestPushRecordSchemas:
    """推送记录模式验证测试"""
    
    def test_push_record_create_valid(self):
        """测试有效的推送记录创建数据"""
        push_data = {
            "user_id": 1,
            "article_id": 2,
            "push_time": datetime.now(),
            "status": PushStatus.SUCCESS.value
        }
        push_record = PushRecordCreate(**push_data)
        assert push_record.user_id == 1
        assert push_record.article_id == 2
        assert push_record.status == PushStatus.SUCCESS.value
    
    def test_push_record_create_invalid_status(self):
        """测试无效的推送状态"""
        with pytest.raises(ValidationError) as exc_info:
            PushRecordCreate(
                user_id=1,
                article_id=2,
                push_time=datetime.now(),
                status="invalid_status"
            )
        
        errors = exc_info.value.errors()
        assert any("不支持的推送状态" in str(error) for error in errors)
    
    def test_push_record_list_valid(self):
        """测试有效的推送记录列表查询"""
        list_data = {
            "user_id": 1,
            "status": PushStatus.SUCCESS.value,
            "start_time": datetime.now() - timedelta(days=7),
            "end_time": datetime.now(),
            "page": 1,
            "page_size": 20
        }
        push_list = PushRecordList(**list_data)
        assert push_list.user_id == 1
        assert push_list.status == PushStatus.SUCCESS.value


class TestCommonSchemas:
    """通用模式验证测试"""
    
    def test_paginated_response_create(self):
        """测试分页响应创建"""
        data = [{"id": 1, "name": "item1"}, {"id": 2, "name": "item2"}]
        response = PaginatedResponse.create(
            data=data,
            total=100,
            page=1,
            page_size=20
        )
        
        assert len(response.data) == 2
        assert response.total == 100
        assert response.page == 1
        assert response.page_size == 20
        assert response.total_pages == 5  # 100 / 20 = 5
    
    def test_error_response(self):
        """测试错误响应"""
        error_response = ErrorResponse(
            code=400,
            message="参数错误",
            errors=["字段1错误", "字段2错误"]
        )
        
        assert error_response.code == 400
        assert error_response.message == "参数错误"
        assert len(error_response.errors) == 2


class TestSchemaValidationEdgeCases:
    """模式验证边界情况测试"""
    
    def test_string_length_limits(self):
        """测试字符串长度限制"""
        # 测试超长昵称
        with pytest.raises(ValidationError):
            UserCreate(openid="test", nickname="x" * 101)  # 超过100字符限制
        
        # 测试超长账号名称
        with pytest.raises(ValidationError):
            AccountCreate(
                name="x" * 201,  # 超过200字符限制
                platform="weibo",
                account_id="123"
            )
    
    def test_numeric_constraints(self):
        """测试数值约束"""
        # 测试负数粉丝数
        with pytest.raises(ValidationError):
            AccountCreate(
                name="测试账号",
                platform="weibo",
                account_id="123",
                follower_count=-1
            )
        
        # 测试页码边界
        with pytest.raises(ValidationError):
            ArticleList(page=0)  # 页码必须大于等于1
        
        with pytest.raises(ValidationError):
            ArticleList(page_size=0)  # 页面大小必须大于等于1
        
        with pytest.raises(ValidationError):
            ArticleList(page_size=101)  # 页面大小不能超过100
    
    def test_optional_fields(self):
        """测试可选字段"""
        # 最小化的用户创建数据
        user = UserCreate(openid="test_openid")
        assert user.openid == "test_openid"
        assert user.nickname is None
        assert user.avatar_url is None
        
        # 最小化的账号创建数据
        account = AccountCreate(
            name="测试账号",
            platform="weibo",
            account_id="123"
        )
        assert account.name == "测试账号"
        assert account.avatar_url is None
        assert account.description is None
        assert account.follower_count == 0  # 默认值