"""
搜索服务实现
"""
import asyncio
from app.core.logging import get_logger
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.services.search.base import SearchServiceBase, SearchResult, PlatformSearchResult
from app.services.search.cache import SearchCache
from app.services.search.aggregator import SearchAggregator
from app.services.search.exceptions import SearchException, PlatformUnavailableException
from app.models.account import Account, Platform
from app.schemas.account import AccountResponse
from app.schemas.article import ArticleWithAccount
from app.db.database import AsyncSessionLocal
from datetime import datetime
import traceback
import time

logger = get_logger(__name__)


class SearchService(SearchServiceBase):
    """搜索服务实现类"""
    
    def __init__(self):
        super().__init__()
        self.cache = SearchCache()
        self.aggregator = SearchAggregator(timeout_seconds=10)
        self._platform_status: Dict[str, bool] = {}
    
    async def get_all_accounts(
        self,
        platforms: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 20
    ) -> SearchResult:
        """
        获取所有博主账号
        
        Args:
            platforms: 指定平台列表，为None时获取所有平台
            page: 页码
            page_size: 每页大小
            
        Returns:
            SearchResult: 搜索结果
        """
        # 转换为AccountResponse格式

        if platforms is None:
            platforms = self.get_supported_platforms()
            logger.info(f"获取所有平台账号: {platforms}")

        try:
            accounts = []
            for platform in platforms:
                adapter = self.get_adapter(platform)
                if adapter and adapter.is_enabled:
                    accounts.extend(await adapter.get_all_accounts())

            return SearchResult(
                accounts=accounts,
                total=len(accounts),
                page=page,
                page_size=page_size,
                has_more=(page * page_size) < len(accounts)
            )
                
        except Exception as e:
            logger.error(f"获取所有博主失败: {e}")
            logger.error(traceback.format_exc())
            return SearchResult(
                accounts=[],
                total=0,
                page=page,
                page_size=page_size,
                has_more=False
            )

    async def search_accounts(
        self,
        keyword: str,
        platforms: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 10
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
        print("\n" + "="*50)
        print(f"【search_accounts】搜索开始")
        print(f"关键词: '{keyword}'")
        print(f"平台列表: {platforms}")
        print(f"页码: {page}, 每页大小: {page_size}")
        
        # 尝试从缓存获取结果
        cached_result = await self.cache.get_search_result(
            keyword=keyword,
            platforms=platforms,
            page=page,
            page_size=page_size
        )
        if cached_result:
            print("从缓存中获取到结果，结果数:", len(cached_result.accounts))
            return cached_result
        else:
            print("缓存中无结果，执行搜索")
        
        # 确定要搜索的平台
        target_platforms = platforms or self.get_supported_platforms()
        print(f"目标搜索平台: {target_platforms}")
        

        # 获取目标平台的适配器
        target_adapters = []
        for platform in target_platforms:
            adapter = self.get_adapter(platform)
            if adapter and adapter.is_enabled:
                target_adapters.append(adapter)
                print(f"添加平台适配器: {platform} - {adapter.__class__.__name__}")
            else:
                print(f"平台 {platform} 的适配器不可用")
        

        # 使用聚合器进行多平台搜索
        try:
            print("开始执行聚合搜索...")
            result, error_info = await self.aggregator.aggregate_search_results(
                target_adapters, keyword, page, page_size
            )
            
            # 记录错误信息
            if error_info["errors"]:
                print(f"搜索过程中发生错误: {error_info}")
                logger.warning(f"搜索过程中发生错误: {error_info}")
            
            # 输出搜索结果概要
            print(f"聚合搜索结果: 总数={result.total}, 当前页结果数={len(result.accounts)}")
            
            # 按相关性重新排序结果
            if result.accounts:
                print("按相关性重新排序结果...")
                result.accounts = self.aggregator.sort_by_relevance(result.accounts, keyword)
                print("排序完成")
            
        except Exception as e:
            print(f"搜索聚合失败: {str(e)}")
            logger.error(f"搜索聚合失败: {e}")
            # 降级到本地数据库搜索
            print("降级到本地数据库搜索...")
            result = await self._fallback_to_local_search(keyword, target_platforms, page, page_size)
            print(f"本地搜索结果: 总数={result.total}, 当前页结果数={len(result.accounts)}")
        
        # 缓存结果
        print("缓存搜索结果...")
        await self.cache.set_search_result(
            keyword=keyword,
            platforms=platforms,
            page=page,
            page_size=page_size,
            result=result
        )
        
        print(f"【search_accounts】搜索完成，总结果数: {result.total}")
        print("="*50 + "\n")
        
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
        start_time = time.time()
        
        adapter = self.get_adapter(platform)
        if adapter and adapter.is_enabled:
            try:
                adapter_start = time.time()
                account_info = await adapter.get_account_info(account_id)
                adapter_time = time.time() - adapter_start
                
                total_time = time.time() - start_time
                if account_info:
                    logger.info(f"获取账号信息成功 - 平台:{platform}, 账号ID:{account_id}, 总耗时:{total_time:.3f}秒, API耗时:{adapter_time:.3f}秒")
                else:
                    logger.info(f"未找到账号信息 - 平台:{platform}, 账号ID:{account_id}, 耗时:{total_time:.3f}秒")
                
                return account_info
            except Exception as e:
                total_time = time.time() - start_time
                logger.error(f"从平台获取账号信息失败 - 平台:{platform}, 账号ID:{account_id}, 耗时:{total_time:.3f}秒, 错误:{str(e)}")
                return None
        else:
            total_time = time.time() - start_time
            logger.warning(f"平台适配器不可用 - 平台:{platform}, 账号ID:{account_id}, 耗时:{total_time:.3f}秒")
            return None
    
    async def get_account_by_id(
        self,
        account_id: str,
        db: AsyncSession,
        platform: Optional[str] = None
    ) -> Optional[AccountResponse]:
        """
        根据账号ID获取账号信息
        
        Args:
            account_id: 账号ID
            db: 数据库会话
            platform: 平台类型，如wechat、weibo、twitter等，为None时不过滤平台
            
        Returns:
            Optional[AccountResponse]: 账号信息，如果不存在返回None
        """
        try:
            return await self.get_account_by_platform_id(platform, account_id)
        except Exception as e:
            logger.error(f"根据ID获取账号信息失败: {str(e)}", exc_info=True)
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
            print(f"=== 执行本地数据库搜索 ===")
            print(f"关键词: '{keyword}'")
            print(f"平台: {platform}")
            print(f"页码: {page}, 每页大小: {page_size}")
            
            async with AsyncSessionLocal() as db:
                # 构建搜索条件
                search_conditions = [
                    Account.platform == platform,
                    or_(
                        Account.name.ilike(f"%{keyword}%"),
                        Account.description.ilike(f"%{keyword}%")
                    )
                ]
                
                print(f"搜索条件: platform='{platform}', keyword ILIKE '%{keyword}%' in name/description")
                
                # 查询总数
                count_stmt = select(Account).where(and_(*search_conditions))
                # 打印实际执行的SQL语句
                compiled_count = count_stmt.compile(
                    dialect=db.bind.dialect, 
                    compile_kwargs={"literal_binds": True}
                )
                print(f"平台搜索COUNT SQL: {str(compiled_count)}")
                
                count_result = await db.execute(count_stmt)
                result_list = count_result.fetchall()
                total = len(result_list)
                
                print(f"找到总记录数: {total}")
                
                # 分页查询
                stmt = (
                    select(Account)
                    .where(and_(*search_conditions))
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                    .order_by(Account.follower_count.desc(), Account.updated_at.desc())
                )
                
                # 打印实际执行的SQL语句
                compiled = stmt.compile(
                    dialect=db.bind.dialect, 
                    compile_kwargs={"literal_binds": True}
                )
                print(f"平台搜索SQL: {str(compiled)}")
                
                print(f"执行分页查询: offset={(page - 1) * page_size}, limit={page_size}")
                print(f"排序: follower_count DESC, updated_at DESC")
                
                result = await db.execute(stmt)
                accounts = result.scalars().all()
                
                print(f"当前页获取记录数: {len(accounts)}")
                if accounts:
                    print("数据样例:")
                    for i, acc in enumerate(accounts[:3]):  # 只打印前3条
                        print(f"  {i+1}. ID={acc.id}, 名称='{acc.name}', 描述='{acc.description[:30]}...'")
                
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
        降级到本地数据库搜索（当外部搜索服务不可用时）
        
        Args:
            keyword: 搜索关键词
            platforms: 平台列表
            page: 页码
            page_size: 每页大小
            
        Returns:
            SearchResult: 搜索结果
        """
        print(f"\n*** 开始本地降级搜索 ***")
        print(f"关键词: '{keyword}'")
        print(f"平台列表: {platforms}")
        print(f"页码: {page}, 每页大小: {page_size}")
        
        all_results = []
        total = 0
        
        try:
            # 如果没有指定平台或平台列表为空，尝试从数据库获取所有平台
            if not platforms:
                print("平台列表为空，尝试直接从数据库搜索所有平台...")
                async with AsyncSessionLocal() as db:
                    # 获取数据库中的所有平台
                    from app.models.account import Account
                    from sqlalchemy import select, distinct
                    
                    query = select(distinct(Account.platform))
                    result = await db.execute(query)
                    db_platforms = [row[0] for row in result.fetchall()]
                    print(f"从数据库获取到的平台列表: {db_platforms}")
                    
                    if db_platforms:
                        platforms = db_platforms
                    else:
                        print("数据库中没有平台记录，无法搜索")
                        return SearchResult(
                            accounts=[],
                            total=0,
                            page=page,
                            page_size=page_size,
                            has_more=False
                        )
            
            # 如果仍然没有平台，执行不限平台的搜索
            if not platforms:
                print("无法获取平台列表，执行不限平台的搜索")
                result = await self._search_all_platforms_local(keyword, page, page_size)
                return result
            
            # 获取每个平台的搜索结果
            platform_results = []
            for platform in platforms:
                print(f"在平台 {platform} 执行本地搜索...")
                platform_result = await self._search_local_database(keyword, platform, 1, 100)  # 获取更多结果用于合并
                if platform_result.success and platform_result.accounts:
                    print(f"平台 {platform} 找到 {len(platform_result.accounts)} 条结果")
                    platform_results.append(platform_result)
                    total += platform_result.total
                else:
                    print(f"平台 {platform} 未找到结果")
            
            # 合并所有平台结果
            for result in platform_results:
                all_results.extend([AccountResponse(**account) for account in result.accounts])
            
            print(f"所有平台合并后总结果数: {len(all_results)}")
            
            # 按相关性排序
            if all_results:
                print("按相关性对所有结果排序...")
                all_results = self.aggregator.sort_by_relevance(all_results, keyword)
                print("排序完成")
            
            # 分页
            start_idx = (page - 1) * page_size
            end_idx = min(start_idx + page_size, len(all_results))
            
            print(f"分页: 从 {start_idx} 到 {end_idx} (总数: {len(all_results)})")
            
            paged_results = all_results[start_idx:end_idx] if start_idx < len(all_results) else []
            
            print(f"当前页结果数: {len(paged_results)}")
            
            return SearchResult(
                accounts=paged_results,
                total=total,
                page=page,
                page_size=page_size,
                has_more=end_idx < len(all_results)
            )
            
        except Exception as e:
            print(f"本地降级搜索异常: {str(e)}")
            logger.error(f"本地降级搜索失败: {e}")
            return SearchResult(
                accounts=[],
                total=0,
                page=page,
                page_size=page_size,
                has_more=False
            )
            
    async def _search_all_platforms_local(self, keyword: str, page: int, page_size: int) -> SearchResult:
        """
        在所有平台执行本地数据库搜索（不限制平台）
        """
        print(f"执行不限平台的全局搜索: 关键词='{keyword}'")
        try:
            async with AsyncSessionLocal() as db:
                # 构建搜索条件
                from sqlalchemy import or_
                
                search_conditions = [
                    or_(
                        Account.name.ilike(f"%{keyword}%"),
                        Account.description.ilike(f"%{keyword}%")
                    )
                ]
                
                print(f"搜索条件: keyword ILIKE '%{keyword}%' in name/description")
                
                # 查询总数
                count_stmt = select(Account).where(and_(*search_conditions))
                # 打印实际执行的SQL语句
                compiled_count = count_stmt.compile(
                    dialect=db.bind.dialect, 
                    compile_kwargs={"literal_binds": True}
                )
                print(f"COUNT SQL: {str(compiled_count)}")
                
                count_result = await db.execute(count_stmt)
                result_list = count_result.fetchall()
                total = len(result_list)
                
                print(f"找到总记录数: {total}")
                
                # 分页查询
                stmt = (
                    select(Account)
                    .where(and_(*search_conditions))
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                    .order_by(Account.follower_count.desc(), Account.updated_at.desc())
                )
                
                # 打印实际执行的SQL语句
                compiled = stmt.compile(
                    dialect=db.bind.dialect, 
                    compile_kwargs={"literal_binds": True}
                )
                print(f"SEARCH SQL: {str(compiled)}")
                
                print(f"执行分页查询: offset={(page - 1) * page_size}, limit={page_size}")
                print(f"排序: follower_count DESC, updated_at DESC")
                
                result = await db.execute(stmt)
                accounts = result.scalars().all()
                
                print(f"当前页获取记录数: {len(accounts)}")
                if accounts:
                    print("数据样例:")
                    for i, acc in enumerate(accounts[:3]):  # 只打印前3条
                        print(f"  {i+1}. ID={acc.id}, 名称='{acc.name}', 平台='{acc.platform}'")
                
                # 转换为AccountResponse格式
                account_responses = []
                for account in accounts:
                    try:
                        account_response = AccountResponse.model_validate(account)
                        account_responses.append(account_response)
                    except Exception as e:
                        print(f"转换账号数据失败: {e}")
                        continue
                
                return SearchResult(
                    accounts=account_responses,
                    total=total,
                    page=page,
                    page_size=page_size,
                    has_more=(page * page_size) < total
                )
                
        except Exception as e:
            print(f"全局搜索异常: {str(e)}")
            logger.error(f"全局搜索失败: {e}")
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

    def get_supported_platforms(self) -> List[str]:
        """获取所有支持的平台列表"""
        platforms = list(self._adapters.keys())
        return platforms

    def get_platform_display_name(self, platform: str) -> str:
        """获取平台显示名称"""
        return self._adapters[platform].platform_name


    async def get_articles_by_platform_id(self, platform: str, account_id: str):
        adapter = self.get_adapter(platform)
        if adapter and adapter.is_enabled:
            try:
                articles = await adapter.get_all_articles_by_account_id(account_id)
                return articles
            except Exception as e:
                logger.error(f"从平台获取账号信息失败: {e}")
                return None

    async def get_articles_by_account(self, db: AsyncSession, account_id: str, platform: str, page: int, page_size: int):

        # 获取账号信息
        account = await self.get_account_by_platform_id(platform, account_id)
        if account:
            articles = await self.get_articles_by_platform_id(platform, account_id)
            if articles:
                result = []  # 创建新列表存储结果
                for article in articles:
                    article_response = ArticleWithAccount(
                        id=article.id,
                        account_id=article.account_id,
                        title=article.title,
                        url=article.url,
                        content=article.content,
                        summary=article.summary,
                        publish_time=article.publish_time,
                        publish_timestamp=article.publish_timestamp,
                        images=article.images,
                        details=article.details,
                        created_at=article.created_at,
                        updated_at=article.updated_at,
                        image_count=article.image_count,
                        has_images=article.has_images,
                        thumbnail_url=article.thumbnail_url,
                        account_name=account.name,
                        account_platform=account.platform,
                        account_avatar_url=account.avatar_url,
                        platform_display_name=account.platform_display_name
                    )
                    result.append(article_response)  # 添加到新列表
                logger.info(f"""组装ArticleWithAccount返回结果完成""")
                return result  # 返回新列表
            return articles
        else:
            logger.error(f"获取账号信息失败: {account_id}")
            return None
    

    async def get_article_detail(self, article_id: str, platform: str):
        adapter = self.get_adapter(platform)
        if adapter and adapter.is_enabled:
            try:
                article = await adapter.get_article_detail(article_id)
                return article
            except Exception as e:
                logger.error(f"从平台获取文章详情失败: {e}")
                return None
    
    async def get_account_article_stats(self, account_id: str, platform: str):
        adapter = self.get_adapter(platform)
        if adapter and adapter.is_enabled:
            try:
                stats = await adapter.get_account_article_stats(account_id)
                return stats
            except Exception as e:
                logger.error(f"从平台获取账号文章统计信息失败: {e}")
                return None
    

    async def add_account(self, platform, mp_name: str, mp_cover: Optional[str] = None, mp_id: Optional[str] = None, 
                   avatar: Optional[str] = None, mp_intro: Optional[str] = None) -> Optional[AccountResponse]:
        adapter = self.get_adapter(platform)
        if adapter and adapter.is_enabled:
            try:
                ret = await adapter.add_account(mp_name=mp_name, mp_id=mp_id, avatar=avatar, mp_intro=mp_intro)
                print("====="*10)
                print(f"添加账号返回结果: {ret}")
                print("====="*10)
                return ret
            except Exception as e:
                logger.error(f"添加账号失败: {e}")
                return None
    

    async def get_id_by_faker_id(self, faker_id: str, platform: str):
        """
        根据faker_id查询账号的id
        """
        adapter = self.get_adapter(platform)
        if adapter and adapter.is_enabled:
            try:
                ret = await adapter.get_id_by_faker_id(faker_id)
                return ret
            except Exception as e:
                logger.error(f"根据faker_id查询账号的id失败: {e}")
                return None

# 创建全局搜索服务实例
search_service = SearchService()
