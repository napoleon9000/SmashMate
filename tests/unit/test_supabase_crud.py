"""
Unit tests for basic Supabase CRUD operations.

These tests verify direct Supabase client operations without going through
the DatabaseService abstraction layer. They test basic connection and
profile CRUD operations.
"""

import pytest
from supabase import Client
from tests.utils import SAMPLE_PROFILE_DATA

# Apply asyncio marker to all tests in this module
pytestmark = pytest.mark.asyncio


async def test_supabase_connection(supabase_client: Client):
    """Test basic Supabase connection and query capability."""
    response = supabase_client.table("profiles").select("*").limit(1).execute()
    assert response is not None, "Should be able to execute basic query"


async def test_create_profile(supabase_client: Client, test_user: dict):
    """Test creating a profile directly through Supabase client."""
    test_profile = {
        "user_id": test_user["id"],
        **SAMPLE_PROFILE_DATA,
        "avatar_url": "https://example.com/avatar.jpg"
    }
    
    # Execute: Create profile
    response = supabase_client.table("profiles").insert(test_profile).execute()
    
    # Assert: Profile created successfully
    assert response.data is not None
    assert response.data[0]["display_name"] == test_profile["display_name"]


async def test_read_profile(supabase_client: Client, test_user: dict):
    """Test reading a profile directly through Supabase client."""
    # Setup: Create a profile for the test user
    test_profile = {
        "user_id": test_user["id"],
        **SAMPLE_PROFILE_DATA,
        "avatar_url": "https://example.com/avatar.jpg"
    }
    
    supabase_client.table("profiles").insert(test_profile).execute()
    
    # Execute: Read the profile
    response = supabase_client.table("profiles").select("*").eq("user_id", test_user["id"]).execute()
    
    # Assert: Profile retrieved successfully
    assert response.data is not None
    assert len(response.data) > 0
    assert response.data[0]["display_name"] == test_profile["display_name"]


async def test_update_profile(supabase_client: Client, test_user: dict):
    """Test updating a profile directly through Supabase client."""
    # Setup: Create initial profile
    test_profile = {
        "user_id": test_user["id"],
        **SAMPLE_PROFILE_DATA,
        "avatar_url": "https://example.com/avatar.jpg"
    }
    
    supabase_client.table("profiles").insert(test_profile).execute()
    
    # Execute: Update the profile
    updated_profile = {
        "display_name": "Updated User"
    }
    
    response = supabase_client.table("profiles").update(updated_profile).eq("user_id", test_user["id"]).execute()
    
    # Assert: Profile updated successfully
    assert response.data is not None
    assert response.data[0]["display_name"] == updated_profile["display_name"]


async def test_delete_profile(supabase_client: Client, test_user: dict):
    """Test deleting a profile directly through Supabase client."""
    # Setup: Create a profile for the test user
    test_profile = {
        "user_id": test_user["id"],
        **SAMPLE_PROFILE_DATA,
        "avatar_url": "https://example.com/avatar.jpg"
    }
    
    supabase_client.table("profiles").insert(test_profile).execute()
    
    # Execute: Delete the profile
    response = supabase_client.table("profiles").delete().eq("user_id", test_user["id"]).execute()
    
    # Assert: Profile deleted successfully
    assert response.data is not None 
