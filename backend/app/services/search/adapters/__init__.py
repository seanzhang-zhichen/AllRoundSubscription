"""
平台适配器模块
"""
from app.services.search.adapters.mock import MockPlatformAdapter
from app.services.search.adapters.wechat import WeChatAdapter
from app.services.search.adapters.weibo import WeiboAdapter
from app.services.search.adapters.twitter import TwitterAdapter

__all__ = [
    "MockPlatformAdapter",
    "WeChatAdapter", 
    "WeiboAdapter",
    "TwitterAdapter"
]