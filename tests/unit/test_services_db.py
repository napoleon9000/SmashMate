import pytest
from datetime import datetime
from uuid import UUID, uuid4
from app.services.database import DatabaseService
import os

# Test data
TEST_URL = os.getenv("LOCAL_SUPABASE_URL", "https://test.supabase.co")
TEST_KEY = os.getenv("LOCAL_SUPABASE_KEY", "your-test-key")
TEST_VENUE_ID = uuid4()
TEST_MATCH_ID = uuid4()

@pytest.fixture(scope="session")
def db_service():
    """Create a database service instance for testing."""
    service = DatabaseService(TEST_URL, TEST_KEY)
    return service

async def reset_database(db_service):
    """Reset the database by deleting all test data."""
    tables = [
        "match_players",  # First delete match_players as it references matches
        "matches",        # Then matches as it references venues and users
        "player_ratings", # Then player ratings as it references users
        "teams",         # Then teams as it references users
        "follows",       # Then follows as it references users
        "venues",        # Then venues as it references users
        "profiles"       # Finally profiles as it references users
    ]
    for table in tables:
        try:
            await db_service.client.table(table).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        except Exception:
            pass

@pytest.fixture
async def additional_test_users(supabase_client, db_service):
    """Create additional test users for testing relationships."""
    users = []
    for i in range(4):  # Create 4 additional users
        test_email = f"test_{i}{uuid4()}@example.com"
        test_password = "test_password123"
        
        # Create user with service role
        auth_response = supabase_client.auth.admin.create_user({
            "email": test_email,
            "password": test_password,
            "email_confirm": True  # Auto-confirm the email
        })
        
        users.append({
            "id": auth_response.user.id,
            "email": test_email,
            "password": test_password
        })
    
    yield users
    
    # Clean up: delete all associated records first
    for user in users:
        # Delete all records associated with this user
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
                await db_service.client.table(table).delete().eq("user_id", user["id"]).execute()
            except Exception:
                pass
            try:
                await db_service.client.table(table).delete().eq("player_id", user["id"]).execute()
            except Exception:
                pass
            try:
                await db_service.client.table(table).delete().eq("follower", user["id"]).execute()
            except Exception:
                pass
            try:
                await db_service.client.table(table).delete().eq("followee", user["id"]).execute()
            except Exception:
                pass
            try:
                await db_service.client.table(table).delete().eq("created_by", user["id"]).execute()
            except Exception:
                pass
        
        # Now delete the user - handle the error gracefully
        try:
            supabase_client.auth.admin.delete_user(user["id"])
        except Exception as e:
            print(f"Warning: Could not delete user {user['id']}: {str(e)}")
            # Continue with cleanup even if user deletion fails
            pass

@pytest.fixture(autouse=True)
async def cleanup_database(db_service):
    """Clean up the database before and after each test."""
    # Reset before test
    await reset_database(db_service)
    yield
    # Reset after test
    await reset_database(db_service)

@pytest.mark.asyncio
async def test_init_with_env_vars():
    with pytest.raises(ValueError):
        DatabaseService()

@pytest.mark.asyncio
async def test_profile(db_service, test_user):
    # Test create profile
    user_id = test_user["id"]
    profile_data = {
        "display_name": "Test User"
    }
    
    result = await db_service.create_profile(user_id, profile_data)
    assert result["user_id"] == str(user_id)
    assert result["display_name"] == profile_data["display_name"]
    
    # Test get profile
    result = await db_service.get_profile(user_id)
    assert result["user_id"] == str(user_id)
    assert result["display_name"] == profile_data["display_name"]
    
    # Test update profile
    update_data = {"display_name": "Updated Name"}
    result = await db_service.update_profile(user_id, update_data)
    assert result["display_name"] == update_data["display_name"]
    
    # Test delete profile
    await db_service.delete_profile(user_id)
    with pytest.raises(Exception):
        await db_service.get_profile(user_id)

@pytest.mark.asyncio
async def test_venue(db_service, test_user):
    # Test create venue
    venue_data = {
        "name": "Test Venue",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "address": "123 Test St",
        "created_by": test_user["id"]
    }
    
    result = await db_service.create_venue(**venue_data)
    assert result["name"] == venue_data["name"]
    assert result["address"] == venue_data["address"]
    
    venue_id = UUID(result["id"])
    
    # Test get venue
    result = await db_service.get_venue(venue_id)
    assert result["name"] == venue_data["name"]
    
    # Test update venue
    update_data = {"name": "Updated Venue"}
    result = await db_service.update_venue(venue_id, update_data)
    assert result["name"] == update_data["name"]
    
    # Test delete venue
    await db_service.delete_venue(venue_id)
    with pytest.raises(Exception):
        await db_service.get_venue(venue_id)

@pytest.mark.asyncio
async def test_follow(db_service, test_user, additional_test_users):
    follower_id = test_user["id"]
    followee_id = additional_test_users[0]["id"]
    
    # Test follow
    result = await db_service.follow_user(follower_id, followee_id)
    assert result["follower"] == str(follower_id)
    assert result["followee"] == str(followee_id)
    
    # Test get followers
    followers = await db_service.get_followers(followee_id)
    assert len(followers) == 1
    assert followers[0]["follower"] == str(follower_id)
    
    # Test get following
    following = await db_service.get_following(follower_id)
    assert len(following) == 1
    assert following[0]["followee"] == str(followee_id)
    
    # Test unfollow
    await db_service.unfollow_user(follower_id, followee_id)
    followers = await db_service.get_followers(followee_id)
    assert len(followers) == 0

@pytest.mark.asyncio
async def test_team(db_service, test_user, additional_test_users):
    player_a = test_user["id"]
    player_b = additional_test_users[0]["id"]
    
    # Test create team
    team_data = {
        "player_a": player_a,
        "player_b": player_b,
        "mu": 25.0,
        "sigma": 8.333
    }
    
    # First create should create a new team
    result = await db_service.create_team(**team_data)
    assert result["player_a"] == str(player_a)
    assert result["player_b"] == str(player_b)
    assert float(result["mu"]) == team_data["mu"]
    
    team_id = UUID(result["id"])
    
    # Second create should return the existing team
    result2 = await db_service.create_team(**team_data)
    assert result2["id"] == result["id"]
    
    # Test update team rating
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
async def test_player_rating(db_service, test_user):
    # Test update player rating
    rating_data = {
        "mu": 25.0,
        "sigma": 8.333,
        "games_played": 10
    }
    
    result = await db_service.update_player_rating(test_user["id"], **rating_data)
    assert float(result["mu"]) == rating_data["mu"]
    assert float(result["sigma"]) == rating_data["sigma"]
    assert result["games_played"] == rating_data["games_played"]

@pytest.mark.asyncio
async def test_match(db_service, test_user, additional_test_users):
    # Create a venue first
    venue_data = {
        "name": "Test Venue",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "address": "123 Test St",
        "created_by": test_user["id"]
    }
    venue = await db_service.create_venue(**venue_data)
    venue_id = UUID(venue["id"])
    
    # Test create match
    player1_id = test_user["id"]
    player2_id = additional_test_users[0]["id"]
    player3_id = additional_test_users[1]["id"]
    player4_id = additional_test_users[2]["id"]
    
    match_data = {
        "venue_id": venue_id,
        "played_at": datetime.now(),
        "created_by": test_user["id"],
        "scores": [{"set": 1, "team1": 21, "team2": 17}],
        "players": [
            (player1_id, 1, True),
            (player2_id, 1, True),
            (player3_id, 2, False),
            (player4_id, 2, False)
        ]
    }
    
    result = await db_service.create_match(**match_data)
    assert result["venue_id"] == str(venue_id)
    assert result["status"] == "confirmed"
    
    match_id = UUID(result["id"])
    
    # Test get match
    result = await db_service.get_match(match_id)
    assert result["id"] == str(match_id)
    assert len(result["players"]) == 4
    
    # Test update match
    update_data = {"status": "pending"}
    result = await db_service.update_match(match_id, update_data)
    assert result["status"] == update_data["status"]

@pytest.mark.asyncio
async def test_team_compatibility(db_service, test_user, additional_test_users):
    player_a = test_user["id"]
    player_b = additional_test_users[0]["id"]
    
    # First create ratings for both players
    rating_data = {
        "mu": 25.0,
        "sigma": 8.333,
        "games_played": 10
    }
    await db_service.update_player_rating(player_a, **rating_data)
    await db_service.update_player_rating(player_b, **rating_data)
    
    # Create a team to test compatibility
    team_data = {
        "player_a": player_a,
        "player_b": player_b,
        "mu": 25.0,
        "sigma": 8.333
    }
    
    # First create should create a new team
    result = await db_service.create_team(**team_data)
    # Since player_a > player_b, they will be swapped in create_team
    assert result["player_a"] == str(player_b)  # player_b becomes player_a
    assert result["player_b"] == str(player_a)  # player_a becomes player_b
    assert float(result["mu"]) == team_data["mu"]
    assert float(result["sigma"]) == team_data["sigma"]
    
    # Second create should return the existing team
    result2 = await db_service.create_team(**team_data)
    assert result2["id"] == result["id"]
