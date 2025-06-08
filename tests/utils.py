"""
Shared test utilities and helpers for the Smash Mate test suite.

This module contains common functions, constants, and patterns used across
multiple test files to reduce duplication and improve maintainability.
"""

from uuid import UUID, uuid4
from typing import List, Dict, Any, Tuple
from datetime import datetime
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Common test constants
DEFAULT_INITIAL_RATING = {
    "mu": 25.0,
    "sigma": 8.333,
    "games_played": 0
}

SAMPLE_VENUE_DATA = {
    "name": "Test Badminton Venue",
    "latitude": 37.7749,
    "longitude": -122.4194,
    "address": "123 Test Badminton Court"
}

SAMPLE_PROFILE_DATA = {
    "display_name": "Test User"
}


async def reset_database(db_service) -> None:
    """
    Reset the database by deleting all test data.
    
    This function deletes all records from test tables in the correct order
    to respect foreign key constraints. It's used to ensure clean state
    before and after each test.
    
    Args:
        db_service: DatabaseService instance to perform the cleanup
    """
    # Order matters - delete child tables before parent tables to respect foreign keys
    tables_to_clean = [
        # First, delete records that reference other tables
        "group_messages",     # References groups and users
        "messages",           # References users
        "match_players",      # References matches and users
        "matches",            # References venues and users
        "player_ratings",     # References users
        "teams",              # References users (player pairs)
        "follows",            # References users
        "groups",             # References users (created_by)
        "venues",             # References users (created_by)
        "profiles",           # References users (user_id)
    ]
    
    cleanup_count = 0
    for table in tables_to_clean:
        try:
            # Use async client method to delete all records
            # We delete all records since this is for testing
            result = await db_service.client.table(table).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            if hasattr(result, 'data') and result.data:
                cleanup_count += len(result.data)
                logger.debug(f"Cleaned {len(result.data)} records from {table}")
        except Exception as e:
            # Log but don't fail - table might be empty or constraint issues
            logger.debug(f"Could not clean table {table}: {str(e)}")
            pass
    
    logger.info(f"Database cleanup completed: {cleanup_count} total records cleaned")


async def comprehensive_database_cleanup(db_service) -> None:
    """
    Comprehensive database cleanup specifically for integration tests.
    
    This function performs a thorough cleanup of all test-related data,
    including attempts to handle constraint violations and orphaned records.
    Should be used with @pytest.fixture(autouse=True) for integration tests.
    
    Args:
        db_service: DatabaseService instance to perform the cleanup
    """
    logger.info("Starting comprehensive database cleanup for integration tests...")
    
    # Step 1: Delete all test-related records in dependency order
    cleanup_operations = [
        # Delete message and group data first (most dependent)
        ("group_messages", ["group_id", "sender_id"]),
        ("messages", ["sender_id", "receiver_id"]),
        
        # Delete match-related data
        ("match_players", ["match_id", "player_id"]),
        ("matches", ["venue_id", "created_by"]),
        
        # Delete rating and team data
        ("player_ratings", ["player_id"]),
        ("teams", ["player1_id", "player2_id"]),
        
        # Delete social connections
        ("follows", ["follower", "followee"]),
        
        # Delete groups
        ("groups", ["created_by"]),
        
        # Delete venue data
        ("venues", ["created_by"]),
        
        # Finally delete profiles (least dependent)
        ("profiles", ["user_id"]),
    ]
    
    total_cleaned = 0
    
    for table, reference_columns in cleanup_operations:
        try:
            # First attempt: delete all records
            result = await db_service.client.table(table).delete().neq("id", "").execute()
            
            if hasattr(result, 'data') and result.data:
                cleaned_count = len(result.data)
                total_cleaned += cleaned_count
                logger.debug(f"Cleaned {cleaned_count} records from {table}")
            
        except Exception as e:
            logger.warning(f"Standard cleanup failed for {table}: {str(e)}")
            
            # Step 2: If standard cleanup fails, try cleaning by reference columns
            for ref_col in reference_columns:
                try:
                    # Delete records where reference column is not null
                    result = await db_service.client.table(table).delete().not_.is_(ref_col, "null").execute()
                    if hasattr(result, 'data') and result.data:
                        cleaned_count = len(result.data)
                        total_cleaned += cleaned_count
                        logger.debug(f"Cleaned {cleaned_count} records from {table} by {ref_col}")
                except Exception as ref_error:
                    logger.debug(f"Reference cleanup failed for {table}.{ref_col}: {str(ref_error)}")
                    continue
    
    # Step 3: Final verification - try to count remaining records
    verification_tables = ["profiles", "venues", "matches", "follows"]
    remaining_records = {}
    
    for table in verification_tables:
        try:
            result = await db_service.client.table(table).select("id").execute()
            count = len(result.data) if hasattr(result, 'data') and result.data else 0
            if count > 0:
                remaining_records[table] = count
        except Exception:
            pass  # Table might not exist or be accessible
    
    if remaining_records:
        logger.warning(f"Some records remain after cleanup: {remaining_records}")
    else:
        logger.info("Database cleanup verification passed - no test records remaining")
    
    logger.info(f"Comprehensive database cleanup completed: {total_cleaned} total records cleaned")


async def cleanup_test_users(supabase_client, user_list: List[Dict[str, str]]) -> None:
    """
    Clean up test users from Supabase auth.
    
    This function attempts to delete test users from the authentication system.
    Should be called in test fixture cleanup.
    
    Args:
        supabase_client: Supabase client instance
        user_list: List of user dictionaries with 'id' field
    """
    deleted_count = 0
    failed_count = 0
    
    for user in user_list:
        try:
            supabase_client.auth.admin.delete_user(user["id"])
            deleted_count += 1
            logger.debug(f"Deleted test user: {user['id']}")
        except Exception as e:
            failed_count += 1
            logger.debug(f"Could not delete user {user['id']}: {str(e)}")
    
    if failed_count > 0:
        logger.warning(f"Failed to delete {failed_count} test users (this is often normal)")
    
    logger.info(f"Test user cleanup completed: {deleted_count} users deleted, {failed_count} failed")


async def setup_initial_ratings(db_service, user_ids: List[str], rating_data: Dict[str, Any] = None) -> None:
    """
    Set up initial player ratings for a list of users.
    
    This is commonly needed in match-related tests to ensure TrueSkill
    calculations work properly.
    
    Args:
        db_service: DatabaseService instance
        user_ids: List of user IDs to create ratings for
        rating_data: Rating data to use (defaults to DEFAULT_INITIAL_RATING)
    """
    if rating_data is None:
        rating_data = DEFAULT_INITIAL_RATING.copy()
    
    for user_id in user_ids:
        await db_service.update_player_rating(UUID(user_id), **rating_data)


async def create_test_profiles(db_service, user_ids: List[str], name_prefix: str = "User") -> List[Dict[str, Any]]:
    """
    Create test profiles for a list of users.
    
    Args:
        db_service: DatabaseService instance
        user_ids: List of user IDs to create profiles for
        name_prefix: Prefix for display names (will be numbered)
        
    Returns:
        List of created profile dictionaries
    """
    profiles = []
    for i, user_id in enumerate(user_ids, 1):
        profile_data = {"display_name": f"{name_prefix} {i}"}
        profile = await db_service.create_profile(UUID(user_id), profile_data)
        profiles.append(profile)
    return profiles


async def create_test_venue(db_service, created_by: str, venue_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Create a test venue with default or provided data.
    
    Args:
        db_service: DatabaseService instance
        created_by: User ID who creates the venue
        venue_data: Custom venue data (merges with defaults)
        
    Returns:
        Created venue dictionary
    """
    if venue_data is None:
        venue_data = SAMPLE_VENUE_DATA.copy()
    
    venue_data["created_by"] = created_by
    return await db_service.create_venue(**venue_data)


def create_sample_match_data(
    venue_id: UUID,
    created_by: str,
    team1_players: Tuple[str, str],
    team2_players: Tuple[str, str],
    team1_wins: bool = True,
    scores: List[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Create sample match data for testing.
    
    Args:
        venue_id: Venue where match is played
        created_by: User who creates the match
        team1_players: Tuple of (player1_id, player2_id) for team 1
        team2_players: Tuple of (player1_id, player2_id) for team 2
        team1_wins: Whether team 1 wins (affects default scores)
        scores: Custom scores (will generate default if None)
        
    Returns:
        Dictionary with match data ready for create_match()
    """
    if scores is None:
        if team1_wins:
            scores = [{"team1": 21, "team2": 18}, {"team1": 21, "team2": 15}]
        else:
            scores = [{"team1": 18, "team2": 21}, {"team1": 15, "team2": 21}]
    
    return {
        "venue_id": venue_id,
        "created_by": created_by,
        "team1_players": team1_players,
        "team2_players": team2_players,
        "scores": scores,
        "played_at": datetime.now()
    }


def assert_follow_relationship_exists(followers_data: List[Dict], follower_id: str, followee_id: str) -> None:
    """
    Assert that a follow relationship exists in the followers data.
    
    Args:
        followers_data: List of follower dictionaries from database
        follower_id: Expected follower ID
        followee_id: Expected followee ID (for error messages)
    """
    follower_ids = [f["follower"] for f in followers_data]
    assert str(follower_id) in follower_ids, f"Follow relationship not found: {follower_id} -> {followee_id}"


def assert_profile_in_list(profiles: List[Dict], expected_name: str) -> None:
    """
    Assert that a profile with the expected display name exists in the list.
    
    Args:
        profiles: List of profile dictionaries
        expected_name: Expected display name to find
    """
    profile_names = {p["display_name"] for p in profiles}
    assert expected_name in profile_names, f"Profile '{expected_name}' not found in {profile_names}"


def assert_match_players_correct(match_data: Dict, expected_player_count: int = 4) -> None:
    """
    Assert that match has the correct number of players and structure.
    
    Args:
        match_data: Match dictionary from database
        expected_player_count: Expected number of players (default 4 for doubles)
    """
    assert "players" in match_data, "Match data missing 'players' field"
    assert len(match_data["players"]) == expected_player_count, \
        f"Expected {expected_player_count} players, got {len(match_data['players'])}"
    
    # Verify player data structure
    for player in match_data["players"]:
        assert "player_id" in player, "Player missing 'player_id'"
        assert "team" in player, "Player missing 'team'"
        assert "is_winner" in player, "Player missing 'is_winner'"


def assert_ratings_updated_correctly(ratings: List[Dict], initial_mu: float = 25.0) -> None:
    """
    Assert that player ratings have been updated from their initial values.
    
    Args:
        ratings: List of rating dictionaries
        initial_mu: Initial mu value to compare against
    """
    for rating in ratings:
        assert rating is not None, "Rating should not be None"
        assert rating["games_played"] >= 1, "Games played should be at least 1 after a match"
        # Rating should have changed from initial value
        assert float(rating["mu"]) != initial_mu, f"Rating mu should have changed from initial {initial_mu}"


class TestDataBuilder:
    """
    Builder class for creating complex test data structures.
    
    This class provides a fluent interface for building test data,
    making test setup more readable and maintainable.
    """
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset the builder to initial state."""
        self._users = []
        self._profiles = []
        self._follows = []
        self._venue = None
        return self
    
    def with_users(self, count: int = 4):
        """Add test users to the builder."""
        self._users = [{"id": str(uuid4()), "email": f"test{i}@example.com"} for i in range(count)]
        return self
    
    def with_profiles(self, name_prefix: str = "Test User"):
        """Add profiles for all users."""
        for i, user in enumerate(self._users, 1):
            self._profiles.append({
                "user_id": user["id"],
                "display_name": f"{name_prefix} {i}"
            })
        return self
    
    def with_mutual_follows(self, user1_idx: int = 0, user2_idx: int = 1):
        """Add mutual follow relationship between two users."""
        if len(self._users) > max(user1_idx, user2_idx):
            user1_id = self._users[user1_idx]["id"]
            user2_id = self._users[user2_idx]["id"]
            self._follows.extend([
                {"follower": user1_id, "followee": user2_id},
                {"follower": user2_id, "followee": user1_id}
            ])
        return self
    
    def with_venue(self, created_by_idx: int = 0):
        """Add a test venue."""
        if self._users:
            self._venue = {
                **SAMPLE_VENUE_DATA,
                "created_by": self._users[created_by_idx]["id"]
            }
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build and return the test data structure."""
        return {
            "users": self._users,
            "profiles": self._profiles,
            "follows": self._follows,
            "venue": self._venue
        } 