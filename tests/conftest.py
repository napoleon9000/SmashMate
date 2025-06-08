import pytest
import asyncio
from typing import Generator
from supabase import create_client, Client
import uuid

from app.core.config import settings
from app.services.database import DatabaseService
from tests.unit.test_services_db import TEST_URL, TEST_KEY


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

@pytest.fixture
async def additional_test_users(supabase_client, db_service):
    """Create additional test users for testing relationships."""
    users = []
    for i in range(4):  # Create 4 additional users
        test_email = f"test_{i}{uuid.uuid4()}@example.com"
        test_password = "test_password123"
        
        # Create user with service role
        auth_response = supabase_client.auth.admin.create_user({
            "email": test_email,
            "password": test_password,
            "email_confirm": True  # Auto-confirm the email
        })
        
        users.append({
            "id": auth_response.user.id,
            "email": test_email,
            "password": test_password
        })
    
    yield users
    
    # Clean up: delete all associated records first
    for user in users:
        # Delete all records associated with this user
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
                await db_service.client.table(table).delete().eq("user_id", user["id"]).execute()
            except Exception:
                pass
            try:
                await db_service.client.table(table).delete().eq("player_id", user["id"]).execute()
            except Exception:
                pass
            try:
                await db_service.client.table(table).delete().eq("follower", user["id"]).execute()
            except Exception:
                pass
            try:
                await db_service.client.table(table).delete().eq("followee", user["id"]).execute()
            except Exception:
                pass
            try:
                await db_service.client.table(table).delete().eq("created_by", user["id"]).execute()
            except Exception:
                pass
        
        # Now delete the user - handle the error gracefully
        try:
            supabase_client.auth.admin.delete_user(user["id"])
        except Exception as e:
            print(f"Warning: Could not delete user {user['id']}: {str(e)}")
            # Continue with cleanup even if user deletion fails
            pass

@pytest.fixture
async def test_venue(db_service, test_user):
    """Create a test venue for match testing."""
    venue_data = {
        "name": "Test Badminton Venue",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "address": "123 Test Badminton Court",
        "created_by": test_user["id"]
    }
    
    venue = await db_service.create_venue(**venue_data)
    
    yield venue
    
    # Cleanup will be handled by the cleanup_database fixture

@pytest.fixture(scope="session")
def db_service():
    """Create a database service instance for testing."""
    service = DatabaseService(TEST_URL, TEST_KEY)
    return service
