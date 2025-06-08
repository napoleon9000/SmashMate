import logging
from typing import Any
from uuid import UUID

from app.services.database import DatabaseService

logger = logging.getLogger(__name__)

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
    
    return await database.create_venue(
        name=name,
        latitude=latitude,
        longitude=longitude,
        address=address or "",
        created_by=created_by
    )

async def find_nearby_venues(
    latitude: float,
    longitude: float,
    radius_meters: float = 5000,
    database: DatabaseService = None
) -> list[dict[str, Any]]:
    """Find venues within a certain radius."""
    if database is None:
        database = DatabaseService()
    
    return await database.find_nearby_venues(latitude, longitude, radius_meters)

async def get_venue(
    venue_id: UUID, database: DatabaseService | None = None
) -> dict[str, Any] | None:
    """Get venue by ID."""
    if database is None:
        database = DatabaseService()
    
    try:
        return await database.get_venue(venue_id)
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
        return await database.update_venue(venue_id, update_data)
    except Exception as e:
        logger.exception("Error updating venue %s: %s", venue_id, e)
        return None
