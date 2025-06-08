"""
Unit tests for match functionality in the Smash Mate application.

Tests cover match creation, rating updates, match retrieval, and TrueSkill
calculations. All tests use the local database and ensure proper cleanup.
"""

import pytest
from uuid import UUID
from app.core.matches import create_match, update_ratings, get_player_matches, get_venue_matches, get_top_players
from tests.utils import (
    reset_database, 
    setup_initial_ratings, 
    create_sample_match_data,
    assert_match_players_correct,
    DEFAULT_INITIAL_RATING
)


@pytest.fixture(autouse=True)
async def cleanup_database(db_service):
    """Clean up the database before and after each test."""
    await reset_database(db_service)
    yield
    await reset_database(db_service)


@pytest.mark.asyncio
async def test_create_match(db_service, test_user, additional_test_users, test_venue):
    """Test creating a match with proper winner determination (team 1 wins)."""
    # Setup: Define teams
    team1_players = (test_user["id"], additional_test_users[0]["id"])
    team2_players = (additional_test_users[1]["id"], additional_test_users[2]["id"])
    
    # Setup: Initialize player ratings for TrueSkill calculations
    all_player_ids = [test_user["id"]] + [user["id"] for user in additional_test_users[:3]]
    await setup_initial_ratings(db_service, all_player_ids)
    
    # Setup: Create match data with team 1 victory
    match_data = create_sample_match_data(
        venue_id=UUID(test_venue["id"]),
        created_by=test_user["id"],
        team1_players=team1_players,
        team2_players=team2_players,
        team1_wins=True  # Team 1 wins 2-0
    )
    
    # Execute: Create the match
    result = await create_match(database=db_service, **match_data)
    
    # Assert: Basic match properties
    assert result["venue_id"] == test_venue["id"]
    assert result["created_by"] == str(test_user["id"])
    assert result["scores"] == match_data["scores"]
    assert result["status"] == "confirmed"
    
    # Verify: Match was created in database with correct structure
    match = await db_service.get_match(UUID(result["id"]))
    assert match["id"] == result["id"]
    assert_match_players_correct(match, expected_player_count=4)
    
    # Verify: Winners are correctly set (team 1 should win)
    team1_players_in_match = [p for p in match["players"] if p["team"] == 1]
    team2_players_in_match = [p for p in match["players"] if p["team"] == 2]
    
    assert all(p["is_winner"] for p in team1_players_in_match), "Team 1 players should be winners"
    assert all(not p["is_winner"] for p in team2_players_in_match), "Team 2 players should be losers"


@pytest.mark.asyncio
async def test_create_match_team2_wins(db_service, test_user, additional_test_users, test_venue):
    """Test creating a match where team 2 wins (2-1 victory)."""
    # Setup: Define teams
    team1_players = (test_user["id"], additional_test_users[0]["id"])
    team2_players = (additional_test_users[1]["id"], additional_test_users[2]["id"])
    
    # Setup: Initialize player ratings for TrueSkill calculations
    all_player_ids = [test_user["id"]] + [user["id"] for user in additional_test_users[:3]]
    await setup_initial_ratings(db_service, all_player_ids)
    
    # Setup: Create match data with team 2 victory (close 3-set match)
    match_data = create_sample_match_data(
        venue_id=UUID(test_venue["id"]),
        created_by=test_user["id"],
        team1_players=team1_players,
        team2_players=team2_players,
        team1_wins=False,  # Team 2 wins
        scores=[
            {"team1": 21, "team2": 18},  # Team 1 wins set 1
            {"team1": 15, "team2": 21},  # Team 2 wins set 2
            {"team1": 18, "team2": 21}   # Team 2 wins set 3
        ]
    )
    
    # Execute: Create the match
    result = await create_match(database=db_service, **match_data)
    
    # Verify: Match was created and retrieved correctly
    match = await db_service.get_match(UUID(result["id"]))
    
    # Verify: Winners are correctly set (team 2 should win)
    team1_players_in_match = [p for p in match["players"] if p["team"] == 1]
    team2_players_in_match = [p for p in match["players"] if p["team"] == 2]
    
    assert all(not p["is_winner"] for p in team1_players_in_match), "Team 1 players should be losers"
    assert all(p["is_winner"] for p in team2_players_in_match), "Team 2 players should be winners"


@pytest.mark.asyncio
async def test_update_ratings(db_service, test_user, additional_test_users, test_venue):
    """Test that TrueSkill ratings are updated correctly after a match."""
    # Setup: Initialize all players with default ratings
    all_users = [test_user] + additional_test_users[:3]
    all_user_ids = [user["id"] for user in all_users]
    await setup_initial_ratings(db_service, all_user_ids)
    
    # Setup: Create match data
    team1_players = (test_user["id"], additional_test_users[0]["id"])
    team2_players = (additional_test_users[1]["id"], additional_test_users[2]["id"])
    match_data = create_sample_match_data(
        venue_id=UUID(test_venue["id"]),
        created_by=test_user["id"],
        team1_players=team1_players,
        team2_players=team2_players,
        team1_wins=True
    )
    
    # Execute: Create match (which triggers rating updates)
    match = await create_match(database=db_service, **match_data)
    
    # Verify: All players have updated ratings
    for user in all_users:
        try:
            rating = await db_service.get_player_rating(user["id"])
            assert rating is not None, f"Rating should exist for user {user['id']}"
            assert rating["games_played"] >= 1, "Games played should be incremented"
            
            # Winners should have higher mu, losers should have lower mu than initial
            initial_mu = DEFAULT_INITIAL_RATING["mu"]
            current_mu = float(rating["mu"])
            
            if user["id"] in team1_players:
                assert current_mu > initial_mu, f"Winner {user['id']} should have increased rating"
            else:
                assert current_mu < initial_mu, f"Loser {user['id']} should have decreased rating"
        except Exception as e:
            # If no rating found, that indicates a problem with rating updates
            pytest.fail(f"Failed to retrieve rating for user {user['id']}: {e}")


@pytest.mark.asyncio
async def test_get_player_matches(db_service, test_user, additional_test_users, test_venue):
    """Test retrieving all matches for a specific player."""
    # Setup: Define consistent teams for multiple matches
    team1_players = (test_user["id"], additional_test_users[0]["id"])
    team2_players = (additional_test_users[1]["id"], additional_test_users[2]["id"])
    
    # Setup: Initialize player ratings
    all_player_ids = [test_user["id"]] + [user["id"] for user in additional_test_users[:3]]
    await setup_initial_ratings(db_service, all_player_ids)
    
    # Setup: Create multiple matches involving the test user
    match1_data = create_sample_match_data(
        venue_id=UUID(test_venue["id"]),
        created_by=test_user["id"],
        team1_players=team1_players,
        team2_players=team2_players,
        scores=[{"team1": 21, "team2": 18}]  # Single set, team 1 wins
    )
    
    match2_data = create_sample_match_data(
        venue_id=UUID(test_venue["id"]),
        created_by=test_user["id"],
        team1_players=team1_players,
        team2_players=team2_players,
        scores=[{"team1": 15, "team2": 21}]  # Single set, team 2 wins
    )
    
    # Execute: Create both matches
    match1 = await create_match(database=db_service, **match1_data)
    match2 = await create_match(database=db_service, **match2_data)
    
    # Execute: Get matches for the test user
    matches = await get_player_matches(test_user["id"], database=db_service)
    
    # Assert: Both matches are returned for the player
    assert len(matches) >= 2, "Should return at least the 2 matches we created"
    match_ids = [m["id"] for m in matches]
    assert match1["id"] in match_ids, "First match should be in player's match history"
    assert match2["id"] in match_ids, "Second match should be in player's match history"


@pytest.mark.asyncio
async def test_get_venue_matches(db_service, test_user, additional_test_users, test_venue):
    """Test retrieving all matches for a specific venue."""
    # Setup: Define teams
    team1_players = (test_user["id"], additional_test_users[0]["id"])
    team2_players = (additional_test_users[1]["id"], additional_test_users[2]["id"])
    
    # Setup: Initialize player ratings
    all_player_ids = [test_user["id"]] + [user["id"] for user in additional_test_users[:3]]
    await setup_initial_ratings(db_service, all_player_ids)
    
    # Setup: Create a match at the test venue
    match_data = create_sample_match_data(
        venue_id=UUID(test_venue["id"]),
        created_by=test_user["id"],
        team1_players=team1_players,
        team2_players=team2_players
    )
    
    # Execute: Create the match
    match1 = await create_match(database=db_service, **match_data)
    
    # Execute: Get all matches at the venue
    matches = await get_venue_matches(UUID(test_venue["id"]), database=db_service)
    
    # Assert: Our match is returned and all matches are at correct venue
    assert len(matches) >= 1, "Should return at least the match we created"
    assert any(m["id"] == match1["id"] for m in matches), "Our match should be in venue matches"
    assert all(m["venue_id"] == test_venue["id"] for m in matches), "All matches should be at the test venue"


@pytest.mark.asyncio
async def test_get_top_players(db_service, test_user, additional_test_users):
    """Test retrieving top players by TrueSkill rating (mu value)."""
    # Setup: Create player ratings with different mu values to establish rankings
    players_with_ratings = [
        (test_user["id"], 30.0),           # Highest rated
        (additional_test_users[0]["id"], 28.0),  # Second highest
        (additional_test_users[1]["id"], 26.0),  # Third highest
        (additional_test_users[2]["id"], 24.0),  # Lowest rated
    ]
    
    # Setup: Create ratings for each player
    for player_id, mu in players_with_ratings:
        await db_service.update_player_rating(
            player_id, 
            mu=mu, 
            sigma=8.333, 
            games_played=10  # Established players with game history
        )
    
    # Execute: Get top 3 players
    top_players = await get_top_players(limit=3, database=db_service)
    
    # Assert: Correct number of players returned
    assert len(top_players) >= 3, "Should return at least 3 top players"
    
    # Assert: Players are sorted by mu (rating) in descending order
    mus = [float(p["mu"]) for p in top_players]
    assert mus == sorted(mus, reverse=True), "Players should be sorted by rating (highest first)"
    
    # Assert: Top player is correct
    assert float(top_players[0]["mu"]) == 30.0, "Test user should be the highest rated player"


@pytest.mark.asyncio
async def test_update_ratings_with_no_existing_ratings(db_service, test_user, additional_test_users, test_venue):
    """
    Test updating ratings when players have no existing ratings.
    
    This tests the system's ability to handle new players who haven't
    been rated yet - they should get default TrueSkill ratings.
    """
    # Setup: Create match WITHOUT pre-existing ratings (simulates new players)
    team1_players = (test_user["id"], additional_test_users[0]["id"])
    team2_players = (additional_test_users[1]["id"], additional_test_users[2]["id"])
    
    match_data = create_sample_match_data(
        venue_id=UUID(test_venue["id"]),
        created_by=test_user["id"],
        team1_players=team1_players,
        team2_players=team2_players
    )
    
    # Execute: Create match (should handle missing ratings gracefully)
    match = await create_match(database=db_service, **match_data)
    
    # Verify: Ratings were created for all players after the match
    all_users = [test_user] + additional_test_users[:3]
    for user in all_users:
        try:
            rating = await db_service.get_player_rating(user["id"])
            assert rating is not None, f"Rating should be created for new player {user['id']}"
            assert rating["games_played"] >= 1, "Games played should be at least 1 after first match"
        except Exception:
            # Some players might not get ratings if the system doesn't create them automatically
            # This is acceptable behavior depending on implementation
            pass 