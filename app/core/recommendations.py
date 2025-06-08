from typing import List, Dict
from uuid import UUID
from app.services.database import DatabaseService

async def get_compatibility_scores(player_id: UUID, database: DatabaseService = None) -> List[Dict]:
    """Get compatibility scores for a player with all other players."""
    if database is None:
        database = DatabaseService()
    
    scores = await database.get_compatibility_scores(player_id)
    
    if not scores:
        return []
    
    # Get partner profiles
    partner_ids = [UUID(row["partner_id"]) for row in scores]
    profiles = await database.get_profiles_by_ids(partner_ids)
    profiles_dict = {p["user_id"]: p for p in profiles}
    
    return [
        {
            "partner": profiles_dict.get(row["partner_id"]),
            "team_rating": row["team_rating"],
            "avg_individual_rating": row["avg_individual_rating"],
            "compatibility_score": row["compatibility_score"]
        }
        for row in scores
        if row["partner_id"] in profiles_dict
    ]

async def get_recommended_partners(
    player_id: UUID,
    limit: int = 5,
    min_games: int = 3,
    database: DatabaseService = None
) -> List[Dict]:
    """Get recommended partners based on compatibility scores."""
    if database is None:
        database = DatabaseService()
    
    recommendations = await database.get_recommended_partners(player_id, limit, min_games)
    
    if not recommendations:
        return []
    
    # Get partner profiles
    partner_ids = [UUID(row["partner_id"]) for row in recommendations]
    profiles = await database.get_profiles_by_ids(partner_ids)
    profiles_dict = {p["user_id"]: p for p in profiles}
    
    return [
        {
            "partner": profiles_dict.get(row["partner_id"]),
            "team_rating": row["team_rating"],
            "avg_individual_rating": row["avg_individual_rating"],
            "compatibility_score": row["compatibility_score"],
            "games_played_together": row["games_played_together"]
        }
        for row in recommendations
        if row["partner_id"] in profiles_dict
    ]

async def get_team_rankings(limit: int = 10, database: DatabaseService = None) -> List[Dict]:
    """Get top teams by team rating."""
    if database is None:
        database = DatabaseService()
    
    teams = await database.get_top_teams(limit)
    
    if not teams:
        return []
    
    # Get all unique player IDs
    player_ids = set()
    for team in teams:
        player_ids.add(UUID(team["player_a"]))
        player_ids.add(UUID(team["player_b"]))
    
    # Get profiles for all players
    profiles = await database.get_profiles_by_ids(list(player_ids))
    profiles_dict = {p["user_id"]: p for p in profiles}
    
    return [
        {
            "player_a": {
                "id": team["player_a"],
                "name": profiles_dict.get(team["player_a"], {}).get("display_name", "Unknown")
            },
            "player_b": {
                "id": team["player_b"],
                "name": profiles_dict.get(team["player_b"], {}).get("display_name", "Unknown")
            },
            "team_rating": team["mu"],
            "games_played": team.get("games_played", 0)
        }
        for team in teams
    ] 