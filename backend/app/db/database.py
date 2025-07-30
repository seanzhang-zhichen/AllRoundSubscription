"""
数据库配置和连接管理
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# 创建异步数据库引擎
if "sqlite" in settings.database_url.lower():
    # SQLite配置
    engine = create_async_engine(
        settings.database_url,
        echo=settings.ENABLE_SQL_LOGGING,  # 通过配置控制SQL日志输出
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
        }
    )
elif "mysql" in settings.database_url.lower():
    # MySQL配置
    engine = create_async_engine(
        settings.database_url,
        echo=settings.ENABLE_SQL_LOGGING,  # 通过配置控制SQL日志输出
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={
            "charset": "utf8mb4",
        }
    )
else:
    # PostgreSQL配置
    engine = create_async_engine(
        settings.database_url,
        echo=settings.ENABLE_SQL_LOGGING,  # 通过配置控制SQL日志输出
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600
    )

# 创建会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    """数据库模型基类"""
    pass


async def get_db() -> AsyncSession:
    """获取数据库会话依赖"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"数据库会话错误: {str(e)}")
            raise
        finally:
            await session.close()


async def init_db():
    """初始化数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库初始化完成")