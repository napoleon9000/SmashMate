import pytest
import asyncio
from typing import Generator
from supabase import create_client, Client
import uuid

from app.core.config import settings

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def supabase_client() -> Client:
    """Create a Supabase client for testing using service role key."""
    return create_client(settings.LOCAL_SUPABASE_URL, settings.LOCAL_SUPABASE_KEY)

@pytest.fixture
async def test_user(supabase_client: Client, db_service):
    """Create a test user and clean up after the test."""
    test_email = f"test_9{uuid.uuid4()}@example.com"
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
    
    # Clean up: delete all associated records first
    tables = [
        "match_players",
        "matches",
        "player_ratings",
        "teams",
        "follows",
        "venues",
        "profiles"
    ]
    for table in tables:
        try:
            await db_service.client.table(table).delete().eq("user_id", user_id).execute()
        except Exception:
            pass
        try:
            await db_service.client.table(table).delete().eq("player_id", user_id).execute()
        except Exception:
            pass
        try:
            await db_service.client.table(table).delete().eq("follower", user_id).execute()
        except Exception:
            pass
        try:
            await db_service.client.table(table).delete().eq("followee", user_id).execute()
        except Exception:
            pass
        try:
            await db_service.client.table(table).delete().eq("created_by", user_id).execute()
        except Exception:
            pass
    
    # Now delete the user - handle the error gracefully
    try:
        supabase_client.auth.admin.delete_user(user_id)
    except Exception as e:
        print(f"Warning: Could not delete user {user_id}: {str(e)}")
        # Continue with cleanup even if user deletion fails
        pass 
