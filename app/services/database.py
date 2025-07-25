from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import os
from supabase import create_client, Client
from uuid import UUID

class DatabaseService:
    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        """Initialize the database service with Supabase credentials."""
        # For testing and explicit parameters, use them directly
        if url and key:
            self.url = url
            self.key = key
        else:
            # Default to environment variables (for backward compatibility)
            # Try LOCAL_ first (for local development), then fallback to remote
            self.url = url or os.getenv("LOCAL_SUPABASE_URL") or os.getenv("SUPABASE_URL")
            self.key = key or os.getenv("LOCAL_SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        
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

    async def get_or_create_profile(self, user_id: UUID, display_name: Optional[str] = None) -> Dict[str, Any]:
        """Get or create a user profile."""
        try:
            # Try to get existing profile
            profile = await self.get_profile(user_id)
            return profile
        except Exception:
            # Profile doesn't exist, create it
            profile_data = {"display_name": display_name or ""}
            return await self.create_profile(user_id, profile_data)

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

    async def find_nearby_venues(self, latitude: float, longitude: float, radius_meters: float = 5000) -> List[Dict[str, Any]]:
        """Find venues within a certain radius using PostGIS."""
        # For now, return all venues since we don't need precise distance filtering
        # In a production app, we could implement PostGIS functions for better performance
        response = self.client.table("venues").select("*").execute()
        return response.data

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

    async def get_mutual_followers(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get mutual followers (users who follow each other)."""
        # Get followers and following in parallel
        followers_response = self.client.table("follows").select("follower").eq("followee", str(user_id)).execute()
        following_response = self.client.table("follows").select("followee").eq("follower", str(user_id)).execute()
        
        # Extract IDs
        follower_ids = {f["follower"] for f in followers_response.data}
        following_ids = {f["followee"] for f in following_response.data}
        
        # Find intersection
        mutual_ids = follower_ids.intersection(following_ids)
        
        return [{"user_id": user_id} for user_id in mutual_ids]

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
        # Use upsert instead of insert
        response = self.client.table("player_ratings").upsert(data).execute()
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

    async def get_player_matches(self, player_id: UUID) -> List[Dict[str, Any]]:
        """Get all matches a player participated in."""
        response = self.client.table("matches").select("*, match_players!inner(*)").eq("match_players.player_id", str(player_id)).execute()
        return response.data

    async def get_venue_matches(self, venue_id: UUID) -> List[Dict[str, Any]]:
        """Get all matches at a venue."""
        response = self.client.table("matches").select("*, match_players(*)").eq("venue_id", str(venue_id)).execute()
        return response.data

    async def get_top_players(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top players by rating."""
        response = self.client.table("player_ratings").select("*").order("mu", desc=True).limit(limit).execute()
        return response.data

    async def get_player_rating(self, player_id: UUID) -> Optional[Dict[str, Any]]:
        """Get a player's rating."""
        try:
            response = self.client.table("player_ratings").select("*").eq("player_id", str(player_id)).single().execute()
            return response.data
        except Exception:
            return None

    async def get_compatibility_scores(self, player_id: UUID) -> List[Dict[str, Any]]:
        """Get compatibility scores for a player with all other players."""
        # Get all teams where this player participates
        response = self.client.table("teams").select("*").execute()
        teams = response.data
        
        # Filter for teams involving the specific player
        player_teams = []
        for team in teams:
            if team["player_a"] == str(player_id):
                player_teams.append({
                    "partner_id": team["player_b"],
                    "team_mu": team["mu"],
                    "team_sigma": team["sigma"]
                })
            elif team["player_b"] == str(player_id):
                player_teams.append({
                    "partner_id": team["player_a"], 
                    "team_mu": team["mu"],
                    "team_sigma": team["sigma"]
                })
        
        if not player_teams:
            return []
        
        # Get individual ratings for the player and all partners
        all_player_ids = [str(player_id)]
        for team in player_teams:
            all_player_ids.append(team["partner_id"])
        
        # Get player ratings
        ratings_response = self.client.table("player_ratings").select("*").in_("player_id", all_player_ids).execute()
        ratings_dict = {r["player_id"]: r for r in ratings_response.data}
        
        # Calculate compatibility scores
        compatibility_scores = []
        player_rating = ratings_dict.get(str(player_id), {}).get("mu", 25.0)  # Default TrueSkill rating
        
        for team in player_teams:
            partner_rating = ratings_dict.get(team["partner_id"], {}).get("mu", 25.0)
            avg_individual_rating = (player_rating + partner_rating) / 2
            compatibility_score = team["team_mu"] - avg_individual_rating
            
            compatibility_scores.append({
                "partner_id": team["partner_id"],
                "team_rating": team["team_mu"],
                "avg_individual_rating": avg_individual_rating,
                "compatibility_score": compatibility_score
            })
        
        # Sort by compatibility score (highest first)
        compatibility_scores.sort(key=lambda x: x["compatibility_score"], reverse=True)
        
        return compatibility_scores

    async def get_recommended_partners(self, player_id: UUID, limit: int = 5, min_games: int = 3) -> List[Dict[str, Any]]:
        """Get recommended partners based on compatibility scores."""
        # Get all teams where the player participates and has minimum games
        response = self.client.table("teams").select("*").gte("games_played", min_games).execute()
        teams = response.data
        
        # Filter for teams involving the specific player
        player_teams = []
        for team in teams:
            if team["player_a"] == str(player_id):
                player_teams.append({
                    "partner_id": team["player_b"],
                    "team_mu": team["mu"],
                    "games_played": team["games_played"]
                })
            elif team["player_b"] == str(player_id):
                player_teams.append({
                    "partner_id": team["player_a"],
                    "team_mu": team["mu"], 
                    "games_played": team["games_played"]
                })
        
        if not player_teams:
            return []
        
        # Get individual ratings
        all_player_ids = [str(player_id)]
        for team in player_teams:
            all_player_ids.append(team["partner_id"])
        
        ratings_response = self.client.table("player_ratings").select("*").in_("player_id", all_player_ids).execute()
        ratings_dict = {r["player_id"]: r for r in ratings_response.data}
        
        # Calculate compatibility scores
        player_rating = ratings_dict.get(str(player_id), {}).get("mu", 25.0)
        
        recommendations = []
        for team in player_teams:
            partner_rating = ratings_dict.get(team["partner_id"], {}).get("mu", 25.0)
            avg_individual_rating = (player_rating + partner_rating) / 2
            compatibility_score = team["team_mu"] - avg_individual_rating
            
            recommendations.append({
                "partner_id": team["partner_id"],
                "team_rating": team["team_mu"],
                "avg_individual_rating": avg_individual_rating,
                "compatibility_score": compatibility_score,
                "games_played_together": team["games_played"]
            })
        
        # Sort by compatibility score (highest first) and limit
        recommendations.sort(key=lambda x: x["compatibility_score"], reverse=True)
        return recommendations[:limit]

    async def get_top_teams(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top teams by rating."""
        response = self.client.table("teams").select("*").order("mu", desc=True).limit(limit).execute()
        return response.data

    async def get_profiles_by_ids(self, user_ids: List[UUID]) -> List[Dict[str, Any]]:
        """Get profiles for multiple user IDs."""
        if not user_ids:
            return []
        
        str_ids = [str(uid) for uid in user_ids]
        response = self.client.table("profiles").select("*").in_("user_id", str_ids).execute()
        return response.data

    # Messaging operations
    async def send_message(self, sender_id: UUID, receiver_id: UUID, content: str) -> Dict[str, Any]:
        """Send a direct message from sender to receiver."""
        data = {
            "sender_id": str(sender_id),
            "receiver_id": str(receiver_id),
            "content": content
        }
        response = self.client.table("messages").insert(data).execute()
        return response.data[0]

    async def get_messages(
        self,
        user1_id: UUID,
        user2_id: UUID,
        limit: int = 50,
        before: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve messages exchanged between two users with optional pagination.

        Messages are returned ordered by creation time ascending. ``limit``
        controls the maximum number of results. ``before`` allows fetching
        messages older than the provided timestamp.
        """

        query = (
            self.client.table("messages")
            .select("*")
            .or_(
                f"and(sender_id.eq.{user1_id},receiver_id.eq.{user2_id}),"
                f"and(sender_id.eq.{user2_id},receiver_id.eq.{user1_id})"
            )
            .order("created_at", desc=True)
            .limit(limit)
        )

        if before:
            query = query.lt("created_at", before.isoformat())

        response = query.execute()
        data = response.data or []
        # Reverse so callers always receive messages oldest -> newest
        return list(reversed(data))

    async def create_group(self, name: str, creator_id: UUID) -> Dict[str, Any]:
        """Create a new chat group and add the creator as a member."""
        data = {"name": name, "creator_id": str(creator_id)}
        response = self.client.table("groups").insert(data).execute()
        group = response.data[0]
        self.client.table("group_members").insert({"group_id": group["id"], "user_id": str(creator_id)}).execute()
        return group

    async def add_group_member(self, group_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """Add a user to a group."""
        data = {"group_id": str(group_id), "user_id": str(user_id)}
        response = self.client.table("group_members").insert(data).execute()
        return response.data[0]

    async def send_group_message(self, group_id: UUID, sender_id: UUID, content: str) -> Dict[str, Any]:
        """Send a message to a group."""
        data = {
            "group_id": str(group_id),
            "sender_id": str(sender_id),
            "content": content
        }
        response = self.client.table("group_messages").insert(data).execute()
        return response.data[0]

    async def get_group_messages(
        self,
        group_id: UUID,
        limit: int = 50,
        before: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve messages from a group with optional pagination."""

        query = (
            self.client.table("group_messages")
            .select("*")
            .eq("group_id", str(group_id))
            .order("created_at", desc=True)
            .limit(limit)
        )

        if before:
            query = query.lt("created_at", before.isoformat())

        response = query.execute()
        data = response.data or []
        return list(reversed(data))
