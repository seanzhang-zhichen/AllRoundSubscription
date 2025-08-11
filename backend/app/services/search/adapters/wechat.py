"""
微信公众号平台适配器
"""
from datetime import datetime
from re import A
from typing import List, Optional, Dict, Any
from app.services.search.base import PlatformAdapter, PlatformSearchResult
from app.models.account import Platform
from app.services.search.adapters.wechat_api import WeChatRSSAPI
from app.services.search.adapters.wechat_db import WechatMySQLDB

from app.core.logging import get_logger
from app.schemas.account import AccountResponse
from app.schemas.article import ArticleResponse

logger = get_logger(__name__)


class WeChatAdapter(PlatformAdapter):
    """微信公众号平台适配器"""
    
    def __init__(self):
        super().__init__(Platform.WECHAT)
        self.wechat_api = WeChatRSSAPI()
        self.wechat_db = WechatMySQLDB()

    @property
    def platform_name(self) -> str:
        """平台名称"""
        return "微信公众号"
    
    @property
    def is_enabled(self) -> bool:
        """是否启用该平台"""
        return True
    
    async def search_accounts(
        self, 
        keyword: str, 
        page: int = 1, 
        page_size: int = 10
    ) -> PlatformSearchResult:
        """
        搜索微信公众号
        
        Args:
            keyword: 搜索关键词
            page: 页码
            page_size: 每页大小
            
        Returns:
            PlatformSearchResult: 平台搜索结果
        """
        
        search_ret = self.wechat_api.search_accounts(keyword, page, page_size)
        
        if search_ret["success"]:
            accounts = search_ret["data"]["list"]
            account_response_list = []
            for account in accounts:
                print(f"account: {account}")
                account_response = AccountResponse(
                    id=account["fakeid"],
                    platform=self.platform.value,
                    account_id=account["fakeid"],
                    avatar_url=account["round_head_img"],
                    description=account["signature"],
                    name=account["nickname"],
                    platform_display_name=self.platform_name,
                    follower_count=0,
                    details={},
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                account_response_list.append(account_response)

            total = search_ret["data"]["total"]
            result = PlatformSearchResult(
                platform=self.platform.value,
                accounts=account_response_list,
                total=total,
                success=True,
                error_message=None
            )
            return result
        else:
            logger.error(f"微信公众号搜索API返回值异常: {search_ret}")
            return PlatformSearchResult(
                platform=self.platform.value,
                accounts=[],
                total=0,
                success=False,
                error_message=search_ret["微信搜索账号API返回值异常"]
            )
    
    async def get_account_info(self, account_id: str) -> Optional[Dict[str, Any]]:
        """
        获取微信公众号详细信息
        
        Args:
            account_id: 公众号ID
            
        Returns:
            Optional[Dict[str, Any]]: 公众号信息，如果不存在返回None
        """
        account_info = self.wechat_db.get_account_info(account_id)

        if account_info["success"]:
            account_response = AccountResponse(
                id=account_info["data"]["id"],
                platform=self.platform.value,
                account_id=account_info["data"]["id"],
                avatar_url=account_info["data"]["mp_cover"],
                description=account_info["data"]["mp_intro"],
                name=account_info["data"]["mp_name"],
                platform_display_name=self.platform_name,
                follower_count=0,
                details={},
                created_at=account_info["data"]["created_at"],
                updated_at=account_info["data"]["created_at"]
            )
            return account_response
        else:
            logger.error(f"微信公众号信息获取API返回值异常: {account_info}")
            return None


    async def get_all_accounts(self) -> List[Dict[str, Any]]:
        """
        获取所有已收录的微信公众号
        """
        ret = self.wechat_db.get_all_accounts()
        result = []
        if ret["success"]:
            for account in ret["data"]:
                account_response = AccountResponse(
                    id=account["id"],
                    platform=self.platform.value,
                    account_id=account.get("id", ""),
                    avatar_url=account.get("mp_cover", ""),
                    description=account.get("mp_intro", ""),
                    name=account.get("mp_name", ""),
                    platform_display_name=self.platform_name,
                    follower_count=0,
                    details={},
                    created_at=account.get("created_at", ""),
                    updated_at=account.get("created_at", "")
                )
                result.append(account_response)
            return result
        else:
            logger.error(f"获取所有微信公众号API返回值异常: {ret}")
            return []



    async def get_all_articles_by_account_id(self, account_id: str):
        result = []
        ret = self.wechat_db.get_all_articles(account_id)
        logger.info(f"""获取所有微信公众号文章返回： {ret['success']}""")
        if ret["success"]:
            for article in ret["data"]:
                article_response = ArticleResponse(
                    id=article["id"],
                    account_id=article["mp_id"],
                    title=article["title"][:100],
                    url=article["url"],
                    content=article["content"],
                    summary=article.get("summary", ""),
                    publish_time=article["publish_time"],
                    publish_timestamp=article["publish_time"],
                    images=[article["pic_url"]] if article["pic_url"] else [],
                    details={},
                    created_at=article["created_at"],
                    updated_at=article["updated_at"],
                    image_count=1,
                    has_images=True,
                    thumbnail_url=article["pic_url"]
                )
                result.append(article_response)
            logger.info("组装返回结果完成")
            
            return result
        else:
            logger.error(f"获取所有微信公众号文章API返回值异常: {ret}")
            return []


    async def get_article_detail(self, article_id: str) -> Optional[Dict[str, Any]]:
        """
        获取微信公众号文章详情
        """
        article = self.wechat_db.get_article_detail(article_id)
        if article["success"]:
            article_response = ArticleResponse(
                id=article["data"]["id"],
                account_id=article["data"]["mp_id"],
                title=article["data"]["title"],
                url=article["data"]["url"],
                content=article["data"]["content"],
                summary=article.get("summary", ""),
                publish_time=article["data"]["publish_time"],
                publish_timestamp=article["data"]["publish_time"],
                images=[article["data"]["pic_url"]] if article["data"]["pic_url"] else [],
                details={},
                created_at=article["data"]["created_at"],
                updated_at=article["data"]["updated_at"],
                image_count=1,
                has_images=True,
                thumbnail_url=article["data"]["pic_url"]
            )
            return article_response
        else:
            return None

    async def get_account_article_stats(self, account_id: str) -> Dict[str, Any]:
        """
        获取微信公众号账号文章统计信息
        """
        ret = self.wechat_db.get_account_article_stats(account_id)
        if ret["success"]:
            return ret["data"]
        else:
            return None

    async def add_account(self, mp_name: str, mp_cover: Optional[str] = None, mp_id: Optional[str] = None, 
                   avatar: Optional[str] = None, mp_intro: Optional[str] = None) -> Optional[AccountResponse]:
        """
        添加微信公众号账号
        """
        ret = self.wechat_api.add_account(mp_name=mp_name, mp_id=mp_id, avatar=avatar, mp_intro=mp_intro)
        print("====="*10)
        print(f"添加账号: {ret}")
        print("====="*10)
        if ret["success"]:
            account_info = ret["data"]
            account_response = AccountResponse(
                id=account_info["id"],
                platform=self.platform.value,
                account_id=account_info["id"],
                avatar_url=account_info["mp_cover"],
                description=account_info["mp_intro"],
                name=account_info["mp_name"],
                platform_display_name=self.platform_name,
                follower_count=0,
                details={},
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            return account_response
        else:
            return None


    async def get_id_by_faker_id(self, faker_id: str):
        """
        根据faker_id查询账号的id
        """
        ret = self.wechat_db.get_id_by_faker_id(faker_id)
        if ret["success"]:
            return ret["data"]
        else:
            return None


    def normalize_account_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化微信公众号数据格式
        
        Args:
            raw_data: 原始公众号数据
            
        Returns:
            Dict[str, Any]: 标准化后的账号数据
        """
        return {
            "name": raw_data.get("mp_name", ""),
            "platform": self.platform.value,
            "account_id": raw_data.get("id", ""),
            "avatar_url": raw_data.get("mp_cover", ""),
            "description": raw_data.get("mp_intro", ""),
            "follower_count": 0,  # 微信公众号不公开粉丝数
            "details": {
                "qr_code": raw_data.get("qr_code", ""),
                "verify_info": raw_data.get("verify_info", ""),
                "original_data": raw_data
            },
            "platform_display_name": self.platform_name
        }