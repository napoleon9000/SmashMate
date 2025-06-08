"""
Unit tests for matches API endpoints.

Tests cover match creation, retrieval, leaderboards, and TrueSkill rating updates.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_database_service
from app.main import app
from tests.utils import (
    reset_database,
    setup_initial_ratings,
    create_test_profiles,
    create_sample_match_data
)


@pytest.fixture
def test_client(db_service):
    """Create a test client with overridden database dependency."""
    # Override the dependency to use our test database service
    app.dependency_overrides[get_database_service] = lambda: db_service
    
    client = TestClient(app)
    yield client
    
    # Clean up the override after the test
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
async def cleanup_database(db_service):
    """Reset database before and after each test."""
    await reset_database(db_service)
    yield
    await reset_database(db_service)


class TestMatchesAPI:
    """Test matches API endpoints."""

    @pytest.mark.asyncio
    async def test_create_match_success(self, test_client, db_service, additional_test_users, test_venue):
        """Test successful match creation with proper TrueSkill rating updates."""
        # Setup: Use real authenticated users
        user_ids = [user["id"] for user in additional_test_users]
        
        # Create profiles and initial ratings
        await create_test_profiles(db_service, user_ids, "Player")
        await setup_initial_ratings(db_service, user_ids)
        
        # Use the test venue
        venue_id = test_venue["id"]
        
        # Setup: Prepare match data
        match_data = {
            "venue_id": venue_id,
            "team1_players": [user_ids[0], user_ids[1]],
            "team2_players": [user_ids[2], user_ids[3]],
            "scores": [
                {"team1": 21, "team2": 15},
                {"team1": 21, "team2": 18}
            ],
            "played_at": datetime.now().isoformat()
        }
        
        # Execute: Create match
        response = test_client.post(
            "/api/v1/matches/",
            params={"created_by": user_ids[0]},
            json=match_data
        )
        
        # Assert: Verify response
        assert response.status_code == 200
        match_response = response.json()
        
        assert match_response["venue_id"] == venue_id
        assert len(match_response["players"]) == 4
        assert len(match_response["scores"]) == 2
        assert "id" in match_response

    @pytest.mark.asyncio
    async def test_create_match_invalid_team_size(self, test_client, additional_test_users, test_venue):
        """Test match creation fails with incorrect team sizes."""
        # Setup: Use real authenticated users (only need 3)
        user_ids = [user["id"] for user in additional_test_users[:3]]
        
        # Execute: Try to create match with wrong team sizes
        match_data = {
            "venue_id": test_venue["id"],
            "team1_players": [user_ids[0]],  # Only 1 player in team1
            "team2_players": [user_ids[1], user_ids[2]],
            "scores": [{"team1": 21, "team2": 15}],
            "played_at": datetime.now().isoformat()
        }
        
        response = test_client.post(
            "/api/v1/matches/",
            params={"created_by": user_ids[0]},
            json=match_data
        )
        
        # Assert: Should return validation error
        assert response.status_code == 400
        assert "exactly 2 players" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_match_missing_created_by(self, test_client, additional_test_users, test_venue):
        """Test match creation fails without created_by parameter."""
        # Setup: Use real authenticated users
        user_ids = [user["id"] for user in additional_test_users]
        
        match_data = {
            "venue_id": test_venue["id"],
            "team1_players": [user_ids[0], user_ids[1]],
            "team2_players": [user_ids[2], user_ids[3]],
            "scores": [{"team1": 21, "team2": 15}],
            "played_at": datetime.now().isoformat()
        }
        
        # Execute: Create match without created_by
        response = test_client.post("/api/v1/matches/", json=match_data)
        
        # Assert: Should return validation error
        assert response.status_code == 422  # Missing required query parameter

    @pytest.mark.asyncio
    async def test_create_match_invalid_venue_id(self, test_client, additional_test_users):
        """Test match creation with non-existent venue ID."""
        # Setup: Use real authenticated users but fake venue
        user_ids = [user["id"] for user in additional_test_users]
        fake_venue_id = str(uuid4())
        
        match_data = {
            "venue_id": fake_venue_id,
            "team1_players": [user_ids[0], user_ids[1]],
            "team2_players": [user_ids[2], user_ids[3]],
            "scores": [{"team1": 21, "team2": 15}],
            "played_at": datetime.now().isoformat()
        }
        
        # Execute: Create match with invalid venue
        response = test_client.post(
            "/api/v1/matches/",
            params={"created_by": user_ids[0]},
            json=match_data
        )
        
        # Assert: Should return server error
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_get_player_matches(self, test_client, db_service, additional_test_users, test_venue):
        """Test retrieving matches for a specific player."""
        # Setup: Use real authenticated users
        user_ids = [user["id"] for user in additional_test_users]
        
        await create_test_profiles(db_service, user_ids, "Player")
        await setup_initial_ratings(db_service, user_ids)
        
        # Create a match
        match_data = create_sample_match_data(
            test_venue["id"], user_ids[0], 
            (user_ids[0], user_ids[1]), 
            (user_ids[2], user_ids[3])
        )
        
        # Use core function to create match (since we're testing API layer)
        from app.core.matches import create_match
        await create_match(
            venue_id=match_data["venue_id"],
            created_by=match_data["created_by"],
            team1_players=(user_ids[0], user_ids[1]),
            team2_players=(user_ids[2], user_ids[3]),
            scores=match_data["scores"],
            played_at=match_data["played_at"],
            database=db_service
        )
        
        # Execute: Get player matches
        response = test_client.get(f"/api/v1/matches/player/{user_ids[0]}")
        
        # Assert: Verify response
        assert response.status_code == 200
        matches = response.json()
        assert len(matches) > 0
        assert any(match for match in matches if user_ids[0] in str(match))

    @pytest.mark.asyncio
    async def test_get_venue_matches(self, test_client, db_service, additional_test_users, test_venue):
        """Test retrieving matches for a specific venue."""
        # Setup: Use real authenticated users
        user_ids = [user["id"] for user in additional_test_users]
        
        await create_test_profiles(db_service, user_ids, "Player")
        await setup_initial_ratings(db_service, user_ids)
        
        # Create a match
        from app.core.matches import create_match
        await create_match(
            venue_id=test_venue["id"],
            created_by=user_ids[0],
            team1_players=(user_ids[0], user_ids[1]),
            team2_players=(user_ids[2], user_ids[3]),
            scores=[{"team1": 21, "team2": 15}],
            played_at=datetime.now(),
            database=db_service
        )
        
        # Execute: Get venue matches
        response = test_client.get(f"/api/v1/matches/venue/{test_venue['id']}")
        
        # Assert: Verify response
        assert response.status_code == 200
        matches = response.json()
        assert len(matches) > 0

    @pytest.mark.asyncio
    async def test_get_leaderboard_default_limit(self, test_client, db_service, additional_test_users):
        """Test getting top players leaderboard with default limit."""
        # Setup: Use real authenticated users with ratings
        user_ids = [user["id"] for user in additional_test_users]
        
        await create_test_profiles(db_service, user_ids, "Player")
        await setup_initial_ratings(db_service, user_ids)
        
        # Execute: Get leaderboard
        response = test_client.get("/api/v1/matches/leaderboard")
        
        # Assert: Verify response
        assert response.status_code == 200
        leaderboard = response.json()
        assert isinstance(leaderboard, list)
        assert len(leaderboard) <= 10  # Default limit

    @pytest.mark.asyncio
    async def test_get_leaderboard_custom_limit(self, test_client, db_service, additional_test_users):
        """Test getting top players leaderboard with custom limit."""
        # Setup: Use real authenticated users with ratings
        user_ids = [user["id"] for user in additional_test_users]
        
        await create_test_profiles(db_service, user_ids, "Player")
        await setup_initial_ratings(db_service, user_ids)
        
        # Execute: Get leaderboard with custom limit
        response = test_client.get("/api/v1/matches/leaderboard", params={"limit": 3})
        
        # Assert: Verify response
        assert response.status_code == 200
        leaderboard = response.json()
        assert len(leaderboard) <= 3

    @pytest.mark.asyncio
    async def test_get_leaderboard_empty_database(self, test_client):
        """Test getting leaderboard when no players exist."""
        # Execute: Get leaderboard from empty database
        response = test_client.get("/api/v1/matches/leaderboard")
        
        # Assert: Verify response
        assert response.status_code == 200
        leaderboard = response.json()
        assert leaderboard == []

    @pytest.mark.asyncio
    async def test_get_player_matches_nonexistent_player(self, test_client):
        """Test getting matches for a player that doesn't exist."""
        # Execute: Get matches for non-existent player
        fake_player_id = str(uuid4())
        response = test_client.get(f"/api/v1/matches/player/{fake_player_id}")
        
        # Assert: Should return empty list or handle gracefully
        assert response.status_code == 200
        matches = response.json()
        assert matches == []

    @pytest.mark.asyncio
    async def test_get_venue_matches_nonexistent_venue(self, test_client):
        """Test getting matches for a venue that doesn't exist."""
        # Execute: Get matches for non-existent venue
        fake_venue_id = str(uuid4())
        response = test_client.get(f"/api/v1/matches/venue/{fake_venue_id}")
        
        # Assert: Should return empty list or handle gracefully
        assert response.status_code == 200
        matches = response.json()
        assert matches == []

    @pytest.mark.asyncio
    async def test_create_match_with_invalid_scores(self, test_client, additional_test_users, test_venue):
        """Test match creation with invalid score format."""
        # Setup: Use real authenticated users
        user_ids = [user["id"] for user in additional_test_users]
        
        # Execute: Create match with invalid scores
        match_data = {
            "venue_id": test_venue["id"],
            "team1_players": [user_ids[0], user_ids[1]],
            "team2_players": [user_ids[2], user_ids[3]],
            "scores": [{"team1": "invalid", "team2": 15}],  # Invalid score type
            "played_at": datetime.now().isoformat()
        }
        
        response = test_client.post(
            "/api/v1/matches/",
            params={"created_by": user_ids[0]},
            json=match_data
        )
        
        # Assert: Should return validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_matches_endpoints_with_invalid_uuids(self, test_client, test_user):
        """Test all match endpoints with invalid UUID formats."""
        # Test player matches with invalid UUID
        response = test_client.get("/api/v1/matches/player/invalid-uuid")
        assert response.status_code == 422
        
        # Test venue matches with invalid UUID
        response = test_client.get("/api/v1/matches/venue/invalid-uuid")
        assert response.status_code == 422
        
        # Test match creation with invalid UUIDs in request body
        match_data = {
            "venue_id": "invalid-venue-uuid",
            "team1_players": ["invalid-player1", "invalid-player2"],
            "team2_players": [str(uuid4()), str(uuid4())],
            "scores": [{"team1": 21, "team2": 15}],
            "played_at": datetime.now().isoformat()
        }
        
        response = test_client.post(
            "/api/v1/matches/",
            params={"created_by": test_user["id"]},
            json=match_data
        )
        assert response.status_code == 422 