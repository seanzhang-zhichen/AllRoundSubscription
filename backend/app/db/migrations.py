"""
数据库迁移脚本
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import engine, Base
from app.models.user import User
from app.models.account import Account
from app.models.article import Article
from app.models.subscription import Subscription
from app.models.push_record import PushRecord
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_tables():
    """创建所有表"""
    async with engine.begin() as conn:
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)
        logger.info("所有表创建完成")


async def create_indexes(session: AsyncSession):
    """创建优化索引"""
    indexes = [
        # 用户表索引
        "CREATE INDEX IF NOT EXISTS idx_user_openid ON users(openid);",
        "CREATE INDEX IF NOT EXISTS idx_user_membership ON users(membership_level, membership_expire_at);",
        
        # 账号表索引
        "CREATE INDEX IF NOT EXISTS idx_account_platform_name ON accounts(platform, name);",
        "CREATE INDEX IF NOT EXISTS idx_account_platform_id ON accounts(platform, account_id);",
        
        # 文章表索引
        "CREATE INDEX IF NOT EXISTS idx_article_account_time ON articles(account_id, publish_timestamp DESC);",
        "CREATE INDEX IF NOT EXISTS idx_article_url ON articles(url);",
        "CREATE INDEX IF NOT EXISTS idx_article_publish_time ON articles(publish_time DESC);",
        
        # 订阅表索引
        "CREATE INDEX IF NOT EXISTS idx_subscription_user ON subscriptions(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_subscription_account ON subscriptions(account_id);",
        
        # 推送记录表索引
        "CREATE INDEX IF NOT EXISTS idx_push_user_time ON push_records(user_id, push_time DESC);",
        "CREATE INDEX IF NOT EXISTS idx_push_article ON push_records(article_id);",
        "CREATE INDEX IF NOT EXISTS idx_push_status ON push_records(status);",
    ]
    
    for index_sql in indexes:
        try:
            await session.execute(text(index_sql))
            logger.info(f"索引创建成功: {index_sql.split()[5]}")
        except Exception as e:
            logger.warning(f"索引创建失败: {index_sql} - {str(e)}")
    
    await session.commit()
    logger.info("所有索引创建完成")


async def migrate_database():
    """执行数据库迁移"""
    try:
        # 创建表
        await create_tables()
        
        # 创建索引
        from app.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await create_indexes(session)
        
        logger.info("数据库迁移完成")
        return True
    except Exception as e:
        logger.error(f"数据库迁移失败: {str(e)}")
        return False


async def check_database_compatibility():
    """检查数据库兼容性"""
    try:
        from app.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            # 检查是否存在旧的accounts和articles表
            result = await session.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('accounts', 'articles');"
            ))
            existing_tables = [row[0] for row in result.fetchall()]
            
            if existing_tables:
                logger.info(f"发现现有表: {existing_tables}")
                # 这里可以添加数据迁移逻辑
                return True
            else:
                logger.info("未发现现有表，将创建新表")
                return True
    except Exception as e:
        logger.error(f"数据库兼容性检查失败: {str(e)}")
        return False


if __name__ == "__main__":
    import asyncio
    
    async def main():
        # 检查兼容性
        if await check_database_compatibility():
            # 执行迁移
            success = await migrate_database()
            if success:
                print("数据库迁移成功完成")
            else:
                print("数据库迁移失败")
        else:
            print("数据库兼容性检查失败")
    
    asyncio.run(main())