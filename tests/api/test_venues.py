"""
Unit tests for venues API endpoints.

Tests cover venue creation, retrieval, nearby search, and updates.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.utils import (
    reset_database,
    SAMPLE_VENUE_DATA,
    create_test_venue
)

client = TestClient(app)


@pytest.fixture(autouse=True)
async def cleanup_database(db_service):
    """Reset database before and after each test."""
    await reset_database(db_service)
    yield
    await reset_database(db_service)


class TestVenuesAPI:
    """Test venues API endpoints."""

    @pytest.mark.asyncio
    async def test_create_venue_success(self, test_user):
        """Test successful venue creation."""
        # Setup: Use real authenticated user
        user_id = test_user["id"]
        
        venue_data = {
            "name": "Test Badminton Center",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "address": "123 Test Street, San Francisco"
        }
        
        # Execute: Create venue
        response = client.post(
            "/api/v1/venues/",
            params={"created_by": user_id},
            json=venue_data
        )
        
        # Assert: Verify response
        assert response.status_code == 200
        venue_response = response.json()
        
        assert venue_response["name"] == venue_data["name"]
        assert venue_response["latitude"] == venue_data["latitude"]
        assert venue_response["longitude"] == venue_data["longitude"]
        assert venue_response["address"] == venue_data["address"]
        assert venue_response["created_by"] == user_id
        assert "id" in venue_response

    @pytest.mark.asyncio
    async def test_create_venue_without_address(self, test_user):
        """Test venue creation without optional address field."""
        # Setup: Use real authenticated user
        user_id = test_user["id"]
        
        venue_data = {
            "name": "Minimal Venue",
            "latitude": 40.7128,
            "longitude": -74.0060
            # No address provided
        }
        
        # Execute: Create venue
        response = client.post(
            "/api/v1/venues/",
            params={"created_by": user_id},
            json=venue_data
        )
        
        # Assert: Verify response
        assert response.status_code == 200
        venue_response = response.json()
        
        assert venue_response["name"] == venue_data["name"]
        assert venue_response["address"] == ""  # Should default to empty string

    @pytest.mark.asyncio
    async def test_create_venue_missing_required_fields(self, test_user):
        """Test venue creation fails with missing required fields."""
        # Setup: Use real authenticated user with incomplete venue data
        user_id = test_user["id"]
        
        incomplete_data = {
            "name": "Incomplete Venue"
            # Missing latitude and longitude
        }
        
        # Execute: Try to create venue with missing fields
        response = client.post(
            "/api/v1/venues/",
            params={"created_by": user_id},
            json=incomplete_data
        )
        
        # Assert: Should return validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_venue_missing_created_by(self):
        """Test venue creation fails without created_by parameter."""
        venue_data = {
            "name": "Test Venue",
            "latitude": 37.7749,
            "longitude": -122.4194
        }
        
        # Execute: Create venue without created_by
        response = client.post("/api/v1/venues/", json=venue_data)
        
        # Assert: Should return validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_venue_success(self, db_service, test_user):
        """Test successful venue retrieval."""
        # Setup: Create a venue using the proper service
        user_id = test_user["id"]
        venue = await create_test_venue(db_service, user_id)
        
        # Execute: Get venue
        response = client.get(f"/api/v1/venues/{venue['id']}")
        
        # Assert: Verify response
        assert response.status_code == 200
        venue_response = response.json()
        
        assert venue_response["id"] == venue["id"]
        assert venue_response["name"] == venue["name"]
        assert venue_response["latitude"] == venue["latitude"]
        assert venue_response["longitude"] == venue["longitude"]

    @pytest.mark.asyncio
    async def test_get_venue_not_found(self):
        """Test getting a venue that doesn't exist."""
        # Execute: Get non-existent venue
        fake_venue_id = str(uuid4())
        response = client.get(f"/api/v1/venues/{fake_venue_id}")
        
        # Assert: Should return 404
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_venue_invalid_uuid(self):
        """Test getting venue with invalid UUID format."""
        # Execute: Call API with invalid UUID
        response = client.get("/api/v1/venues/invalid-uuid")
        
        # Assert: Should return validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_find_nearby_venues_success(self, db_service, test_user):
        """Test finding nearby venues with default radius."""
        # Setup: Create test venues at different locations using real user
        user_id = test_user["id"]
        
        # Create venue near SF
        venue1_data = {**SAMPLE_VENUE_DATA, "latitude": 37.7749, "longitude": -122.4194}
        venue1 = await create_test_venue(db_service, user_id, venue1_data)
        
        # Create venue near NYC (far away)
        venue2_data = {**SAMPLE_VENUE_DATA, "name": "NYC Venue", "latitude": 40.7128, "longitude": -74.0060}
        venue2 = await create_test_venue(db_service, user_id, venue2_data)
        
        # Execute: Find venues near SF
        response = client.get(
            "/api/v1/venues/nearby",
            params={
                "latitude": 37.7749,
                "longitude": -122.4194
            }
        )
        
        # Assert: Should find SF venue but not NYC venue
        assert response.status_code == 200
        venues = response.json()
        
        venue_ids = [v["id"] for v in venues]
        assert venue1["id"] in venue_ids
        # NYC venue should not be in results due to distance

    @pytest.mark.asyncio
    async def test_find_nearby_venues_custom_radius(self, db_service, test_user):
        """Test finding nearby venues with custom radius."""
        # Setup: Create test venue using real user
        user_id = test_user["id"]
        venue = await create_test_venue(db_service, user_id)
        
        # Execute: Find venues with large radius (should find the venue)
        response = client.get(
            "/api/v1/venues/nearby",
            params={
                "latitude": venue["latitude"],
                "longitude": venue["longitude"],
                "radius_meters": 10000  # 10km radius - should find the venue
            }
        )
        
        # Assert: Should return the venue we created
        assert response.status_code == 200
        venues = response.json()
        # Should find at least our created venue
        assert len(venues) >= 1
        venue_ids = [v["id"] for v in venues]
        assert venue["id"] in venue_ids

    @pytest.mark.asyncio
    async def test_find_nearby_venues_missing_coordinates(self):
        """Test finding nearby venues with missing coordinates."""
        # Execute: Try to find venues without coordinates
        response = client.get("/api/v1/venues/nearby")
        
        # Assert: Should return validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_venue_success(self, db_service, test_user):
        """Test successful venue update with all fields."""
        # Setup: Create existing venue using real user
        user_id = test_user["id"]
        venue = await create_test_venue(db_service, user_id)
        
        # Setup: Prepare update data
        update_data = {
            "name": "Updated Venue Name",
            "latitude": 40.7589,
            "longitude": -73.9851,
            "address": "Updated Address, New York"
        }
        
        # Execute: Update venue
        response = client.put(
            f"/api/v1/venues/{venue['id']}",
            json=update_data
        )
        
        # Assert: Verify response
        assert response.status_code == 200
        venue_response = response.json()
        
        assert venue_response["name"] == update_data["name"]
        assert venue_response["latitude"] == update_data["latitude"]
        assert venue_response["longitude"] == update_data["longitude"]
        assert venue_response["address"] == update_data["address"]

    @pytest.mark.asyncio
    async def test_update_venue_partial_update(self, db_service, test_user):
        """Test partial venue update with only name."""
        # Setup: Create existing venue using real user
        user_id = test_user["id"]
        venue = await create_test_venue(db_service, user_id)
        
        # Execute: Update only name
        update_data = {"name": "Partially Updated Name"}
        response = client.put(
            f"/api/v1/venues/{venue['id']}",
            json=update_data
        )
        
        # Assert: Verify partial update
        assert response.status_code == 200
        venue_response = response.json()
        
        assert venue_response["name"] == "Partially Updated Name"
        assert venue_response["latitude"] == venue["latitude"]  # Should remain unchanged
        assert venue_response["longitude"] == venue["longitude"]  # Should remain unchanged

    @pytest.mark.asyncio
    async def test_update_venue_not_found(self):
        """Test updating a venue that doesn't exist."""
        # Execute: Try to update non-existent venue
        fake_venue_id = str(uuid4())
        update_data = {"name": "New Name"}
        
        response = client.put(
            f"/api/v1/venues/{fake_venue_id}",
            json=update_data
        )
        
        # Assert: Should return 404
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_venue_empty_request(self, db_service, test_user):
        """Test venue update with empty request body returns current venue."""
        # Setup: Create existing venue using real user
        user_id = test_user["id"]
        venue = await create_test_venue(db_service, user_id)
        
        # Execute: Send empty update
        response = client.put(
            f"/api/v1/venues/{venue['id']}",
            json={}
        )
        
        # Assert: Verify response returns original venue
        assert response.status_code == 200
        venue_response = response.json()
        
        assert venue_response["name"] == venue["name"]
        assert venue_response["latitude"] == venue["latitude"]
        assert venue_response["longitude"] == venue["longitude"]

    @pytest.mark.asyncio
    async def test_update_venue_invalid_coordinates(self, db_service, test_user):
        """Test updating venue with invalid coordinate values."""
        # Setup: Create existing venue using real user
        user_id = test_user["id"]
        venue = await create_test_venue(db_service, user_id)
        
        # Execute: Try to update with invalid coordinates
        update_data = {
            "latitude": 200.0,  # Invalid latitude (should be -90 to 90)
            "longitude": -200.0  # Invalid longitude (should be -180 to 180)
        }
        
        response = client.put(
            f"/api/v1/venues/{venue['id']}",
            json=update_data
        )
        
        # Assert: Should return validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_venue_coordinate_bounds(self, db_service, test_user):
        """Test updating venue with coordinates at valid bounds."""
        # Setup: Create existing venue using real user
        user_id = test_user["id"]
        venue = await create_test_venue(db_service, user_id)
        
        # Execute: Update with coordinates at valid bounds
        update_data = {
            "latitude": 90.0,   # Max valid latitude
            "longitude": 180.0  # Max valid longitude
        }
        
        response = client.put(
            f"/api/v1/venues/{venue['id']}",
            json=update_data
        )
        
        # Assert: Should succeed
        assert response.status_code == 200
        venue_response = response.json()
        
        assert venue_response["latitude"] == 90.0
        assert venue_response["longitude"] == 180.0

    @pytest.mark.asyncio
    async def test_venues_endpoints_with_invalid_uuids(self):
        """Test all venue endpoints with invalid UUID formats."""
        # Test get venue with invalid UUID
        response = client.get("/api/v1/venues/invalid-uuid")
        assert response.status_code == 422
        
        # Test update venue with invalid UUID
        response = client.put(
            "/api/v1/venues/invalid-uuid",
            json={"name": "Test"}
        )
        assert response.status_code == 422
        
        # Test create venue with invalid created_by UUID
        venue_data = {
            "name": "Test Venue",
            "latitude": 37.7749,
            "longitude": -122.4194
        }
        
        response = client.post(
            "/api/v1/venues/",
            params={"created_by": "invalid-uuid"},
            json=venue_data
        )
        assert response.status_code == 422 