import os
import requests
import traceback
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)




class WeChatRSSAPI:
    def __init__(self):
        """初始化API客户端

        Args:
            base_url: API服务基础URL
            username: 登录用户名
            password: 登录密码
        """
        self.base_url = settings.WECHAT_RSS_API_URL
        self.username = settings.WECHAT_RSS_API_USERNAME
        self.password = settings.WECHAT_RSS_API_PASSWORD
        self.token = None
        self.headers = {"Content-Type": "application/json"}
        self.is_login = False
        logger.info(f"初始化API客户端: {self.base_url}")
    
    def ensure_login(self) -> bool:
        """确保已登录
        
        Returns:
            bool: 是否已登录成功
        """
        if not self.is_login:
            logger.info("未登录，尝试登录...")
            login_result = self.login()
            if not login_result:
                logger.error("登录失败，无法进行后续操作")
                return False
            self.is_login = True
            return True
        else:
            # 验证当前 token 是否有效
            logger.debug("已登录，验证 token 有效性")
            token_valid = self.verify_token()
            if not token_valid:
                logger.warning("当前 token 已失效，尝试重新登录")
                login_result = self.login()
                if not login_result:
                    logger.error("重新登录失败，无法进行后续操作")
                    return False
                self.is_login = True
            return True
    
    def verify_token(self) -> bool:
        """验证当前 token 是否有效
        
        Returns:
            bool: token 是否有效
        """
        try:
            if not self.token:
                logger.warning("没有 token，无法验证")
                return False
                
            verify_url = f"{self.base_url}/api/v1/wx/auth/verify"
            logger.info(f"验证 token: GET {verify_url}")
            
            response = requests.get(verify_url, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") == 0 and "data" in result and result["data"].get("is_valid"):
                logger.info(f"✅ token 验证成功，用户: {result['data'].get('username')}")
                return True
            else:
                logger.warning("❌ token 已失效或验证失败")
                return False
                
        except requests.exceptions.HTTPError as e:
            logger.error(f"token 验证请求 HTTP 错误: {e}")
            logger.error(f"响应内容: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"token 验证请求异常: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def login(self) -> bool:
        """登录并获取认证令牌

        Returns:
            bool: 登录是否成功
        """
        try:
            login_url = f"{self.base_url}/api/v1/wx/auth/login"
            # 使用表单数据格式提交
            data = {"username": self.username, "password": self.password}
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            
            logger.info(f"尝试登录: POST {login_url}")
            response = requests.post(login_url, data=data, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if "access_token" in result:
                self.token = result["access_token"]
                self.headers["Authorization"] = f"Bearer {self.token}"
                logger.info("登录成功，获取到令牌")
                return True
            elif "data" in result and "access_token" in result["data"]:
                self.token = result["data"]["access_token"]
                self.headers["Authorization"] = f"Bearer {self.token}"
                logger.info("登录成功，获取到令牌")
                return True
            else:
                logger.error(f"登录失败: {result}")
                return False
                
        except requests.exceptions.HTTPError as e:
            logger.error(f"登录请求HTTP错误: {e}")
            logger.error(f"响应内容: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"登录请求异常: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def get_article_list(self, mp_id: Optional[str] = None, offset: int = 0, limit: int = 5, 
                     status: Optional[str] = None, search: Optional[str] = None) -> Dict[str, Any]:
        """获取微信公众号文章列表
        
        Args:
            mp_id: 可选的公众号ID，如不提供则不进行筛选
            offset: 分页偏移量，默认为0
            limit: 每页数量，默认为5，最大为100
            status: 可选的文章状态过滤
            search: 可选的搜索关键词
            
        Returns:
            Dict[str, Any]: 接口响应结果
        """
        # 确保已登录
        if not self.ensure_login():
            logger.error("未登录，无法获取文章列表")
            return {
                "success": False,
                "data": []
            }
            
        try:
            # 构建请求参数
            params = {}
            if mp_id is not None:
                params["mp_id"] = str(mp_id)  # 确保转换为字符串
            params["offset"] = offset
            params["limit"] = limit
            if status is not None:
                params["status"] = status
            if search is not None:
                params["search"] = search
                
            # 构建请求URL
            url = f"{self.base_url}/api/v1/wx/articles"
            
            # 发送请求
            logger.info(f"获取文章列表: POST {url} 参数: {params}")
            response = requests.post(url, params=params, headers=self.headers)
            status_code = response.status_code
            
            result = {
                "success": True,
                "data": []
            }
            if 200 <= status_code < 300:
                ret = response.json()
                article_list = ret["data"]["list"]
                article_count = len(article_list)
                logger.info(f"✅ 成功获取文章列表，共 {article_count} 条文章")
                result["data"] = article_list
            else:
                result["success"] = False
                logger.warning(f"❌ 获取文章列表失败: {status_code} - {response.text}")
                
            return result
            
        except Exception as e:
            logger.error(f"获取文章列表出错: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "data": []
            }
    
    def get_all_articles(self, mp_id: Optional[str] = None, status: Optional[str] = None, 
                         search: Optional[str] = None, batch_size: int = 100) -> Dict[str, Any]:
        """获取所有微信公众号文章（自动处理分页）
        
        Args:
            mp_id: 可选的公众号ID，如不提供则不进行筛选
            status: 可选的文章状态过滤
            search: 可选的搜索关键词
            batch_size: 每批次获取的文章数量，默认为100
            
        Returns:
            Dict[str, Any]: 包含所有文章的结果
        """
        logger.info("开始获取所有文章...")
        
        if not self.ensure_login():
            logger.error("未登录，无法获取所有文章")
            return {
                "success": False,
                "data": [],
                "total": 0
            }
        
        all_articles = []
        offset = 0
        has_more = True
        total_count = 0
        
        try:
            # 循环获取所有文章
            while has_more:
                # 获取当前批次的文章
                result = self.get_article_list(
                    mp_id=mp_id,
                    offset=offset,
                    limit=batch_size,
                    status=status,
                    search=search
                )
                
                if not result["success"]:
                    logger.error(f"获取文章批次失败，中断获取（已获取 {len(all_articles)} 条）")
                    return {
                        "success": False,
                        "data": all_articles,
                        "total": len(all_articles)
                    }
                
                # 解析当前批次结果
                current_batch = result["data"]
                batch_size_actual = len(current_batch)
                
                # 更新总数
                if offset == 0 and "total" in result["data"]:
                    total_count = len(result["data"])
                    logger.info(f"文章总数: {total_count}")
                
                # 添加到结果列表
                all_articles.extend(current_batch)
                
                # 是否继续获取下一批
                if batch_size_actual < batch_size:
                    has_more = False
                else:
                    offset += batch_size
                
                logger.info(f"已获取 {len(all_articles)} 条文章，继续: {has_more}")
            
            logger.info(f"✅ 成功获取所有文章，共 {len(all_articles)} 条")
            return {
                "success": True,
                "data": all_articles,
                "total": len(all_articles)
            }
            
        except Exception as e:
            logger.error(f"获取所有文章出错: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "data": all_articles,
                "total": len(all_articles)
            }
            
    def search_accounts(self, keyword: str, offset: int = 0, limit: int = 5) -> Dict[str, Any]:
        """搜索微信公众号
        
        Args:
            keyword: 搜索关键词
            offset: 分页偏移量，默认为0
            limit: 每页数量，默认为5
            
        Returns:
            Dict[str, Any]: 搜索结果
        """
        # 确保已登录
        if not self.ensure_login():
            logger.error("未登录，无法搜索公众号")
            return {
                "success": False,
                "data": {
                    "list": [],
                    "total": 0
                }
            }
            
        try:
            # 构建请求URL（包含路径参数）
            url = f"{self.base_url}/api/v1/wx/mps/search/{keyword}"
            
            # 构建请求参数
            params = {
                "offset": offset,
                "limit": limit
            }
            
            # 发送GET请求
            logger.info(f"搜索公众号: GET {url} 参数: {params}")
            response = requests.get(url, params=params, headers=self.headers)
            status_code = response.status_code
            
            result = {
                "success": True,
                "data": {
                    "list": [],
                    "total": 0
                }
            }
            
            if 200 <= status_code < 300:
                ret = response.json()
                
                if "data" in ret and "list" in ret["data"]:
                    accounts = ret["data"]["list"]
                    account_count = len(accounts)
                    total = ret["data"].get("total", account_count)
                    
                    logger.info(f"✅ 成功搜索公众号，关键词: {keyword}，找到 {account_count} 个结果")
                    
                    result["data"]["list"] = accounts
                    result["data"]["total"] = total
                    result["data"]["page"] = {
                        "limit": limit,
                        "offset": offset
                    }
                else:
                    logger.warning(f"搜索公众号返回格式异常: {ret}")
            else:
                result["success"] = False
                logger.warning(f"❌ 搜索公众号失败: {status_code} - {response.text}")
                
            return result
            
        except Exception as e:
            logger.error(f"搜索公众号出错: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "data": {
                    "list": [],
                    "total": 0
                },
                "error": str(e)
            }

    def get_account_info(self, mp_id: str) -> Dict[str, Any]:
        """获取微信公众号详情
        
        Args:
            mp_id: 公众号ID
            
        Returns:
            Dict[str, Any]: 公众号详情信息
        """
        # 确保已登录
        if not self.ensure_login():
            logger.error("未登录，无法获取公众号详情")
            return {
                "success": False,
                "data": {},
                "error": "未登录"
            }
            
        try:
            # 构建请求URL
            url = f"{self.base_url}/api/v1/wx/mps/{mp_id}"
            
            # 发送GET请求
            logger.info(f"获取公众号详情: GET {url}")
            response = requests.get(url, headers=self.headers)
            status_code = response.status_code
            
            result = {
                "success": True,
                "data": {}
            }
            
            if 200 <= status_code < 300:
                ret = response.json()
                
                if "data" in ret:
                    account_info = ret["data"]
                    logger.info(f"✅ 成功获取公众号详情: {account_info['mp_name'] if 'mp_name' in account_info else mp_id}")
                    result["data"] = account_info
                else:
                    logger.warning(f"获取公众号详情返回格式异常: {ret}")
            else:
                result["success"] = False
                logger.warning(f"❌ 获取公众号详情失败: {status_code} - {response.text}")
                result["error"] = f"请求失败 ({status_code})"
                
            return result
            
        except Exception as e:
            logger.error(f"获取公众号详情出错: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "data": {},
                "error": str(e)
            }

    def get_all_accounts(self, keyword: Optional[str] = None, batch_size: int = 100) -> Dict[str, Any]:
        """获取所有微信公众号列表
        
        Args:
            keyword: 可选的搜索关键词
            batch_size: 每批次获取的公众号数量，默认为100
            
        Returns:
            Dict[str, Any]: 包含所有公众号的结果
        """
        # 确保已登录
        if not self.ensure_login():
            logger.error("未登录，无法获取所有公众号")
            return {
                "success": False,
                "data": [],
                "total": 0
            }
        
        all_accounts = []
        offset = 0
        has_more = True
        total_count = 0
        
        try:
            # 循环获取所有公众号
            while has_more:
                # 构建请求URL
                url = f"{self.base_url}/api/v1/wx/mps"
                
                # 构建请求参数
                params = {
                    "offset": offset,
                    "limit": batch_size
                }
                
                # 如果有关键词，添加到请求参数
                if keyword:
                    params["kw"] = keyword
                
                # 发送GET请求
                logger.info(f"获取公众号列表: GET {url} 参数: {params}")
                response = requests.get(url, params=params, headers=self.headers)
                status_code = response.status_code
                
                if 200 <= status_code < 300:
                    ret = response.json()
                    
                    if "data" in ret and "list" in ret["data"]:
                        current_batch = ret["data"]["list"]
                        batch_size_actual = len(current_batch)
                        
                        # 更新总数
                        if offset == 0 and "total" in ret["data"]:
                            total_count = ret["data"]["total"]
                            logger.info(f"公众号总数: {total_count}")
                        
                        # 添加到结果列表
                        all_accounts.extend(current_batch)
                        
                        # 是否继续获取下一批
                        if batch_size_actual < batch_size:
                            has_more = False
                        else:
                            offset += batch_size
                        
                        logger.info(f"已获取 {len(all_accounts)} 个公众号，继续: {has_more}")
                    else:
                        logger.warning(f"获取公众号列表返回格式异常: {ret}")
                        has_more = False
                else:
                    logger.warning(f"❌ 获取公众号列表失败: {status_code} - {response.text}")
                    has_more = False
            
            logger.info(f"✅ 成功获取所有公众号，共 {len(all_accounts)} 个")
            return {
                "success": True,
                "data": all_accounts,
                "total": len(all_accounts)
            }
            
        except Exception as e:
            logger.error(f"获取所有公众号出错: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "data": all_accounts,
                "total": len(all_accounts),
                "error": str(e)
            }


    def get_article_detail(self, article_id: str, content: bool = False) -> Dict[str, Any]:
        """获取文章详情
        
        Args:
            article_id: 文章ID
            content: 是否获取文章内容，默认为 False
            
        Returns:
            Dict[str, Any]: 文章详情
        """
        # 确保已登录
        if not self.ensure_login():
            logger.error("未登录，无法获取文章详情")
            return {
                "success": False,
                "data": {},
                "error": "未登录"
            }
        
        try:
            # 构建请求URL
            url = f"{self.base_url}/api/v1/wx/articles/{article_id}"
            params = { "content": content }
            
            # 发送GET请求
            logger.info(f"获取文章详情: GET {url} params: {params}")
            response = requests.get(url, params=params, headers=self.headers)
            status_code = response.status_code
            
            result = {
                "success": True,
                "data": {}
            }
            
            if 200 <= status_code < 300:
                ret = response.json()
                
                if ret.get("code") == 0:
                    if "data" in ret:
                        article_detail = ret["data"]
                        logger.info(f"✅ 成功获取文章详情: {article_id}")
                        result["data"] = article_detail
                    else:
                        logger.warning(f"获取文章详情返回格式异常: {ret}")
                else:
                    result["success"] = False
                    logger.warning(f"获取文章详情失败: {status_code} - {ret.get('message')}")
                    result["error"] = ret.get('message')

            else:
                result["success"] = False
                logger.warning(f"❌ 获取文章详情失败: {status_code} - {response.text}")
                result["error"] = f"请求失败 ({status_code})"
                
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取文章详情请求出错: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "data": {},
                "error": str(e)
            }


    def get_account_article_stats(self, mp_id: str) -> Dict[str, Any]:
        """获取最新文章时间和文章数量统计
        
        Args:
            mp_id: 公众号ID
            
        Returns:
            Dict[str, Any]: 最新文章时间和文章数量统计
        """
        logger.info("开始获取所有文章...")
        
        if not self.ensure_login():
            logger.error("未登录，无法获取所有文章")
            return {
                "success": False,
                "data": {}
            }
        
        all_articles = []
        offset = 0
        total_count = 0
        batch_size = 1
        status = 1
        search = None
        
        try:
            # 循环获取所有文章

            result = self.get_article_list(
                mp_id=mp_id,
                offset=offset,
                limit=batch_size,
                status=status,
                search=search
            )
            
            if not result["success"]:
                logger.error(f"获取文章批次失败，中断获取（已获取 {len(all_articles)} 条）")
                return {
                    "success": False,
                    "data": {}
                }
            
            # 解析当前批次结果
            current_batch = result["data"]
            batch_size_actual = len(current_batch)
            
            # 更新总数
            if offset == 0 and "total" in result["data"]:
                total_count = len(result["data"])
                logger.info(f"文章总数: {total_count}")
            
            # 添加到结果列表
            all_articles.extend(current_batch)

            logger.info(f"已获取 {len(all_articles)} 条文章")


        except Exception as e:
            logger.error(f"获取文章出错: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "data": {}
            }


        # 获取最新文章时间和文章数量统计
        if all_articles:
            publish_time = all_articles[0].get('publish_time')
            latest_article_time = datetime.fromtimestamp(publish_time) if publish_time else None
            article_count = len(all_articles)
        else:
            latest_article_time = None
            article_count = 0

        return {
            "success": True,
            "data": {
                "latest_article_time": latest_article_time,
                "article_count": article_count
            }
        }
