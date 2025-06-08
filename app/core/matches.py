from datetime import datetime
from typing import Any
from uuid import UUID

from trueskill import Rating, rate

from app.services.database import DatabaseService


async def create_match(
    venue_id: UUID,
    created_by: UUID,
    team1_players: tuple[UUID, UUID],
    team2_players: tuple[UUID, UUID],
    scores: list[dict[str, int]],
    played_at: datetime,
    database: DatabaseService = None,
) -> dict[str, Any]:
    """Create a new match and update ratings."""

    if database is None:
        database = DatabaseService()
    # Determine winners based on scores
    team1_wins = sum(1 for score in scores if score["team1"] > score["team2"])
    team2_wins = sum(1 for score in scores if score["team2"] > score["team1"])
    team1_won = team1_wins > team2_wins
    
    # Create match with players
    players = [
        (team1_players[0], 1, team1_won),
        (team1_players[1], 1, team1_won),
        (team2_players[0], 2, not team1_won),
        (team2_players[1], 2, not team1_won)
    ]
    
    match = await database.create_match(
        venue_id=venue_id,
        played_at=played_at,
        created_by=created_by,
        scores=scores,
        players=players
    )
    
    # Update ratings
    await update_ratings(match["id"], database=database)
    
    return match

async def update_ratings(match_id: UUID, database: DatabaseService | None = None) -> None:
    """Update TrueSkill ratings after a match."""
    if database is None:
        database = DatabaseService()

    match = await database.get_match(match_id)
    if not match:
        return
    
    players = match["players"]
    team1_players = [p for p in players if p["team"] == 1]
    team2_players = [p for p in players if p["team"] == 2]
    
    # Get current ratings
    team1_ratings = []
    team2_ratings = []
    
    for player in team1_players:
        rating = await database.get_player_rating(UUID(player["player_id"]))
        if rating:
            team1_ratings.append(Rating(mu=float(rating["mu"]), sigma=float(rating["sigma"])))
        else:
            team1_ratings.append(Rating())
    
    for player in team2_players:
        rating = await database.get_player_rating(UUID(player["player_id"]))
        if rating:
            team2_ratings.append(Rating(mu=float(rating["mu"]), sigma=float(rating["sigma"])))
        else:
            team2_ratings.append(Rating())
    
    # Calculate new ratings
    if team1_players[0]["is_winner"]:
        new_team1_ratings, new_team2_ratings = rate([team1_ratings, team2_ratings])
    else:
        new_team2_ratings, new_team1_ratings = rate([team2_ratings, team1_ratings])
    
    # Update individual ratings
    for player, new_rating in zip(team1_players, new_team1_ratings, strict=False):
        # Get current games_played from existing rating
        current_rating = await database.get_player_rating(UUID(player["player_id"]))
        current_games_played = current_rating.get("games_played", 0) if current_rating else 0
        
        await database.update_player_rating(
            UUID(player["player_id"]),
            new_rating.mu,
            new_rating.sigma,
            current_games_played + 1
        )
    
    for player, new_rating in zip(team2_players, new_team2_ratings, strict=False):
        # Get current games_played from existing rating
        current_rating = await database.get_player_rating(UUID(player["player_id"]))
        current_games_played = current_rating.get("games_played", 0) if current_rating else 0
        
        await database.update_player_rating(
            UUID(player["player_id"]),
            new_rating.mu,
            new_rating.sigma,
            current_games_played + 1
        )
    
    # Update team ratings
    await database.create_team(
        UUID(team1_players[0]["player_id"]),
        UUID(team1_players[1]["player_id"]),
        new_team1_ratings[0].mu,
        new_team1_ratings[0].sigma
    )
    
    await database.create_team(
        UUID(team2_players[0]["player_id"]),
        UUID(team2_players[1]["player_id"]),
        new_team2_ratings[0].mu,
        new_team2_ratings[0].sigma
    )

async def get_player_matches(
    player_id: UUID, database: DatabaseService | None = None
) -> list[dict[str, Any]]:
    """Get all matches a player participated in."""
    if database is None:
        database = DatabaseService()

    return await database.get_player_matches(player_id)

async def get_venue_matches(
    venue_id: UUID, database: DatabaseService | None = None
) -> list[dict[str, Any]]:
    """Get all matches at a venue."""
    if database is None:
        database = DatabaseService()

    return await database.get_venue_matches(venue_id)

async def get_top_players(
    limit: int = 10, database: DatabaseService | None = None
) -> list[dict[str, Any]]:
    """Get top players by rating."""
    if database is None:
        database = DatabaseService()

    return await database.get_top_players(limit)
