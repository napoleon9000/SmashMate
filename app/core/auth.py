from typing import Any
from uuid import UUID

from app.services.database import DatabaseService


async def get_or_create_profile(
    user_id: UUID, 
    display_name: str | None = None,
    database: DatabaseService | None = None
) -> dict[str, Any]:
    """Get or create a user profile."""
    if database is None:
        database = DatabaseService()
    
    return await database.get_or_create_profile(user_id, display_name)

async def update_profile(
    user_id: UUID,
    display_name: str | None = None,
    avatar_url: str | None = None,
    default_venue: UUID | None = None,
    database: DatabaseService | None = None
) -> dict[str, Any]:
    """Update user profile information."""
    if database is None:
        database = DatabaseService()
    
    update_data = {}
    if display_name is not None:
        update_data["display_name"] = display_name
    if avatar_url is not None:
        update_data["avatar_url"] = avatar_url
    if default_venue is not None:
        update_data["default_venue"] = str(default_venue)
    
    # If no fields to update, just return the current profile
    if not update_data:
        return await database.get_profile(user_id)
    
    return await database.update_profile(user_id, update_data) 
