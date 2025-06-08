from typing import List, Optional, Dict, Any
from uuid import UUID
import traceback
from app.services.database import DatabaseService

async def create_venue(
    name: str,
    latitude: float,
    longitude: float,
    address: Optional[str],
    created_by: UUID,
    database: DatabaseService = None
) -> Dict[str, Any]:
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
) -> List[Dict[str, Any]]:
    """Find venues within a certain radius."""
    if database is None:
        database = DatabaseService()
    
    return await database.find_nearby_venues(latitude, longitude, radius_meters)

async def get_venue(venue_id: UUID, database: DatabaseService = None) -> Optional[Dict[str, Any]]:
    """Get venue by ID."""
    if database is None:
        database = DatabaseService()
    
    try:
        return await database.get_venue(venue_id)
    except Exception as e:
        print(f"Error getting venue {venue_id}: {str(e)}")
        traceback.print_exc()
        return None

async def update_venue(
    venue_id: UUID,
    name: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    address: Optional[str] = None,
    database: DatabaseService = None
) -> Optional[Dict[str, Any]]:
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
        print(f"Error updating venue {venue_id}: {str(e)}")
        traceback.print_exc()
        return None 