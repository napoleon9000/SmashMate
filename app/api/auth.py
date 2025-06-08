from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core import auth as auth_core
from app.schemas.auth import ProfileResponse, UpdateProfileRequest

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/profile/{user_id}", response_model=ProfileResponse)
async def get_or_create_profile(
    user_id: UUID,
    display_name: Optional[str] = None
):
    """Get or create a user profile."""
    try:
        profile = await auth_core.get_or_create_profile(user_id, display_name)
        return ProfileResponse(**profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/profile/{user_id}", response_model=ProfileResponse)
async def update_profile(
    user_id: UUID,
    profile_data: UpdateProfileRequest
):
    """Update user profile information."""
    try:
        profile = await auth_core.update_profile(
            user_id=user_id,
            display_name=profile_data.display_name,
            avatar_url=profile_data.avatar_url,
            default_venue=profile_data.default_venue
        )
        return ProfileResponse(**profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 