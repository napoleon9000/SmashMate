from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class PartnerProfileResponse(BaseModel):
    user_id: UUID
    display_name: str
    avatar_url: Optional[str] = None


class CompatibilityScoreResponse(BaseModel):
    partner: PartnerProfileResponse
    team_rating: float
    avg_individual_rating: float
    compatibility_score: float


class RecommendedPartnerResponse(BaseModel):
    partner: PartnerProfileResponse
    team_rating: float
    avg_individual_rating: float
    compatibility_score: float
    games_played_together: int


class PlayerInfo(BaseModel):
    id: UUID
    name: str


class TeamRankingResponse(BaseModel):
    player_a: PlayerInfo
    player_b: PlayerInfo
    team_rating: float
    games_played: int 