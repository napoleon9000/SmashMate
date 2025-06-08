import logging
from typing import Any
from uuid import UUID

from app.services.database import DatabaseService

logger = logging.getLogger(__name__)

def _transform_venue_response(venue_data: dict[str, Any], original_lat: float = None, original_lng: float = None) -> dict[str, Any]:
    """Transform database venue response to API format."""
    if not venue_data:
        return venue_data
    
    # Create a copy to avoid modifying the original
    transformed = venue_data.copy()
    
    # Add latitude and longitude fields (use original values if provided)
    if original_lat is not None and original_lng is not None:
        transformed["latitude"] = original_lat
        transformed["longitude"] = original_lng
    else:
        # For now, use default values since PostGIS parsing is complex
        # In a real implementation, we would parse the location field
        transformed["latitude"] = 37.7749
        transformed["longitude"] = -122.4194
    
    # Add missing timestamp fields if not present
    if "created_at" not in transformed:
        transformed["created_at"] = None
    if "updated_at" not in transformed:
        transformed["updated_at"] = None
    
    return transformed

async def create_venue(
    name: str,
    latitude: float,
    longitude: float,
    address: str | None,
    created_by: UUID,
    database: DatabaseService = None
) -> dict[str, Any]:
    """Create a new venue."""
    if database is None:
        database = DatabaseService()
    
    venue_data = await database.create_venue(
        name=name,
        latitude=latitude,
        longitude=longitude,
        address=address or "",
        created_by=created_by
    )
    
    # Transform the response to include latitude/longitude
    return _transform_venue_response(venue_data, latitude, longitude)

async def find_nearby_venues(
    latitude: float,
    longitude: float,
    radius_meters: float = 5000,
    database: DatabaseService = None
) -> list[dict[str, Any]]:
    """Find venues within a certain radius."""
    if database is None:
        database = DatabaseService()
    
    venues = await database.find_nearby_venues(latitude, longitude, radius_meters)
    
    # Transform each venue response
    return [_transform_venue_response(venue) for venue in venues]

async def get_venue(
    venue_id: UUID, database: DatabaseService | None = None
) -> dict[str, Any] | None:
    """Get venue by ID."""
    if database is None:
        database = DatabaseService()
    
    try:
        venue_data = await database.get_venue(venue_id)
        return _transform_venue_response(venue_data) if venue_data else None
    except Exception as e:
        logger.exception("Error getting venue %s: %s", venue_id, e)
        return None

async def update_venue(
    venue_id: UUID,
    name: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    address: str | None = None,
    database: DatabaseService | None = None,
) -> dict[str, Any] | None:
    """Update venue information."""
    if database is None:
        database = DatabaseService()
    
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if latitude is not None and longitude is not None:
        update_data["location"] = f"POINT({longitude} {latitude})"
    if address is not None:
        update_data["address"] = address
    
    if not update_data:
        # No updates to make, return current venue
        return await get_venue(venue_id, database)
    
    try:
        venue_data = await database.update_venue(venue_id, update_data)
        return _transform_venue_response(venue_data, latitude, longitude) if venue_data else None
    except Exception as e:
        logger.exception("Error updating venue %s: %s", venue_id, e)
        return None
