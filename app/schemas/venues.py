from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CreateVenueRequest(BaseModel):
    name: str
    latitude: float = Field(..., ge=-90, le=90, description="Latitude must be between -90 and 90 degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude must be between -180 and 180 degrees")
    address: Optional[str] = None


class UpdateVenueRequest(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude must be between -90 and 180 degrees")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude must be between -180 and 180 degrees")
    address: Optional[str] = None


class VenueResponse(BaseModel):
    id: UUID
    name: str
    latitude: float
    longitude: float
    address: str
    created_by: UUID 