"""
搜索结果聚合器
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from app.core.logging import get_logger
from app.services.search.base import PlatformAdapter, PlatformSearchResult, SearchResult
from app.services.search.exceptions import SearchException, PlatformUnavailableException
from app.schemas.account import AccountResponse

logger = get_logger(__name__)


class SearchAggregator:
    """搜索结果聚合器"""
    
    def __init__(self, timeout_seconds: int = 10):
        self.timeout_seconds = timeout_seconds
        self.max_concurrent_searches = 5
    
    async def aggregate_search_results(
        self,
        adapters: List[PlatformAdapter],
        keyword: str,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[SearchResult, Dict[str, Any]]:
        """
        聚合多平台搜索结果
        
        Args:
            adapters: 平台适配器列表
            keyword: 搜索关键词
            page: 页码
            page_size: 每页大小
            
        Returns:
            Tuple[SearchResult, Dict[str, Any]]: 聚合结果和错误信息
        """
        start_time = datetime.now()
        
        # 限制并发搜索数量
        semaphore = asyncio.Semaphore(self.max_concurrent_searches)
        
        # 创建搜索任务
        search_tasks = []
        for adapter in adapters:
            if adapter.is_enabled:
                task = self._search_with_semaphore(
                    semaphore, adapter, keyword, page, page_size
                )
                search_tasks.append(task)
        
        if not search_tasks:
            return SearchResult(
                accounts=[],
                total=0,
                page=page,
                page_size=page_size,
                has_more=False
            ), {"error": "没有可用的平台适配器"}
        
        # 并发执行搜索任务
        try:
            platform_results = await asyncio.wait_for(
                asyncio.gather(*search_tasks, return_exceptions=True),
                timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.warning(f"搜索聚合超时: {self.timeout_seconds}秒")
            platform_results = [PlatformUnavailableException("unknown", "搜索超时")]
        
        # 处理搜索结果
        successful_results = []
        error_info = {
            "failed_platforms": [],
            "errors": [],
            "total_platforms": len(adapters),
            "successful_platforms": 0
        }
        
        for i, result in enumerate(platform_results):
            adapter = adapters[i] if i < len(adapters) else None
            platform_name = adapter.platform.value if adapter else "unknown"
            
            if isinstance(result, Exception):
                error_msg = str(result)
                logger.error(f"平台 {platform_name} 搜索失败: {error_msg}")
                error_info["failed_platforms"].append(platform_name)
                error_info["errors"].append({
                    "platform": platform_name,
                    "error": error_msg,
                    "type": type(result).__name__
                })
            elif isinstance(result, PlatformSearchResult):
                if result.success:
                    successful_results.append(result)
                    error_info["successful_platforms"] += 1
                else:
                    error_info["failed_platforms"].append(result.platform)
                    error_info["errors"].append({
                        "platform": result.platform,
                        "error": result.error_message,
                        "type": "PlatformSearchError"
                    })
        
        # 聚合成功的结果
        aggregated_result = self._aggregate_platform_results(
            successful_results, page, page_size
        )
        
        # 添加搜索时间信息
        end_time = datetime.now()
        search_time_ms = int((end_time - start_time).total_seconds() * 1000)
        aggregated_result.search_time_ms = search_time_ms
        
        return aggregated_result, error_info
    
    async def _search_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        adapter: PlatformAdapter,
        keyword: str,
        page: int,
        page_size: int
    ) -> PlatformSearchResult:
        """
        使用信号量控制并发的搜索
        
        Args:
            semaphore: 并发控制信号量
            adapter: 平台适配器
            keyword: 搜索关键词
            page: 页码
            page_size: 每页大小
            
        Returns:
            PlatformSearchResult: 平台搜索结果
        """
        async with semaphore:
            try:
                return await adapter.search_accounts(keyword, page, page_size)
            except Exception as e:
                logger.error(f"平台 {adapter.platform.value} 搜索异常: {str(e)}")
                return PlatformSearchResult(
                    platform=adapter.platform.value,
                    accounts=[],
                    total=0,
                    success=False,
                    error_message=str(e)
                )
    
    def _aggregate_platform_results(
        self,
        platform_results: List[PlatformSearchResult],
        page: int,
        page_size: int
    ) -> SearchResult:
        """
        聚合平台搜索结果
        
        Args:
            platform_results: 平台搜索结果列表
            page: 页码
            page_size: 每页大小
            
        Returns:
            SearchResult: 聚合后的搜索结果
        """
        all_accounts = []
        total_count = 0
        
        # 收集所有账号数据
        for result in platform_results:
            if result.success and result.accounts:
                for account_data in result.accounts:
                    try:
                        account_response = AccountResponse(**account_data)
                        all_accounts.append(account_response)
                    except Exception as e:
                        logger.warning(f"转换账号数据失败: {e}")
                        continue
                total_count += result.total
        
        # 去重处理
        unique_accounts = self._deduplicate_accounts(all_accounts)
        
        # 排序：按粉丝数量降序，然后按更新时间降序
        unique_accounts.sort(
            key=lambda x: (x.follower_count, x.updated_at),
            reverse=True
        )
        
        # 分页处理
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_accounts = unique_accounts[start_idx:end_idx]
        
        return SearchResult(
            accounts=paginated_accounts,
            total=len(unique_accounts),
            page=page,
            page_size=page_size,
            has_more=end_idx < len(unique_accounts)
        )
    
    def _deduplicate_accounts(self, accounts: List[AccountResponse]) -> List[AccountResponse]:
        """
        账号去重
        
        Args:
            accounts: 账号列表
            
        Returns:
            List[AccountResponse]: 去重后的账号列表
        """
        # 使用多种策略进行去重
        seen_keys = set()
        unique_accounts = []
        
        for account in accounts:
            # 策略1: 平台+账号ID
            key1 = f"{account.platform}:{account.account_id}"
            
            # 策略2: 平台+账号名称（处理同一账号在不同平台的情况）
            key2 = f"{account.platform}:{account.name.lower().strip()}"
            
            # 策略3: 跨平台去重（相同名称的账号，优先保留粉丝数多的）
            key3 = account.name.lower().strip()
            
            # 检查是否已存在
            if key1 not in seen_keys and key2 not in seen_keys:
                # 检查是否有同名账号
                existing_account = None
                for existing in unique_accounts:
                    if existing.name.lower().strip() == key3:
                        existing_account = existing
                        break
                
                if existing_account:
                    # 如果当前账号粉丝数更多，替换现有账号
                    if account.follower_count > existing_account.follower_count:
                        unique_accounts.remove(existing_account)
                        unique_accounts.append(account)
                        # 更新seen_keys
                        old_key1 = f"{existing_account.platform}:{existing_account.account_id}"
                        old_key2 = f"{existing_account.platform}:{existing_account.name.lower().strip()}"
                        seen_keys.discard(old_key1)
                        seen_keys.discard(old_key2)
                        seen_keys.add(key1)
                        seen_keys.add(key2)
                else:
                    # 新账号，直接添加
                    unique_accounts.append(account)
                    seen_keys.add(key1)
                    seen_keys.add(key2)
        
        return unique_accounts
    
    def calculate_relevance_score(self, account: AccountResponse, keyword: str) -> float:
        """
        计算账号与搜索关键词的相关性得分
        
        Args:
            account: 账号信息
            keyword: 搜索关键词
            
        Returns:
            float: 相关性得分 (0-1)
        """
        score = 0.0
        keyword_lower = keyword.lower()
        
        # 名称匹配得分 (权重: 0.4)
        if keyword_lower in account.name.lower():
            if account.name.lower() == keyword_lower:
                score += 0.4  # 完全匹配
            elif account.name.lower().startswith(keyword_lower):
                score += 0.3  # 前缀匹配
            else:
                score += 0.2  # 包含匹配
        
        # 描述匹配得分 (权重: 0.2)
        if account.description and keyword_lower in account.description.lower():
            score += 0.2
        
        # 粉丝数量得分 (权重: 0.3)
        # 使用对数缩放，避免粉丝数量差异过大
        import math
        if account.follower_count > 0:
            # 将粉丝数量映射到0-0.3的范围
            follower_score = min(0.3, math.log10(account.follower_count + 1) / 10)
            score += follower_score
        
        # 认证状态得分 (权重: 0.1)
        if account.details and account.details.get("verified", False):
            score += 0.1
        
        return min(1.0, score)
    
    def sort_by_relevance(
        self, 
        accounts: List[AccountResponse], 
        keyword: str
    ) -> List[AccountResponse]:
        """
        按相关性排序账号列表
        
        Args:
            accounts: 账号列表
            keyword: 搜索关键词
            
        Returns:
            List[AccountResponse]: 按相关性排序的账号列表
        """
        # 计算每个账号的相关性得分
        account_scores = []
        for account in accounts:
            relevance_score = self.calculate_relevance_score(account, keyword)
            account_scores.append((account, relevance_score))
        
        # 按相关性得分降序排序
        account_scores.sort(key=lambda x: x[1], reverse=True)
        
        return [account for account, score in account_scores]