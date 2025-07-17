"""
微信API服务
"""
import httpx
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json

from app.core.config import settings
from app.core.exceptions import BusinessException, ErrorCode
from app.db.redis import get_redis

logger = logging.getLogger(__name__)


class WeChatService:
    """微信服务类"""
    
    def __init__(self):
        self.app_id = settings.WECHAT_APP_ID
        self.app_secret = settings.WECHAT_APP_SECRET
        self.service_app_id = settings.WECHAT_SERVICE_APP_ID
        self.service_app_secret = settings.WECHAT_SERVICE_APP_SECRET
        self.template_id = settings.WECHAT_TEMPLATE_ID
        self.mini_program_app_id = settings.WECHAT_MINI_PROGRAM_APP_ID
        self.mini_program_path = settings.WECHAT_MINI_PROGRAM_PATH
        self.base_url = "https://api.weixin.qq.com"
        self.access_token_key = "wechat_service_access_token"
    
    async def code_to_session(self, code: str) -> Dict[str, Any]:
        """
        通过code换取session_key和openid
        
        Args:
            code: 微信小程序登录时获取的code
            
        Returns:
            包含openid和session_key的字典
            
        Raises:
            BusinessException: 当API调用失败时
        """
        if not self.app_id or not self.app_secret:
            logger.error("微信配置缺失: WECHAT_APP_ID 或 WECHAT_APP_SECRET 未设置")
            raise BusinessException(
                error_code=ErrorCode.PLATFORM_ERROR,
                message="微信配置错误"
            )
        
        url = f"{self.base_url}/sns/jscode2session"
        params = {
            "appid": self.app_id,
            "secret": self.app_secret,
            "js_code": code,
            "grant_type": "authorization_code"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                logger.info(f"调用微信API获取session，code: {code[:10]}...")
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                logger.debug(f"微信API响应: {data}")
                
                # 检查是否有错误
                if "errcode" in data:
                    error_code = data["errcode"]
                    error_msg = data.get("errmsg", "未知错误")
                    
                    logger.error(f"微信API返回错误: {error_code} - {error_msg}")
                    
                    # 根据错误码返回友好的错误信息
                    error_messages = {
                        40013: "无效的AppID",
                        40014: "无效的AppSecret",
                        40029: "无效的code",
                        45011: "API调用太频繁",
                        40226: "高风险等级用户，小程序登录拦截"
                    }
                    
                    friendly_message = error_messages.get(error_code, f"微信登录失败: {error_msg}")
                    raise BusinessException(
                        error_code=ErrorCode.INVALID_PARAMS,
                        message=friendly_message
                    )
                
                # 检查必要字段
                if "openid" not in data:
                    logger.error("微信API响应缺少openid字段")
                    raise BusinessException(
                        error_code=ErrorCode.PLATFORM_ERROR,
                        message="微信API响应格式错误"
                    )
                
                logger.info(f"微信登录成功，openid: {data['openid'][:10]}...")
                return {
                    "openid": data["openid"],
                    "session_key": data.get("session_key"),
                    "unionid": data.get("unionid")
                }
                
        except httpx.TimeoutException:
            logger.error("微信API调用超时")
            raise BusinessException(
                error_code=ErrorCode.PLATFORM_ERROR,
                message="微信服务暂时不可用，请稍后重试"
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"微信API HTTP错误: {e.response.status_code}")
            raise BusinessException(
                error_code=ErrorCode.PLATFORM_ERROR,
                message="微信服务异常"
            )
        except Exception as e:
            logger.error(f"微信API调用异常: {str(e)}", exc_info=True)
            raise BusinessException(
                error_code=ErrorCode.PLATFORM_ERROR,
                message="微信登录服务异常"
            )
    
    async def get_user_info(self, access_token: str, openid: str) -> Optional[Dict[str, Any]]:
        """
        获取用户信息（需要用户授权）
        
        Args:
            access_token: 访问令牌
            openid: 用户openid
            
        Returns:
            用户信息字典或None
        """
        url = f"{self.base_url}/sns/userinfo"
        params = {
            "access_token": access_token,
            "openid": openid,
            "lang": "zh_CN"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                if "errcode" in data:
                    logger.warning(f"获取用户信息失败: {data}")
                    return None
                
                return data
                
        except Exception as e:
            logger.error(f"获取用户信息异常: {str(e)}")
            return None
    
    async def get_service_access_token(self) -> Optional[str]:
        """
        获取服务号access_token
        
        Returns:
            access_token或None
        """
        if not self.service_app_id or not self.service_app_secret:
            logger.error("微信服务号配置缺失")
            return None
        
        try:
            # 先从Redis缓存中获取
            redis = await get_redis()
            if redis:
                cached_token = await redis.get(self.access_token_key)
                if cached_token:
                    logger.debug("使用缓存的access_token")
                    return cached_token.decode('utf-8')
            
            # 从微信API获取新的access_token
            url = f"{self.base_url}/cgi-bin/token"
            params = {
                "grant_type": "client_credential",
                "appid": self.service_app_id,
                "secret": self.service_app_secret
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                logger.info("获取微信服务号access_token...")
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                logger.debug(f"微信服务号API响应: {data}")
                
                if "errcode" in data:
                    error_code = data["errcode"]
                    error_msg = data.get("errmsg", "未知错误")
                    logger.error(f"获取access_token失败: {error_code} - {error_msg}")
                    return None
                
                access_token = data.get("access_token")
                expires_in = data.get("expires_in", 7200)
                
                if access_token and redis:
                    # 缓存access_token，提前5分钟过期
                    cache_expire = max(expires_in - 300, 300)
                    await redis.setex(
                        self.access_token_key, 
                        cache_expire, 
                        access_token
                    )
                    logger.info(f"access_token已缓存，过期时间: {cache_expire}秒")
                
                return access_token
                
        except Exception as e:
            logger.error(f"获取access_token异常: {str(e)}")
            return None
    
    async def send_template_message(
        self, 
        openid: str, 
        article_title: str, 
        account_name: str, 
        article_id: int,
        platform_name: str = "未知平台",
        article_url: str = None
    ) -> Dict[str, Any]:
        """
        发送模板消息
        
        Args:
            openid: 用户openid
            article_title: 文章标题
            account_name: 账号名称
            article_id: 文章ID
            platform_name: 平台名称
            
        Returns:
            发送结果
        """
        if not self.template_id:
            logger.error("微信模板ID未配置")
            return {
                "success": False,
                "error": "微信模板ID未配置"
            }
        
        access_token = await self.get_service_access_token()
        if not access_token:
            logger.error("无法获取access_token")
            return {
                "success": False,
                "error": "无法获取微信访问令牌"
            }
        
        try:
            url = f"{self.base_url}/cgi-bin/message/template/send"
            params = {"access_token": access_token}
            
            # 构建消息数据 - 使用更丰富的模板格式
            message_data = {
                "touser": openid,
                "template_id": self.template_id,
                "data": {
                    "first": {
                        "value": f"🔔 您关注的{platform_name}博主有新动态！",
                        "color": "#FF6B35"
                    },
                    "keyword1": {
                        "value": f"📝 {account_name}",
                        "color": "#2E86AB"
                    },
                    "keyword2": {
                        "value": article_title[:60] + ("..." if len(article_title) > 60 else ""),
                        "color": "#333333"
                    },
                    "keyword3": {
                        "value": datetime.now().strftime("%Y年%m月%d日 %H:%M"),
                        "color": "#666666"
                    },
                    "remark": {
                        "value": "💡 点击查看完整内容，不要错过精彩动态！",
                        "color": "#FF6B35"
                    }
                }
            }
            
            # 如果有文章URL，添加到备注中
            if article_url:
                message_data["url"] = article_url
            
            # 如果配置了小程序跳转
            if self.mini_program_app_id:
                message_data["miniprogram"] = {
                    "appid": self.mini_program_app_id,
                    "pagepath": f"{self.mini_program_path}?id={article_id}"
                }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                logger.info(f"发送模板消息给用户: {openid[:10]}...")
                response = await client.post(
                    url, 
                    params=params, 
                    json=message_data
                )
                response.raise_for_status()
                
                result = response.json()
                logger.debug(f"模板消息发送响应: {result}")
                
                if result.get("errcode") == 0:
                    logger.info(f"模板消息发送成功，msgid: {result.get('msgid')}")
                    return {
                        "success": True,
                        "msgid": result.get("msgid"),
                        "message": "推送成功"
                    }
                else:
                    error_code = result.get("errcode")
                    error_msg = result.get("errmsg", "未知错误")
                    
                    # 常见错误处理
                    error_messages = {
                        43004: "用户未关注服务号",
                        40001: "access_token无效",
                        40003: "openid无效",
                        47001: "模板消息数据格式错误",
                        41028: "form_id不正确或者过期",
                        41029: "form_id已被使用",
                        41030: "page不正确"
                    }
                    
                    friendly_message = error_messages.get(
                        error_code, 
                        f"推送失败: {error_msg}"
                    )
                    
                    logger.warning(f"模板消息发送失败: {error_code} - {error_msg}")
                    return {
                        "success": False,
                        "error_code": error_code,
                        "error": friendly_message
                    }
                
        except httpx.TimeoutException:
            logger.error("模板消息发送超时")
            return {
                "success": False,
                "error": "推送服务超时"
            }
        except Exception as e:
            logger.error(f"模板消息发送异常: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"推送服务异常: {str(e)}"
            }
    
    async def send_push_notification(
        self, 
        user_openid: str, 
        article_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        发送推送通知（统一接口）
        
        Args:
            user_openid: 用户openid
            article_data: 文章数据，包含title, account_name, id, platform等
            
        Returns:
            推送结果
        """
        try:
            article_title = article_data.get("title", "新文章")
            account_name = article_data.get("account_name", "未知博主")
            article_id = article_data.get("id")
            platform_name = article_data.get("platform_display_name", "未知平台")
            
            if not article_id:
                logger.error("文章ID缺失")
                return {
                    "success": False,
                    "error": "文章ID缺失"
                }
            
            result = await self.send_template_message(
                openid=user_openid,
                article_title=article_title,
                account_name=account_name,
                article_id=article_id,
                platform_name=platform_name
            )
            
            return result
            
        except Exception as e:
            logger.error(f"发送推送通知异常: {str(e)}")
            return {
                "success": False,
                "error": f"推送异常: {str(e)}"
            }
    
    async def get_template_industry(self) -> Optional[Dict[str, Any]]:
        """
        获取模板消息行业设置
        
        Returns:
            行业设置信息或None
        """
        access_token = await self.get_service_access_token()
        if not access_token:
            return None
        
        try:
            url = f"{self.base_url}/cgi-bin/template/get_industry"
            params = {"access_token": access_token}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                result = response.json()
                
                if result.get("errcode") == 0:
                    return result
                else:
                    logger.warning(f"获取行业设置失败: {result}")
                    return None
                    
        except Exception as e:
            logger.error(f"获取行业设置异常: {str(e)}")
            return None


# 全局微信服务实例
wechat_service = WeChatService()