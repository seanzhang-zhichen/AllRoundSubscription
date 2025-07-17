"""
Pydantic数据验证模型
"""
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserProfile, MembershipInfo
from app.schemas.account import AccountCreate, AccountUpdate, AccountResponse, AccountSearch
from app.schemas.article import ArticleCreate, ArticleUpdate, ArticleResponse, ArticleList
from app.schemas.subscription import SubscriptionCreate, SubscriptionResponse
from app.schemas.push_record import PushRecordCreate, PushRecordResponse
from app.schemas.limits import (
    SubscriptionLimitInfo, PushLimitInfo, UserLimitsSummary, 
    LevelBenefits, AllMembershipBenefits
)
from app.schemas.search import (
    SearchRequest, PlatformSearchRequest, SearchResponse,
    PlatformStatusResponse, SearchStatisticsResponse, SupportedPlatformsResponse,
    SearchSuggestionRequest, SearchSuggestion, SearchSuggestionResponse,
    SearchHistoryItem, SearchHistoryResponse, CacheStatsResponse
)
from app.schemas.common import BaseResponse, PaginatedResponse

__all__ = [
    # User schemas
    "UserCreate", "UserUpdate", "UserResponse", "UserProfile", "MembershipInfo",
    # Account schemas  
    "AccountCreate", "AccountUpdate", "AccountResponse", "AccountSearch",
    # Article schemas
    "ArticleCreate", "ArticleUpdate", "ArticleResponse", "ArticleList",
    # Subscription schemas
    "SubscriptionCreate", "SubscriptionResponse",
    # Push record schemas
    "PushRecordCreate", "PushRecordResponse",
    # Limits schemas
    "SubscriptionLimitInfo", "PushLimitInfo", "UserLimitsSummary", 
    "LevelBenefits", "AllMembershipBenefits",
    # Search schemas
    "SearchRequest", "PlatformSearchRequest", "SearchResponse",
    "PlatformStatusResponse", "SearchStatisticsResponse", "SupportedPlatformsResponse",
    "SearchSuggestionRequest", "SearchSuggestion", "SearchSuggestionResponse",
    "SearchHistoryItem", "SearchHistoryResponse", "CacheStatsResponse",
    # Common schemas
    "BaseResponse", "PaginatedResponse"
]