"""
Unit tests for social functionality in the Smash Mate application.

Tests cover following/unfollowing players, retrieving follower/following lists,
and mutual follower relationships. All tests use the local database and
include proper error handling verification.
"""

import pytest
from uuid import UUID
from app.core.social import follow_player, unfollow_player, get_followers, get_following, get_mutual_followers
from tests.utils import (
    reset_database, 
    create_test_profiles, 
    assert_follow_relationship_exists,
    assert_profile_in_list
)


@pytest.fixture(autouse=True)
async def cleanup_database(db_service):
    """Clean up the database before and after each test."""
    await reset_database(db_service)
    yield
    await reset_database(db_service)


@pytest.mark.asyncio
async def test_follow_player_success(db_service, test_user, additional_test_users):
    """Test successfully following another player."""
    follower_id = UUID(test_user["id"])
    followee_id = UUID(additional_test_users[0]["id"])
    
    # Execute: Create follow relationship
    result = await follow_player(follower_id, followee_id, database=db_service)
    
    # Assert: Follow relationship created with correct IDs
    assert result["follower"] == str(follower_id)
    assert result["followee"] == str(followee_id)
    
    # Verify: Follow relationship exists in database
    followers = await db_service.get_followers(followee_id)
    assert len(followers) == 1
    assert_follow_relationship_exists(followers, follower_id, followee_id)


@pytest.mark.asyncio
async def test_follow_player_with_default_database(test_user, additional_test_users):
    """Test following a player using default database service initialization."""
    follower_id = UUID(test_user["id"])
    followee_id = UUID(additional_test_users[0]["id"])
    
    # Execute: Use default database parameter (None)
    result = await follow_player(follower_id, followee_id)
    
    # Assert: Follow relationship created correctly
    assert result["follower"] == str(follower_id)
    assert result["followee"] == str(followee_id)


@pytest.mark.asyncio
async def test_unfollow_player_success(db_service, test_user, additional_test_users):
    """Test successfully unfollowing another player."""
    follower_id = UUID(test_user["id"])
    followee_id = UUID(additional_test_users[0]["id"])
    
    # Setup: Create a follow relationship first
    await follow_player(follower_id, followee_id, database=db_service)
    
    # Verify setup: Follow relationship exists
    followers = await db_service.get_followers(followee_id)
    assert len(followers) == 1
    
    # Execute: Remove follow relationship
    await unfollow_player(follower_id, followee_id, database=db_service)
    
    # Assert: Follow relationship was removed
    followers = await db_service.get_followers(followee_id)
    assert len(followers) == 0


@pytest.mark.asyncio
async def test_unfollow_player_nonexistent_relationship(db_service, test_user, additional_test_users):
    """Test unfollowing when no follow relationship exists (should not raise error)."""
    follower_id = UUID(test_user["id"])
    followee_id = UUID(additional_test_users[0]["id"])
    
    # Execute: Attempt to unfollow non-existent relationship (should not error)
    await unfollow_player(follower_id, followee_id, database=db_service)
    
    # Assert: No followers exist (operation was safe)
    followers = await db_service.get_followers(followee_id)
    assert len(followers) == 0


@pytest.mark.asyncio
async def test_get_followers_with_profiles(db_service, test_user, additional_test_users):
    """Test getting followers with their profile information."""
    user_id = UUID(test_user["id"])
    follower_ids = [additional_test_users[0]["id"], additional_test_users[1]["id"]]
    
    # Setup: Create profiles for followers
    await create_test_profiles(db_service, follower_ids, "Follower")
    
    # Setup: Create follow relationships
    for follower_id in follower_ids:
        await follow_player(UUID(follower_id), user_id, database=db_service)
    
    # Execute: Get followers with profile data
    followers = await get_followers(user_id, database=db_service)
    
    # Assert: Both followers returned with correct profile data
    assert len(followers) == 2
    assert_profile_in_list(followers, "Follower 1")
    assert_profile_in_list(followers, "Follower 2")


@pytest.mark.asyncio
async def test_get_followers_empty_list(db_service, test_user):
    """Test getting followers when user has no followers."""
    user_id = UUID(test_user["id"])
    
    # Execute: Get followers for user with no followers
    followers = await get_followers(user_id, database=db_service)
    
    # Assert: Empty list returned
    assert len(followers) == 0


@pytest.mark.asyncio
async def test_get_followers_with_missing_profiles(db_service, test_user, additional_test_users, caplog):
    """
    Test getting followers when some followers don't have profiles.
    
    This tests error handling - missing profiles should be skipped gracefully
    with appropriate error logging.
    """
    user_id = UUID(test_user["id"])
    follower1_id = UUID(additional_test_users[0]["id"])
    follower2_id = UUID(additional_test_users[1]["id"])
    
    # Setup: Create profile for only one follower
    await db_service.create_profile(follower1_id, {"display_name": "Follower One"})
    # Intentionally skip creating profile for follower2_id
    
    # Setup: Create follow relationships for both users
    await follow_player(follower1_id, user_id, database=db_service)
    await follow_player(follower2_id, user_id, database=db_service)
    
    # Execute: Get followers (should handle missing profile gracefully)
    followers = await get_followers(user_id, database=db_service)
    
    # Assert: Only follower with profile is returned
    assert len(followers) == 1
    assert followers[0]["display_name"] == "Follower One"
    
    # Assert: Error was logged for missing profile
    assert "Error getting profile for follower" in caplog.text
    assert str(follower2_id) in caplog.text


@pytest.mark.asyncio
async def test_get_following_with_profiles(db_service, test_user, additional_test_users):
    """Test getting users that a user is following with their profile information."""
    user_id = UUID(test_user["id"])
    followee_ids = [additional_test_users[0]["id"], additional_test_users[1]["id"]]
    
    # Setup: Create profiles for followees
    await create_test_profiles(db_service, followee_ids, "Followee")
    
    # Setup: Create follow relationships
    for followee_id in followee_ids:
        await follow_player(user_id, UUID(followee_id), database=db_service)
    
    # Execute: Get following list with profile data
    following = await get_following(user_id, database=db_service)
    
    # Assert: Both followees returned with correct profile data
    assert len(following) == 2
    assert_profile_in_list(following, "Followee 1")
    assert_profile_in_list(following, "Followee 2")


@pytest.mark.asyncio
async def test_get_following_empty_list(db_service, test_user):
    """Test getting following when user is not following anyone."""
    user_id = UUID(test_user["id"])
    
    # Execute: Get following list for user following no one
    following = await get_following(user_id, database=db_service)
    
    # Assert: Empty list returned
    assert len(following) == 0


@pytest.mark.asyncio
async def test_get_following_with_missing_profiles(db_service, test_user, additional_test_users, caplog):
    """
    Test getting following when some followees don't have profiles.
    
    This tests error handling - missing profiles should be skipped gracefully
    with appropriate error logging.
    """
    user_id = UUID(test_user["id"])
    followee1_id = UUID(additional_test_users[0]["id"])
    followee2_id = UUID(additional_test_users[1]["id"])
    
    # Setup: Create profile for only one followee
    await db_service.create_profile(followee1_id, {"display_name": "Followee One"})
    # Intentionally skip creating profile for followee2_id
    
    # Setup: Create follow relationships for both users
    await follow_player(user_id, followee1_id, database=db_service)
    await follow_player(user_id, followee2_id, database=db_service)
    
    # Execute: Get following list (should handle missing profile gracefully)
    following = await get_following(user_id, database=db_service)
    
    # Assert: Only followee with profile is returned
    assert len(following) == 1
    assert following[0]["display_name"] == "Followee One"
    
    # Assert: Error was logged for missing profile
    assert "Error getting profile for followee" in caplog.text
    assert str(followee2_id) in caplog.text


@pytest.mark.asyncio
async def test_get_mutual_followers_success(db_service, test_user, additional_test_users):
    """
    Test getting mutual followers (users who follow each other).
    
    Sets up various follow relationships:
    - Two mutual relationships (user <-> user1, user <-> user3)
    - One one-way relationship (user -> user2 only)
    - Verifies only mutual relationships are returned
    """
    user_id = UUID(test_user["id"])
    user1_id = UUID(additional_test_users[0]["id"])
    user2_id = UUID(additional_test_users[1]["id"])
    user3_id = UUID(additional_test_users[2]["id"])
    
    # Setup: Create profiles for all test users
    user_ids = [str(user1_id), str(user2_id), str(user3_id)]
    await create_test_profiles(db_service, user_ids, "Mutual User")
    
    # Setup: Create mutual follow relationships
    # user <-> user1 (mutual)
    await follow_player(user_id, user1_id, database=db_service)
    await follow_player(user1_id, user_id, database=db_service)
    
    # user <-> user3 (mutual)
    await follow_player(user_id, user3_id, database=db_service)
    await follow_player(user3_id, user_id, database=db_service)
    
    # user -> user2 (one-way only, should not appear in results)
    await follow_player(user_id, user2_id, database=db_service)
    
    # Execute: Get mutual followers
    mutual_followers = await get_mutual_followers(user_id, database=db_service)
    
    # Assert: Only mutual relationships returned
    assert len(mutual_followers) == 2
    assert_profile_in_list(mutual_followers, "Mutual User 1")  # user1
    assert_profile_in_list(mutual_followers, "Mutual User 3")  # user3
    
    # Assert: One-way relationship not included
    profile_names = {m["display_name"] for m in mutual_followers}
    assert "Mutual User 2" not in profile_names


@pytest.mark.asyncio
async def test_get_mutual_followers_empty_list(db_service, test_user, additional_test_users):
    """Test getting mutual followers when there are no mutual relationships."""
    user_id = UUID(test_user["id"])
    user1_id = UUID(additional_test_users[0]["id"])
    
    # Setup: Create only one-way relationship (no mutual follows)
    await follow_player(user_id, user1_id, database=db_service)
    
    # Execute: Get mutual followers
    mutual_followers = await get_mutual_followers(user_id, database=db_service)
    
    # Assert: No mutual relationships found
    assert len(mutual_followers) == 0


@pytest.mark.asyncio
async def test_get_mutual_followers_with_missing_profiles(db_service, test_user, additional_test_users, caplog):
    """
    Test getting mutual followers when some don't have profiles.
    
    This tests error handling - missing profiles should be skipped gracefully
    with appropriate error logging.
    """
    user_id = UUID(test_user["id"])
    user1_id = UUID(additional_test_users[0]["id"])
    user2_id = UUID(additional_test_users[1]["id"])
    
    # Setup: Create profile for only one mutual follower
    await db_service.create_profile(user1_id, {"display_name": "Mutual User One"})
    # Intentionally skip creating profile for user2_id
    
    # Setup: Create mutual follow relationships for both users
    await follow_player(user_id, user1_id, database=db_service)
    await follow_player(user1_id, user_id, database=db_service)
    
    await follow_player(user_id, user2_id, database=db_service)
    await follow_player(user2_id, user_id, database=db_service)
    
    # Execute: Get mutual followers (should handle missing profile gracefully)
    mutual_followers = await get_mutual_followers(user_id, database=db_service)
    
    # Assert: Only mutual follower with profile is returned
    assert len(mutual_followers) == 1
    assert mutual_followers[0]["display_name"] == "Mutual User One"
    
    # Assert: Error was logged for missing profile
    assert "Error getting profile for mutual follower" in caplog.text
    assert str(user2_id) in caplog.text


@pytest.mark.asyncio
async def test_multiple_functions_integration(db_service, test_user, additional_test_users):
    """
    Integration test verifying multiple social functions work together.
    
    This test creates a realistic scenario with multiple users, follows,
    and profile data, then verifies all functions work correctly together.
    """
    user_id = UUID(test_user["id"])
    user1_id = UUID(additional_test_users[0]["id"])
    user2_id = UUID(additional_test_users[1]["id"])
    
    # Setup: Create profiles for test users
    await create_test_profiles(db_service, [str(user1_id), str(user2_id)], "Friend")
    
    # Setup: Create various follow relationships
    await follow_player(user_id, user1_id, database=db_service)  # user -> user1
    await follow_player(user_id, user2_id, database=db_service)  # user -> user2
    await follow_player(user1_id, user_id, database=db_service)  # user1 -> user (makes user1 mutual)
    
    # Test: Get following list (should include both friends)
    following = await get_following(user_id, database=db_service)
    assert len(following) == 2
    
    # Test: Get followers list (should include only user1)
    followers = await get_followers(user_id, database=db_service)
    assert len(followers) == 1
    assert followers[0]["display_name"] == "Friend 1"
    
    # Test: Get mutual followers (should include only user1)
    mutual_followers = await get_mutual_followers(user_id, database=db_service)
    assert len(mutual_followers) == 1
    assert mutual_followers[0]["display_name"] == "Friend 1"
    
    # Test: Unfollow operation
    await unfollow_player(user_id, user2_id, database=db_service)
    
    # Verify: Following list updated after unfollow
    following_after_unfollow = await get_following(user_id, database=db_service)
    assert len(following_after_unfollow) == 1
    assert following_after_unfollow[0]["display_name"] == "Friend 1" 