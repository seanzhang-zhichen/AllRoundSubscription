"""
安全相关工具模块
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
import logging

from app.core.config import settings
from app.core.exceptions import AuthenticationException

logger = logging.getLogger(__name__)

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class JWTManager:
    """JWT令牌管理器"""
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({
            "exp": expire,
            "type": "access"
        })
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            logger.info(f"创建访问令牌成功，用户ID: {data.get('sub')}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"创建访问令牌失败: {str(e)}")
            raise AuthenticationException("令牌创建失败")
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """创建刷新令牌"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({
            "exp": expire,
            "type": "refresh"
        })
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            logger.info(f"创建刷新令牌成功，用户ID: {data.get('sub')}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"创建刷新令牌失败: {str(e)}")
            raise AuthenticationException("令牌创建失败")
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # 检查令牌类型
            if payload.get("type") != token_type:
                raise AuthenticationException(f"无效的令牌类型，期望: {token_type}")
            
            # 检查是否过期
            exp = payload.get("exp")
            if exp is None:
                raise AuthenticationException("令牌缺少过期时间")
            
            # 使用UTC时间进行比较，确保时区一致性
            current_time = datetime.utcnow().timestamp()
            if current_time > exp:
                raise AuthenticationException("令牌已过期")
            
            logger.debug(f"令牌验证成功，用户ID: {payload.get('sub')}")
            return payload
            
        except JWTError as e:
            logger.error(f"JWT解码失败: {str(e)}")
            raise AuthenticationException("无效的令牌格式")
        except Exception as e:
            logger.error(f"令牌验证失败: {str(e)}")
            raise AuthenticationException("令牌验证失败")
    
    def get_user_id_from_token(self, token: str) -> int:
        """从令牌中获取用户ID"""
        payload = self.verify_token(token)
        user_id = payload.get("sub")
        
        if user_id is None:
            raise AuthenticationException("令牌中缺少用户ID")
        
        try:
            return int(user_id)
        except (ValueError, TypeError):
            raise AuthenticationException("无效的用户ID格式")


# 全局JWT管理器实例
jwt_manager = JWTManager()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return pwd_context.hash(password)