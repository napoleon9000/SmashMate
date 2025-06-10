from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ProfileResponse(BaseModel):
    user_id: UUID
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    default_venue: Optional[UUID] = None


class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    default_venue: Optional[UUID] = None 