from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core import recommendations as recommendations_core
from app.schemas.recommendations import (
    CompatibilityScoreResponse,
    RecommendedPartnerResponse,
    TeamRankingResponse,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/compatibility/{player_id}", response_model=List[CompatibilityScoreResponse])
async def get_compatibility_scores(player_id: UUID):
    """Get compatibility scores for a player with all other players."""
    try:
        scores = await recommendations_core.get_compatibility_scores(player_id)
        return [CompatibilityScoreResponse(**score) for score in scores]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/partners/{player_id}", response_model=List[RecommendedPartnerResponse])
async def get_recommended_partners(
    player_id: UUID,
    limit: int = Query(5, description="Number of recommendations to return"),
    min_games: int = Query(3, description="Minimum games played together")
):
    """Get recommended partners based on compatibility scores."""
    try:
        recommendations = await recommendations_core.get_recommended_partners(
            player_id, limit, min_games
        )
        return [RecommendedPartnerResponse(**rec) for rec in recommendations]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/teams/rankings", response_model=List[TeamRankingResponse])
async def get_team_rankings(limit: int = Query(10, description="Number of top teams to return")):
    """Get top teams by team rating."""
    try:
        teams = await recommendations_core.get_team_rankings(limit)
        return [TeamRankingResponse(**team) for team in teams]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 