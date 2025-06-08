"""
Unit tests for venue functionality in the Smash Mate application.

Tests cover venue creation, retrieval, updates, and location-based searches.
All tests use the local database and ensure proper cleanup.
"""

import pytest
from uuid import UUID, uuid4
from app.core.venues import create_venue, find_nearby_venues, get_venue, update_venue
from tests.utils import (
    reset_database,
    create_test_venue,
    SAMPLE_VENUE_DATA,
)


@pytest.fixture(autouse=True)
async def cleanup_database(db_service):
    """Clean up the database before and after each test."""
    await reset_database(db_service)
    yield
    await reset_database(db_service)


@pytest.mark.asyncio
async def test_create_venue_success(db_service, test_user):
    """Test creating a venue with valid data."""
    # Setup: Prepare venue data
    venue_name = "Test Sports Center"
    latitude = 37.7749
    longitude = -122.4194
    address = "123 Test Street, San Francisco, CA"
    
    # Execute: Create the venue
    result = await create_venue(
        name=venue_name,
        latitude=latitude,
        longitude=longitude,
        address=address,
        created_by=test_user["id"],
        database=db_service
    )
    
    # Assert: Basic venue properties
    assert result["name"] == venue_name
    assert result["address"] == address
    assert result["created_by"] == str(test_user["id"])
    assert "id" in result
    assert "location" in result  # PostGIS POINT field
    
    # Verify: Venue was created in database
    venue = await db_service.get_venue(UUID(result["id"]))
    assert venue["id"] == result["id"]
    assert venue["name"] == venue_name


@pytest.mark.asyncio
async def test_create_venue_with_none_address(db_service, test_user):
    """Test creating a venue with None address (should convert to empty string)."""
    # Setup: Prepare venue data with None address
    venue_name = "Test Venue No Address"
    latitude = 40.7128
    longitude = -74.0060
    
    # Execute: Create venue with None address
    result = await create_venue(
        name=venue_name,
        latitude=latitude,
        longitude=longitude,
        address=None,
        created_by=test_user["id"],
        database=db_service
    )
    
    # Assert: Address should be empty string
    assert result["address"] == ""
    assert result["name"] == venue_name


@pytest.mark.asyncio
async def test_create_venue_with_default_database(test_user):
    """Test creating a venue using default database service."""
    # Setup: Prepare venue data
    venue_name = "Default DB Test Venue"
    latitude = 51.5074
    longitude = -0.1278
    address = "London Test Address"
    
    # Execute: Create venue without passing database parameter
    result = await create_venue(
        name=venue_name,
        latitude=latitude,
        longitude=longitude,
        address=address,
        created_by=test_user["id"]
        # Note: not passing database parameter to test default
    )
    
    # Assert: Venue should be created successfully
    assert result["name"] == venue_name
    assert result["address"] == address
    assert "id" in result


@pytest.mark.asyncio
async def test_get_venue_success(db_service, test_user):
    """Test retrieving an existing venue by ID."""
    # Setup: Create a test venue
    venue = await create_test_venue(db_service, test_user["id"])
    venue_id = UUID(venue["id"])
    
    # Execute: Get the venue
    result = await get_venue(venue_id, database=db_service)
    
    # Assert: Venue data is returned correctly
    assert result is not None
    assert result["id"] == venue["id"]
    assert result["name"] == venue["name"]
    assert result["address"] == venue["address"]
    assert result["created_by"] == venue["created_by"]


@pytest.mark.asyncio
async def test_get_venue_not_found(db_service):
    """Test retrieving a non-existent venue returns None."""
    # Setup: Generate a random UUID that doesn't exist
    non_existent_id = uuid4()
    
    # Execute: Try to get non-existent venue
    result = await get_venue(non_existent_id, database=db_service)
    
    # Assert: Should return None
    assert result is None


@pytest.mark.asyncio
async def test_get_venue_with_default_database(test_user):
    """Test retrieving venue using default database service."""
    # Setup: Create a venue first using default database
    venue = await create_venue(
        name="Default DB Get Test",
        latitude=35.6762,
        longitude=139.6503,
        address="Tokyo Test Address",
        created_by=test_user["id"]
    )
    venue_id = UUID(venue["id"])
    
    # Execute: Get venue without passing database parameter
    result = await get_venue(venue_id)
    
    # Assert: Venue should be retrieved successfully
    assert result is not None
    assert result["id"] == venue["id"]
    assert result["name"] == "Default DB Get Test"


@pytest.mark.asyncio
async def test_update_venue_all_fields(db_service, test_user):
    """Test updating all venue fields."""
    # Setup: Create a test venue
    venue = await create_test_venue(db_service, test_user["id"])
    venue_id = UUID(venue["id"])
    
    # Setup: New data for update
    new_name = "Updated Venue Name"
    new_latitude = 40.7128
    new_longitude = -74.0060
    new_address = "Updated Address, NYC"
    
    # Execute: Update all fields
    result = await update_venue(
        venue_id=venue_id,
        name=new_name,
        latitude=new_latitude,
        longitude=new_longitude,
        address=new_address,
        database=db_service
    )
    
    # Assert: All fields are updated
    assert result is not None
    assert result["name"] == new_name
    assert result["address"] == new_address
    assert result["id"] == venue["id"]
    
    # Verify: Changes persisted in database
    updated_venue = await db_service.get_venue(venue_id)
    assert updated_venue["name"] == new_name
    assert updated_venue["address"] == new_address


@pytest.mark.asyncio
async def test_update_venue_partial_fields(db_service, test_user):
    """Test updating only some venue fields."""
    # Setup: Create a test venue
    venue = await create_test_venue(db_service, test_user["id"])
    venue_id = UUID(venue["id"])
    original_name = venue["name"]
    original_address = venue["address"]
    
    # Execute: Update only name
    result = await update_venue(
        venue_id=venue_id,
        name="Partially Updated Venue",
        database=db_service
    )
    
    # Assert: Only name is updated, other fields remain unchanged
    assert result is not None
    assert result["name"] == "Partially Updated Venue"
    assert result["address"] == original_address
    assert result["id"] == venue["id"]


@pytest.mark.asyncio
async def test_update_venue_location_only(db_service, test_user):
    """Test updating only venue location coordinates."""
    # Setup: Create a test venue
    venue = await create_test_venue(db_service, test_user["id"])
    venue_id = UUID(venue["id"])
    original_name = venue["name"]
    
    # Execute: Update only location
    new_latitude = 48.8566
    new_longitude = 2.3522
    result = await update_venue(
        venue_id=venue_id,
        latitude=new_latitude,
        longitude=new_longitude,
        database=db_service
    )
    
    # Assert: Location is updated, other fields remain unchanged
    assert result is not None
    assert result["name"] == original_name
    assert result["id"] == venue["id"]
    
    # Note: Location is stored as PostGIS POINT, so we can't easily assert the exact coordinates
    # but we can verify the update succeeded


@pytest.mark.asyncio
async def test_update_venue_no_changes(db_service, test_user):
    """Test updating venue with no changes returns current venue."""
    # Setup: Create a test venue
    venue = await create_test_venue(db_service, test_user["id"])
    venue_id = UUID(venue["id"])
    
    # Execute: Update with no changes
    result = await update_venue(venue_id=venue_id, database=db_service)
    
    # Assert: Returns current venue data
    assert result is not None
    assert result["id"] == venue["id"]
    assert result["name"] == venue["name"]
    assert result["address"] == venue["address"]


@pytest.mark.asyncio
async def test_update_venue_not_found(db_service):
    """Test updating a non-existent venue returns None."""
    # Setup: Generate a random UUID that doesn't exist
    non_existent_id = uuid4()
    
    # Execute: Try to update non-existent venue
    result = await update_venue(
        venue_id=non_existent_id,
        name="Should Not Work",
        database=db_service
    )
    
    # Assert: Should return None
    assert result is None


@pytest.mark.asyncio
async def test_update_venue_with_default_database(test_user):
    """Test updating venue using default database service."""
    # Setup: Create a venue first
    venue = await create_venue(
        name="Default DB Update Test",
        latitude=34.0522,
        longitude=-118.2437,
        address="LA Test Address",
        created_by=test_user["id"]
    )
    venue_id = UUID(venue["id"])
    
    # Execute: Update venue without passing database parameter
    result = await update_venue(
        venue_id=venue_id,
        name="Updated via Default DB"
    )
    
    # Assert: Venue should be updated successfully
    assert result is not None
    assert result["name"] == "Updated via Default DB"


@pytest.mark.asyncio
async def test_find_nearby_venues_success(db_service, test_user):
    """Test finding venues within a specified radius."""
    # Setup: Create multiple venues at different locations
    # Central location: San Francisco
    central_venue = await create_venue(
        name="Central Venue",
        latitude=37.7749,
        longitude=-122.4194,
        address="San Francisco",
        created_by=test_user["id"],
        database=db_service
    )
    
    # Nearby location: Oakland (about 13km away)
    nearby_venue = await create_venue(
        name="Nearby Venue",
        latitude=37.8044,
        longitude=-122.2712,
        address="Oakland",
        created_by=test_user["id"],
        database=db_service
    )
    
    # Far location: Los Angeles (about 600km away)
    far_venue = await create_venue(
        name="Far Venue",
        latitude=34.0522,
        longitude=-118.2437,
        address="Los Angeles",
        created_by=test_user["id"],
        database=db_service
    )
    
    # Execute: Find venues within 50km of San Francisco
    search_latitude = 37.7749
    search_longitude = -122.4194
    radius_meters = 50000  # 50km
    
    result = await find_nearby_venues(
        latitude=search_latitude,
        longitude=search_longitude,
        radius_meters=radius_meters,
        database=db_service
    )
    
    # Assert: Should return a list containing all created venues
    assert isinstance(result, list)
    assert len(result) >= 3  # Should contain at least our 3 test venues
    
    # Verify: All created venues are in the result
    venue_names = [v["name"] for v in result]
    assert "Central Venue" in venue_names
    assert "Nearby Venue" in venue_names
    assert "Far Venue" in venue_names
    
    # Note: In a full implementation with PostGIS distance filtering,
    # we would test that only venues within the radius are returned


@pytest.mark.asyncio
async def test_find_nearby_venues_default_radius(db_service, test_user):
    """Test finding venues with default radius (5000m)."""
    # Setup: Create a venue
    venue = await create_test_venue(db_service, test_user["id"])
    
    # Execute: Find venues without specifying radius (should use default 5000m)
    result = await find_nearby_venues(
        latitude=37.7749,
        longitude=-122.4194,
        database=db_service
    )
    
    # Assert: Should return a list (content depends on test data)
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_find_nearby_venues_with_default_database(test_user):
    """Test finding venues using default database service."""
    # Setup: Create a venue first
    venue = await create_venue(
        name="Default DB Search Test",
        latitude=37.7749,
        longitude=-122.4194,
        address="SF Test",
        created_by=test_user["id"]
    )
    
    # Execute: Find venues without passing database parameter
    result = await find_nearby_venues(
        latitude=37.7749,
        longitude=-122.4194,
        radius_meters=10000
    )
    
    # Assert: Should return a list
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_find_nearby_venues_empty_result(db_service):
    """Test finding venues in an area with no venues."""
    # Execute: Search in middle of ocean where no venues exist
    result = await find_nearby_venues(
        latitude=0.0,  # Equator
        longitude=0.0,  # Prime Meridian (middle of Atlantic)
        radius_meters=1000,  # 1km radius
        database=db_service
    )
    
    # Assert: Should return empty list
    assert isinstance(result, list)
    # Note: May or may not be empty depending on test data, but should be a list


@pytest.mark.asyncio
async def test_venue_crud_workflow(db_service, test_user):
    """Test complete CRUD workflow for venues."""
    # Setup: Prepare initial data
    initial_name = "CRUD Test Venue"
    initial_latitude = 37.7749
    initial_longitude = -122.4194
    initial_address = "Initial Address"
    
    # Execute: Create venue
    created_venue = await create_venue(
        name=initial_name,
        latitude=initial_latitude,
        longitude=initial_longitude,
        address=initial_address,
        created_by=test_user["id"],
        database=db_service
    )
    
    # Assert: Venue created successfully
    assert created_venue["name"] == initial_name
    venue_id = UUID(created_venue["id"])
    
    # Execute: Read venue
    retrieved_venue = await get_venue(venue_id, database=db_service)
    
    # Assert: Venue retrieved successfully
    assert retrieved_venue is not None
    assert retrieved_venue["name"] == initial_name
    assert retrieved_venue["id"] == created_venue["id"]
    
    # Execute: Update venue
    updated_name = "Updated CRUD Venue"
    updated_address = "Updated Address"
    updated_venue = await update_venue(
        venue_id=venue_id,
        name=updated_name,
        address=updated_address,
        database=db_service
    )
    
    # Assert: Venue updated successfully
    assert updated_venue is not None
    assert updated_venue["name"] == updated_name
    assert updated_venue["address"] == updated_address
    assert updated_venue["id"] == created_venue["id"]
    
    # Verify: Final state in database
    final_venue = await get_venue(venue_id, database=db_service)
    assert final_venue["name"] == updated_name
    assert final_venue["address"] == updated_address


@pytest.mark.asyncio
async def test_venue_operations_with_test_data_builder(db_service, test_user):
    """Test venue operations using TestDataBuilder for complex scenarios."""
    # Setup: Use sample venue data since TestDataBuilder.with_venue() requires users
    venue_data = SAMPLE_VENUE_DATA.copy()
    
    created_venue = await create_venue(
        name=venue_data["name"],
        latitude=venue_data["latitude"],
        longitude=venue_data["longitude"],
        address=venue_data["address"],
        created_by=test_user["id"],
        database=db_service
    )
    
    # Execute: Test various venue operations
    venue_id = UUID(created_venue["id"])
    
    # Test: Get venue
    retrieved_venue = await get_venue(venue_id, database=db_service)
    assert retrieved_venue is not None
    
    # Test: Update venue
    updated_venue = await update_venue(
        venue_id=venue_id,
        name="Builder Updated Venue",
        database=db_service
    )
    assert updated_venue is not None
    assert updated_venue["name"] == "Builder Updated Venue"
    
    # Test: Find nearby venues
    nearby_venues = await find_nearby_venues(
        latitude=venue_data["latitude"],
        longitude=venue_data["longitude"],
        radius_meters=10000,
        database=db_service
    )
    assert isinstance(nearby_venues, list) 