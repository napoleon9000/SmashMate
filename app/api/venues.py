from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends

from app.core import venues as venues_core
from app.core.dependencies import get_database_service
from app.services.database import DatabaseService
from app.schemas.venues import CreateVenueRequest, UpdateVenueRequest, VenueResponse

router = APIRouter(prefix="/venues", tags=["venues"])


@router.post("/", response_model=VenueResponse)
async def create_venue(
    venue_data: CreateVenueRequest, 
    created_by: UUID = Query(..., description="User ID of the venue creator"),
    database: DatabaseService = Depends(get_database_service)
):
    """Create a new venue."""
    try:
        venue = await venues_core.create_venue(
            name=venue_data.name,
            latitude=venue_data.latitude,
            longitude=venue_data.longitude,
            address=venue_data.address,
            created_by=created_by,
            database=database
        )
        return VenueResponse(**venue)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nearby", response_model=List[VenueResponse])
async def find_nearby_venues(
    latitude: float = Query(..., description="Latitude coordinate"),
    longitude: float = Query(..., description="Longitude coordinate"),
    radius_meters: float = Query(5000, description="Search radius in meters"),
    database: DatabaseService = Depends(get_database_service)
):
    """Find venues within a certain radius."""
    try:
        venues = await venues_core.find_nearby_venues(latitude, longitude, radius_meters, database)
        return [VenueResponse(**venue) for venue in venues]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{venue_id}", response_model=VenueResponse)
async def get_venue(
    venue_id: UUID,
    database: DatabaseService = Depends(get_database_service)
):
    """Get venue by ID."""
    try:
        venue = await venues_core.get_venue(venue_id, database)
        if venue is None:
            raise HTTPException(status_code=404, detail="Venue not found")
        return VenueResponse(**venue)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{venue_id}", response_model=VenueResponse)
async def update_venue(
    venue_id: UUID, 
    venue_data: UpdateVenueRequest,
    database: DatabaseService = Depends(get_database_service)
):
    """Update venue information."""
    try:
        venue = await venues_core.update_venue(
            venue_id=venue_id,
            name=venue_data.name,
            latitude=venue_data.latitude,
            longitude=venue_data.longitude,
            address=venue_data.address,
            database=database
        )
        if venue is None:
            raise HTTPException(status_code=404, detail="Venue not found")
        return VenueResponse(**venue)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 