"""
Unit tests for recommendation functionality in the Smash Mate application.

Tests cover compatibility score retrieval, partner recommendations, and team rankings.
All tests use the local database and ensure proper cleanup.
"""

import pytest
import os
from uuid import UUID, uuid4
from app.core.recommendations import get_compatibility_scores, get_recommended_partners, get_team_rankings
from app.services.database import DatabaseService


# Test configuration constants
TEST_URL = os.getenv("LOCAL_SUPABASE_URL", "http://localhost:54321")
TEST_KEY = os.getenv("LOCAL_SUPABASE_KEY", "your-test-key")


@pytest.fixture
def db_service():
    """Create a database service instance for testing."""
    return DatabaseService(TEST_URL, TEST_KEY)


@pytest.fixture(autouse=True)
async def cleanup_database(db_service):
    """Clean up the database before and after each test."""
    await reset_database(db_service)
    yield
    await reset_database(db_service)


async def reset_database(db_service) -> None:
    """Reset the database by deleting all test data."""
    tables = [
        "match_players",
        "matches", 
        "player_ratings",
        "teams",
        "follows",
        "venues",
        "profiles"
    ]
    
    for table in tables:
        try:
            db_service.client.table(table).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        except Exception:
            pass


async def create_test_profiles(db_service, user_ids: list, name_prefix: str = "User") -> list:
    """Create test profiles for a list of users."""
    profiles = []
    for i, user_id in enumerate(user_ids, 1):
        try:
            profile_data = {"display_name": f"{name_prefix} {i}"}
            profile = await db_service.create_profile(UUID(user_id), profile_data)
            profiles.append(profile)
        except Exception:
            pass  # Profile might already exist
    return profiles


async def setup_initial_ratings(db_service, user_ids: list) -> None:
    """Set up initial player ratings for a list of users."""
    for user_id in user_ids:
        try:
            await db_service.update_player_rating(
                UUID(user_id), 
                mu=25.0, 
                sigma=8.333, 
                games_played=0
            )
        except Exception:
            pass  # Rating might already exist


@pytest.mark.asyncio
async def test_get_compatibility_scores_empty_database(db_service):
    """Test getting compatibility scores when no data exists."""
    # Create a test user ID
    test_user_id = UUID(str(uuid4()))
    
    # Execute: Get compatibility scores for a user with no data
    scores = await get_compatibility_scores(test_user_id, database=db_service)
    
    # Assert: Should return empty list
    assert scores == []


@pytest.mark.asyncio
async def test_get_compatibility_scores_with_data(db_service):
    """Test getting compatibility scores with sample data."""
    # Setup: Create test user IDs
    user_ids = [str(uuid4()) for _ in range(4)]
    
    # Setup: Create profiles for all users
    await create_test_profiles(db_service, user_ids, "Player")
    
    # Setup: Create initial ratings
    await setup_initial_ratings(db_service, user_ids)
    
    # Setup: Create some teams with different ratings
    team1_data = {
        "player_a": UUID(user_ids[0]),
        "player_b": UUID(user_ids[1]),
        "mu": 26.5,
        "sigma": 7.8
    }
    
    team2_data = {
        "player_a": UUID(user_ids[0]),
        "player_b": UUID(user_ids[2]),
        "mu": 24.2,
        "sigma": 8.1
    }
    
    await db_service.create_team(**team1_data)
    await db_service.create_team(**team2_data)
    
    # Execute: Get compatibility scores
    scores = await get_compatibility_scores(UUID(user_ids[0]), database=db_service)
    
    # Assert: Function should return list
    assert isinstance(scores, list)


@pytest.mark.asyncio
async def test_get_recommended_partners_empty_database(db_service):
    """Test getting recommended partners when no data exists."""
    # Create a test user ID
    test_user_id = UUID(str(uuid4()))
    
    # Execute: Get recommended partners for a user with no data
    recommendations = await get_recommended_partners(test_user_id, database=db_service)
    
    # Assert: Should return empty list
    assert recommendations == []


@pytest.mark.asyncio
async def test_get_recommended_partners_with_parameters(db_service):
    """Test getting recommended partners with custom parameters."""
    # Setup: Create test user IDs
    user_ids = [str(uuid4()) for _ in range(4)]
    test_user_id = UUID(user_ids[0])
    
    # Setup: Create profiles
    await create_test_profiles(db_service, user_ids, "Recommended")
    
    # Execute: Get recommended partners with custom parameters
    recommendations = await get_recommended_partners(
        test_user_id, 
        limit=3, 
        min_games=5,
        database=db_service
    )
    
    # Assert: Should return list respecting the limit
    assert isinstance(recommendations, list)
    assert len(recommendations) <= 3


@pytest.mark.asyncio
async def test_get_team_rankings_empty_database(db_service):
    """Test getting team rankings when no teams exist."""
    # Execute: Get team rankings from empty database
    rankings = await get_team_rankings(database=db_service)
    
    # Assert: Should return empty list
    assert rankings == []


@pytest.mark.asyncio
async def test_get_team_rankings_with_teams(db_service):
    """Test getting team rankings with sample team data."""
    # Setup: Create test user IDs
    user_ids = [str(uuid4()) for _ in range(4)]
    
    # Setup: Create profiles for all users
    await create_test_profiles(db_service, user_ids, "Team Player")
    
    # Setup: Create initial ratings
    await setup_initial_ratings(db_service, user_ids)
    
    # Setup: Create teams with different ratings
    team_data = [
        {
            "player_a": UUID(user_ids[0]),
            "player_b": UUID(user_ids[1]),
            "mu": 28.5,
            "sigma": 7.2
        },
        {
            "player_a": UUID(user_ids[2]),
            "player_b": UUID(user_ids[3]),
            "mu": 23.8,
            "sigma": 8.5
        }
    ]
    
    # Create the teams
    for team in team_data:
        await db_service.create_team(**team)
    
    # Execute: Get team rankings
    rankings = await get_team_rankings(limit=5, database=db_service)
    
    # Assert: Should return list of teams
    assert isinstance(rankings, list)
    assert len(rankings) <= 5
    
    # Assert: Each ranking should have the correct structure
    for ranking in rankings:
        assert "player_a" in ranking
        assert "player_b" in ranking
        assert "team_rating" in ranking
        assert "games_played" in ranking
        
        # Assert: Player data structure
        assert "id" in ranking["player_a"]
        assert "name" in ranking["player_a"]
        assert "id" in ranking["player_b"]  
        assert "name" in ranking["player_b"]
        
        # Assert: Team rating should be a number
        assert isinstance(ranking["team_rating"], (int, float))
        assert isinstance(ranking["games_played"], int)


@pytest.mark.asyncio
async def test_get_team_rankings_ordered_by_rating(db_service):
    """Test that team rankings are ordered by rating (highest first)."""
    # Setup: Create test user IDs
    user_ids = [str(uuid4()) for _ in range(4)]
    
    # Setup: Create profiles
    await create_test_profiles(db_service, user_ids, "Ordered")
    
    # Setup: Create teams with clearly different ratings
    high_rating_team = {
        "player_a": UUID(user_ids[0]),
        "player_b": UUID(user_ids[1]),
        "mu": 30.0,
        "sigma": 6.0
    }
    
    low_rating_team = {
        "player_a": UUID(user_ids[2]),
        "player_b": UUID(user_ids[3]),
        "mu": 20.0,
        "sigma": 9.0
    }
    
    # Create teams
    await db_service.create_team(**low_rating_team)
    await db_service.create_team(**high_rating_team)
    
    # Execute: Get team rankings
    rankings = await get_team_rankings(database=db_service)
    
    # Assert: Should be ordered by rating (highest first)
    if len(rankings) >= 2:
        assert rankings[0]["team_rating"] >= rankings[1]["team_rating"]


@pytest.mark.asyncio
async def test_functions_with_none_database():
    """Test that functions handle None database parameter gracefully."""
    from uuid import uuid4
    
    # Create a test user ID
    test_user_id = UUID(str(uuid4()))
    
    # Execute: Test functions with None database (should create default)
    try:
        compatibility_scores = await get_compatibility_scores(test_user_id, database=None)
        recommendations = await get_recommended_partners(test_user_id, database=None)  
        rankings = await get_team_rankings(database=None)
        
        # Assert: All should return lists
        assert isinstance(compatibility_scores, list)
        assert isinstance(recommendations, list)
        assert isinstance(rankings, list)
        
    except Exception as e:
        # Connection errors are acceptable for this test
        assert any(word in str(e).lower() for word in ["database", "connection", "url", "key"])


@pytest.mark.asyncio
async def test_get_team_rankings_custom_limit(db_service):
    """Test getting team rankings with custom limit."""
    # Setup: Create test user IDs and team
    user_ids = [str(uuid4()) for _ in range(2)]
    await create_test_profiles(db_service, user_ids, "Limit Test")
    
    await db_service.create_team(
        UUID(user_ids[0]),
        UUID(user_ids[1]),
        mu=25.0,
        sigma=8.0
    )
    
    # Execute: Get team rankings with limit of 1
    rankings = await get_team_rankings(limit=1, database=db_service)
    
    # Assert: Should return at most 1 team
    assert len(rankings) <= 1 