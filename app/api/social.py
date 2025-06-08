from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core import social as social_core
from app.schemas.social import FollowRequest, UserProfileResponse

router = APIRouter(prefix="/social", tags=["social"])


@router.post("/follow/{user_id}")
async def follow_player(user_id: UUID, follow_request: FollowRequest):
    """Follow another player."""
    try:
        # Check if already following
        following = await social_core.get_following(user_id)
        if any(f["user_id"] == str(follow_request.followee_id) for f in following):
            return {"message": "Already following this user", "data": None}
        
        # Create follow relationship
        result = await social_core.follow_player(user_id, follow_request.followee_id)
        return {"message": "Successfully followed user", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/follow/{user_id}/{followee_id}")
async def unfollow_player(user_id: UUID, followee_id: UUID):
    """Unfollow another player."""
    try:
        await social_core.unfollow_player(user_id, followee_id)
        return {"message": "Successfully unfollowed user"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/followers/{user_id}", response_model=List[UserProfileResponse])
async def get_followers(user_id: UUID):
    """Get all followers of a user."""
    try:
        followers = await social_core.get_followers(user_id)
        return [UserProfileResponse(**follower) for follower in followers]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/following/{user_id}", response_model=List[UserProfileResponse])
async def get_following(user_id: UUID):
    """Get all users that a user is following."""
    try:
        following = await social_core.get_following(user_id)
        return [UserProfileResponse(**followee) for followee in following]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mutual/{user_id}", response_model=List[UserProfileResponse])
async def get_mutual_followers(user_id: UUID):
    """Get mutual followers (users who follow each other)."""
    try:
        mutual = await social_core.get_mutual_followers(user_id)
        return [UserProfileResponse(**user) for user in mutual]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 