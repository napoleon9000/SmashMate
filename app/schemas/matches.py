from datetime import datetime
from typing import List, Any
from uuid import UUID

from pydantic import BaseModel


class ScoreData(BaseModel):
    team1: int
    team2: int


class CreateMatchRequest(BaseModel):
    venue_id: UUID
    team1_players: List[UUID]
    team2_players: List[UUID]
    scores: List[ScoreData]
    played_at: datetime


class PlayerResponse(BaseModel):
    player_id: UUID
    display_name: str
    team: int
    is_winner: bool


class MatchResponse(BaseModel):
    id: UUID
    venue_id: UUID
    played_at: datetime
    created_by: UUID
    scores: List[Any]
    players: List[Any]
    status: str
    version: int


class PlayerRatingResponse(BaseModel):
    user_id: UUID
    display_name: str
    mu: float
    sigma: float
    games_played: int 