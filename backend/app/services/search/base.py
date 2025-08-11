"""
搜索服务基础抽象类和接口定义
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.models.account import Platform
from app.schemas.account import AccountResponse


class SearchResult(BaseModel):
    """搜索结果模型"""
    accounts: List[AccountResponse]
    total: int
    page: int
    page_size: int
    platform: Optional[str] = None
    has_more: bool = False
    search_time_ms: Optional[int] = None
    
    class Config:
        from_attributes = True


class PlatformSearchResult(BaseModel):
    """平台搜索结果模型"""
    platform: str
    accounts: List[AccountResponse]
    total: int
    success: bool = True
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class PlatformAdapter(ABC):
    """平台适配器抽象基类"""
    
    def __init__(self, platform: Platform):
        self.platform = platform
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """平台名称"""
        pass
    
    @property
    @abstractmethod
    def is_enabled(self) -> bool:
        """是否启用该平台"""
        pass
    
    @abstractmethod
    async def search_accounts(
        self, 
        keyword: str, 
        page: int = 0,  # 修改默认页码为0
        page_size: int = 20
    ) -> PlatformSearchResult:
        """
        搜索账号
        
        Args:
            keyword: 搜索关键词
            page: 页码（从0开始）
            page_size: 每页大小
            
        Returns:
            PlatformSearchResult: 平台搜索结果
        """
        pass
    
    @abstractmethod
    async def get_account_info(self, account_id: str) -> Optional[Dict[str, Any]]:
        """
        获取账号详细信息
        
        Args:
            account_id: 账号ID
            
        Returns:
            Optional[Dict[str, Any]]: 账号信息，如果不存在返回None
        """
        pass
    
    @abstractmethod
    async def get_all_accounts(self) -> List[Dict[str, Any]]:
        """
        获取所有账号
        """
        pass
    

    @abstractmethod
    async def get_all_articles_by_account_id(self, account_id: str) -> List[Dict[str, Any]]:
        """
        获取所有文章
        """
        pass

    @abstractmethod
    async def get_article_detail(self, article_id: str) -> Optional[Dict[str, Any]]:
        """
        获取文章详情
        """
        pass
    
    @abstractmethod
    async def get_account_article_stats(self, account_id: str) -> Dict[str, Any]:
        """
        获取账号文章统计信息
        """
        pass

    @abstractmethod
    async def add_account(self, mp_name: str, mp_cover: Optional[str] = None, mp_id: Optional[str] = None, 
                   avatar: Optional[str] = None, mp_intro: Optional[str] = None) -> Dict[str, Any]:
        """
        添加公众号账号
        """
        pass

    @abstractmethod
    async def get_id_by_faker_id(self, faker_id: str):
        """
        根据faker_id查询账号的id
        """
        pass

    def normalize_account_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化账号数据格式
        
        Args:
            raw_data: 原始账号数据
            
        Returns:
            Dict[str, Any]: 标准化后的账号数据
        """
        return {
            "name": raw_data.get("name", ""),
            "platform": self.platform.value,
            "account_id": raw_data.get("id", ""),
            "avatar_url": raw_data.get("avatar", ""),
            "description": raw_data.get("description", ""),
            "follower_count": raw_data.get("followers", 0),
            "details": raw_data
        }


class SearchServiceBase(ABC):
    """搜索服务抽象基类"""
    
    def __init__(self):
        self._adapters: Dict[str, PlatformAdapter] = {}
    
    def register_adapter(self, adapter: PlatformAdapter):
        """
        注册平台适配器
        
        Args:
            adapter: 平台适配器实例
        """
        self._adapters[adapter.platform.value] = adapter
    
    def get_adapter(self, platform: str) -> Optional[PlatformAdapter]:
        """
        获取平台适配器
        
        Args:
            platform: 平台标识
            
        Returns:
            Optional[PlatformAdapter]: 平台适配器，如果不存在返回None
        """
        return self._adapters.get(platform)
    
    def get_supported_platforms(self) -> List[str]:
        """
        获取支持的平台列表
        
        Returns:
            List[str]: 支持的平台列表
        """
        return [
            platform for platform, adapter in self._adapters.items()
            if adapter.is_enabled
        ]
    
    @abstractmethod
    async def search_accounts(
        self,
        keyword: str,
        platforms: Optional[List[str]] = None,
        page: int = 0,
        page_size: int = 20
    ) -> SearchResult:
        """
        搜索账号
        
        Args:
            keyword: 搜索关键词
            platforms: 指定平台列表，为None时搜索所有平台
            page: 页码
            page_size: 每页大小
            
        Returns:
            SearchResult: 搜索结果
        """
        pass
    
    @abstractmethod
    async def search_by_platform(
        self,
        keyword: str,
        platform: str,
        page: int = 0,
        page_size: int = 20
    ) -> SearchResult:
        """
        在指定平台搜索账号
        
        Args:
            keyword: 搜索关键词
            platform: 平台标识
            page: 页码
            page_size: 每页大小
            
        Returns:
            SearchResult: 搜索结果
        """
        pass
    
    @abstractmethod
    async def get_account_by_platform_id(
        self,
        platform: str,
        account_id: str
    ) -> Optional[AccountResponse]:
        """
        根据平台账号ID获取账号信息
        
        Args:
            platform: 平台标识
            account_id: 平台账号ID
            
        Returns:
            Optional[AccountResponse]: 账号信息，如果不存在返回None
        """
        pass