"""
搜索服务模块
"""
from app.services.search.base import SearchServiceBase, PlatformAdapter
from app.services.search.service import search_service
from app.services.search.cache import SearchCache

__all__ = [
    "SearchServiceBase",
    "PlatformAdapter", 
    "search_service",
    "SearchCache"
]