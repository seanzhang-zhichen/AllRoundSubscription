"""
搜索服务适配器注册器
"""
from app.services.search.service import search_service
from app.services.search.adapters.mock import MockPlatformAdapter
from app.services.search.adapters.wechat import WeChatAdapter
from app.services.search.adapters.weibo import WeiboAdapter
from app.services.search.adapters.twitter import TwitterAdapter
from app.models.account import Platform


def register_all_adapters():
    """注册所有平台适配器"""
    
    # 注册Mock适配器（用于测试和演示）
    mock_wechat = MockPlatformAdapter(Platform.WECHAT, enabled=True)
    mock_weibo = MockPlatformAdapter(Platform.WEIBO, enabled=True)
    mock_twitter = MockPlatformAdapter(Platform.TWITTER, enabled=True)
    
    search_service.register_adapter(mock_wechat)
    search_service.register_adapter(mock_weibo)
    search_service.register_adapter(mock_twitter)
    
    # 注册真实平台适配器
    wechat_adapter = WeChatAdapter()
    weibo_adapter = WeiboAdapter()
    twitter_adapter = TwitterAdapter()
    
    search_service.register_adapter(wechat_adapter)
    search_service.register_adapter(weibo_adapter)
    search_service.register_adapter(twitter_adapter)


def get_registered_platforms():
    """获取已注册的平台列表"""
    return search_service.get_supported_platforms()


def get_platform_adapter(platform: str):
    """获取指定平台的适配器"""
    return search_service.get_adapter(platform)


# 自动注册所有适配器
register_all_adapters()