from typing import List, Dict, Any
from uuid import UUID
import traceback
from app.services.database import DatabaseService

async def follow_player(follower_id: UUID, followee_id: UUID, database: DatabaseService = None) -> Dict[str, Any]:
    """Follow another player."""
    if database is None:
        database = DatabaseService()
    return await database.follow_user(follower_id, followee_id)

async def unfollow_player(follower_id: UUID, followee_id: UUID, database: DatabaseService = None) -> None:
    """Unfollow another player."""
    if database is None:
        database = DatabaseService()
    await database.unfollow_user(follower_id, followee_id)

async def get_followers(user_id: UUID, database: DatabaseService = None) -> List[Dict[str, Any]]:
    """Get all followers of a user with their profiles."""
    if database is None:
        database = DatabaseService()
    
    followers = await database.get_followers(user_id)
    profiles = []
    
    for follower in followers:
        try:
            profile = await database.get_profile(UUID(follower["follower"]))
            profiles.append(profile)
        except Exception as e:
            # Print traceback and related info
            print(f"Error getting profile for follower {follower['follower']} of user {user_id}:")
            print(f"Exception: {type(e).__name__}: {e}")
            print(f"Traceback:")
            traceback.print_exc()
            # Skip if profile doesn't exist
            continue
    
    return profiles

async def get_following(user_id: UUID, database: DatabaseService = None) -> List[Dict[str, Any]]:
    """Get all users that a user is following with their profiles."""
    if database is None:
        database = DatabaseService()
    
    following = await database.get_following(user_id)
    profiles = []
    
    for followee in following:
        try:
            profile = await database.get_profile(UUID(followee["followee"]))
            profiles.append(profile)
        except Exception as e:
            # Print traceback and related info
            print(f"Error getting profile for followee {followee['followee']} followed by user {user_id}:")
            print(f"Exception: {type(e).__name__}: {e}")
            print(f"Traceback:")
            traceback.print_exc()
            # Skip if profile doesn't exist
            continue
    
    return profiles

async def get_mutual_followers(user_id: UUID, database: DatabaseService = None) -> List[Dict[str, Any]]:
    """Get mutual followers (users who follow each other) with their profiles."""
    if database is None:
        database = DatabaseService()
    
    mutual_followers = await database.get_mutual_followers(user_id)
    profiles = []
    
    for mutual in mutual_followers:
        try:
            profile = await database.get_profile(UUID(mutual["user_id"]))
            profiles.append(profile)
        except Exception as e:
            # Print traceback and related info
            print(f"Error getting profile for mutual follower {mutual['user_id']} of user {user_id}:")
            print(f"Exception: {type(e).__name__}: {e}")
            print(f"Traceback:")
            traceback.print_exc()
            # Skip if profile doesn't exist
            continue
    
    return profiles 