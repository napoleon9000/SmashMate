from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core import players as players_core
from app.core.dependencies import get_database_service
from app.services.database import DatabaseService

router = APIRouter(prefix="/players", tags=["players"])


@router.post("/fake")
async def create_fake_player(
    owner_id: UUID,
    display_name: str,
    database: DatabaseService = Depends(get_database_service),
):
    """Create a fake player profile."""
    try:
        player = await players_core.create_fake_player(
            owner_id=owner_id,
            display_name=display_name,
            database=database,
        )
        return player
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{fake_id}/link/{real_id}")
async def link_fake_player(
    fake_id: UUID,
    real_id: UUID,
    database: DatabaseService = Depends(get_database_service),
):
    """Link a fake player to an existing player."""
    try:
        player = await players_core.link_fake_player(
            fake_id=fake_id,
            real_player_id=real_id,
            database=database,
        )
        return player
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
