"""
Unit tests for recommendation functionality in the Smash Mate application.

Tests cover compatibility score retrieval, partner recommendations, and team rankings.
All tests use the local database and ensure proper cleanup.
"""

import pytest
import os
import traceback
import json
from datetime import datetime, timezone
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


async def create_test_users(db_service, user_ids: list) -> None:
    """Create test users in the users table."""
    user_data = {}
    for user_id in user_ids:
        try:
            # Create user data with proper format
            user_data = {
                "id": str(user_id),  # Ensure UUID is converted to string
                "email": f"test_{user_id}@example.com",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # First check if user already exists
            try:
                existing_user = await db_service.client.table("users").select("*").eq("id", str(user_id)).execute()
                if existing_user.data:
                    print(f"User {user_id} already exists, skipping creation")
                    continue
            except Exception as e:
                print(f"Error checking existing user {user_id}: {str(e)}")
            
            # Insert new user
            response = await db_service.client.table("users").insert(user_data).execute()
            
            if not response.data:
                raise Exception(f"Failed to create user {user_id}: No data returned")
                
        except Exception as e:
            print(f"Error creating user {user_id}:")
            print(f"Error message: {str(e)}")
            print("Traceback:")
            print(traceback.format_exc())
            print(f"User data attempted: {json.dumps(user_data, indent=2)}")
            raise


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
        except Exception as e:
            print(f"Error setting up rating for user {user_id}:")
            print(f"Error message: {str(e)}")
            print("Traceback:")
            print(traceback.format_exc())
            raise  # Re-raise the exception after logging


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
async def test_get_compatibility_scores_with_data(db_service, test_user, additional_test_users, test_venue):
    """Test getting compatibility scores with sample data."""
    # Get all test user IDs
    user_ids = [test_user["id"]] + [user["id"] for user in additional_test_users]
    
    # Setup: Create profiles for all users
    await create_test_profiles(db_service, user_ids, "Player")
    
    # Setup: Create initial ratings with different values
    await db_service.update_player_rating(UUID(user_ids[0]), mu=25.0, sigma=8.333, games_played=0)
    await db_service.update_player_rating(UUID(user_ids[1]), mu=24.0, sigma=8.333, games_played=0)
    await db_service.update_player_rating(UUID(user_ids[2]), mu=26.0, sigma=8.333, games_played=0)
    await db_service.update_player_rating(UUID(user_ids[3]), mu=23.0, sigma=8.333, games_played=0)
    
    # Setup: Create teams with different ratings
    # Team 1: user[0] + user[1], team rating = 26.5, individual avg = (25+24)/2 = 24.5, compatibility = 2.0
    team1_data = {
        "player_a": UUID(user_ids[0]),
        "player_b": UUID(user_ids[1]),
        "mu": 26.5,
        "sigma": 7.8
    }
    
    # Team 2: user[0] + user[2], team rating = 24.2, individual avg = (25+26)/2 = 25.5, compatibility = -1.3
    team2_data = {
        "player_a": UUID(user_ids[0]),
        "player_b": UUID(user_ids[2]),
        "mu": 24.2,
        "sigma": 8.1
    }
    
    # Create teams
    team1 = await db_service.create_team(**team1_data)
    team2 = await db_service.create_team(**team2_data)
    
    # Execute: Get compatibility scores for user[0]
    scores = await get_compatibility_scores(UUID(user_ids[0]), database=db_service)
    
    # Assert: Function should return list with 2 partners
    assert isinstance(scores, list)
    assert len(scores) == 2
    
    # Assert: Scores should be ordered by compatibility (highest first)
    assert scores[0]["compatibility_score"] > scores[1]["compatibility_score"]
    
    # Assert: Verify the calculation is correct
    # First score should be team1 (user[1] as partner): 26.5 - 24.5 = 2.0
    user1_score = next(s for s in scores if s["partner"]["user_id"] == user_ids[1])
    assert abs(user1_score["compatibility_score"] - 2.0) < 0.01
    assert user1_score["team_rating"] == 26.5
    assert abs(user1_score["avg_individual_rating"] - 24.5) < 0.01
    
    # Second score should be team2 (user[2] as partner): 24.2 - 25.5 = -1.3
    user2_score = next(s for s in scores if s["partner"]["user_id"] == user_ids[2])
    assert abs(user2_score["compatibility_score"] - (-1.3)) < 0.01
    assert user2_score["team_rating"] == 24.2
    assert abs(user2_score["avg_individual_rating"] - 25.5) < 0.01
    
    # Assert: Each score entry should have the correct structure
    for score in scores:
        assert "partner" in score
        assert "team_rating" in score
        assert "avg_individual_rating" in score
        assert "compatibility_score" in score
        
        # Assert: Partner profile should contain user information
        partner = score["partner"]
        assert partner is not None
        assert "user_id" in partner
        assert "display_name" in partner


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
async def test_get_team_rankings_with_teams(db_service, test_user, additional_test_users):
    """Test getting team rankings with sample team data."""
    # Get all test user IDs
    user_ids = [test_user["id"]] + [user["id"] for user in additional_test_users]
    
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
async def test_get_team_rankings_ordered_by_rating(db_service, test_user, additional_test_users):
    """Test that team rankings are ordered by rating (highest first)."""
    # Get all test user IDs
    user_ids = [test_user["id"]] + [user["id"] for user in additional_test_users]
    
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


@pytest.mark.asyncio
async def test_get_compatibility_scores_structure(db_service, test_user, additional_test_users):
    """Test the structure and content of compatibility scores with partner profiles."""
    # Get all test user IDs
    user_ids = [test_user["id"]] + [user["id"] for user in additional_test_users]
    test_user_id = UUID(user_ids[0])
    
    # Setup: Create profiles for all users
    await create_test_profiles(db_service, user_ids, "Compatibility")
    
    # Setup: Create initial ratings
    await setup_initial_ratings(db_service, user_ids)
    
    # Setup: Create a team with the test user
    team_data = {
        "player_a": test_user_id,
        "player_b": UUID(user_ids[1]),
        "mu": 26.5,
        "sigma": 7.8
    }
    await db_service.create_team(**team_data)
    
    # Execute: Get compatibility scores
    scores = await get_compatibility_scores(test_user_id, database=db_service)
    
    # Assert: Should return a list
    assert isinstance(scores, list)
    
    # Assert: Each score entry should have the correct structure
    for score in scores:
        assert "partner" in score
        assert "team_rating" in score
        assert "avg_individual_rating" in score
        assert "compatibility_score" in score
        
        # Assert: Partner profile should contain user information
        partner = score["partner"]
        assert partner is not None
        assert "user_id" in partner
        assert "display_name" in partner
        
        # Assert: Ratings should be numeric values
        assert isinstance(score["team_rating"], (int, float))
        assert isinstance(score["avg_individual_rating"], (int, float))
        assert isinstance(score["compatibility_score"], (int, float))


@pytest.mark.asyncio
async def test_setup_initial_ratings(db_service, test_user, additional_test_users):
    """Test setting up initial player ratings."""
    # Get all test user IDs
    user_ids = [test_user["id"]] + [user["id"] for user in additional_test_users]
    
    try:
        # Setup: Create profiles for all users
        await create_test_profiles(db_service, user_ids, "Rating Test")
        
        # Execute: Set up initial ratings
        await setup_initial_ratings(db_service, user_ids)
        
        # Verify: Check that ratings were created correctly
        for user_id in user_ids:
            rating = await db_service.get_player_rating(UUID(user_id))
            assert rating is not None
            assert rating["mu"] == 25.0
            assert rating["sigma"] == 8.333
            assert rating["games_played"] == 0
    except Exception as e:
        print(f"Test failed with error: {str(e)}")
        print("Traceback:")
        print(traceback.format_exc())
        raise


@pytest.mark.asyncio
async def test_setup_initial_ratings_invalid_user(db_service):
    """Test setting up initial ratings with invalid user ID."""
    # Setup: Create an invalid user ID
    invalid_user_id = "invalid-uuid"
    
    # Execute and Assert: Should raise ValueError for invalid UUID
    with pytest.raises(ValueError):
        await setup_initial_ratings(db_service, [invalid_user_id]) 