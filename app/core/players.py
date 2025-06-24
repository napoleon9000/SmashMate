import logging
from typing import Any
from uuid import UUID

from app.services.database import DatabaseService

logger = logging.getLogger(__name__)


async def create_fake_player(
    owner_id: UUID,
    display_name: str,
    database: DatabaseService | None = None,
) -> dict[str, Any]:
    """Create a fake player owned by a user."""
    if database is None:
        database = DatabaseService()

    return await database.create_fake_player(owner_id, display_name)


async def link_fake_player(
    fake_id: UUID,
    real_player_id: UUID,
    database: DatabaseService | None = None,
) -> dict[str, Any]:
    """Link a fake player to a real player."""
    if database is None:
        database = DatabaseService()

    return await database.link_fake_to_real(fake_id, real_player_id)
