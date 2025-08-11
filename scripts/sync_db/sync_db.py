#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, Integer, DateTime, JSON, ForeignKey, BigInteger, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.mysql import MEDIUMTEXT

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
    summary = Column(Text)

# 定义目标数据库模型 - 根据提供的模型结构更新
TargetBase = declarative_base()

class TargetAccount(TargetBase):
    """账号模型 (博主)"""
    __tablename__ = "accounts"
    __table_args__ = (
        Index("ux_accounts_account_id", "account_id", unique=True),
        UniqueConstraint("platform", "account_id", name="uq_platform_account_id"),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="账号名称")
    platform = Column(String(50), nullable=False, index=True, comment="平台类型")
    account_id = Column(String(200), nullable=False, comment="平台账号ID")
    avatar_url = Column(String(500), nullable=True, comment="头像URL")
    description = Column(Text, nullable=True, comment="账号描述")
    details = Column(JSON, nullable=True, comment="平台特定详细信息")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系定义
    articles = relationship("TargetArticle", back_populates="account", primaryjoin="TargetAccount.account_id == TargetArticle.account_id")

class TargetArticle(TargetBase):
    """文章模型"""
    __tablename__ = "articles"
    __table_args__ = (
        Index("ux_articles_url_prefix", "url", mysql_length=768, unique=True),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String(200), ForeignKey("accounts.account_id"), nullable=False, index=True, comment="账号ID")
    title = Column(String(500), nullable=False, comment="文章标题")
    url = Column(String(1000), nullable=False, comment="文章链接")
    content = Column(MEDIUMTEXT, nullable=True, comment="文章内容")
    summary = Column(Text, nullable=True, comment="文章摘要")
    publish_time = Column(DateTime, nullable=False, comment="发布时间")
    details = Column(JSON, nullable=True, comment="平台特定详细信息")
    cover_url = Column(String(500), nullable=True, comment="封面图片URL")
    platform = Column(String(50), nullable=False, comment="平台类型")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系定义
    account = relationship("TargetAccount", back_populates="articles", foreign_keys=[account_id], primaryjoin="TargetArticle.account_id == TargetAccount.account_id")

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
        
        # 使用no_autoflush上下文来避免premature flush
        with target_session.no_autoflush:
            # 预先加载所有现有的accounts，避免在循环中查询时触发autoflush
            feed_ids = [feed.id for feed in feeds if feed.id]
            existing_accounts_map = {}
            if feed_ids:
                existing_accounts = target_session.query(TargetAccount).filter(
                    TargetAccount.account_id.in_(feed_ids),
                    TargetAccount.platform == "wechat"
                ).all()
                existing_accounts_map = {account.account_id: account for account in existing_accounts}
            
            # 同步feeds到accounts
            new_accounts_count = 0
            updated_accounts_count = 0
            for feed in feeds:
                # 使用预加载的account数据
                account = existing_accounts_map.get(feed.id)
                
                if not account:
                    account = TargetAccount(
                        name=feed.mp_name,
                        platform="wechat",
                        account_id=feed.id,
                        avatar_url=feed.mp_cover,
                        description=feed.mp_intro,
                        details={
                            "faker_id": feed.faker_id,
                        },
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    target_session.add(account)
                    new_accounts_count += 1
                    logger.info(f"创建账号: {feed.mp_name}")
                else:
                    # 更新现有账号信息
                    if account.name != feed.mp_name or account.avatar_url != feed.mp_cover or account.description != feed.mp_intro:
                        account.name = feed.mp_name
                        account.avatar_url = feed.mp_cover
                        account.description = feed.mp_intro
                        account.updated_at = datetime.now()
                        updated_accounts_count += 1
                        logger.info(f"更新账号: {feed.mp_name}")
        
        # 在no_autoflush块外进行提交
        if new_accounts_count > 0 or updated_accounts_count > 0:
            logger.info(f"准备提交 {new_accounts_count} 个新账号，{updated_accounts_count} 个更新账号")
            target_session.commit()
            logger.info(f"成功提交 {new_accounts_count} 个新账号，{updated_accounts_count} 个更新账号")
        else:
            logger.info("没有账号需要同步")
        
        # 更新同步时间
        update_sync_time('feeds', datetime.now())
        
        logger.info(f"feeds表同步完成，新增 {new_accounts_count} 个账号，更新 {updated_accounts_count} 个账号")
    
    except Exception as e:
        target_session.rollback()
        logger.error(f"同步feeds表时出错: {str(e)}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        raise
    
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
        
        # 使用no_autoflush上下文来避免premature flush
        with target_session.no_autoflush:
            # 预先加载所有需要的accounts到内存中，避免在循环中查询时触发autoflush
            account_ids = list(set([article.mp_id for article in articles if article.mp_id]))
            accounts_map = {}
            if account_ids:
                accounts = target_session.query(TargetAccount).filter(
                    TargetAccount.account_id.in_(account_ids),
                    TargetAccount.platform == "wechat"
                ).all()
                accounts_map = {account.account_id: account for account in accounts}
            
            # 预先加载所有现有文章的URL，避免在循环中查询时触发autoflush
            article_urls = [article.url for article in articles if article.url]
            existing_articles_map = {}
            if article_urls:
                existing_articles = target_session.query(TargetArticle).filter(
                    TargetArticle.url.in_(article_urls)
                ).all()
                existing_articles_map = {article.url: article for article in existing_articles}
            
            # 同步articles到target_articles
            new_articles_count = 0
            for article in articles:
                # 使用预加载的account数据
                account = accounts_map.get(article.mp_id)
                
                if not account:
                    logger.warning(f"找不到对应的账号: mp_id={article.mp_id}")
                    continue
                    
                # 处理发布时间
                if article.publish_time:
                    publish_datetime = datetime.fromtimestamp(article.publish_time)
                else:
                    publish_datetime = datetime.now()
                
                # 使用预加载的文章数据
                target_article = existing_articles_map.get(article.url)
                
                if not target_article:
                    content = article.content
                    
                    target_article = TargetArticle(
                        account_id=article.mp_id,
                        title=article.title[:500] if article.title else "",
                        url=article.url if article.url else "",
                        content=content,
                        platform="wechat",
                        summary=article.summary,
                        publish_time=publish_datetime,
                        cover_url=article.pic_url,
                        details={
                            "status": article.status,
                            "is_export": article.is_export,
                            "description": article.description,
                            "images": [article.pic_url] if article.pic_url else []
                        },
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    target_session.add(target_article)
                    new_articles_count += 1
                    logger.info(f"创建文章: {article.title}")
        
        # 在no_autoflush块外进行提交
        if new_articles_count > 0:
            logger.info(f"准备提交 {new_articles_count} 篇新文章")
            target_session.commit()
            logger.info(f"成功提交 {new_articles_count} 篇新文章")
        else:
            logger.info("没有新文章需要同步")
        
        # 更新同步时间
        update_sync_time('articles', datetime.now())
        
        logger.info(f"articles表同步完成，新增 {new_articles_count} 篇文章")
    
    except Exception as e:
        target_session.rollback()
        logger.error(f"同步articles表时出错: {str(e)}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        raise
    
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
            start_time = datetime.now()
            logger.info(f"开始执行每小时同步任务: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 同步feeds表到accounts表
            sync_feeds_to_accounts()
            
            # 同步articles表
            sync_articles()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"本次同步任务完成，耗时 {duration:.2f} 秒")
            
            # 计算需要等待的时间，确保每小时整点执行
            next_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
            next_hour = next_hour.replace(hour=next_hour.hour + 1)
            wait_seconds = (next_hour - datetime.now()).total_seconds()
            
            # 如果计算出的等待时间小于0或大于SYNC_INTERVAL，则使用SYNC_INTERVAL
            if wait_seconds <= 0 or wait_seconds > SYNC_INTERVAL:
                wait_seconds = SYNC_INTERVAL
                
            from datetime import timedelta
            next_sync_time = datetime.now() + timedelta(seconds=wait_seconds)
            logger.info(f"等待 {wait_seconds:.2f} 秒后进行下一次同步，预计下次同步时间: {next_sync_time.strftime('%Y-%m-%d %H:%M:%S')}...")
            time.sleep(wait_seconds)
            
        except KeyboardInterrupt:
            logger.info("程序被手动中断")
            break
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            time.sleep(60)  # 发生错误后等待一段时间再重试

if __name__ == "__main__":
    main() 