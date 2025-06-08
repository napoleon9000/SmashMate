"""
Unit tests for social API endpoints.

Tests cover following/unfollowing users, retrieving followers/following lists,
and mutual follower functionality.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.utils import (
    reset_database,
    create_test_profiles
)

client = TestClient(app)


@pytest.fixture(autouse=True)
async def cleanup_database(db_service):
    """Reset database before and after each test."""
    await reset_database(db_service)
    yield
    await reset_database(db_service)


class TestSocialAPI:
    """Test social API endpoints."""

    @pytest.mark.asyncio
    async def test_follow_player_success(self, db_service, additional_test_users):
        """Test successfully following another player."""
        # Setup: Use real authenticated users
        user_ids = [user["id"] for user in additional_test_users[:2]]
        await create_test_profiles(db_service, user_ids, "User")
        
        follower_id = user_ids[0]
        followee_id = user_ids[1]
        
        # Execute: Follow another player
        response = client.post(
            f"/api/v1/social/follow/{follower_id}",
            json={"followee_id": followee_id}
        )
        
        # Assert: Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert "message" in response_data
        assert "Successfully followed user" in response_data["message"]
        assert "data" in response_data

    @pytest.mark.asyncio
    async def test_follow_nonexistent_player(self, db_service, test_user):
        """Test following a player that doesn't exist."""
        # Setup: Use real authenticated user
        user_id = test_user["id"]
        await create_test_profiles(db_service, [user_id], "User")
        
        fake_followee_id = str(uuid4())
        
        # Execute: Try to follow non-existent user
        response = client.post(
            f"/api/v1/social/follow/{user_id}",
            json={"followee_id": fake_followee_id}
        )
        
        # Assert: Should return error
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_follow_invalid_request_format(self, test_user):
        """Test follow endpoint with invalid request format."""
        # Setup: Use real authenticated user
        user_id = test_user["id"]
        
        # Execute: Send invalid request body
        response = client.post(
            f"/api/v1/social/follow/{user_id}",
            json={"invalid_field": "invalid_value"}
        )
        
        # Assert: Should return validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_unfollow_player_success(self, db_service, additional_test_users):
        """Test successfully unfollowing a player."""
        # Setup: Use real authenticated users and establish follow relationship
        user_ids = [user["id"] for user in additional_test_users[:2]]
        await create_test_profiles(db_service, user_ids, "User")
        
        follower_id = user_ids[0]
        followee_id = user_ids[1]
        
        # First, establish follow relationship
        await db_service.follow_user(follower_id, followee_id)
        
        # Execute: Unfollow the player
        response = client.delete(f"/api/v1/social/follow/{follower_id}/{followee_id}")
        
        # Assert: Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert "Successfully unfollowed user" in response_data["message"]

    @pytest.mark.asyncio
    async def test_unfollow_player_not_following(self, db_service, additional_test_users):
        """Test unfollowing a player when no follow relationship exists."""
        # Setup: Use real authenticated users without follow relationship
        user_ids = [user["id"] for user in additional_test_users[:2]]
        await create_test_profiles(db_service, user_ids, "User")
        
        follower_id = user_ids[0]
        followee_id = user_ids[1]
        
        # Execute: Try to unfollow when not following
        response = client.delete(f"/api/v1/social/follow/{follower_id}/{followee_id}")
        
        # Assert: Should handle gracefully
        assert response.status_code == 200  # Usually still returns success

    @pytest.mark.asyncio
    async def test_get_followers_success(self, db_service, additional_test_users):
        """Test getting followers list for a user."""
        # Setup: Use real authenticated users with followers
        user_ids = [user["id"] for user in additional_test_users]
        
        # Create all profiles
        await create_test_profiles(db_service, user_ids, "Test User")
        
        # Establish follow relationships: users 1, 2, 3 follow user 0
        target_user_id = user_ids[0]
        for i in range(1, 4):
            await db_service.follow_user(user_ids[i], target_user_id)
        
        # Execute: Get followers
        response = client.get(f"/api/v1/social/followers/{target_user_id}")
        
        # Assert: Verify response
        assert response.status_code == 200
        followers = response.json()
        
        assert len(followers) == 3  # Should have 3 followers
        assert all("user_id" in follower for follower in followers)
        assert all("display_name" in follower for follower in followers)

    @pytest.mark.asyncio
    async def test_get_followers_empty_list(self, db_service, test_user):
        """Test getting followers when user has no followers."""
        # Setup: Use real authenticated user with no followers
        user_id = test_user["id"]
        await create_test_profiles(db_service, [user_id], "Lonely User")
        
        # Execute: Get followers
        response = client.get(f"/api/v1/social/followers/{user_id}")
        
        # Assert: Should return empty list
        assert response.status_code == 200
        followers = response.json()
        assert followers == []

    @pytest.mark.asyncio
    async def test_get_following_success(self, db_service, additional_test_users):
        """Test getting following list for a user."""
        # Setup: Use real authenticated users where user follows others
        user_ids = [user["id"] for user in additional_test_users]
        await create_test_profiles(db_service, user_ids, "Test User")
        
        # User 0 follows users 1, 2, 3
        follower_id = user_ids[0]
        for i in range(1, 4):
            await db_service.follow_user(follower_id, user_ids[i])
        
        # Execute: Get following list
        response = client.get(f"/api/v1/social/following/{follower_id}")
        
        # Assert: Verify response
        assert response.status_code == 200
        following = response.json()
        
        assert len(following) == 3  # Should be following 3 users
        assert all("user_id" in user for user in following)
        assert all("display_name" in user for user in following)

    @pytest.mark.asyncio
    async def test_get_following_empty_list(self, db_service, test_user):
        """Test getting following list when user follows no one."""
        # Setup: Use real authenticated user with no following
        user_id = test_user["id"]
        await create_test_profiles(db_service, [user_id], "Solo User")
        
        # Execute: Get following list
        response = client.get(f"/api/v1/social/following/{user_id}")
        
        # Assert: Should return empty list
        assert response.status_code == 200
        following = response.json()
        assert following == []

    @pytest.mark.asyncio
    async def test_get_mutual_followers_success(self, db_service, test_user, additional_test_users):
        """Test getting mutual followers (users who follow each other)."""
        # Setup: Create profiles for test users
        user1_id = additional_test_users[0]["id"]
        user2_id = additional_test_users[1]["id"]
        user3_id = additional_test_users[2]["id"]
        
        # Create profiles for all test users
        await create_test_profiles(db_service, [user1_id, user2_id, user3_id], "Mutual User")
        
        # Setup: Create mutual follow relationships
        # user <-> user1 (mutual)
        await db_service.follow_user(test_user["id"], user1_id)
        await db_service.follow_user(user1_id, test_user["id"])
        
        # user <-> user3 (mutual)
        await db_service.follow_user(test_user["id"], user3_id)
        await db_service.follow_user(user3_id, test_user["id"])
        
        # user -> user2 (one-way only, should not appear in results)
        await db_service.follow_user(test_user["id"], user2_id)
        
        # Execute: Get mutual followers
        response = client.get(f"/api/v1/social/mutual/{test_user['id']}")
        
        # Assert: Response is successful
        assert response.status_code == 200
        
        # Assert: Only mutual relationships returned
        mutual_followers = response.json()
        assert len(mutual_followers) == 2
        
        # Verify correct users are in the response
        mutual_names = {user["display_name"] for user in mutual_followers}
        assert "Mutual User 1" in mutual_names  # user1
        assert "Mutual User 3" in mutual_names  # user3
        assert "Mutual User 2" not in mutual_names  # user2 (one-way only)

    @pytest.mark.asyncio
    async def test_get_mutual_followers_empty_list(self, db_service, test_user, additional_test_users):
        """Test getting mutual followers when none exist."""
        # Setup: Use real authenticated users with no mutual followers
        user1_id = additional_test_users[0]["id"]
        user2_id = additional_test_users[1]["id"]
        
        # Create profiles for test users
        await create_test_profiles(db_service, [user1_id, user2_id], "Test User")
        
        # Create one-way relationship (no mutual follows)
        await db_service.follow_user(test_user["id"], user1_id)  # test_user follows user1
        
        # Execute: Get mutual followers
        response = client.get(f"/api/v1/social/mutual/{test_user['id']}")
        
        # Assert: Should return empty list
        assert response.status_code == 200
        mutual_followers = response.json()
        assert mutual_followers == []

    @pytest.mark.asyncio
    async def test_social_endpoints_with_nonexistent_users(self, db_service, test_user):
        """Test social endpoints with non-existent user IDs."""
        # Setup: Use one real user
        user_id = test_user["id"]
        await create_test_profiles(db_service, [user_id], "Test User")
        fake_user_id = str(uuid4())
        
        # Test followers with non-existent user
        response = client.get(f"/api/v1/social/followers/{fake_user_id}")
        assert response.status_code == 200
        assert response.json() == []
        
        # Test following with non-existent user
        response = client.get(f"/api/v1/social/following/{fake_user_id}")
        assert response.status_code == 200
        assert response.json() == []
        
        # Test mutual followers with non-existent user
        response = client.get(f"/api/v1/social/mutual/{fake_user_id}")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_social_endpoints_with_invalid_uuids(self):
        """Test all social endpoints with invalid UUID formats."""
        # Test follow with invalid UUIDs
        response = client.post(
            "/api/v1/social/follow/invalid-uuid",
            json={"followee_id": str(uuid4())}
        )
        assert response.status_code == 422
        
        # Test unfollow with invalid UUIDs
        response = client.delete("/api/v1/social/follow/invalid-uuid/another-invalid-uuid")
        assert response.status_code == 422
        
        # Test get followers with invalid UUID
        response = client.get("/api/v1/social/followers/invalid-uuid")
        assert response.status_code == 422
        
        # Test get following with invalid UUID
        response = client.get("/api/v1/social/following/invalid-uuid")
        assert response.status_code == 422
        
        # Test mutual followers with invalid UUID
        response = client.get("/api/v1/social/mutual/invalid-uuid")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_follow_with_invalid_followee_uuid(self, test_user):
        """Test follow endpoint with invalid followee UUID in request body."""
        # Execute: Send follow request with invalid followee UUID
        response = client.post(
            f"/api/v1/social/follow/{test_user['id']}",
            json={"followee_id": "invalid-followee-uuid"}
        )
        
        # Assert: Should return validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_follow_duplicate_relationship(self, db_service, additional_test_users):
        """Test following the same user twice."""
        # Setup: Use real authenticated users and establish follow relationship
        user_ids = [user["id"] for user in additional_test_users[:2]]
        await create_test_profiles(db_service, user_ids, "User")
        
        follower_id = user_ids[0]
        followee_id = user_ids[1]
        
        # First follow
        await db_service.follow_user(follower_id, followee_id)
        
        # Execute: Try to follow again
        response = client.post(
            f"/api/v1/social/follow/{follower_id}",
            json={"followee_id": followee_id}
        )
        
        # Assert: Should handle gracefully (implementation dependent)
        # This might return 400 or 200 depending on business logic
        assert response.status_code in [200, 400] 