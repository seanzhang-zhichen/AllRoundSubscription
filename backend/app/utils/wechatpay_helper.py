# -*- coding: utf-8 -*-
import json
import logging
import os
import time
import uuid
from string import ascii_letters, digits
from random import sample
from typing import Dict, Any, Optional, Tuple

from wechatpayv3 import WeChatPay, WeChatPayType, SignType
from app.core.config import settings

# Setup logger for WeChat Pay helper
logger = logging.getLogger(__name__)

class WeChatPayHelper:
    """
    Helper class for WeChat Pay V3 API, using the minibear2021/wechatpayv3 library.
    Provides methods for different payment types and utilities.
    """
    
    def __init__(self):
        """Initialize WeChat Pay V3 client using settings from config."""
        try:
            # Read private key content
            try:
                with open(settings.WXPAY_PRIVATE_KEY_PATH, 'r') as f:
                    private_key_content = f.read()
                with open(settings.WXPAY_PUBLIC_KEY_PATH, 'r') as f:
                    public_key_content = f.read()
            except FileNotFoundError:
                logger.error(f"WeChat Pay private key file not found at: {settings.WXPAY_PRIVATE_KEY_PATH}")
                private_key_content = None
                raise ValueError(f"WeChat Pay private key file not found at: {settings.WXPAY_PRIVATE_KEY_PATH}")
            except Exception as e:
                logger.error(f"Error reading WeChat Pay private key file: {e}")
                private_key_content = None
                raise ValueError(f"Error reading WeChat Pay private key file: {e}")

            # Initialize using WeChatPay class
            self.wxpay = WeChatPay(
                wechatpay_type=WeChatPayType.NATIVE,  # Default to mini program
                mchid=settings.WXPAY_MCHID,
                private_key=private_key_content,  # Pass key content directly
                cert_serial_no=settings.WXPAY_SERIAL_NO,
                apiv3_key=settings.WXPAY_API_V3_KEY,
                appid=settings.WXPAY_APPID,  # Default AppID
                notify_url=settings.WXPAY_NOTIFY_URL,  # Default Notify URL
                cert_dir=settings.WXPAY_PLATFORM_CERT_DIR,  # Dir for platform certs
                logger=logger,
                proxy=None,
                timeout=(10, 30),  # Added explicit timeout settings: 10s for connection, 30s for read
                partner_mode=False,  # Set True for Service Provider mode
                public_key=public_key_content,
                public_key_id=settings.WXPAY_PUBLIC_KEY_ID
            )
            logger.info("WeChatPay (minibear2021) initialized successfully.")
        except ImportError:
            logger.error("WeChat Pay v3 library (minibear2021/wechatpayv3) not found. Please install it.")
            self.wxpay = None
            raise ImportError("WeChat Pay v3 library (minibear2021/wechatpayv3) not found. Please install it.")
        except Exception as e:
            logger.exception(f"Unexpected error initializing WeChatPay (minibear2021): {e}")
            self.wxpay = None
            raise ValueError(f"Failed to initialize WeChat Pay: {e}")

    def _generate_out_trade_no(self) -> str:
        """Generate a unique out_trade_no for WeChat Pay order."""
        # Using the same approach as in example.py for consistency
        return ''.join(sample(ascii_letters + digits, 8))

    def create_jsapi_payment(self, openid: str, amount: int, description: str, 
                           out_trade_no: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
        """
        Create a JSAPI payment for WeChat mini program.
        
        Args:
            openid: User's OpenID in the mini program
            amount: Payment amount in cents (integer)
            description: Order description
            out_trade_no: Optional order number, generated if not provided
            
        Returns:
            Tuple of (status_code, payment_params) where payment_params are ready for wx.requestPayment
        """
        if not self.wxpay:
            logger.error("WeChatPay object not initialized")
            return 500, {"error": "WeChatPay client not initialized"}
            
        # Generate out_trade_no if not provided
        if not out_trade_no:
            out_trade_no = self._generate_out_trade_no()
            
        # Prepare data for WeChat Pay API
        pay_data = {
            'description': description,
            'out_trade_no': out_trade_no,
            'amount': {'total': amount, 'currency': 'CNY'},
            'payer': {'openid': openid}
        }
        
        try:
            # Call WeChat Pay API
            code, message = self.wxpay.pay(
                pay_type=WeChatPayType.JSAPI,
                **pay_data
            )
            
            # Process API response
            if code in range(200, 300):
                try:
                    result = json.loads(message)
                    prepay_id = result.get('prepay_id')
                    if not prepay_id:
                        logger.error(f"WeChat API returned 200 but missing prepay_id. Message: {message}")
                        return code, {"error": "Missing prepay_id in response"}
                        
                    # Generate parameters for frontend
                    timestamp = str(int(time.time()))
                    noncestr = str(uuid.uuid4()).replace('-', '')
                    package = f'prepay_id={prepay_id}'
                    
                    # Sign the parameters - Using exact syntax from example.py
                    sign = self.wxpay.sign(data=[
                        settings.WXPAY_APPID, 
                        timestamp, 
                        noncestr, 
                        package
                    ])
                    
                    # Return the parameters needed by mini program's wx.requestPayment
                    return code, {
                        "appId": settings.WXPAY_APPID,
                        "timeStamp": timestamp,
                        "nonceStr": noncestr,
                        "package": package,
                        "signType": "RSA",
                        "paySign": sign,
                        "out_trade_no": out_trade_no,
                        "prepay_id": prepay_id  # Include for reference
                    }
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse WeChat API response. Message: {message}")
                    return 500, {"error": "Failed to parse WeChat API response"}
            else:
                logger.error(f"WeChat API call failed. Code: {code}, Message: {message}")
                try:
                    error_data = json.loads(message)
                    return code, {"error": error_data.get("message", "WeChat Pay API error")}
                except (json.JSONDecodeError, TypeError):
                    return code, {"error": f"WeChat Pay API error: {message}"}
                    
        except Exception as e:
            logger.exception(f"Exception in create_jsapi_payment: {e}")
            return 500, {"error": f"Internal error: {str(e)}"}

    def create_app_payment(self, amount: int, description: str, 
                         out_trade_no: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
        """
        Create an APP payment for WeChat Pay.
        
        Args:
            amount: Payment amount in cents (integer)
            description: Order description
            out_trade_no: Optional order number, generated if not provided
            
        Returns:
            Tuple of (status_code, payment_params) where payment_params are ready for APP SDK
        """
        if not self.wxpay:
            logger.error("WeChatPay object not initialized")
            return 500, {"error": "WeChatPay client not initialized"}
            
        # Generate out_trade_no if not provided
        if not out_trade_no:
            out_trade_no = self._generate_out_trade_no()
            
        # Prepare data for WeChat Pay API
        pay_data = {
            'description': description,
            'out_trade_no': out_trade_no,
            'amount': {'total': amount, 'currency': 'CNY'}
        }
        
        try:
            # Call WeChat Pay API
            code, message = self.wxpay.pay(
                pay_type=WeChatPayType.APP,
                **pay_data
            )
            
            # Process API response
            if code in range(200, 300):
                try:
                    result = json.loads(message)
                    prepay_id = result.get('prepay_id')
                    if not prepay_id:
                        logger.error(f"WeChat API returned 200 but missing prepay_id. Message: {message}")
                        return code, {"error": "Missing prepay_id in response"}
                        
                    # Generate parameters for APP SDK - Following example.py exactly
                    timestamp = str(int(time.time()))
                    noncestr = str(uuid.uuid4()).replace('-', '')
                    package = "Sign=WXPay"  # Fixed value for APP pay
                    
                    # Sign exactly as it's done in example.py - Note the "data=" parameter name!
                    sign = self.wxpay.sign(data=[
                        settings.WXPAY_APPID,
                        timestamp,
                        noncestr,
                        prepay_id
                    ])
                    
                    # Return the parameters needed by APP SDK - Matching example.py keys exactly
                    return code, {
                        "appid": settings.WXPAY_APPID,
                        "partnerid": settings.WXPAY_MCHID,
                        "prepayid": prepay_id,
                        "package": package,
                        "nonceStr": noncestr,
                        "timestamp": timestamp,
                        "sign": sign,
                        "out_trade_no": out_trade_no
                    }
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse WeChat API response. Message: {message}")
                    return 500, {"error": "Failed to parse WeChat API response"}
            else:
                logger.error(f"WeChat API call failed. Code: {code}, Message: {message}")
                try:
                    error_data = json.loads(message)
                    return code, {"error": error_data.get("message", "WeChat Pay API error")}
                except (json.JSONDecodeError, TypeError):
                    return code, {"error": f"WeChat Pay API error: {message}"}
                    
        except Exception as e:
            logger.exception(f"Exception in create_app_payment: {e}")
            return 500, {"error": f"Internal error: {str(e)}"}

    def create_h5_payment(self, amount: int, description: str, client_ip: str,
                        out_trade_no: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
        """
        Create an H5 payment for WeChat Pay (used in mobile browsers).
        
        Args:
            amount: Payment amount in cents (integer)
            description: Order description
            client_ip: Client IP address
            out_trade_no: Optional order number, generated if not provided
            
        Returns:
            Tuple of (status_code, payment_result) where payment_result contains h5_url for redirect
        """
        if not self.wxpay:
            logger.error("WeChatPay object not initialized")
            return 500, {"error": "WeChatPay client not initialized"}
            
        # Generate out_trade_no if not provided
        if not out_trade_no:
            out_trade_no = self._generate_out_trade_no()
            
        # Prepare data for H5 payment
        pay_data = {
            'description': description,
            'out_trade_no': out_trade_no,
            'amount': {'total': amount, 'currency': 'CNY'},
            'scene_info': {
                'payer_client_ip': client_ip,
                'h5_info': {'type': 'Wap'}
            }
        }
        
        try:
            # Call WeChat Pay API
            code, message = self.wxpay.pay(
                pay_type=WeChatPayType.H5,
                **pay_data
            )
            
            # Process API response
            if code in range(200, 300):
                try:
                    result = json.loads(message)
                    h5_url = result.get('h5_url')
                    if not h5_url:
                        logger.error(f"WeChat API returned 200 but missing h5_url. Message: {message}")
                        return code, {"error": "Missing h5_url in response"}
                    
                    return code, {
                        "h5_url": h5_url,
                        "out_trade_no": out_trade_no
                    }
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse WeChat API response. Message: {message}")
                    return 500, {"error": "Failed to parse WeChat API response"}
            else:
                logger.error(f"WeChat API call failed. Code: {code}, Message: {message}")
                try:
                    error_data = json.loads(message)
                    return code, {"error": error_data.get("message", "WeChat Pay API error")}
                except (json.JSONDecodeError, TypeError):
                    return code, {"error": f"WeChat Pay API error: {message}"}
                    
        except Exception as e:
            logger.exception(f"Exception in create_h5_payment: {e}")
            return 500, {"error": f"Internal error: {str(e)}"}

    def create_miniprog_payment(self, openid: str, amount: int, description: str,
                              out_trade_no: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
        """
        Create a Mini Program payment for WeChat Pay.
        Similar to JSAPI payment but with WeChatPayType.MINIPROG.
        
        Args:
            openid: User's OpenID in the mini program
            amount: Payment amount in cents (integer)
            description: Order description
            out_trade_no: Optional order number, generated if not provided
            
        Returns:
            Tuple of (status_code, payment_params) where payment_params are ready for mini program
        """
        if not self.wxpay:
            logger.error("WeChatPay object not initialized")
            return 500, {"error": "WeChatPay client not initialized"}
            
        # Generate out_trade_no if not provided
        if not out_trade_no:
            out_trade_no = self._generate_out_trade_no()
            
        try:
            # Call WeChat Pay API
            code, message = self.wxpay.pay(
                pay_type=WeChatPayType.MINIPROG,
                description=description,
                out_trade_no=out_trade_no,
                amount={'total': amount},
                payer={'openid': openid}
            )
            # Process API response
            if code in range(200, 300):
                try:
                    result = json.loads(message)
                    prepay_id = result.get('prepay_id')
                    if not prepay_id:
                        logger.error(f"WeChat API returned 200 but missing prepay_id. Message: {message}")
                        return code, {"error": "Missing prepay_id in response"}
                    
                    # Generate parameters for mini program payment
                    timestamp = str(int(time.time()))
                    noncestr = str(uuid.uuid4()).replace('-', '')
                    package = f'prepay_id={prepay_id}'
                    
                    # Sign the parameters - Exact approach from example.py with data= parameter
                    sign = self.wxpay.sign(data=[
                        settings.WXPAY_APPID, 
                        timestamp, 
                        noncestr, 
                        package
                    ])
                    
                    # Return the parameters needed by mini program's wx.requestPayment
                    return code, {
                        "appId": settings.WXPAY_APPID,
                        "timeStamp": timestamp,
                        "nonceStr": noncestr,
                        "package": package,
                        "signType": "RSA",
                        "paySign": sign,
                        "out_trade_no": out_trade_no,
                        "prepay_id": prepay_id  # Include for reference
                    }
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse WeChat API response. Message: {message}")
                    return 500, {"error": "Failed to parse WeChat API response"}
            else:
                logger.error(f"WeChat API call failed. Code: {code}, Message: {message}")
                try:
                    error_data = json.loads(message)
                    return code, {"error": error_data.get("message", "WeChat Pay API error")}
                except (json.JSONDecodeError, TypeError):
                    return code, {"error": f"WeChat Pay API error: {message}"}
                    
        except Exception as e:
            logger.exception(f"Exception in create_miniprog_payment: {e}")
            return 500, {"error": f"Internal error: {str(e)}"}

    def query_order(self, out_trade_no: str) -> Tuple[int, Dict[str, Any]]:
        """
        Query the status of an order by its out_trade_no.
        
        Args:
            out_trade_no: The merchant order number
            
        Returns:
            Tuple of (status_code, query_result)
        """
        if not self.wxpay:
            logger.error("WeChatPay object not initialized")
            return 500, {"error": "WeChatPay client not initialized"}
            
        try:
            # Call WeChat Pay query API
            code, message = self.wxpay.query(out_trade_no=out_trade_no)
            
            # Process API response
            if code in range(200, 300):
                try:
                    result = json.loads(message)
                    return code, result
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse WeChat query response. Message: {message}")
                    return 500, {"error": "Failed to parse query response"}
            else:
                logger.error(f"WeChat query API call failed. Code: {code}, Message: {message}")
                try:
                    error_data = json.loads(message)
                    return code, {"error": error_data.get("message", "WeChat Pay query error")}
                except (json.JSONDecodeError, TypeError):
                    return code, {"error": f"WeChat Pay query error: {message}"}
                    
        except Exception as e:
            logger.exception(f"Exception in query_order: {e}")
            return 500, {"error": f"Internal error: {str(e)}"}

    def close_order(self, out_trade_no: str) -> Tuple[int, Dict[str, Any]]:
        """
        Close an unpaid order.
        
        Args:
            out_trade_no: The merchant order number
            
        Returns:
            Tuple of (status_code, result)
        """
        if not self.wxpay:
            logger.error("WeChatPay object not initialized")
            return 500, {"error": "WeChatPay client not initialized"}
            
        try:
            # Call WeChat Pay close API
            code, message = self.wxpay.close(out_trade_no=out_trade_no)
            
            # Process API response
            if code in range(200, 300):
                return code, {"status": "success"}
            else:
                logger.error(f"WeChat close API call failed. Code: {code}, Message: {message}")
                try:
                    error_data = json.loads(message)
                    return code, {"error": error_data.get("message", "WeChat Pay close error")}
                except (json.JSONDecodeError, TypeError):
                    return code, {"error": f"WeChat Pay close error: {message}"}
                    
        except Exception as e:
            logger.exception(f"Exception in close_order: {e}")
            return 500, {"error": f"Internal error: {str(e)}"}
    
    def process_notification(self, headers: dict, body: bytes) -> Dict[str, Any]:
        """
        Process and verify a notification from WeChat Pay.
        
        Args:
            headers: HTTP headers from the notification request
            body: Raw request body as bytes
            
        Returns:
            Dictionary containing the verified and decrypted notification data,
            or an error dictionary if verification fails
        """
        if not self.wxpay:
            logger.error("WeChatPay object not initialized")
            return {"status": "error", "message": "WeChatPay client not initialized"}
            
        try:
            # Use the library's callback method to verify and decrypt
            notification_data = self.wxpay.callback(headers, body)
            
            if notification_data is None:
                logger.error("WeChat notification verification or decryption failed")
                return {"status": "error", "message": "Notification verification failed"}
                
            logger.info("WeChat notification verified and decrypted successfully")
            return notification_data
            
        except Exception as e:
            logger.exception(f"Exception in process_notification: {e}")
            return {"status": "error", "message": f"Error processing notification: {str(e)}"}

# Initialize a singleton instance to be imported by other modules
try:
    wechat_pay_helper = WeChatPayHelper()
    logger.info("WeChatPayHelper singleton created successfully")
except Exception as e:
    logger.exception(f"Failed to create WeChatPayHelper singleton: {e}")
    wechat_pay_helper = None 