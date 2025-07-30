#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, Integer, DateTime, JSON, ForeignKey, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# 导入配置
from config import SOURCE_DB, TARGET_DB, SYNC_INTERVAL, LOG_CONFIG

# 配置日志
logging.basicConfig(
    level=getattr(logging, LOG_CONFIG["level"]),
    format=LOG_CONFIG["format"],
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_CONFIG["file"])
    ]
)
logger = logging.getLogger('db_sync')

# 创建数据库连接串
SOURCE_DB_URL = f"mysql+pymysql://{SOURCE_DB['user']}:{SOURCE_DB['password']}@{SOURCE_DB['host']}:{SOURCE_DB['port']}/{SOURCE_DB['database']}?charset={SOURCE_DB['charset']}"
TARGET_DB_URL = f"mysql+pymysql://{TARGET_DB['user']}:{TARGET_DB['password']}@{TARGET_DB['host']}:{TARGET_DB['port']}/{TARGET_DB['database']}?charset={TARGET_DB['charset']}"

# 创建数据库引擎
source_engine = create_engine(SOURCE_DB_URL, pool_recycle=3600)
target_engine = create_engine(TARGET_DB_URL, pool_recycle=3600)

# 创建会话
SourceSession = sessionmaker(bind=source_engine)
TargetSession = sessionmaker(bind=target_engine)

# 定义源数据库模型
SourceBase = declarative_base()

class SourceFeed(SourceBase):
    __tablename__ = 'feeds'
    id = Column(String(255), primary_key=True)
    mp_name = Column(String(255))
    mp_cover = Column(String(255))
    mp_intro = Column(String(255))
    status = Column(Integer)
    sync_time = Column(Integer)
    update_time = Column(Integer)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    faker_id = Column(String(255))

class SourceArticle(SourceBase):
    __tablename__ = 'articles'
    id = Column(String(255), primary_key=True)
    mp_id = Column(String(255))
    title = Column(String(1000))
    pic_url = Column(String(500))
    url = Column(String(500))
    content = Column(Text)
    description = Column(Text)
    status = Column(Integer, default=1)
    publish_time = Column(Integer, index=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    is_export = Column(Integer)

# 定义目标数据库模型
TargetBase = declarative_base()

class TargetAccount(TargetBase):
    __tablename__ = 'accounts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="账号名称")
    platform = Column(String(50), nullable=False, index=True, comment="平台类型")
    account_id = Column(String(200), nullable=False, comment="平台账号ID")
    avatar_url = Column(String(500), nullable=True, comment="头像URL")
    description = Column(Text, nullable=True, comment="账号描述")
    follower_count = Column(Integer, default=0, comment="粉丝数量")
    details = Column(JSON, nullable=True, comment="平台特定详细信息")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    articles = relationship("TargetArticle", back_populates="account")

class TargetArticle(TargetBase):
    __tablename__ = 'articles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True, comment="账号ID")
    title = Column(String(500), nullable=False, comment="文章标题")
    url = Column(String(1000), nullable=False, comment="文章链接")
    content = Column(Text(length=4294967295).with_variant(Text(length=4294967295), "mysql", "mariadb"), nullable=True, comment="文章内容")
    summary = Column(Text(length=4294967295).with_variant(Text(length=4294967295), "mysql", "mariadb"), nullable=True, comment="文章摘要")
    publish_time = Column(DateTime, nullable=False, comment="发布时间")
    publish_timestamp = Column(BigInteger, nullable=False, index=True, comment="发布时间戳")
    images = Column(JSON, nullable=True, comment="图片链接列表")
    details = Column(JSON, nullable=True, comment="平台特定详细信息")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    account = relationship("TargetAccount", back_populates="articles")
    
    
    # 重新定义索引，避免在完整URL上创建唯一索引
    # 实现在迁移脚本中手动添加：CREATE UNIQUE INDEX ix_article_url ON articles (url(768));

def sync_feeds_to_accounts():
    """同步feeds表到accounts表"""
    source_session = SourceSession()
    target_session = TargetSession()
    
    try:
        # 获取上次同步时间
        last_sync_time = get_last_sync_time('feeds')
        
        # 查询需要同步的feeds
        if last_sync_time:
            feeds = source_session.query(SourceFeed).filter(
                SourceFeed.updated_at > last_sync_time
            ).all()
        else:
            feeds = source_session.query(SourceFeed).all()
        
        logger.info(f"开始同步feeds表，共 {len(feeds)} 条记录")
        
        # 同步feeds到accounts
        for feed in feeds:
            # 查找或创建对应的account
            account = target_session.query(TargetAccount).filter_by(
                account_id=feed.id,
                platform="wechat"
            ).first()
            
            if not account:
                account = TargetAccount(
                    name=feed.mp_name,
                    platform="wechat",
                    account_id=feed.id,
                    avatar_url=feed.mp_cover,
                    description=feed.mp_intro,
                    follower_count=0,
                    details=json.dumps({
                        "original_id": feed.id,
                        "faker_id": feed.faker_id,
                        "source": "sub_database"
                    }),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                target_session.add(account)
            else:
                account.name = feed.mp_name
                account.avatar_url = feed.mp_cover
                account.description = feed.mp_intro
                account.updated_at = datetime.now()
                account.details = json.dumps({
                    "original_id": feed.id,
                    "faker_id": feed.faker_id,
                    "source": "sub_database"
                })
            
        # 提交事务
        target_session.commit()
        
        # 更新同步时间
        update_sync_time('feeds', datetime.now())
        
        logger.info(f"feeds表同步完成")
    
    except Exception as e:
        target_session.rollback()
        logger.error(f"同步feeds表时出错: {str(e)}")
    
    finally:
        source_session.close()
        target_session.close()

def sync_articles():
    """同步articles表"""
    source_session = SourceSession()
    target_session = TargetSession()
    
    try:
        # 获取上次同步时间
        last_sync_time = get_last_sync_time('articles')
        
        # 查询需要同步的articles
        if last_sync_time:
            articles = source_session.query(SourceArticle).filter(
                SourceArticle.updated_at > last_sync_time
            ).all()
        else:
            articles = source_session.query(SourceArticle).all()
        
        logger.info(f"开始同步articles表，共 {len(articles)} 条记录")
        
        # 同步articles到target_articles
        for article in articles:
            # 查找对应的account
            account = target_session.query(TargetAccount).filter_by(
                account_id=article.mp_id,
                platform="wechat"
            ).first()
            
            if not account:
                logger.warning(f"找不到对应的账号: mp_id={article.mp_id}")
                continue
                
            # 处理发布时间
            if article.publish_time:
                publish_datetime = datetime.fromtimestamp(article.publish_time)
                publish_timestamp = article.publish_time
            else:
                publish_datetime = datetime.now()
                publish_timestamp = int(publish_datetime.timestamp())
            
            # 处理图片
            images = []
            if article.pic_url:
                images.append(article.pic_url)
            
            # 查找或创建对应的文章
            target_article = target_session.query(TargetArticle).filter_by(
                url=article.url
            ).first()
            
            if not target_article:
                target_article = TargetArticle(
                    account_id=account.id,
                    title=article.title if article.title else "",
                    url=article.url if article.url else "",
                    content=article.content,
                    summary=article.description,
                    publish_time=publish_datetime,
                    publish_timestamp=publish_timestamp,
                    images=json.dumps(images) if images else None,
                    details=json.dumps({
                        "original_id": article.id,
                        "source": "sub_database",
                        "status": article.status,
                        "is_export": article.is_export
                    }),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                target_session.add(target_article)
            else:
                target_article.title = article.title if article.title else ""
                target_article.content = article.content
                target_article.summary = article.description
                target_article.publish_time = publish_datetime
                target_article.publish_timestamp = publish_timestamp
                target_article.images = json.dumps(images) if images else None
                target_article.details = json.dumps({
                    "original_id": article.id,
                    "source": "sub_database",
                    "status": article.status,
                    "is_export": article.is_export
                })
                target_article.updated_at = datetime.now()
                
        # 提交事务
        target_session.commit()
        
        # 更新同步时间
        update_sync_time('articles', datetime.now())
        
        logger.info(f"articles表同步完成")
    
    except Exception as e:
        target_session.rollback()
        logger.error(f"同步articles表时出错: {str(e)}")
    
    finally:
        source_session.close()
        target_session.close()

def get_last_sync_time(table_name):
    """获取上次同步时间"""
    try:
        with open(f"sync_time_{table_name}.txt", "r") as f:
            time_str = f.read().strip()
            return datetime.fromisoformat(time_str) if time_str else None
    except FileNotFoundError:
        return None

def update_sync_time(table_name, sync_time):
    """更新同步时间"""
    with open(f"sync_time_{table_name}.txt", "w") as f:
        f.write(sync_time.isoformat())

def initialize_target_db():
    """初始化目标数据库表结构"""
    logger.info("检查并初始化目标数据库表结构")
    try:
        # 导入所需的库
        from sqlalchemy import inspect, text
        
        # 获取检查器对象
        inspector = inspect(target_engine)
        
        # 检查表是否已存在
        existing_tables = inspector.get_table_names()
        required_tables = [TargetAccount.__tablename__, TargetArticle.__tablename__]
        
        # 删除并重建所有表（当模型结构有变化时）
        rebuild_tables = False  # 设置为True将强制重建表结构
        
        if rebuild_tables and any(table in existing_tables for table in required_tables):
            logger.info("强制重建表结构")
            # 删除现有的表（注意顺序，先删除有外键约束的表）
            with target_engine.connect() as conn:
                if TargetArticle.__tablename__ in existing_tables:
                    logger.info(f"删除表: {TargetArticle.__tablename__}")
                    conn.execute(text(f"DROP TABLE IF EXISTS {TargetArticle.__tablename__}"))
                    
                if TargetAccount.__tablename__ in existing_tables:
                    logger.info(f"删除表: {TargetAccount.__tablename__}")
                    conn.execute(text(f"DROP TABLE IF EXISTS {TargetAccount.__tablename__}"))
                
                conn.commit()
            
            # 重新加载表信息
            inspector = inspect(target_engine)
            existing_tables = inspector.get_table_names()
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            logger.info(f"缺少表: {', '.join(missing_tables)}，准备创建")
            # 只创建缺少的表
            TargetBase.metadata.create_all(target_engine)
            logger.info("目标数据库表结构初始化成功")
        else:
            logger.info("所有必要的表已存在，无需创建")
    except Exception as e:
        logger.error(f"初始化目标数据库表结构时出错: {str(e)}")
        raise

def main():
    """主函数"""
    logger.info("数据库同步程序启动")
    
    # 初始化目标数据库表结构
    initialize_target_db()
    
    while True:
        try:
            # 同步feeds表到accounts表
            sync_feeds_to_accounts()
            
            # 同步articles表
            sync_articles()
            
            # 等待一段时间后再次同步
            logger.info(f"等待 {SYNC_INTERVAL} 秒后进行下一次同步...")
            time.sleep(SYNC_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("程序被手动中断")
            break
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            time.sleep(60)  # 发生错误后等待一段时间再重试

if __name__ == "__main__":
    main() 