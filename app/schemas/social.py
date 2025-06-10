from uuid import UUID

from pydantic import BaseModel


class FollowRequest(BaseModel):
    followee_id: UUID


class UserProfileResponse(BaseModel):
    user_id: UUID
    display_name: str
    avatar_url: str | None = None 