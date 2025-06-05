import pytest
from supabase import Client
import uuid

pytestmark = pytest.mark.asyncio

async def test_supabase_connection(supabase_client: Client):
    """Test basic Supabase connection."""
    response = supabase_client.table("profiles").select("*").limit(1).execute()
    assert response is not None

async def test_create_profile(supabase_client: Client, test_user: dict):
    """Test creating a profile."""
    test_profile = {
        "user_id": test_user["id"],
        "display_name": "Test User",
        "avatar_url": "https://example.com/avatar.jpg"
    }
    
    response = supabase_client.table("profiles").insert(test_profile).execute()
    assert response.data is not None
    assert response.data[0]["display_name"] == test_profile["display_name"]

async def test_read_profile(supabase_client: Client, test_user: dict):
    """Test reading a profile."""
    # Create a profile for the test user
    test_profile = {
        "user_id": test_user["id"],
        "display_name": "Test User",
        "avatar_url": "https://example.com/avatar.jpg"
    }
    
    supabase_client.table("profiles").insert(test_profile).execute()
    
    # Now try to read the profile
    response = supabase_client.table("profiles").select("*").eq("user_id", test_user["id"]).execute()
    assert response.data is not None
    assert len(response.data) > 0
    assert response.data[0]["display_name"] == test_profile["display_name"]

async def test_update_profile(supabase_client: Client, test_user: dict):
    """Test updating a profile."""
    # Create initial profile
    test_profile = {
        "user_id": test_user["id"],
        "display_name": "Test User",
        "avatar_url": "https://example.com/avatar.jpg"
    }
    
    supabase_client.table("profiles").insert(test_profile).execute()
    
    # Update the profile
    updated_profile = {
        "display_name": "Updated User"
    }
    
    response = supabase_client.table("profiles").update(updated_profile).eq("user_id", test_user["id"]).execute()
    assert response.data is not None
    assert response.data[0]["display_name"] == updated_profile["display_name"]

async def test_delete_profile(supabase_client: Client, test_user: dict):
    """Test deleting a profile."""
    # Create a profile for the test user
    test_profile = {
        "user_id": test_user["id"],
        "display_name": "Test User",
        "avatar_url": "https://example.com/avatar.jpg"
    }
    
    supabase_client.table("profiles").insert(test_profile).execute()
    
    # Delete the profile
    response = supabase_client.table("profiles").delete().eq("user_id", test_user["id"]).execute()
    assert response.data is not None 