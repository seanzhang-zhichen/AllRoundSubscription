"""
微博平台适配器
"""
import asyncio
import aiohttp
from typing import Optional, Dict, Any
from app.services.search.base import PlatformAdapter, PlatformSearchResult
from app.services.search.exceptions import (
    PlatformAPIException, RateLimitException, AuthenticationException,
    SearchTimeoutException, DataParsingException
)
from app.models.account import Platform
from app.core.config import settings


class WeiboAdapter(PlatformAdapter):
    """微博平台适配器"""
    
    def __init__(self):
        super().__init__(Platform.WEIBO)
        # 微博API配置
        self._app_key = getattr(settings, 'WEIBO_APP_KEY', '')
        self._app_secret = getattr(settings, 'WEIBO_APP_SECRET', '')
        self._access_token = getattr(settings, 'WEIBO_ACCESS_TOKEN', '')
        
        # API端点
        self._base_url = "https://api.weibo.com/2"
        self._search_url = f"{self._base_url}/search/suggestions/users.json"
        self._user_info_url = f"{self._base_url}/users/show.json"
        
        # 请求配置
        self._timeout = 10
        self._max_retries = 3
        self._retry_delay = 1
    
    @property
    def platform_name(self) -> str:
        """平台名称"""
        return "微博"
    
    @property
    def is_enabled(self) -> bool:
        """是否启用该平台"""
        # 检查必要的配置是否完整
        return bool(self._app_key and self._access_token)
    
    async def search_accounts(
        self, 
        keyword: str, 
        page: int = 1, 
        page_size: int = 20
    ) -> PlatformSearchResult:
        """
        搜索微博用户
        
        Args:
            keyword: 搜索关键词
            page: 页码
            page_size: 每页大小
            
        Returns:
            PlatformSearchResult: 平台搜索结果
        """
        if not self.is_enabled:
            return PlatformSearchResult(
                platform=self.platform.value,
                accounts=[],
                total=0,
                success=False,
                error_message="微博API配置不完整"
            )
        
        try:
            # 构建请求参数
            params = {
                "q": keyword,
                "count": min(page_size, 50),  # 微博API限制单次最多50个
                "page": page,
                "access_token": self._access_token
            }
            
            # 发送API请求
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self._timeout)) as session:
                response_data = await self._make_request_with_retry(session, self._search_url, params)
            
            # 解析响应数据
            if not response_data:
                return PlatformSearchResult(
                    platform=self.platform.value,
                    accounts=[],
                    total=0,
                    success=False,
                    error_message="API返回空数据"
                )
            
            # 处理微博API响应格式
            users = response_data.get("users", [])
            total_count = len(users)  # 微博搜索API不返回总数，使用当前结果数
            
            # 标准化账号数据
            normalized_accounts = []
            for user_data in users:
                try:
                    normalized_account = self.normalize_account_data(user_data)
                    normalized_accounts.append(normalized_account)
                except Exception as e:
                    # 单个账号数据解析失败不影响整体结果
                    continue
            
            return PlatformSearchResult(
                platform=self.platform.value,
                accounts=normalized_accounts,
                total=total_count,
                success=True
            )
            
        except AuthenticationException as e:
            return PlatformSearchResult(
                platform=self.platform.value,
                accounts=[],
                total=0,
                success=False,
                error_message=f"认证失败: {str(e)}"
            )
        except RateLimitException as e:
            return PlatformSearchResult(
                platform=self.platform.value,
                accounts=[],
                total=0,
                success=False,
                error_message=f"API限流: {str(e)}"
            )
        except SearchTimeoutException as e:
            return PlatformSearchResult(
                platform=self.platform.value,
                accounts=[],
                total=0,
                success=False,
                error_message=f"搜索超时: {str(e)}"
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
        获取微博用户详细信息
        
        Args:
            account_id: 微博用户ID
            
        Returns:
            Optional[Dict[str, Any]]: 用户信息，如果不存在返回None
        """
        if not self.is_enabled:
            return None
        
        try:
            params = {
                "uid": account_id,
                "access_token": self._access_token
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self._timeout)) as session:
                response_data = await self._make_request_with_retry(session, self._user_info_url, params)
            
            return response_data
            
        except Exception as e:
            print(f"获取微博用户信息失败: {e}")
            return None
    
    async def _make_request_with_retry(
        self, 
        session: aiohttp.ClientSession, 
        url: str, 
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        带重试机制的API请求
        
        Args:
            session: HTTP会话
            url: 请求URL
            params: 请求参数
            
        Returns:
            Dict[str, Any]: API响应数据
            
        Raises:
            各种搜索异常
        """
        last_exception = None
        
        for attempt in range(self._max_retries):
            try:
                async with session.get(url, params=params) as response:
                    # 检查HTTP状态码
                    if response.status == 401:
                        raise AuthenticationException(self.platform.value, "访问令牌无效或过期")
                    elif response.status == 429:
                        retry_after = int(response.headers.get('Retry-After', 60))
                        raise RateLimitException(self.platform.value, retry_after)
                    elif response.status != 200:
                        raise PlatformAPIException(
                            f"API请求失败，状态码: {response.status}",
                            self.platform.value,
                            response.status
                        )
                    
                    # 解析JSON响应
                    try:
                        data = await response.json()
                    except Exception as e:
                        raise DataParsingException(self.platform.value, "响应数据", "JSON解析失败")
                    
                    # 检查微博API错误
                    if "error" in data:
                        error_code = data.get("error_code", "unknown")
                        error_msg = data.get("error", "未知错误")
                        
                        if error_code in ["21327", "21332"]:  # 访问令牌相关错误
                            raise AuthenticationException(self.platform.value, error_msg)
                        elif error_code == "10023":  # 请求过于频繁
                            raise RateLimitException(self.platform.value)
                        else:
                            raise PlatformAPIException(error_msg, self.platform.value, error_code)
                    
                    return data
                    
            except asyncio.TimeoutError:
                last_exception = SearchTimeoutException(self.platform.value, self._timeout)
            except (AuthenticationException, RateLimitException, PlatformAPIException, DataParsingException):
                # 这些异常不需要重试
                raise
            except Exception as e:
                last_exception = e
            
            # 重试前等待
            if attempt < self._max_retries - 1:
                await asyncio.sleep(self._retry_delay * (attempt + 1))
        
        # 所有重试都失败了
        if last_exception:
            raise last_exception
        else:
            raise PlatformAPIException("请求失败", self.platform.value)
    
    def normalize_account_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化微博用户数据格式
        
        Args:
            raw_data: 原始用户数据
            
        Returns:
            Dict[str, Any]: 标准化后的账号数据
        """
        from datetime import datetime
        
        return {
            "id": hash(str(raw_data.get("id", ""))) % 1000000,  # 生成模拟ID
            "name": raw_data.get("screen_name", ""),
            "platform": self.platform.value,
            "account_id": str(raw_data.get("id", "")),
            "avatar_url": raw_data.get("profile_image_url", ""),
            "description": raw_data.get("description", ""),
            "follower_count": raw_data.get("followers_count", 0),
            "details": {
                "verified": raw_data.get("verified", False),
                "verified_type": raw_data.get("verified_type", -1),
                "verified_reason": raw_data.get("verified_reason", ""),
                "location": raw_data.get("location", ""),
                "url": raw_data.get("url", ""),
                "gender": raw_data.get("gender", ""),
                "statuses_count": raw_data.get("statuses_count", 0),
                "friends_count": raw_data.get("friends_count", 0),
                "created_at": raw_data.get("created_at", ""),
                "original_data": raw_data
            },
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "platform_display_name": self.platform_name
        }