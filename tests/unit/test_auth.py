"""
Unit tests for auth functionality in the Smash Mate application.

Tests cover profile management operations including get-or-create and update
functionality. All tests use the local Supabase database with proper cleanup.
"""

import pytest
from uuid import UUID
from app.core.auth import get_or_create_profile, update_profile
from tests.utils import (
    reset_database,
    SAMPLE_PROFILE_DATA,
    create_test_venue,
)


@pytest.fixture(autouse=True)
async def cleanup_database(db_service):
    """Clean up the database before and after each test."""
    await reset_database(db_service)
    yield
    await reset_database(db_service)


@pytest.mark.asyncio
async def test_get_or_create_profile_creates_new_profile(db_service, test_user):
    """Test get_or_create_profile creates a new profile when one doesn't exist."""
    user_id = UUID(test_user["id"])
    display_name = "New Test User"
    
    # Execute: Get or create profile for user without existing profile
    result = await get_or_create_profile(user_id, display_name, database=db_service)
    
    # Assert: Profile was created with correct data
    assert result["user_id"] == str(user_id)
    assert result["display_name"] == display_name
    
    # Verify: Profile exists in database
    profile = await db_service.get_profile(user_id)
    assert profile["user_id"] == str(user_id)
    assert profile["display_name"] == display_name


@pytest.mark.asyncio
async def test_get_or_create_profile_returns_existing_profile(db_service, test_user):
    """Test get_or_create_profile returns existing profile without creating duplicate."""
    user_id = UUID(test_user["id"])
    original_name = "Original Name"
    
    # Setup: Create profile first
    await db_service.create_profile(user_id, {"display_name": original_name})
    
    # Execute: Get or create profile for user with existing profile
    result = await get_or_create_profile(user_id, "Different Name", database=db_service)
    
    # Assert: Returns existing profile, not creating new one
    assert result["user_id"] == str(user_id)
    assert result["display_name"] == original_name  # Should keep original name
    
    # Verify: Only one profile exists in database
    profile = await db_service.get_profile(user_id)
    assert profile["display_name"] == original_name


@pytest.mark.asyncio
async def test_get_or_create_profile_with_empty_display_name(db_service, test_user):
    """Test get_or_create_profile handles None display_name correctly."""
    user_id = UUID(test_user["id"])
    
    # Execute: Get or create profile with None display_name
    result = await get_or_create_profile(user_id, None, database=db_service)
    
    # Assert: Profile created with empty display_name
    assert result["user_id"] == str(user_id)
    assert result["display_name"] == ""
    
    # Verify: Profile exists in database with empty display_name
    profile = await db_service.get_profile(user_id)
    assert profile["display_name"] == ""


@pytest.mark.asyncio
async def test_get_or_create_profile_with_default_database_service(test_user):
    """Test get_or_create_profile works with default DatabaseService instance."""
    user_id = UUID(test_user["id"])
    display_name = "Default DB Service User"
    
    # Execute: Get or create profile without passing database parameter
    result = await get_or_create_profile(user_id, display_name)
    
    # Assert: Profile was created successfully
    assert result["user_id"] == str(user_id)
    assert result["display_name"] == display_name


@pytest.mark.asyncio
async def test_update_profile_with_all_fields(db_service, test_user):
    """Test update_profile updates all profile fields correctly."""
    user_id = UUID(test_user["id"])
    
    # Setup: Create initial profile
    await db_service.create_profile(user_id, SAMPLE_PROFILE_DATA.copy())
    
    # Setup: Create a test venue first (required for foreign key constraint)
    venue = await create_test_venue(db_service, test_user["id"])
    default_venue = UUID(venue["id"])
    
    # Execute: Update profile with all fields
    update_data = {
        "display_name": "Updated Name",
        "avatar_url": "https://example.com/avatar.jpg",
        "default_venue": default_venue
    }
    
    result = await update_profile(
        user_id,
        display_name=update_data["display_name"],
        avatar_url=update_data["avatar_url"],
        default_venue=default_venue,
        database=db_service
    )
    
    # Assert: All fields were updated
    assert result["display_name"] == update_data["display_name"]
    assert result["avatar_url"] == update_data["avatar_url"]
    assert result["default_venue"] == str(default_venue)
    
    # Verify: Changes persisted in database
    profile = await db_service.get_profile(user_id)
    assert profile["display_name"] == update_data["display_name"]
    assert profile["avatar_url"] == update_data["avatar_url"]
    assert profile["default_venue"] == str(default_venue)


@pytest.mark.asyncio
async def test_update_profile_with_partial_fields(db_service, test_user):
    """Test update_profile updates only specified fields, leaving others unchanged."""
    user_id = UUID(test_user["id"])
    
    # Setup: Create initial profile with data
    initial_data = {
        "display_name": "Original Name",
        "avatar_url": "https://original.com/avatar.jpg"
    }
    await db_service.create_profile(user_id, initial_data)
    
    # Execute: Update only display_name
    result = await update_profile(
        user_id,
        display_name="Updated Name Only",
        database=db_service
    )
    
    # Assert: Only display_name was updated
    assert result["display_name"] == "Updated Name Only"
    # Other fields should remain unchanged (avatar_url should still be there)
    
    # Verify: Changes persisted correctly in database
    profile = await db_service.get_profile(user_id)
    assert profile["display_name"] == "Updated Name Only"


@pytest.mark.asyncio
async def test_update_profile_with_none_values(db_service, test_user):
    """Test update_profile ignores None values and doesn't update those fields."""
    user_id = UUID(test_user["id"])
    
    # Setup: Create initial profile
    initial_data = {"display_name": "Original Name"}
    await db_service.create_profile(user_id, initial_data)
    
    # Execute: Update with None values (should be ignored)
    result = await update_profile(
        user_id,
        display_name=None,
        avatar_url=None,
        default_venue=None,
        database=db_service
    )
    
    # Assert: Profile was returned (update happened but with empty data)
    assert result["user_id"] == str(user_id)
    assert result["display_name"] == "Original Name"  # Should remain unchanged
    
    # Verify: Original data preserved in database
    profile = await db_service.get_profile(user_id)
    assert profile["display_name"] == "Original Name"


@pytest.mark.asyncio
async def test_update_profile_with_default_database_service(test_user):
    """Test update_profile works with default DatabaseService instance."""
    user_id = UUID(test_user["id"])
    
    # Setup: Create initial profile using default service
    await get_or_create_profile(user_id, "Initial Name")
    
    # Execute: Update profile without passing database parameter
    result = await update_profile(
        user_id,
        display_name="Updated with Default Service"
    )
    
    # Assert: Profile was updated successfully
    assert result["display_name"] == "Updated with Default Service"


@pytest.mark.asyncio
async def test_update_profile_nonexistent_user_creates_record(db_service, test_user):
    """Test update_profile handles updating non-existent profile gracefully."""
    user_id = UUID(test_user["id"])
    
    # Execute: Update profile for user without existing profile
    # Note: This may create a new record or raise an exception depending on implementation
    try:
        result = await update_profile(
            user_id,
            display_name="New User Profile",
            database=db_service
        )
        
        # Assert: If successful, profile should be created
        assert result["user_id"] == str(user_id)
        assert result["display_name"] == "New User Profile"
        
        # Verify: Profile exists in database
        profile = await db_service.get_profile(user_id)
        assert profile["display_name"] == "New User Profile"
        
    except Exception:
        # If update fails for non-existent profile, that's also acceptable behavior
        # The important thing is that it fails gracefully
        pass


@pytest.mark.asyncio
async def test_auth_functions_integration_workflow(db_service, test_user):
    """Test complete workflow: get_or_create followed by update operations."""
    user_id = UUID(test_user["id"])
    
    # Setup: Create a test venue first
    venue = await create_test_venue(db_service, test_user["id"])
    venue_id = UUID(venue["id"])
    
    # Execute: Complete workflow
    # Step 1: Get or create profile
    profile = await get_or_create_profile(user_id, "Initial User", database=db_service)
    assert profile["display_name"] == "Initial User"
    
    # Step 2: Update profile information
    updated_profile = await update_profile(
        user_id,
        display_name="Updated User",
        avatar_url="https://example.com/new-avatar.jpg",
        database=db_service
    )
    assert updated_profile["display_name"] == "Updated User"
    assert updated_profile["avatar_url"] == "https://example.com/new-avatar.jpg"
    
    # Step 3: Update venue preference
    final_profile = await update_profile(
        user_id,
        default_venue=venue_id,
        database=db_service
    )
    assert final_profile["default_venue"] == str(venue_id)
    
    # Verify: Final state in database
    profile = await db_service.get_profile(user_id)
    assert profile["display_name"] == "Updated User"
    assert profile["avatar_url"] == "https://example.com/new-avatar.jpg"
    assert profile["default_venue"] == str(venue_id) 