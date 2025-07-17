"""
用户管理功能测试
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from app.services.user import user_service
from app.models.user import User, MembershipLevel
from app.core.exceptions import NotFoundException, BusinessException
from app.schemas.user import UserUpdate, MembershipUpgrade


class TestUserService:
    """用户服务测试"""
    
    @pytest.mark.asyncio
    async def test_get_user_profile_success(self):
        """测试成功获取用户档案"""
        mock_db = AsyncMock()
        
        # 创建测试用户
        test_user = User(
            id=1,
            openid="test_openid",
            nickname="测试用户",
            avatar_url="http://example.com/avatar.jpg",
            membership_level=MembershipLevel.BASIC,
            membership_expire_at=datetime.utcnow() + timedelta(days=30),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with patch.object(user_service, '_get_user_by_id', return_value=test_user):
            with patch.object(user_service, '_get_user_subscription_count', return_value=5):
                with patch.object(user_service, '_get_daily_push_count', return_value=3):
                    profile = await user_service.get_user_profile(1, mock_db)
                    
                    assert profile["id"] == 1
                    assert profile["openid"] == "test_openid"
                    assert profile["nickname"] == "测试用户"
                    assert profile["membership_level"] == "basic"
                    assert profile["subscription_count"] == 5
                    assert profile["daily_push_count"] == 3
                    assert profile["subscription_limit"] == 50
                    assert profile["daily_push_limit"] == 20
                    assert profile["can_subscribe"] is True
                    assert profile["can_receive_push"] is True
    
    @pytest.mark.asyncio
    async def test_get_user_profile_not_found(self):
        """测试获取不存在用户的档案"""
        mock_db = AsyncMock()
        
        with patch.object(user_service, '_get_user_by_id', return_value=None):
            with pytest.raises(NotFoundException):
                await user_service.get_user_profile(999, mock_db)
    
    @pytest.mark.asyncio
    async def test_update_user_profile_success(self):
        """测试成功更新用户档案"""
        mock_db = AsyncMock()
        
        test_user = User(
            id=1,
            openid="test_openid",
            nickname="旧昵称",
            avatar_url="http://example.com/old_avatar.jpg",
            membership_level=MembershipLevel.FREE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        update_data = {
            "nickname": "新昵称",
            "avatar_url": "http://example.com/new_avatar.jpg"
        }
        
        with patch.object(user_service, '_get_user_by_id', return_value=test_user):
            with patch.object(user_service, '_clear_user_cache'):
                with patch.object(user_service, 'get_user_profile') as mock_get_profile:
                    mock_get_profile.return_value = {
                        "id": 1,
                        "nickname": "新昵称",
                        "avatar_url": "http://example.com/new_avatar.jpg"
                    }
                    
                    result = await user_service.update_user_profile(1, update_data, mock_db)
                    
                    assert result["nickname"] == "新昵称"
                    assert result["avatar_url"] == "http://example.com/new_avatar.jpg"
                    mock_db.execute.assert_called_once()
                    mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_user_profile_no_valid_fields(self):
        """测试更新用户档案时没有有效字段"""
        mock_db = AsyncMock()
        
        test_user = User(
            id=1,
            openid="test_openid",
            membership_level=MembershipLevel.FREE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # 包含不允许更新的字段
        update_data = {
            "openid": "new_openid",  # 不允许更新
            "membership_level": "premium"  # 不允许更新
        }
        
        with patch.object(user_service, '_get_user_by_id', return_value=test_user):
            with patch.object(user_service, 'get_user_profile') as mock_get_profile:
                mock_get_profile.return_value = {"id": 1}
                
                result = await user_service.update_user_profile(1, update_data, mock_db)
                
                # 应该返回当前档案，不执行更新
                mock_db.execute.assert_not_called()
                mock_get_profile.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_membership_info_success(self):
        """测试成功获取会员信息"""
        mock_db = AsyncMock()
        
        test_user = User(
            id=1,
            openid="test_openid",
            membership_level=MembershipLevel.PREMIUM,
            membership_expire_at=datetime.utcnow() + timedelta(days=60),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with patch.object(user_service, '_get_user_by_id', return_value=test_user):
            membership_info = await user_service.get_membership_info(1, mock_db)
            
            assert membership_info["level"] == "premium"
            assert membership_info["is_active"] is True
            assert membership_info["subscription_limit"] == -1  # 无限制
            assert membership_info["daily_push_limit"] == -1  # 无限制
            assert "benefits" in membership_info
            assert len(membership_info["benefits"]) > 0
    
    @pytest.mark.asyncio
    async def test_upgrade_membership_success(self):
        """测试成功升级会员"""
        mock_db = AsyncMock()
        
        test_user = User(
            id=1,
            openid="test_openid",
            membership_level=MembershipLevel.FREE,
            membership_expire_at=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with patch.object(user_service, '_get_user_by_id', return_value=test_user):
            with patch.object(user_service, '_clear_user_cache'):
                with patch.object(user_service, 'get_membership_info') as mock_get_membership:
                    mock_get_membership.return_value = {
                        "level": "basic",
                        "is_active": True
                    }
                    
                    result = await user_service.upgrade_membership(
                        1, MembershipLevel.BASIC, 3, mock_db
                    )
                    
                    assert result["level"] == "basic"
                    assert result["is_active"] is True
                    mock_db.execute.assert_called_once()
                    mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_upgrade_membership_to_free_error(self):
        """测试升级到免费等级的错误"""
        mock_db = AsyncMock()
        
        test_user = User(
            id=1,
            openid="test_openid",
            membership_level=MembershipLevel.BASIC,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with patch.object(user_service, '_get_user_by_id', return_value=test_user):
            with pytest.raises(BusinessException):
                await user_service.upgrade_membership(
                    1, MembershipLevel.FREE, 1, mock_db
                )
    
    @pytest.mark.asyncio
    async def test_get_user_limits_success(self):
        """测试成功获取用户限制信息"""
        mock_db = AsyncMock()
        
        test_user = User(
            id=1,
            openid="test_openid",
            membership_level=MembershipLevel.BASIC,
            membership_expire_at=datetime.utcnow() + timedelta(days=30),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with patch.object(user_service, '_get_user_by_id', return_value=test_user):
            with patch.object(user_service, '_get_user_subscription_count', return_value=10):
                with patch.object(user_service, '_get_daily_push_count', return_value=5):
                    limits = await user_service.get_user_limits(1, mock_db)
                    
                    assert limits["subscription_limit"] == 50
                    assert limits["subscription_used"] == 10
                    assert limits["daily_push_limit"] == 20
                    assert limits["daily_push_used"] == 5
                    assert limits["can_subscribe"] is True
                    assert limits["can_receive_push"] is True
    
    @pytest.mark.asyncio
    async def test_get_user_limits_at_limit(self):
        """测试用户达到限制时的情况"""
        mock_db = AsyncMock()
        
        test_user = User(
            id=1,
            openid="test_openid",
            membership_level=MembershipLevel.FREE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with patch.object(user_service, '_get_user_by_id', return_value=test_user):
            with patch.object(user_service, '_get_user_subscription_count', return_value=10):  # 达到限制
                with patch.object(user_service, '_get_daily_push_count', return_value=5):  # 达到限制
                    limits = await user_service.get_user_limits(1, mock_db)
                    
                    assert limits["subscription_limit"] == 10
                    assert limits["subscription_used"] == 10
                    assert limits["daily_push_limit"] == 5
                    assert limits["daily_push_used"] == 5
                    assert limits["can_subscribe"] is False
                    assert limits["can_receive_push"] is False
    
    @pytest.mark.asyncio
    async def test_delete_user_success(self):
        """测试成功删除用户"""
        mock_db = AsyncMock()
        
        test_user = User(
            id=1,
            openid="test_openid",
            membership_level=MembershipLevel.FREE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Mock删除结果
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result
        
        with patch.object(user_service, '_get_user_by_id', return_value=test_user):
            with patch.object(user_service, '_clear_user_cache'):
                result = await user_service.delete_user(1, mock_db)
                
                assert result is True
                mock_db.execute.assert_called_once()
                mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_user_not_found(self):
        """测试删除不存在的用户"""
        mock_db = AsyncMock()
        
        with patch.object(user_service, '_get_user_by_id', return_value=None):
            with pytest.raises(NotFoundException):
                await user_service.delete_user(999, mock_db)
    
    def test_get_membership_benefits(self):
        """测试获取会员权益列表"""
        # 测试免费用户权益
        free_benefits = user_service._get_membership_benefits(MembershipLevel.FREE)
        assert len(free_benefits) > 0
        assert "订阅10个博主" in free_benefits
        
        # 测试基础会员权益
        basic_benefits = user_service._get_membership_benefits(MembershipLevel.BASIC)
        assert len(basic_benefits) > len(free_benefits)
        assert "订阅50个博主" in basic_benefits
        
        # 测试高级会员权益
        premium_benefits = user_service._get_membership_benefits(MembershipLevel.PREMIUM)
        assert len(premium_benefits) > len(basic_benefits)
        assert "无限订阅博主" in premium_benefits


class TestUserSchemas:
    """用户模式测试"""
    
    def test_user_update_schema(self):
        """测试用户更新模式"""
        # 测试有效数据
        update_data = UserUpdate(
            nickname="新昵称",
            avatar_url="http://example.com/avatar.jpg"
        )
        assert update_data.nickname == "新昵称"
        assert update_data.avatar_url == "http://example.com/avatar.jpg"
        
        # 测试空数据
        empty_update = UserUpdate()
        assert empty_update.nickname is None
        assert empty_update.avatar_url is None
    
    def test_membership_upgrade_schema(self):
        """测试会员升级模式"""
        # 测试有效数据
        upgrade_data = MembershipUpgrade(
            level=MembershipLevel.BASIC,
            duration_months=3
        )
        assert upgrade_data.level == MembershipLevel.BASIC
        assert upgrade_data.duration_months == 3
        
        # 测试无效月数
        with pytest.raises(ValueError):
            MembershipUpgrade(
                level=MembershipLevel.BASIC,
                duration_months=0  # 无效
            )
        
        with pytest.raises(ValueError):
            MembershipUpgrade(
                level=MembershipLevel.BASIC,
                duration_months=13  # 超出范围
            )
    
    def test_membership_upgrade_free_level_validation(self):
        """测试升级到免费等级的验证"""
        with pytest.raises(ValueError):
            MembershipUpgrade(
                level=MembershipLevel.FREE,  # 不能升级到免费等级
                duration_months=1
            )