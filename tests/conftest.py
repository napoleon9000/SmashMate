import pytest
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from supabase import create_client, Client
import uuid
from sqlalchemy.engine.url import URL
from sqlalchemy import text, MetaData, Table, Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID

from app.core.config import settings
from app.services.database import Base

# Define auth.users table in the same metadata as Base
auth_users = Table(
    "users",
    Base.metadata,
    Column("id", UUID, primary_key=True),
    Column("email", String),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    schema="auth"
)

# Test database URL - always use local database for tests
TEST_DATABASE_URL = URL.create(
    drivername="postgresql+asyncpg",
    username=settings.LOCAL_SUPABASE_DB_USER,
    password=settings.LOCAL_SUPABASE_PASSWORD,
    host="localhost",
    port=54322,
    database=settings.LOCAL_SUPABASE_DB_NAME
)

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=True)
TestingSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db_engine():
    """Create a test database engine."""
    async with test_engine.begin() as conn:
        # Create our test tables
        await conn.run_sync(Base.metadata.create_all)
    
    yield test_engine
    
    async with test_engine.begin() as conn:
        # Drop our test tables
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()

@pytest.fixture
def supabase_client() -> Client:
    """Create a Supabase client for testing using service role key."""
    return create_client(settings.LOCAL_SUPABASE_URL, settings.LOCAL_SUPABASE_KEY)

@pytest.fixture
async def test_user(supabase_client: Client):
    """Create a test user and clean up after the test."""
    test_email = f"test_{uuid.uuid4()}@example.com"
    test_password = "test_password123"
    
    # Create user with service role
    auth_response = supabase_client.auth.admin.create_user({
        "email": test_email,
        "password": test_password,
        "email_confirm": True  # Auto-confirm the email
    })
    
    user_id = auth_response.user.id
    
    yield {
        "id": user_id,
        "email": test_email,
        "password": test_password
    }
    
    # Clean up: delete the test user
    supabase_client.auth.admin.delete_user(user_id) 
