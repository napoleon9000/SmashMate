from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends

from app.core import matches as matches_core
from app.schemas.matches import CreateMatchRequest, MatchResponse, PlayerRatingResponse
from app.core.dependencies import get_database_service
from app.services.database import DatabaseService

router = APIRouter(prefix="/matches", tags=["matches"])


@router.post("/", response_model=MatchResponse)
async def create_match(
    match_data: CreateMatchRequest, 
    created_by: UUID = Query(..., description="User ID of the match creator"),
    database: DatabaseService = Depends(get_database_service)
):
    """Create a new match and update ratings."""
    # Validate that we have exactly 2 players per team
    if len(match_data.team1_players) != 2 or len(match_data.team2_players) != 2:
        raise HTTPException(
            status_code=400, 
            detail="Each team must have exactly 2 players"
        )
    
    try:
        # Create the match using the core business logic
        match = await matches_core.create_match(
            venue_id=match_data.venue_id,
            created_by=created_by,
            team1_players=(match_data.team1_players[0], match_data.team1_players[1]),
            team2_players=(match_data.team2_players[0], match_data.team2_players[1]),
            scores=[{"team1": score.team1, "team2": score.team2} for score in match_data.scores],
            played_at=match_data.played_at,
            database=database
        )
        
        # Fetch the complete match with players for proper response serialization
        complete_match = await database.get_match(UUID(match["id"]))
        
        return complete_match
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create match: {str(e)}")


@router.get("/player/{player_id}")
async def get_player_matches(
    player_id: UUID,
    database: DatabaseService = Depends(get_database_service)
):
    """Get all matches a player participated in."""
    try:
        matches = await matches_core.get_player_matches(player_id, database=database)
        return matches
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/venue/{venue_id}")
async def get_venue_matches(
    venue_id: UUID,
    database: DatabaseService = Depends(get_database_service)
):
    """Get all matches at a venue."""
    try:
        matches = await matches_core.get_venue_matches(venue_id, database=database)
        return matches
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leaderboard", response_model=List[PlayerRatingResponse])
async def get_top_players(
    limit: int = 10,
    database: DatabaseService = Depends(get_database_service)
):
    """Get top players by rating."""
    try:
        players = await matches_core.get_top_players(limit, database=database)
        
        # Transform the data to match the expected schema
        transformed_players = []
        for player in players:
            # Get the player's profile to get their display name
            profile = await database.get_profiles_by_ids([UUID(player["player_id"])])
            if profile:
                transformed_players.append({
                    "user_id": UUID(player["player_id"]),
                    "display_name": profile[0]["display_name"],
                    "mu": float(player["mu"]),
                    "sigma": float(player["sigma"]),
                    "games_played": player["games_played"]
                })
        
        return [PlayerRatingResponse(**player) for player in transformed_players]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 