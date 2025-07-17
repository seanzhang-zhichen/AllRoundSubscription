"""
搜索服务实现
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.services.search.base import SearchServiceBase, SearchResult, PlatformSearchResult
from app.services.search.cache import SearchCache
from app.services.search.aggregator import SearchAggregator
from app.services.search.exceptions import SearchException, PlatformUnavailableException
from app.models.account import Account, Platform
from app.schemas.account import AccountResponse
from app.db.database import AsyncSessionLocal
from datetime import datetime

logger = logging.getLogger(__name__)


class SearchService(SearchServiceBase):
    """搜索服务实现类"""
    
    def __init__(self):
        super().__init__()
        self.cache = SearchCache()
        self.aggregator = SearchAggregator(timeout_seconds=10)
        self._platform_status: Dict[str, bool] = {}
    
    async def search_accounts(
        self,
        keyword: str,
        platforms: Optional[List[str]] = None,
        page: int = 1,
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
        # 尝试从缓存获取结果
        cached_result = await self.cache.get_search_result(
            keyword=keyword,
            platforms=platforms,
            page=page,
            page_size=page_size
        )
        if cached_result:
            return cached_result
        
        # 确定要搜索的平台
        target_platforms = platforms or self.get_supported_platforms()
        if not target_platforms:
            return SearchResult(
                accounts=[],
                total=0,
                page=page,
                page_size=page_size,
                has_more=False
            )
        
        # 获取目标平台的适配器
        target_adapters = []
        for platform in target_platforms:
            adapter = self.get_adapter(platform)
            if adapter and adapter.is_enabled:
                target_adapters.append(adapter)
        
        if not target_adapters:
            return SearchResult(
                accounts=[],
                total=0,
                page=page,
                page_size=page_size,
                has_more=False
            )
        
        # 使用聚合器进行多平台搜索
        try:
            result, error_info = await self.aggregator.aggregate_search_results(
                target_adapters, keyword, page, page_size
            )
            
            # 记录错误信息
            if error_info["errors"]:
                logger.warning(f"搜索过程中发生错误: {error_info}")
            
            # 按相关性重新排序结果
            if result.accounts:
                result.accounts = self.aggregator.sort_by_relevance(result.accounts, keyword)
            
        except Exception as e:
            logger.error(f"搜索聚合失败: {e}")
            # 降级到本地数据库搜索
            result = await self._fallback_to_local_search(keyword, target_platforms, page, page_size)
        
        # 缓存结果
        await self.cache.set_search_result(
            keyword=keyword,
            platforms=platforms,
            page=page,
            page_size=page_size,
            result=result
        )
        
        return result
    
    async def search_by_platform(
        self,
        keyword: str,
        platform: str,
        page: int = 1,
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
        # 尝试从缓存获取结果
        cached_result = await self.cache.get_platform_result(
            keyword=keyword,
            platform=platform,
            page=page,
            page_size=page_size
        )
        if cached_result and cached_result.success:
            # 转换为SearchResult格式
            accounts = []
            for account_data in cached_result.accounts:
                try:
                    account_response = AccountResponse(**account_data)
                    accounts.append(account_response)
                except Exception:
                    continue
            
            return SearchResult(
                accounts=accounts,
                total=cached_result.total,
                page=page,
                page_size=page_size,
                platform=platform,
                has_more=(page * page_size) < cached_result.total
            )
        
        # 获取平台适配器
        adapter = self.get_adapter(platform)
        if not adapter or not adapter.is_enabled:
            return SearchResult(
                accounts=[],
                total=0,
                page=page,
                page_size=page_size,
                platform=platform,
                has_more=False
            )
        
        # 执行平台搜索
        platform_result = await self._search_platform_with_fallback(
            adapter, keyword, page, page_size
        )
        
        # 转换结果格式
        accounts = []
        if platform_result.success:
            for account_data in platform_result.accounts:
                try:
                    account_response = AccountResponse(**account_data)
                    accounts.append(account_response)
                except Exception as e:
                    print(f"转换账号数据失败: {e}")
                    continue
        
        result = SearchResult(
            accounts=accounts,
            total=platform_result.total if platform_result.success else 0,
            page=page,
            page_size=page_size,
            platform=platform,
            has_more=(page * page_size) < (platform_result.total if platform_result.success else 0)
        )
        
        # 缓存平台结果
        if platform_result.success:
            await self.cache.set_platform_result(
                keyword=keyword,
                platform=platform,
                page=page,
                page_size=page_size,
                result=platform_result
            )
        
        return result
    
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
        # 先从数据库查找
        async with AsyncSessionLocal() as db:
            stmt = select(Account).where(
                and_(
                    Account.platform == platform,
                    Account.account_id == account_id
                )
            )
            result = await db.execute(stmt)
            account = result.scalar_one_or_none()
            
            if account:
                return AccountResponse.model_validate(account)
        
        # 如果数据库中没有，尝试从平台API获取
        adapter = self.get_adapter(platform)
        if adapter and adapter.is_enabled:
            try:
                account_info = await adapter.get_account_info(account_id)
                if account_info:
                    # 标准化数据格式
                    normalized_data = adapter.normalize_account_data(account_info)
                    return AccountResponse(**normalized_data)
            except Exception as e:
                print(f"从平台获取账号信息失败: {e}")
        
        return None
    
    async def _search_platform_with_fallback(
        self,
        adapter,
        keyword: str,
        page: int,
        page_size: int
    ) -> PlatformSearchResult:
        """
        带降级策略的平台搜索
        
        Args:
            adapter: 平台适配器
            keyword: 搜索关键词
            page: 页码
            page_size: 每页大小
            
        Returns:
            PlatformSearchResult: 平台搜索结果
        """
        try:
            # 检查平台状态缓存
            platform_status = await self.cache.get_platform_status(adapter.platform.value)
            if platform_status is False:
                # 平台不可用，返回本地数据库搜索结果
                return await self._search_local_database(
                    keyword, adapter.platform.value, page, page_size
                )
            
            # 尝试平台API搜索
            result = await adapter.search_accounts(keyword, page, page_size)
            
            # 更新平台状态
            await self.cache.set_platform_status(adapter.platform.value, result.success)
            
            if result.success:
                return result
            else:
                # API调用失败，降级到本地数据库搜索
                return await self._search_local_database(
                    keyword, adapter.platform.value, page, page_size
                )
                
        except Exception as e:
            print(f"平台搜索失败: {e}")
            # 标记平台不可用
            await self.cache.set_platform_status(adapter.platform.value, False)
            
            # 降级到本地数据库搜索
            return await self._search_local_database(
                keyword, adapter.platform.value, page, page_size
            )
    
    async def _search_local_database(
        self,
        keyword: str,
        platform: str,
        page: int,
        page_size: int
    ) -> PlatformSearchResult:
        """
        本地数据库搜索（降级策略）
        
        Args:
            keyword: 搜索关键词
            platform: 平台标识
            page: 页码
            page_size: 每页大小
            
        Returns:
            PlatformSearchResult: 搜索结果
        """
        try:
            async with AsyncSessionLocal() as db:
                # 构建搜索条件
                search_conditions = [
                    Account.platform == platform,
                    or_(
                        Account.name.ilike(f"%{keyword}%"),
                        Account.description.ilike(f"%{keyword}%")
                    )
                ]
                
                # 查询总数
                count_stmt = select(Account).where(and_(*search_conditions))
                count_result = await db.execute(count_stmt)
                total = len(count_result.fetchall())
                
                # 分页查询
                stmt = (
                    select(Account)
                    .where(and_(*search_conditions))
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                    .order_by(Account.follower_count.desc(), Account.updated_at.desc())
                )
                
                result = await db.execute(stmt)
                accounts = result.scalars().all()
                
                # 转换为字典格式
                account_dicts = []
                for account in accounts:
                    account_dict = {
                        "id": account.id,
                        "name": account.name,
                        "platform": account.platform,
                        "account_id": account.account_id,
                        "avatar_url": account.avatar_url,
                        "description": account.description,
                        "follower_count": account.follower_count,
                        "details": account.details or {},
                        "created_at": account.created_at,
                        "updated_at": account.updated_at,
                        "platform_display_name": account.platform_display_name
                    }
                    account_dicts.append(account_dict)
                
                return PlatformSearchResult(
                    platform=platform,
                    accounts=account_dicts,
                    total=total,
                    success=True
                )
                
        except Exception as e:
            print(f"本地数据库搜索失败: {e}")
            return PlatformSearchResult(
                platform=platform,
                accounts=[],
                total=0,
                success=False,
                error_message=f"本地搜索失败: {str(e)}"
            )
    
    async def _fallback_to_local_search(
        self,
        keyword: str,
        platforms: List[str],
        page: int,
        page_size: int
    ) -> SearchResult:
        """
        降级到本地数据库搜索
        
        Args:
            keyword: 搜索关键词
            platforms: 平台列表
            page: 页码
            page_size: 每页大小
            
        Returns:
            SearchResult: 搜索结果
        """
        try:
            async with AsyncSessionLocal() as db:
                # 构建搜索条件
                search_conditions = [
                    Account.platform.in_(platforms),
                    or_(
                        Account.name.ilike(f"%{keyword}%"),
                        Account.description.ilike(f"%{keyword}%")
                    )
                ]
                
                # 查询总数
                count_stmt = select(Account).where(and_(*search_conditions))
                count_result = await db.execute(count_stmt)
                total = len(count_result.fetchall())
                
                # 分页查询
                stmt = (
                    select(Account)
                    .where(and_(*search_conditions))
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                    .order_by(Account.follower_count.desc(), Account.updated_at.desc())
                )
                
                result = await db.execute(stmt)
                accounts = result.scalars().all()
                
                # 转换为AccountResponse格式
                account_responses = []
                for account in accounts:
                    try:
                        account_response = AccountResponse.model_validate(account)
                        account_responses.append(account_response)
                    except Exception as e:
                        logger.warning(f"转换账号数据失败: {e}")
                        continue
                
                return SearchResult(
                    accounts=account_responses,
                    total=total,
                    page=page,
                    page_size=page_size,
                    has_more=(page * page_size) < total
                )
                
        except Exception as e:
            logger.error(f"本地数据库搜索失败: {e}")
            return SearchResult(
                accounts=[],
                total=0,
                page=page,
                page_size=page_size,
                has_more=False
            )
    
    def _deduplicate_accounts(self, accounts: List[AccountResponse]) -> List[AccountResponse]:
        """
        账号去重
        
        Args:
            accounts: 账号列表
            
        Returns:
            List[AccountResponse]: 去重后的账号列表
        """
        seen = set()
        unique_accounts = []
        
        for account in accounts:
            # 使用平台+账号ID作为唯一标识
            key = f"{account.platform}:{account.account_id}"
            if key not in seen:
                seen.add(key)
                unique_accounts.append(account)
        
        # 按粉丝数量排序
        unique_accounts.sort(key=lambda x: x.follower_count, reverse=True)
        return unique_accounts
    
    async def get_search_statistics(self) -> Dict[str, Any]:
        """
        获取搜索统计信息
        
        Returns:
            Dict[str, Any]: 搜索统计信息
        """
        cache_stats = await self.cache.get_cache_stats()
        
        return {
            "supported_platforms": self.get_supported_platforms(),
            "registered_adapters": list(self._adapters.keys()),
            "platform_status": self._platform_status,
            "cache_stats": cache_stats,
            "timestamp": datetime.now().isoformat()
        }


# 创建全局搜索服务实例
search_service = SearchService()