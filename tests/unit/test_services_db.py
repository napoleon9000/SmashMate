"""
Unit tests for DatabaseService functionality in the Smash Mate application.

Tests cover all database operations including profiles, venues, follows, teams,
matches, and ratings. All tests use the local Supabase database with proper cleanup.
"""

import pytest
from datetime import datetime
from uuid import UUID
from tests.utils import (
    reset_database,
    create_test_venue,
    SAMPLE_VENUE_DATA,
    SAMPLE_PROFILE_DATA,
    DEFAULT_INITIAL_RATING
)
import os


# Test configuration constants
TEST_URL = os.getenv("LOCAL_SUPABASE_URL", "https://test.supabase.co")
TEST_KEY = os.getenv("LOCAL_SUPABASE_KEY", "your-test-key")


@pytest.fixture(autouse=True)
async def cleanup_database(db_service):
    """Clean up the database before and after each test."""
    await reset_database(db_service)
    yield
    await reset_database(db_service)


@pytest.mark.asyncio
async def test_profile_crud_operations(db_service, test_user):
    """Test complete CRUD operations for user profiles."""
    user_id = test_user["id"]
    
    # Test: Create profile
    profile_data = SAMPLE_PROFILE_DATA.copy()
    result = await db_service.create_profile(user_id, profile_data)
    assert result["user_id"] == str(user_id)
    assert result["display_name"] == profile_data["display_name"]
    
    # Test: Get profile (read)
    result = await db_service.get_profile(user_id)
    assert result["user_id"] == str(user_id)
    assert result["display_name"] == profile_data["display_name"]
    
    # Test: Update profile
    update_data = {"display_name": "Updated Name"}
    result = await db_service.update_profile(user_id, update_data)
    assert result["display_name"] == update_data["display_name"]
    
    # Test: Delete profile
    await db_service.delete_profile(user_id)
    with pytest.raises(Exception):
        await db_service.get_profile(user_id)


@pytest.mark.asyncio
async def test_venue_crud_operations(db_service, test_user):
    """Test complete CRUD operations for venues."""
    # Test: Create venue
    venue = await create_test_venue(db_service, test_user["id"])
    assert venue["name"] == SAMPLE_VENUE_DATA["name"]
    assert venue["address"] == SAMPLE_VENUE_DATA["address"]
    
    venue_id = UUID(venue["id"])
    
    # Test: Get venue (read)
    result = await db_service.get_venue(venue_id)
    assert result["name"] == SAMPLE_VENUE_DATA["name"]
    
    # Test: Update venue
    update_data = {"name": "Updated Venue"}
    result = await db_service.update_venue(venue_id, update_data)
    assert result["name"] == update_data["name"]
    
    # Test: Delete venue
    await db_service.delete_venue(venue_id)
    with pytest.raises(Exception):
        await db_service.get_venue(venue_id)


@pytest.mark.asyncio
async def test_follow_operations(db_service, test_user, additional_test_users):
    """Test follow/unfollow operations and retrieving follow relationships."""
    follower_id = test_user["id"]
    followee_id = additional_test_users[0]["id"]
    
    # Test: Create follow relationship
    result = await db_service.follow_user(follower_id, followee_id)
    assert result["follower"] == str(follower_id)
    assert result["followee"] == str(followee_id)
    
    # Test: Get followers
    followers = await db_service.get_followers(followee_id)
    assert len(followers) == 1
    assert followers[0]["follower"] == str(follower_id)
    
    # Test: Get following
    following = await db_service.get_following(follower_id)
    assert len(following) == 1
    assert following[0]["followee"] == str(followee_id)
    
    # Test: Unfollow
    await db_service.unfollow_user(follower_id, followee_id)
    followers = await db_service.get_followers(followee_id)
    assert len(followers) == 0


@pytest.mark.asyncio
async def test_team_operations(db_service, test_user, additional_test_users):
    """Test team creation and rating updates."""
    player_a = test_user["id"]
    player_b = additional_test_users[0]["id"]
    
    # Test: Create team (first time should create new team)
    team_data = {
        "player_a": player_a,
        "player_b": player_b,
        "mu": 25.0,
        "sigma": 8.333
    }
    
    result = await db_service.create_team(**team_data)
    # Note: Database enforces player_a < player_b, so we check both combinations
    assert {player_a, player_b} == {result["player_a"], result["player_b"]}
    assert float(result["mu"]) == team_data["mu"]
    
    team_id = UUID(result["id"])
    
    # Test: Create team again (should return existing team)
    result2 = await db_service.create_team(**team_data)
    assert result2["id"] == result["id"], "Should return existing team instead of creating duplicate"
    
    # Test: Update team rating
    rating_data = {
        "mu": 26.0,
        "sigma": 8.0,
        "games_played": 5
    }
    
    result = await db_service.update_team_rating(team_id, **rating_data)
    assert float(result["mu"]) == rating_data["mu"]
    assert float(result["sigma"]) == rating_data["sigma"]
    assert result["games_played"] == rating_data["games_played"]


@pytest.mark.asyncio
async def test_player_rating_operations(db_service, test_user):
    """Test player rating creation and updates (upsert functionality)."""
    # Test: Update player rating (creates if doesn't exist)
    rating_data = {
        "mu": 25.0,
        "sigma": 8.333,
        "games_played": 10
    }
    
    result = await db_service.update_player_rating(test_user["id"], **rating_data)
    assert float(result["mu"]) == rating_data["mu"]
    assert float(result["sigma"]) == rating_data["sigma"]
    assert result["games_played"] == rating_data["games_played"]
    
    # Test: Get player rating
    rating = await db_service.get_player_rating(test_user["id"])
    assert rating is not None
    assert float(rating["mu"]) == rating_data["mu"]


@pytest.mark.asyncio
async def test_match_operations(db_service, test_user, additional_test_users):
    """Test match creation, retrieval, and updates."""
    # Setup: Create a venue first (matches require venues)
    venue = await create_test_venue(db_service, test_user["id"])
    venue_id = UUID(venue["id"])
    
    # Setup: Define players for doubles match
    player1_id = test_user["id"]
    player2_id = additional_test_users[0]["id"]
    player3_id = additional_test_users[1]["id"]
    player4_id = additional_test_users[2]["id"]
    
    # Test: Create match with all required data
    match_data = {
        "venue_id": venue_id,
        "played_at": datetime.now(),
        "created_by": test_user["id"],
        "scores": [{"set": 1, "team1": 21, "team2": 17}],  # Team 1 wins
        "players": [
            (player1_id, 1, True),   # Team 1, winner
            (player2_id, 1, True),   # Team 1, winner
            (player3_id, 2, False),  # Team 2, loser
            (player4_id, 2, False)   # Team 2, loser
        ]
    }
    
    result = await db_service.create_match(**match_data)
    assert result["venue_id"] == str(venue_id)
    assert result["status"] == "confirmed"
    
    match_id = UUID(result["id"])
    
    # Test: Get match (should include players)
    result = await db_service.get_match(match_id)
    assert result["id"] == str(match_id)
    assert len(result["players"]) == 4, "Match should have 4 players for doubles"
    
    # Verify player data structure
    for player in result["players"]:
        assert "player_id" in player
        assert "team" in player
        assert "is_winner" in player
    
    # Test: Update match status
    update_data = {"status": "pending"}
    result = await db_service.update_match(match_id, update_data)
    assert result["status"] == update_data["status"]


@pytest.mark.asyncio
async def test_team_compatibility_operations(db_service, test_user, additional_test_users):
    """Test team creation for compatibility calculations."""
    player_a = test_user["id"]
    player_b = additional_test_users[0]["id"]
    
    # Setup: Create ratings for both players (required for compatibility calculations)
    for player_id in [player_a, player_b]:
        await db_service.update_player_rating(player_id, **DEFAULT_INITIAL_RATING)
    
    # Test: Create a team to enable compatibility calculations
    team_data = {
        "player_a": player_a,
        "player_b": player_b,
        "mu": 25.0,
        "sigma": 8.333
    }
    
    # First creation should create new team
    result = await db_service.create_team(**team_data)
    assert {player_a, player_b} == {result["player_a"], result["player_b"]}
    assert float(result["mu"]) == team_data["mu"]
    assert float(result["sigma"]) == team_data["sigma"]
    
    # Second creation should return existing team (no duplicates)
    result2 = await db_service.create_team(**team_data)
    assert result2["id"] == result["id"], "Should return existing team, not create duplicate"


@pytest.mark.asyncio
async def test_mutual_followers_operations(db_service, test_user, additional_test_users):
    """Test the new get_mutual_followers functionality."""
    user_id = test_user["id"]
    user1_id = additional_test_users[0]["id"]
    user2_id = additional_test_users[1]["id"]
    
    # Setup: Create mutual follow relationship with user1
    await db_service.follow_user(user_id, user1_id)  # user follows user1
    await db_service.follow_user(user1_id, user_id)  # user1 follows user back
    
    # Setup: Create one-way relationship with user2
    await db_service.follow_user(user_id, user2_id)  # user follows user2 only
    
    # Test: Get mutual followers
    mutual_followers = await db_service.get_mutual_followers(user_id)
    
    # Assert: Only mutual relationship is returned
    assert len(mutual_followers) == 1
    assert mutual_followers[0]["user_id"] == str(user1_id)


@pytest.mark.asyncio
async def test_get_player_matches_and_venue_matches(db_service, test_user, additional_test_users):
    """Test retrieving matches by player and by venue."""
    # Setup: Create venue and match
    venue = await create_test_venue(db_service, test_user["id"])
    venue_id = UUID(venue["id"])
    
    # Create a simple match
    match_data = {
        "venue_id": venue_id,
        "played_at": datetime.now(),
        "created_by": test_user["id"],
        "scores": [{"team1": 21, "team2": 15}],
        "players": [
            (test_user["id"], 1, True),
            (additional_test_users[0]["id"], 1, True),
            (additional_test_users[1]["id"], 2, False),
            (additional_test_users[2]["id"], 2, False)
        ]
    }
    
    match = await db_service.create_match(**match_data)
    
    # Test: Get player matches
    player_matches = await db_service.get_player_matches(test_user["id"])
    assert len(player_matches) >= 1
    assert any(m["id"] == match["id"] for m in player_matches)
    
    # Test: Get venue matches
    venue_matches = await db_service.get_venue_matches(venue_id)
    assert len(venue_matches) >= 1
    assert any(m["id"] == match["id"] for m in venue_matches)
    assert all(m["venue_id"] == str(venue_id) for m in venue_matches)


@pytest.mark.asyncio
async def test_get_top_players(db_service, test_user, additional_test_users):
    """Test retrieving top players by rating."""
    # Setup: Create players with different ratings
    players_ratings = [
        (test_user["id"], 30.0),
        (additional_test_users[0]["id"], 28.0),
        (additional_test_users[1]["id"], 26.0)
    ]
    
    for player_id, mu in players_ratings:
        await db_service.update_player_rating(player_id, mu=mu, sigma=8.333, games_played=5)
    
    # Test: Get top players
    top_players = await db_service.get_top_players(limit=2)
    
    # Assert: Correct ordering and count
    assert len(top_players) >= 2
    assert float(top_players[0]["mu"]) >= float(top_players[1]["mu"])  # Descending order
    assert float(top_players[0]["mu"]) == 30.0  # Test user should be highest
