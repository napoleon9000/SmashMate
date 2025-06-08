"""
Unit tests for authentication API endpoints.

Tests cover profile creation, retrieval, and updates through the REST API.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.utils import (
    reset_database,
    create_test_profiles
)

client = TestClient(app)


@pytest.fixture(autouse=True)
async def cleanup_database(db_service):
    """Reset database before and after each test."""
    await reset_database(db_service)
    yield
    await reset_database(db_service)


class TestAuthAPI:
    """Test authentication API endpoints."""

    @pytest.mark.asyncio
    async def test_get_or_create_profile_creates_new_profile(self, test_user):
        """Test that GET profile endpoint creates a new profile when user doesn't exist."""
        # Setup: Use real authenticated user
        user_id = test_user["id"]
        display_name = "New Test User"
        
        # Execute: Call the API endpoint
        response = client.get(
            f"/api/v1/auth/profile/{user_id}",
            params={"display_name": display_name}
        )
        
        # Assert: Verify response
        assert response.status_code == 200
        profile_data = response.json()
        
        assert profile_data["user_id"] == user_id
        assert profile_data["display_name"] == display_name
        assert profile_data["avatar_url"] is None
        assert profile_data["default_venue"] is None

    @pytest.mark.asyncio
    async def test_get_or_create_profile_returns_existing_profile(self, db_service, test_user):
        """Test that GET profile endpoint returns existing profile without changes."""
        # Setup: Create an existing profile using the proper service
        user_id = test_user["id"]
        existing_profile = await create_test_profiles(db_service, [user_id], "Existing User")
        
        # Execute: Call the API endpoint
        response = client.get(f"/api/v1/auth/profile/{user_id}")
        
        # Assert: Verify response matches existing profile
        assert response.status_code == 200
        profile_data = response.json()
        
        assert profile_data["user_id"] == user_id
        assert profile_data["display_name"] == existing_profile[0]["display_name"]

    @pytest.mark.asyncio
    async def test_get_profile_with_invalid_uuid(self):
        """Test that GET profile endpoint handles invalid UUID format."""
        # Execute: Call API with invalid UUID
        response = client.get("/api/v1/auth/profile/invalid-uuid")
        
        # Assert: Verify error response
        assert response.status_code == 422  # Pydantic validation error

    @pytest.mark.asyncio
    async def test_update_profile_success(self, db_service, test_user, test_venue):
        """Test successful profile update with all fields."""
        # Setup: Create existing profile
        user_id = test_user["id"]
        await create_test_profiles(db_service, [user_id], "Original Name")
        
        # Setup: Prepare update data using the test venue
        update_data = {
            "display_name": "Updated Name",
            "avatar_url": "https://example.com/avatar.jpg",
            "default_venue": test_venue["id"]
        }
        
        # Execute: Call update endpoint
        response = client.put(
            f"/api/v1/auth/profile/{user_id}",
            json=update_data
        )
        
        # Assert: Verify response
        assert response.status_code == 200
        profile_data = response.json()
        
        assert profile_data["user_id"] == user_id
        assert profile_data["display_name"] == update_data["display_name"]
        assert profile_data["avatar_url"] == update_data["avatar_url"]
        assert profile_data["default_venue"] == update_data["default_venue"]

    @pytest.mark.asyncio
    async def test_update_profile_partial_update(self, db_service, test_user):
        """Test partial profile update with only display name."""
        # Setup: Create existing profile
        user_id = test_user["id"]
        original_profile = await create_test_profiles(db_service, [user_id], "Original Name")
        
        # Execute: Update only display name
        update_data = {"display_name": "Updated Name Only"}
        response = client.put(
            f"/api/v1/auth/profile/{user_id}",
            json=update_data
        )
        
        # Assert: Verify partial update
        assert response.status_code == 200
        profile_data = response.json()
        
        assert profile_data["display_name"] == "Updated Name Only"
        assert profile_data["avatar_url"] is None  # Should remain unchanged
        assert profile_data["default_venue"] is None  # Should remain unchanged

    @pytest.mark.asyncio
    async def test_update_profile_empty_request(self, db_service, test_user):
        """Test profile update with empty request body returns current profile."""
        # Setup: Create existing profile
        user_id = test_user["id"]
        original_profile = await create_test_profiles(db_service, [user_id], "Original Name")
        
        # Execute: Send empty update
        response = client.put(
            f"/api/v1/auth/profile/{user_id}",
            json={}
        )
        
        # Assert: Verify response returns original profile
        assert response.status_code == 200
        profile_data = response.json()
        
        assert profile_data["display_name"] == original_profile[0]["display_name"]

    @pytest.mark.asyncio
    async def test_update_nonexistent_profile(self, additional_test_users):
        """Test updating a profile that doesn't exist."""
        # Setup: Use a user who doesn't have a profile yet
        user_id = additional_test_users[0]["id"]
        update_data = {"display_name": "New User"}
        
        # Execute: Try to update non-existent profile
        response = client.put(
            f"/api/v1/auth/profile/{user_id}",
            json=update_data
        )
        
        # Assert: Should handle gracefully (implementation dependent)
        # This might return 404 or 500 depending on implementation
        assert response.status_code in [404, 500]

    @pytest.mark.asyncio
    async def test_update_profile_with_invalid_uuid(self):
        """Test update profile endpoint with invalid UUID format."""
        # Execute: Call API with invalid UUID
        response = client.put(
            "/api/v1/auth/profile/invalid-uuid",
            json={"display_name": "Test"}
        )
        
        # Assert: Verify validation error
        assert response.status_code == 422  # Pydantic validation error

    @pytest.mark.asyncio
    async def test_update_profile_with_invalid_venue_uuid(self, db_service, test_user):
        """Test update profile with invalid default venue UUID."""
        # Setup: Create existing profile
        user_id = test_user["id"]
        await create_test_profiles(db_service, [user_id], "Test User")
        
        # Execute: Try to update with invalid venue UUID
        update_data = {
            "display_name": "Updated Name",
            "default_venue": "invalid-venue-uuid"
        }
        
        response = client.put(
            f"/api/v1/auth/profile/{user_id}",
            json=update_data
        )
        
        # Assert: Should return validation error
        assert response.status_code == 422  # Pydantic validation error

    @pytest.mark.asyncio
    async def test_auth_endpoints_error_handling(self, db_service, test_user):
        """Test error handling in auth endpoints."""
        # Test various edge cases that might cause server errors
        
        # Setup: Create a profile first so the update doesn't fail
        user_id = test_user["id"]
        await create_test_profiles(db_service, [user_id], "Test User")
        
        # Test with None values (should be handled by Pydantic)
        # This should be handled gracefully
        response = client.put(
            f"/api/v1/auth/profile/{user_id}",
            json={"display_name": None}
        )
        
        # Should either succeed (treating None as no update) or return validation error
        assert response.status_code in [200, 422] 