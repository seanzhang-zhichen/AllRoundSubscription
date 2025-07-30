"""
Mock平台适配器 - 用于测试和演示
"""
import asyncio
from typing import List, Optional, Dict, Any
from app.services.search.base import PlatformAdapter, PlatformSearchResult
from app.models.account import Platform


class MockPlatformAdapter(PlatformAdapter):
    """Mock平台适配器 - 用于测试"""
    
    def __init__(self, platform: Platform, enabled: bool = True):
        super().__init__(platform)
        self._enabled = enabled
        self._mock_accounts = self._generate_mock_accounts()
    
    @property
    def platform_name(self) -> str:
        """平台名称"""
        return f"Mock {self.platform.value.title()}"
    
    @property
    def is_enabled(self) -> bool:
        """是否启用该平台"""
        return self._enabled
    
    async def get_all_accounts(self) -> List[Dict[str, Any]]:
        """
        获取所有账号
        """
        return self._mock_accounts
    
    def _generate_mock_accounts(self) -> List[Dict[str, Any]]:
        """生成模拟账号数据"""
        base_accounts = [
            {
                "id": f"mock_{self.platform.value}_001",
                "name": f"测试博主1_{self.platform.value}",
                "avatar": f"https://example.com/avatar1_{self.platform.value}.jpg",
                "description": f"这是{self.platform.value}平台的测试博主1",
                "followers": 10000,
                "verified": True
            },
            {
                "id": f"mock_{self.platform.value}_002", 
                "name": f"科技达人_{self.platform.value}",
                "avatar": f"https://example.com/avatar2_{self.platform.value}.jpg",
                "description": f"专注科技资讯的{self.platform.value}博主",
                "followers": 50000,
                "verified": True
            },
            {
                "id": f"mock_{self.platform.value}_003",
                "name": f"美食分享_{self.platform.value}",
                "avatar": f"https://example.com/avatar3_{self.platform.value}.jpg", 
                "description": f"分享美食制作的{self.platform.value}账号",
                "followers": 25000,
                "verified": False
            },
            {
                "id": f"mock_{self.platform.value}_004",
                "name": f"旅行记录_{self.platform.value}",
                "avatar": f"https://example.com/avatar4_{self.platform.value}.jpg",
                "description": f"记录旅行足迹的{self.platform.value}博主",
                "followers": 15000,
                "verified": False
            },
            {
                "id": f"mock_{self.platform.value}_005",
                "name": f"健身教练_{self.platform.value}",
                "avatar": f"https://example.com/avatar5_{self.platform.value}.jpg",
                "description": f"专业健身指导的{self.platform.value}账号",
                "followers": 30000,
                "verified": True
            }
        ]
        return base_accounts
    
    async def search_accounts(
        self, 
        keyword: str, 
        page: int = 1, 
        page_size: int = 20
    ) -> PlatformSearchResult:
        """
        搜索账号
        
        Args:
            keyword: 搜索关键词
            page: 页码
            page_size: 每页大小
            
        Returns:
            PlatformSearchResult: 平台搜索结果
        """
        # 模拟网络延迟
        await asyncio.sleep(0.1)
        
        if not self._enabled:
            return PlatformSearchResult(
                platform=self.platform.value,
                accounts=[],
                total=0,
                success=False,
                error_message="平台适配器已禁用"
            )
        
        try:
            # 模拟搜索过滤
            filtered_accounts = []
            for account in self._mock_accounts:
                if (keyword.lower() in account["name"].lower() or 
                    keyword.lower() in account["description"].lower()):
                    filtered_accounts.append(account)
            
            # 按粉丝数排序
            filtered_accounts.sort(key=lambda x: x["followers"], reverse=True)
            
            # 分页处理
            total = len(filtered_accounts)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_accounts = filtered_accounts[start_idx:end_idx]
            
            # 标准化数据格式
            normalized_accounts = []
            for account in paginated_accounts:
                normalized_account = self.normalize_account_data(account)
                normalized_accounts.append(normalized_account)
            
            return PlatformSearchResult(
                platform=self.platform.value,
                accounts=normalized_accounts,
                total=total,
                success=True
            )
            
        except Exception as e:
            return PlatformSearchResult(
                platform=self.platform.value,
                accounts=[],
                total=0,
                success=False,
                error_message=f"搜索失败: {str(e)}"
            )
    
    async def get_account_info(self, account_id: str) -> Optional[Dict[str, Any]]:
        """
        获取账号详细信息
        
        Args:
            account_id: 账号ID
            
        Returns:
            Optional[Dict[str, Any]]: 账号信息，如果不存在返回None
        """
        # 模拟网络延迟
        await asyncio.sleep(0.05)
        
        if not self._enabled:
            return None
        
        # 查找账号
        for account in self._mock_accounts:
            if account["id"] == account_id:
                return account
        
        return None
    
    def normalize_account_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化账号数据格式
        
        Args:
            raw_data: 原始账号数据
            
        Returns:
            Dict[str, Any]: 标准化后的账号数据
        """
        from datetime import datetime
        
        return {
            "id": hash(raw_data.get("id", "")) % 1000000,  # 生成一个模拟ID
            "name": raw_data.get("name", ""),
            "platform": self.platform.value,
            "account_id": raw_data.get("id", ""),
            "avatar_url": raw_data.get("avatar", ""),
            "description": raw_data.get("description", ""),
            "follower_count": raw_data.get("followers", 0),
            "details": {
                "verified": raw_data.get("verified", False),
                "original_data": raw_data
            },
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "platform_display_name": self.platform_name
        }
    
    def set_enabled(self, enabled: bool):
        """设置适配器启用状态"""
        self._enabled = enabled
    
    def add_mock_account(self, account_data: Dict[str, Any]):
        """添加模拟账号数据"""
        self._mock_accounts.append(account_data)
    
    def clear_mock_accounts(self):
        """清空模拟账号数据"""
        self._mock_accounts = []