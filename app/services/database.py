from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import os
from supabase import create_client, Client
from uuid import UUID

class DatabaseService:
    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        """Initialize the database service with Supabase credentials."""
        self.url = url or os.getenv("SUPABASE_URL")
        self.key = key or os.getenv("SUPABASE_KEY")
        if not self.url or not self.key:
            raise ValueError("Supabase URL and key must be provided or set in environment variables")
        self.client: Client = create_client(self.url, self.key)

    # Profile operations
    async def get_profile(self, user_id: UUID) -> Dict[str, Any]:
        """Get a user's profile."""
        response = self.client.table("profiles").select("*").eq("user_id", str(user_id)).single().execute()
        return response.data

    async def create_profile(self, user_id: UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user profile."""
        profile_data = {
            "user_id": str(user_id),
            "display_name": data.get("display_name", "")
        }
        response = self.client.table("profiles").insert(profile_data).execute()
        return response.data[0]

    async def delete_profile(self, user_id: UUID) -> None:
        """Delete a user's profile."""
        self.client.table("profiles").delete().eq("user_id", str(user_id)).execute()

    async def update_profile(self, user_id: UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a user's profile."""
        response = self.client.table("profiles").update(data).eq("user_id", str(user_id)).execute()
        return response.data[0]

    # Venue operations
    async def create_venue(self, name: str, latitude: float, longitude: float, address: str, created_by: UUID) -> Dict[str, Any]:
        """Create a new venue."""
        # First ensure the user exists
        try:
            self.client.table("users").insert({"id": str(created_by)}).execute()
        except Exception:
            pass  # User might already exist

        data = {
            "name": name,
            "location": f"POINT({longitude} {latitude})",
            "address": address,
            "created_by": str(created_by)
        }
        response = self.client.table("venues").insert(data).execute()
        return response.data[0]

    async def get_venue(self, venue_id: UUID) -> Dict[str, Any]:
        """Get a venue by ID."""
        response = self.client.table("venues").select("*").eq("id", str(venue_id)).single().execute()
        return response.data

    async def update_venue(self, venue_id: UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a venue."""
        response = self.client.table("venues").update(data).eq("id", str(venue_id)).execute()
        return response.data[0]

    async def delete_venue(self, venue_id: UUID) -> None:
        """Delete a venue."""
        self.client.table("venues").delete().eq("id", str(venue_id)).execute()

    # Follow operations
    async def follow_user(self, follower_id: UUID, followee_id: UUID) -> Dict[str, Any]:
        """Create a follow relationship."""
        # First ensure both users exist
        try:
            self.client.table("users").insert({"id": str(follower_id)}).execute()
            self.client.table("users").insert({"id": str(followee_id)}).execute()
        except Exception:
            pass  # Users might already exist

        data = {
            "follower": str(follower_id),
            "followee": str(followee_id)
        }
        response = self.client.table("follows").insert(data).execute()
        return response.data[0]

    async def unfollow_user(self, follower_id: UUID, followee_id: UUID) -> None:
        """Remove a follow relationship."""
        self.client.table("follows").delete().eq("follower", str(follower_id)).eq("followee", str(followee_id)).execute()

    async def get_followers(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get all followers of a user."""
        response = self.client.table("follows").select("follower").eq("followee", str(user_id)).execute()
        return response.data

    async def get_following(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get all users that a user follows."""
        response = self.client.table("follows").select("followee").eq("follower", str(user_id)).execute()
        return response.data

    # Team operations
    async def create_team(self, player_a: UUID, player_b: UUID, mu: float, sigma: float) -> Dict[str, Any]:
        """Create a new team.

        Note: The database enforces that player_a < player_b lexicographically.
        This function will automatically swap the players if needed.
        """
        # Ensure player_a < player_b to satisfy the constraint
        if str(player_a) > str(player_b):
            player_a, player_b = player_b, player_a

        # Check if team exists
        try:
            existing_team = self.client.table("teams").select("*").eq("player_a", str(player_a)).eq("player_b", str(player_b)).execute()
            if existing_team.data:
                # Team exists, return it
                return existing_team.data[0]
        except Exception:
            pass  # No existing team found

        # Create new team
        data = {
            "player_a": str(player_a),
            "player_b": str(player_b),
            "mu": mu,
            "sigma": sigma
        }
        response = self.client.table("teams").insert(data).execute()
        return response.data[0]

    async def update_team_rating(self, team_id: UUID, mu: float, sigma: float, games_played: int) -> Dict[str, Any]:
        """Update a team's rating."""
        data = {
            "mu": mu,
            "sigma": sigma,
            "games_played": games_played
        }
        response = self.client.table("teams").update(data).eq("id", str(team_id)).execute()
        return response.data[0]

    # Player rating operations
    async def update_player_rating(self, player_id: UUID, mu: float, sigma: float, games_played: int) -> Dict[str, Any]:
        """Update a player's rating."""
        # First ensure the player exists
        try:
            self.client.table("users").insert({"id": str(player_id)}).execute()
        except Exception:
            pass  # Player might already exist

        data = {
            "player_id": str(player_id),
            "mu": mu,
            "sigma": sigma,
            "games_played": games_played
        }
        # Use insert with on_conflict instead of upsert
        response = self.client.table("player_ratings").insert(data).execute()
        return response.data[0]

    # Match operations
    async def create_match(
        self,
        venue_id: UUID,
        played_at: datetime,
        created_by: UUID,
        scores: List[Dict[str, Any]],
        players: List[Tuple[UUID, int, bool]]  # (player_id, team, is_winner)
    ) -> Dict[str, Any]:
        """Create a new match with its players."""
        # First ensure all players exist
        for player_id, _, _ in players:
            try:
                self.client.table("users").insert({"id": str(player_id)}).execute()
            except Exception:
                pass  # Player might already exist

        # First create the match
        match_data = {
            "venue_id": str(venue_id),
            "played_at": played_at.isoformat(),
            "created_by": str(created_by),
            "scores": scores,
            "status": "confirmed"
        }
        match_response = self.client.table("matches").insert(match_data).execute()
        match = match_response.data[0]

        # Then add the players
        player_data = [
            {
                "match_id": match["id"],
                "player_id": str(player_id),
                "team": team,
                "is_winner": is_winner
            }
            for player_id, team, is_winner in players
        ]
        self.client.table("match_players").insert(player_data).execute()

        return match

    async def get_match(self, match_id: UUID) -> Dict[str, Any]:
        """Get a match by ID with its players."""
        match_response = self.client.table("matches").select("*").eq("id", str(match_id)).single().execute()
        players_response = self.client.table("match_players").select("*").eq("match_id", str(match_id)).execute()

        match = match_response.data
        match["players"] = players_response.data
        return match

    async def update_match(self, match_id: UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a match."""
        response = self.client.table("matches").update(data).eq("id", str(match_id)).execute()
        return response.data[0]

    # Compatibility view operations
    async def get_team_compatibility(self, player_a: UUID, player_b: UUID) -> Dict[str, Any]:
        """Get compatibility data for a team."""
        response = self.client.table("compatibility").select("*").eq("player_a", str(player_a)).eq("player_b", str(player_b)).single().execute()
        return response.data

    async def refresh_compatibility_view(self) -> None:
        """Refresh the compatibility materialized view."""
        self.client.rpc("refresh_compatibility_view").execute()
