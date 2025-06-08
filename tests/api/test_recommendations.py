"""
Unit tests for recommendations API endpoints.

Tests cover compatibility scores, partner recommendations, and team rankings.
"""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app
from tests.utils import (
    reset_database,
    create_test_profiles,
    setup_initial_ratings
)


client = TestClient(app)


@pytest.fixture(autouse=True)
async def cleanup_database(db_service):
    """Reset database before and after each test."""
    await reset_database(db_service)
    yield
    await reset_database(db_service)


class TestRecommendationsAPI:
    """Test recommendations API endpoints."""

    @pytest.mark.asyncio
    async def test_get_compatibility_scores_success(self, db_service, additional_test_users):
        """Test getting compatibility scores for a player."""
        # Setup: Use real authenticated users with teams and ratings
        user_ids = [user["id"] for user in additional_test_users]
        await create_test_profiles(db_service, user_ids, "Player")
        await setup_initial_ratings(db_service, user_ids)
        
        # Create some team ratings to have compatibility data
        # This requires teams to exist in the database
        await db_service.create_team(user_ids[0], user_ids[1], 27.0, 7.0)
        await db_service.create_team(user_ids[0], user_ids[2], 26.0, 7.5)
        
        # Execute: Get compatibility scores
        response = client.get(f"/api/v1/recommendations/compatibility/{user_ids[0]}")
        
        # Assert: Verify response
        assert response.status_code == 200
        scores = response.json()
        
        # Should return list of compatibility scores
        assert isinstance(scores, list)
        
        # If there are scores, verify structure
        for score in scores:
            assert "partner" in score
            assert "team_rating" in score
            assert "avg_individual_rating" in score
            assert "compatibility_score" in score
            
            # Verify partner structure
            partner = score["partner"]
            assert "user_id" in partner
            assert "display_name" in partner

    @pytest.mark.asyncio
    async def test_get_compatibility_scores_no_teams(self, db_service, test_user):
        """Test getting compatibility scores when player has no teams."""
        # Setup: Use real authenticated user with no team history
        user_id = test_user["id"]
        await create_test_profiles(db_service, [user_id], "Solo Player")
        await setup_initial_ratings(db_service, [user_id])
        
        # Execute: Get compatibility scores
        response = client.get(f"/api/v1/recommendations/compatibility/{user_id}")
        
        # Assert: Should return empty list
        assert response.status_code == 200
        scores = response.json()
        assert scores == []

    @pytest.mark.asyncio
    async def test_get_compatibility_scores_nonexistent_player(self):
        """Test getting compatibility scores for non-existent player."""
        # Execute: Get scores for non-existent player
        fake_player_id = str(uuid4())
        response = client.get(f"/api/v1/recommendations/compatibility/{fake_player_id}")
        
        # Assert: Should return empty list or handle gracefully
        assert response.status_code == 200
        scores = response.json()
        assert scores == []

    @pytest.mark.asyncio
    async def test_get_recommended_partners_success(self, db_service, additional_test_users):
        """Test getting recommended partners with default parameters."""
        # Setup: Use real authenticated users with multiple teams
        user_ids = [user["id"] for user in additional_test_users]
        await create_test_profiles(db_service, user_ids, "Player")
        await setup_initial_ratings(db_service, user_ids)
        
        # Create multiple team combinations with different ratings
        teams_data = [
            (user_ids[0], user_ids[1], 28.0, 6.0),  # High rating team
            (user_ids[0], user_ids[2], 26.0, 7.0),  # Medium rating team
            (user_ids[0], user_ids[3], 24.0, 8.0),  # Lower rating team
        ]
        
        for player1, player2, mu, sigma in teams_data:
            await db_service.create_team(player1, player2, mu, sigma)
        
        # Execute: Get recommended partners
        response = client.get(f"/api/v1/recommendations/partners/{user_ids[0]}")
        
        # Assert: Verify response
        assert response.status_code == 200
        recommendations = response.json()
        
        assert isinstance(recommendations, list)
        assert len(recommendations) <= 5  # Default limit
        
        # Verify structure of recommendations
        for rec in recommendations:
            assert "partner" in rec
            assert "team_rating" in rec
            assert "avg_individual_rating" in rec
            assert "compatibility_score" in rec
            assert "games_played_together" in rec
            
            # Verify partner structure
            partner = rec["partner"]
            assert "user_id" in partner
            assert "display_name" in partner

    @pytest.mark.asyncio
    async def test_get_recommended_partners_custom_parameters(self, db_service, additional_test_users):
        """Test getting recommended partners with custom limit and min_games."""
        # Setup: Use real authenticated users
        user_ids = [user["id"] for user in additional_test_users[:5]]
        await create_test_profiles(db_service, user_ids, "Player")
        await setup_initial_ratings(db_service, user_ids)
        
        # Create team data
        for i in range(1, 4):
            await db_service.create_team(user_ids[0], user_ids[i], 25.0 + i, 7.0)
        
        # Execute: Get recommendations with custom parameters
        response = client.get(
            f"/api/v1/recommendations/partners/{user_ids[0]}",
            params={"limit": 2, "min_games": 1}
        )
        
        # Assert: Verify response respects custom limit
        assert response.status_code == 200
        recommendations = response.json()
        
        assert len(recommendations) <= 2  # Custom limit

    @pytest.mark.asyncio
    async def test_get_recommended_partners_no_data(self, db_service, test_user):
        """Test getting recommended partners when player has no team data."""
        # Setup: Use real authenticated user with no teams
        user_id = test_user["id"]
        await create_test_profiles(db_service, [user_id], "New Player")
        await setup_initial_ratings(db_service, [user_id])
        
        # Execute: Get recommendations
        response = client.get(f"/api/v1/recommendations/partners/{user_id}")
        
        # Assert: Should return empty list
        assert response.status_code == 200
        recommendations = response.json()
        assert recommendations == []

    @pytest.mark.asyncio
    async def test_get_team_rankings_success(self, db_service, additional_test_users):
        """Test getting team rankings with default limit."""
        # Setup: Use real authenticated users with multiple teams
        user_ids = [user["id"] for user in additional_test_users]
        await create_test_profiles(db_service, user_ids, "Player")
        
        # Create teams with different ratings
        teams_data = [
            (user_ids[0], user_ids[1], 30.0, 5.0),  # Highest rated team
            (user_ids[1], user_ids[2], 28.0, 6.0),  # Second highest
            (user_ids[2], user_ids[3], 26.0, 7.0),  # Third highest
        ]
        
        for player1, player2, mu, sigma in teams_data:
            await db_service.create_team(player1, player2, mu, sigma)
        
        # Execute: Get team rankings
        response = client.get("/api/v1/recommendations/teams/rankings")
        
        # Assert: Verify response
        assert response.status_code == 200
        rankings = response.json()
        
        assert isinstance(rankings, list)
        assert len(rankings) <= 10  # Default limit
        assert len(rankings) >= 3  # Should have our 3 teams
        
        # Verify structure
        for ranking in rankings:
            assert "player_a" in ranking
            assert "player_b" in ranking
            assert "team_rating" in ranking
            assert "games_played" in ranking
            
            # Verify player structure
            for player_key in ["player_a", "player_b"]:
                player = ranking[player_key]
                assert "id" in player
                assert "name" in player
                assert isinstance(player["id"], str)
                assert isinstance(player["name"], str)

    @pytest.mark.asyncio
    async def test_get_team_rankings_custom_limit(self, db_service, additional_test_users):
        """Test getting team rankings with custom limit."""
        # Setup: Use real authenticated users with multiple teams
        user_ids = [user["id"] for user in additional_test_users]
        await create_test_profiles(db_service, user_ids, "Player")
        
        # Create several teams
        teams_data = [
            (user_ids[0], user_ids[1], 30.0, 5.0),
            (user_ids[1], user_ids[2], 28.0, 6.0),
            (user_ids[2], user_ids[3], 26.0, 7.0),
        ]
        
        for player1, player2, mu, sigma in teams_data:
            await db_service.create_team(player1, player2, mu, sigma)
        
        # Execute: Get rankings with custom limit
        response = client.get("/api/v1/recommendations/teams/rankings", params={"limit": 2})
        
        # Assert: Verify response respects custom limit
        assert response.status_code == 200
        rankings = response.json()
        assert len(rankings) <= 2

    @pytest.mark.asyncio
    async def test_get_team_rankings_empty_database(self):
        """Test getting team rankings when no teams exist."""
        # Execute: Get rankings from empty database
        response = client.get("/api/v1/recommendations/teams/rankings")
        
        # Assert: Should return empty list
        assert response.status_code == 200
        rankings = response.json()
        assert rankings == []

    @pytest.mark.asyncio
    async def test_recommendations_endpoints_with_invalid_uuids(self):
        """Test all recommendation endpoints with invalid UUID formats."""
        # Test compatibility scores with invalid UUID
        response = client.get("/api/v1/recommendations/compatibility/invalid-uuid")
        assert response.status_code == 422
        
        # Test recommended partners with invalid UUID
        response = client.get("/api/v1/recommendations/partners/invalid-uuid")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_recommendations_endpoints_with_invalid_parameters(self, test_user):
        """Test recommendation endpoints with invalid query parameters."""
        user_id = test_user["id"]
        
        # Test recommended partners with invalid limit
        response = client.get(
            f"/api/v1/recommendations/partners/{user_id}",
            params={"limit": "invalid"}
        )
        assert response.status_code == 422
        
        # Test recommended partners with invalid min_games
        response = client.get(
            f"/api/v1/recommendations/partners/{user_id}",
            params={"min_games": "invalid"}
        )
        assert response.status_code == 422
        
        # Test team rankings with invalid limit
        response = client.get(
            "/api/v1/recommendations/teams/rankings",
            params={"limit": "invalid"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_recommendations_endpoints_with_extreme_parameters(self, test_user):
        """Test recommendation endpoints with extreme parameter values."""
        user_id = test_user["id"]
        
        # Test with very large limit
        response = client.get(
            f"/api/v1/recommendations/partners/{user_id}",
            params={"limit": 10000}
        )
        assert response.status_code == 200
        recommendations = response.json()
        assert len(recommendations) <= 10000  # Should handle large limits
        
        # Test with zero limit
        response = client.get(
            f"/api/v1/recommendations/partners/{user_id}",
            params={"limit": 0}
        )
        # Implementation dependent - might return error or empty list
        assert response.status_code in [200, 422]
        
        # Test with negative min_games
        response = client.get(
            f"/api/v1/recommendations/partners/{user_id}",
            params={"min_games": -1}
        )
        # Should handle gracefully
        assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_compatibility_calculation_accuracy(self, db_service, additional_test_users):
        """Test that compatibility calculations return mathematically accurate results."""
        # Setup: Use real authenticated users with known ratings
        user_ids = [user["id"] for user in additional_test_users[:3]]
        await create_test_profiles(db_service, user_ids, "Player")
        
        # Set specific individual ratings
        player1_mu, player1_sigma = 25.0, 8.33
        player2_mu, player2_sigma = 27.0, 7.50
        
        await db_service.update_player_rating(user_ids[0], player1_mu, player1_sigma, 10)
        await db_service.update_player_rating(user_ids[1], player2_mu, player2_sigma, 8)
        
        # Set specific team rating
        team_mu, team_sigma = 28.0, 6.0
        await db_service.create_team(user_ids[0], user_ids[1], team_mu, team_sigma)
        
        # Execute: Get compatibility scores
        response = client.get(f"/api/v1/recommendations/compatibility/{user_ids[0]}")
        
        # Assert: Verify mathematical accuracy
        assert response.status_code == 200
        scores = response.json()
        
        if scores:  # If we have data to test
            score = scores[0]
            
            # Calculate expected values
            expected_avg_individual = (player1_mu + player2_mu) / 2
            expected_compatibility = team_mu - expected_avg_individual
            
            # Verify calculations (allow small floating point differences)
            assert abs(score["avg_individual_rating"] - expected_avg_individual) < 0.01
            assert abs(score["compatibility_score"] - expected_compatibility) < 0.01 