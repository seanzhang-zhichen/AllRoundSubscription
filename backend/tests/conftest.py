"""
测试配置文件
"""
import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.database import get_db, Base
from app.core.config import settings

# 测试数据库URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# 创建测试数据库引擎
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
    echo=False
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session():
    """创建测试数据库会话"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session = TestSessionLocal()
    try:
        yield session
    finally:
        await session.close()
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session):
    """创建测试客户端"""
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def test_user(db_session):
    """创建测试用户"""
    from app.models.user import User, MembershipLevel
    from datetime import datetime, timedelta
    
    user = User(
        openid="test_user_openid",
        nickname="测试用户",
        avatar_url="https://example.com/avatar.jpg",
        membership_level=MembershipLevel.BASIC,
        membership_expire_at=datetime.utcnow() + timedelta(days=30)
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


@pytest.fixture(scope="function")
async def test_account(db_session):
    """创建测试账号"""
    from app.models.account import Account, Platform
    
    account = Account(
        name="测试公众号",
        platform=Platform.WECHAT,
        account_id="test_wechat_account",
        avatar_url="https://example.com/account_avatar.jpg",
        description="这是一个测试公众号",
        follower_count=10000,
        details={"verified": True}
    )
    
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    
    return account


@pytest.fixture(scope="function")
async def auth_headers(test_user):
    """创建认证头部"""
    from app.core.security import jwt_manager
    
    # 创建访问令牌
    token_data = {"sub": str(test_user.id)}
    access_token = jwt_manager.create_access_token(token_data)
    
    return {"Authorization": f"Bearer {access_token}"}