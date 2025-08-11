import os
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from typing import Dict, List, Any, Optional

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class WechatMySQLDB:
    """MySQL数据库连接类，用于管理数据库连接和执行SQL查询"""
    
    def __init__(self):
        """
        初始化数据库连接
        """
        connection_string = settings.WECHAT_RSS_DB_URL
        
        self.connection_string = connection_string
        
        self.engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=3600
        )
        self.Session = sessionmaker(bind=self.engine)
        
    def execute_query(self, query, params=None):
        """
        执行SQL查询并返回结果
        
        Args:
            query (str): SQL查询语句
            params (dict, optional): 查询参数
            
        Returns:
            list: 查询结果列表
        """
        session = self.Session()
        try:
            if params:
                result = session.execute(text(query), params)
            else:
                result = session.execute(text(query))
            
            # 获取列名
            columns = result.keys()
            
            # 获取所有行
            rows = result.fetchall()
            
            # 转换为字典列表
            result_list = [dict(zip(columns, row)) for row in rows]
            
            return result_list
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_article_list(self, mp_id: Optional[str] = None, offset: int = 0, limit: int = 5,
                         status: Optional[int] = None, search: Optional[str] = None) -> Dict[str, Any]:
        params = {"limit": limit, "offset": offset}
        where_clauses = []

        if mp_id:
            where_clauses.append("mp_id = :mp_id")
            params["mp_id"] = mp_id
        if status is not None:
            where_clauses.append("status = :status")
            params["status"] = status
        if search:
            where_clauses.append("title LIKE :search")
            params["search"] = f"%{search}%"

        where_sql = ""
        if where_clauses:
            where_sql = " WHERE " + " AND ".join(where_clauses)
            
        try:
            count_params = {k: v for k, v in params.items() if k not in ['limit', 'offset']}
            count_query = f"SELECT COUNT(id) as total FROM articles {where_sql}"
            total_result = self.execute_query(count_query, count_params)
            total = total_result[0]['total'] if total_result else 0
            
            data_query = f"SELECT * FROM articles {where_sql} ORDER BY publish_time DESC LIMIT :limit OFFSET :offset"
            articles = self.execute_query(data_query, params)

            return {
                "success": True,
                "data": articles
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_all_articles(self, mp_id: Optional[str] = None, status: Optional[int] = None, 
                         search: Optional[str] = None) -> Dict[str, Any]:
        params = {}
        where_clauses = []

        if mp_id:
            where_clauses.append("mp_id = :mp_id")
            params["mp_id"] = mp_id
        if status is not None:
            where_clauses.append("status = :status")
            params["status"] = status
        if search:
            where_clauses.append("title LIKE :search")
            params["search"] = f"%{search}%"
            
        where_sql = ""
        if where_clauses:
            where_sql = " WHERE " + " AND ".join(where_clauses)
            
        try:
            query = f"SELECT * FROM articles {where_sql} ORDER BY publish_time DESC"
            articles = self.execute_query(query, params)
            return {
                "success": True,
                "data": articles,
                "total": len(articles)
            }
        except Exception as e:
            return {"success": False, "error": str(e), "data": [], "total": 0}

    def search_accounts(self, keyword: str, offset: int = 0, limit: int = 5) -> Dict[str, Any]:
        params = {"limit": limit, "offset": offset}
        where_sql = ""
        
        if keyword:
            where_sql = "WHERE mp_name LIKE :keyword"
            params["keyword"] = f"%{keyword}%"
            
        try:
            count_params = {k: v for k, v in params.items() if k not in ['limit', 'offset']}
            count_query = f"SELECT COUNT(id) as total FROM feeds {where_sql}"
            total_result = self.execute_query(count_query, count_params)
            total = total_result[0]['total'] if total_result else 0
            
            data_query = f"SELECT * FROM feeds {where_sql} LIMIT :limit OFFSET :offset"
            accounts = self.execute_query(data_query, params)

            return {
                "success": True,
                "data": { "list": accounts, "total": total }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_account_info(self, mp_id: str) -> Dict[str, Any]:
        query = "SELECT * FROM feeds WHERE id = :mp_id LIMIT 1"
        try:
            result = self.execute_query(query, {"mp_id": mp_id})
            if result:
                # 格式化datetime对象为ISO格式字符串
                account_data = result[0]
                if 'created_at' in account_data and isinstance(account_data['created_at'], datetime):
                    account_data['created_at'] = account_data['created_at'].isoformat()
                if 'updated_at' in account_data and isinstance(account_data['updated_at'], datetime):
                    account_data['updated_at'] = account_data['updated_at'].isoformat()
                
                return {"success": True, "data": account_data}
            else:
                return {"success": False, "error": "Account not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_account(self, mp_name: str, mp_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        session = self.Session()
        try:
            data = {"mp_name": mp_name}
            if mp_id:
                data['id'] = mp_id
            data.update(kwargs)

            # Since the ORM model is removed, we explicitly define columns
            valid_columns = [
                'id', 'mp_name', 'mp_cover', 'mp_intro', 'status', 
                'sync_time', 'update_time', 'created_at', 'updated_at', 'faker_id'
            ]
            insert_data = {k: v for k, v in data.items() if k in valid_columns and v is not None}

            if 'id' not in insert_data:
                return {"success": False, "error": "mp_id is required"}

            columns = ", ".join(f"`{k}`" for k in insert_data.keys())
            placeholders = ", ".join(f":{k}" for k in insert_data.keys())
            query = f"INSERT INTO feeds ({columns}) VALUES ({placeholders})"
            
            session.execute(text(query), insert_data)
            session.commit()
            
            return {"success": True, "data": insert_data}
        except SQLAlchemyError as e:
            session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    def get_all_accounts(self, keyword: Optional[str] = None, offset: int = 0, limit: int = 100) -> Dict[str, Any]:
        params = {"limit": limit, "offset": offset}
        where_sql = ""
            
        try:
            count_params = {k: v for k, v in params.items() if k not in ['limit', 'offset']}
            count_query = f"SELECT COUNT(id) as total FROM feeds {where_sql}"
            total_result = self.execute_query(count_query, count_params)
            total = total_result[0]['total'] if total_result else 0
            
            data_query = f"SELECT * FROM feeds {where_sql} LIMIT :limit OFFSET :offset"
            accounts = self.execute_query(data_query, params)

            return {
                "success": True,
                "data": accounts,
                "total": len(accounts)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_article_detail(self, article_id: str) -> Dict[str, Any]:
        query = "SELECT * FROM articles WHERE id = :article_id LIMIT 1"
        try:
            result = self.execute_query(query, {"article_id": article_id})
            if result:
                return {"success": True, "data": result[0]}
            else:
                return {"success": False, "error": "Article not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_account_article_stats(self, mp_id: str) -> Dict[str, Any]:
        query = "SELECT COUNT(id) as article_count, MAX(publish_time) as latest_publish_time FROM articles WHERE mp_id = :mp_id"
        try:
            result = self.execute_query(query, {"mp_id": mp_id})
            if result and result[0].get('article_count', 0) > 0:
                stats = result[0]
                latest_article_time = None
                if stats.get('latest_publish_time'):
                    latest_article_time = datetime.fromtimestamp(stats['latest_publish_time'])
                
                return {
                    "success": True,
                    "data": {
                        "article_count": stats['article_count'],
                        "latest_article_time": latest_article_time
                    }
                }
            else:
                return {
                    "success": True,
                    "data": { "article_count": 0, "latest_article_time": None }
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


    def get_id_by_faker_id(self, faker_id: str):
        """
        根据faker_id查询账号的id
        
        Args:
            faker_id (str): 要查询的faker_id
            
        Returns:
            Dict[str, Any]: 包含查询结果的字典
        """
        query = "SELECT id FROM feeds WHERE faker_id = :faker_id LIMIT 1"
        try:
            result = self.execute_query(query, {"faker_id": faker_id})
            if result:
                return {"success": True, "data": result[0]['id']}
            else:
                return {"success": False, "error": "Account not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
