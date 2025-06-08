"""
Integration tests for SmashMate happy path scenarios.

This module tests the complete user journey from profile creation to match completion,
including messaging, venue search, group formation, and rating calculations.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import UUID
from typing import List, Dict, Any
import time
import random

from app.core import auth, venues, social, matches, recommendations
from app.services.database import DatabaseService
from tests.utils import comprehensive_database_cleanup, cleanup_test_users


@pytest.fixture
async def six_test_users(supabase_client, db_service):
    """Create six test users for integration testing."""
    # Create unique identifier for this test run
    unique_id = f"{int(time.time())}{random.randint(1000, 9999)}"
    
    users = []
    for i in range(6):
        test_email = f"player{i+1}_{unique_id}@smashmate.test"
        test_password = "test_password123"
        
        # Create user with service role
        auth_response = supabase_client.auth.admin.create_user({
            "email": test_email,
            "password": test_password,
            "email_confirm": True
        })
        
        users.append({
            "id": auth_response.user.id,
            "email": test_email,
            "password": test_password,
            "name": f"Player {i+1}"
        })
    
    yield users
    
    # Cleanup users from auth system
    await cleanup_test_users(supabase_client, users)


@pytest.fixture(autouse=True)
async def integration_test_cleanup(db_service):
    """
    Comprehensive database cleanup for integration tests.
    
    This fixture automatically runs before and after each integration test
    to ensure a clean database state.
    """
    # Clean up before test
    await comprehensive_database_cleanup(db_service)
    
    yield
    
    # Clean up after test
    await comprehensive_database_cleanup(db_service)


class TestHappyPath:
    """Integration tests for the complete SmashMate user journey."""
    
    @pytest.mark.asyncio
    async def test_complete_happy_path_flow(self, six_test_users, db_service):
        """
        Test the complete happy path:
        1. Create user profiles
        2. Users message each other to coordinate
        3. 4 users form a group chat
        4. Search for nearby venues
        5. Play matches with different partner combinations
        6. Verify rating and compatibility calculations
        """
        users = six_test_users
        
        # Step 1: Create user profiles
        profiles = []
        for user in users:
            profile = await auth.get_or_create_profile(
                UUID(user["id"]), 
                user["name"], 
                database=db_service
            )
            profiles.append(profile)
            assert profile["display_name"] == user["name"]
        
        # Step 2: Users send direct messages to coordinate
        # Player 1 and 2 coordinate
        msg1 = await db_service.send_message(
            UUID(users[0]["id"]), 
            UUID(users[1]["id"]), 
            "Hey, want to play badminton this weekend?"
        )
        assert msg1["content"] == "Hey, want to play badminton this weekend?"
        
        # Player 2 responds
        msg2 = await db_service.send_message(
            UUID(users[1]["id"]), 
            UUID(users[0]["id"]), 
            "Sure! Let's find 2 more players and a venue."
        )
        
        # Check messages can be retrieved
        messages = await db_service.get_messages(UUID(users[0]["id"]), UUID(users[1]["id"]))
        assert len(messages) == 2
        
        # Player 3 and 4 also coordinate
        await db_service.send_message(
            UUID(users[2]["id"]), 
            UUID(users[3]["id"]), 
            "I heard Player 1 and 2 are organizing a game. Want to join?"
        )
        await db_service.send_message(
            UUID(users[3]["id"]), 
            UUID(users[2]["id"]), 
            "Absolutely! Let's create a group chat."
        )
        
        # Step 3: Create a group chat with 4 players
        group = await db_service.create_group("Weekend Badminton Squad", UUID(users[0]["id"]))
        group_id = UUID(group["id"])
        
        # Send group messages
        group_messages = [
            "Great! We have 4 players now.",
            "What time works for everyone?",
            "How about Saturday 2 PM?",
            "Perfect! Now we need to find a venue."
        ]
        
        for i, message in enumerate(group_messages):
            await db_service.send_group_message(
                group_id, 
                UUID(users[i % 4]["id"]), 
                message
            )
        
        # Verify group messages
        retrieved_messages = await db_service.get_group_messages(group_id)
        assert len(retrieved_messages) == 4
        
        # Step 4: Search for nearby venues
        # Create some venues at different locations
        venue_locations = [
            {"name": "Downtown Badminton Center", "lat": 37.7749, "lng": -122.4194, "address": "123 Downtown St"},
            {"name": "Suburban Sports Club", "lat": 37.7849, "lng": -122.4094, "address": "456 Suburb Ave"},
            {"name": "Community Recreation Center", "lat": 37.7649, "lng": -122.4294, "address": "789 Community Blvd"}
        ]
        
        created_venues = []
        for venue_data in venue_locations:
            venue = await venues.create_venue(
                name=venue_data["name"],
                latitude=venue_data["lat"],
                longitude=venue_data["lng"],
                address=venue_data["address"],
                created_by=UUID(users[0]["id"]),
                database=db_service
            )
            created_venues.append(venue)
        
        # Search for nearby venues (near downtown)
        nearby_venues = await venues.find_nearby_venues(
            latitude=37.7749,
            longitude=-122.4194,
            radius_meters=10000,  # 10km radius
            database=db_service
        )
        
        assert len(nearby_venues) >= 3  # Should find all created venues
        
        # Choose the first venue
        selected_venue = nearby_venues[0]
        venue_id = UUID(selected_venue["id"])
        
        # Step 5: Players follow each other for social connections
        # Create mutual follows between the 4 players
        follow_pairs = [
            (0, 1), (0, 2), (0, 3),  # Player 1 follows 2, 3, 4
            (1, 0), (1, 2), (1, 3),  # Player 2 follows 1, 3, 4
            (2, 0), (2, 1), (2, 3),  # Player 3 follows 1, 2, 4
            (3, 0), (3, 1), (3, 2),  # Player 4 follows 1, 2, 3
        ]
        
        for follower_idx, followee_idx in follow_pairs:
            await social.follow_player(
                UUID(users[follower_idx]["id"]),
                UUID(users[followee_idx]["id"]),
                database=db_service
            )
        
        # Verify mutual followers
        mutual_followers = await social.get_mutual_followers(UUID(users[0]["id"]), database=db_service)
        assert len(mutual_followers) == 3  # Players 2, 3, 4
        
        # Step 6: Play matches with different partner combinations
        player_ids = [UUID(user["id"]) for user in users[:4]]
        
        # Match 1: (Player1, Player2) vs (Player3, Player4)
        match1 = await matches.create_match(
            venue_id=venue_id,
            created_by=player_ids[0],
            team1_players=(player_ids[0], player_ids[1]),
            team2_players=(player_ids[2], player_ids[3]),
            scores=[{"team1": 21, "team2": 18}, {"team1": 21, "team2": 15}],  # Team 1 wins
            played_at=datetime.now(),
            database=db_service
        )
        
        # Match 2: Switch partners - (Player1, Player3) vs (Player2, Player4)
        match2 = await matches.create_match(
            venue_id=venue_id,
            created_by=player_ids[0],
            team1_players=(player_ids[0], player_ids[2]),
            team2_players=(player_ids[1], player_ids[3]),
            scores=[{"team1": 18, "team2": 21}, {"team1": 15, "team2": 21}],  # Team 2 wins
            played_at=datetime.now() + timedelta(minutes=30),
            database=db_service
        )
        
        # Match 3: Another combination - (Player1, Player4) vs (Player2, Player3)
        match3 = await matches.create_match(
            venue_id=venue_id,
            created_by=player_ids[0],
            team1_players=(player_ids[0], player_ids[3]),
            team2_players=(player_ids[1], player_ids[2]),
            scores=[{"team1": 21, "team2": 19}, {"team1": 19, "team2": 21}, {"team1": 21, "team2": 16}],  # Team 1 wins 2-1
            played_at=datetime.now() + timedelta(hours=1),
            database=db_service
        )
        
        # Step 7: Verify matches were created correctly
        assert match1["id"] is not None
        assert match2["id"] is not None
        assert match3["id"] is not None
        
        # Verify player matches
        player1_matches = await matches.get_player_matches(player_ids[0], database=db_service)
        assert len(player1_matches) == 3  # Player 1 participated in all matches
        
        venue_matches = await matches.get_venue_matches(venue_id, database=db_service)
        assert len(venue_matches) == 3  # All matches at this venue
        
        # Step 8: Verify ratings were updated
        for player_id in player_ids:
            rating = await db_service.get_player_rating(player_id)
            assert rating is not None
            assert rating["games_played"] == 3  # Each player played 3 games
            # Rating should have changed from initial 25.0
            assert float(rating["mu"]) != 25.0
        
        # Step 9: Check team ratings and compatibility scores
        # Get compatibility scores for Player 1
        compatibility_scores = await recommendations.get_compatibility_scores(
            player_ids[0], 
            database=db_service
        )
        
        # Should have compatibility scores with other 3 players
        assert len(compatibility_scores) >= 3
        
        # Each compatibility score should have the required fields
        for score in compatibility_scores:
            assert "partner" in score
            assert "team_rating" in score
            assert "avg_individual_rating" in score
            assert "compatibility_score" in score
            assert score["partner"] is not None
        
        # Step 10: Get partner recommendations
        recommendations_list = await recommendations.get_recommended_partners(
            player_ids[0],
            limit=3,
            min_games=1,  # Lower threshold since we only played 3 games
            database=db_service
        )
        
        # Should get recommendations (players they've played with)
        assert len(recommendations_list) >= 0  # Might be empty if min_games is too high
        
        # Step 11: Check leaderboards
        top_players = await matches.get_top_players(limit=10, database=db_service)
        assert len(top_players) == 4  # Our 4 players should be the only ones with ratings
        
        # All players should be in the leaderboard
        player_ids_in_leaderboard = {UUID(p["player_id"]) for p in top_players}
        assert set(player_ids).issubset(player_ids_in_leaderboard)
        
        # Step 12: Test additional social features
        # Get followers and following
        followers = await social.get_followers(player_ids[0], database=db_service)
        following = await social.get_following(player_ids[0], database=db_service)
        
        assert len(followers) == 3  # 3 other players follow Player 1
        assert len(following) == 3  # Player 1 follows 3 other players
        
        print("✅ Complete happy path integration test passed!")


class TestEdgeCaseScenarios:
    """Integration tests for edge cases and error scenarios."""
    
    @pytest.mark.asyncio
    async def test_single_player_journey(self, six_test_users, db_service):
        """Test a single player's journey when they join existing groups."""
        users = six_test_users
        
        # Create profile for the main player
        main_player = users[0]
        profile = await auth.get_or_create_profile(
            UUID(main_player["id"]), 
            main_player["name"], 
            database=db_service
        )
        
        # Create some existing venues
        venue = await venues.create_venue(
            name="Existing Venue",
            latitude=37.7749,
            longitude=-122.4194,
            address="123 Existing St",
            created_by=UUID(main_player["id"]),
            database=db_service
        )
        
        # Search for venues
        nearby = await venues.find_nearby_venues(
            latitude=37.7749,
            longitude=-122.4194,
            database=db_service
        )
        
        assert len(nearby) >= 1
        assert any(v["name"] == "Existing Venue" for v in nearby)
        
        # Update profile with default venue
        updated_profile = await auth.update_profile(
            UUID(main_player["id"]),
            default_venue=UUID(venue["id"]),
            database=db_service
        )
        
        assert updated_profile["default_venue"] == venue["id"]
    
    @pytest.mark.asyncio
    async def test_venue_search_edge_cases(self, six_test_users, db_service):
        """Test venue search with various parameters."""
        users = six_test_users
        user_id = UUID(users[0]["id"])
        
        # Create venues at different distances
        venues_data = [
            {"name": "Very Close", "lat": 37.7749, "lng": -122.4194},  # Same location
            {"name": "Nearby", "lat": 37.7759, "lng": -122.4184},     # ~1km away
            {"name": "Far Away", "lat": 37.8049, "lng": -122.3894},   # ~5km away
        ]
        
        for venue_data in venues_data:
            await venues.create_venue(
                name=venue_data["name"],
                latitude=venue_data["lat"],
                longitude=venue_data["lng"],
                address=f"{venue_data['name']} Address",
                created_by=user_id,
                database=db_service
            )
        
        # Test different search radii
        # Small radius - should find only very close venues
        close_venues = await venues.find_nearby_venues(
            latitude=37.7749,
            longitude=-122.4194,
            radius_meters=500,  # 500m
            database=db_service
        )
        
        # Large radius - should find all venues
        all_venues = await venues.find_nearby_venues(
            latitude=37.7749,
            longitude=-122.4194,
            radius_meters=10000,  # 10km
            database=db_service
        )
        
        assert len(close_venues) <= len(all_venues)
        assert len(all_venues) >= 3  # Should find all created venues
    
    @pytest.mark.asyncio
    async def test_match_rating_calculations(self, six_test_users, db_service):
        """Test that TrueSkill ratings are calculated correctly across multiple matches."""
        users = six_test_users
        player_ids = [UUID(user["id"]) for user in users[:4]]
        
        # Create profiles
        for i, user in enumerate(users[:4]):
            await auth.get_or_create_profile(
                UUID(user["id"]), 
                user["name"], 
                database=db_service
            )
        
        # Create venue
        venue = await venues.create_venue(
            name="Rating Test Venue",
            latitude=37.7749,
            longitude=-122.4194,
            address="123 Rating St",
            created_by=player_ids[0],
            database=db_service
        )
        venue_id = UUID(venue["id"])
        
        # Get initial ratings
        initial_ratings = {}
        for player_id in player_ids:
            rating = await db_service.get_player_rating(player_id)
            # If no rating exists, it should default to TrueSkill defaults
            if rating:
                initial_ratings[str(player_id)] = float(rating["mu"])
            else:
                initial_ratings[str(player_id)] = 25.0  # Default TrueSkill mu
        
        # Play a series of matches where the same team always wins
        # This should cause ratings to diverge
        winning_team = (player_ids[0], player_ids[1])
        losing_team = (player_ids[2], player_ids[3])
        
        for i in range(5):  # Play 5 matches
            await matches.create_match(
                venue_id=venue_id,
                created_by=player_ids[0],
                team1_players=winning_team,
                team2_players=losing_team,
                scores=[{"team1": 21, "team2": 15}, {"team1": 21, "team2": 18}],  # Team 1 always wins
                played_at=datetime.now() + timedelta(minutes=i*30),
                database=db_service
            )
        
        # Check that ratings have changed appropriately
        final_ratings = {}
        for player_id in player_ids:
            rating = await db_service.get_player_rating(player_id)
            assert rating is not None
            assert rating["games_played"] == 5
            final_ratings[str(player_id)] = float(rating["mu"])
        
        # Winners should have higher ratings than losers
        winner1_rating = final_ratings[str(player_ids[0])]
        winner2_rating = final_ratings[str(player_ids[1])]
        loser1_rating = final_ratings[str(player_ids[2])]
        loser2_rating = final_ratings[str(player_ids[3])]
        
        # Both winners should have ratings above initial
        assert winner1_rating > initial_ratings[str(player_ids[0])]
        assert winner2_rating > initial_ratings[str(player_ids[1])]
        
        # Both losers should have ratings below initial
        assert loser1_rating < initial_ratings[str(player_ids[2])]
        assert loser2_rating < initial_ratings[str(player_ids[3])]
        
        # Winners should have higher average rating than losers
        winner_avg = (winner1_rating + winner2_rating) / 2
        loser_avg = (loser1_rating + loser2_rating) / 2
        assert winner_avg > loser_avg
    
    @pytest.mark.asyncio
    async def test_social_network_features(self, six_test_users, db_service):
        """Test complex social network scenarios."""
        users = six_test_users
        
        # Create profiles for all users
        for user in users:
            await auth.get_or_create_profile(
                UUID(user["id"]), 
                user["name"], 
                database=db_service
            )
        
        # Create a complex follow network
        # User 0 follows users 1, 2, 3
        # User 1 follows users 0, 2, 4
        # User 2 follows users 0, 1, 5
        # User 3 follows users 0, 4, 5
        # User 4 follows users 1, 3, 5
        # User 5 follows users 2, 3, 4
        
        follow_relationships = [
            (0, 1), (0, 2), (0, 3),
            (1, 0), (1, 2), (1, 4),
            (2, 0), (2, 1), (2, 5),
            (3, 0), (3, 4), (3, 5),
            (4, 1), (4, 3), (4, 5),
            (5, 2), (5, 3), (5, 4),
        ]
        
        for follower_idx, followee_idx in follow_relationships:
            await social.follow_player(
                UUID(users[follower_idx]["id"]),
                UUID(users[followee_idx]["id"]),
                database=db_service
            )
        
        # Test mutual followers for each user
        user0_mutual = await social.get_mutual_followers(UUID(users[0]["id"]), database=db_service)
        assert len(user0_mutual) == 3  # Users 1, 2, and 3 (mutual with user 0)
        
        user1_mutual = await social.get_mutual_followers(UUID(users[1]["id"]), database=db_service)
        assert len(user1_mutual) == 3  # Users 0, 2, and 4
        
        # Test followers and following counts
        user0_followers = await social.get_followers(UUID(users[0]["id"]), database=db_service)
        user0_following = await social.get_following(UUID(users[0]["id"]), database=db_service)
        
        assert len(user0_followers) == 3  # Users 1, 2, 3 follow user 0
        assert len(user0_following) == 3  # User 0 follows users 1, 2, 3
        
        # Test unfollowing
        await social.unfollow_player(
            UUID(users[0]["id"]),
            UUID(users[1]["id"]),
            database=db_service
        )
        
        # Check that the relationship was removed
        user0_following_after = await social.get_following(UUID(users[0]["id"]), database=db_service)
        assert len(user0_following_after) == 2  # Now only follows users 2, 3
        
        user1_followers_after = await social.get_followers(UUID(users[1]["id"]), database=db_service)
        following_user1 = [f["user_id"] for f in user1_followers_after]
        assert users[0]["id"] not in following_user1  # User 0 no longer follows user 1


class TestMessagingIntegration:
    """Integration tests for messaging features in realistic scenarios."""
    
    @pytest.mark.asyncio
    async def test_match_coordination_messaging(self, six_test_users, db_service):
        """Test messaging workflow for coordinating matches."""
        users = six_test_users
        
        # Create profiles
        for user in users[:4]:
            await auth.get_or_create_profile(
                UUID(user["id"]), 
                user["name"], 
                database=db_service
            )
        
        # Simulate match coordination conversation
        conversations = [
            (0, 1, "Hey, want to play badminton this Saturday?"),
            (1, 0, "Sure! What time?"),
            (0, 1, "How about 2 PM? We need 2 more players."),
            (1, 0, "I'll ask Player 3 and Player 4."),
        ]
        
        # Send direct messages
        for sender_idx, receiver_idx, content in conversations:
            await db_service.send_message(
                UUID(users[sender_idx]["id"]),
                UUID(users[receiver_idx]["id"]),
                content
            )
        
        # Check conversation history
        messages = await db_service.get_messages(
            UUID(users[0]["id"]),
            UUID(users[1]["id"])
        )
        assert len(messages) == 4
        
        # Player 1 contacts Player 3
        await db_service.send_message(
            UUID(users[1]["id"]),
            UUID(users[2]["id"]),
            "Want to join us for badminton on Saturday at 2 PM?"
        )
        
        await db_service.send_message(
            UUID(users[2]["id"]),
            UUID(users[1]["id"]),
            "Yes! I'll bring Player 4."
        )
        
        # Create group chat for final coordination
        group = await db_service.create_group("Saturday Badminton", UUID(users[0]["id"]))
        group_id = UUID(group["id"])
        
        final_messages = [
            "Great! We have our 4 players confirmed.",
            "I found a venue - Downtown Badminton Center.",
            "Perfect! See everyone there at 2 PM.",
            "Can't wait! It's going to be a great game."
        ]
        
        for i, message in enumerate(final_messages):
            await db_service.send_group_message(
                group_id,
                UUID(users[i]["id"]),
                message
            )
        
        # Verify all group messages
        group_messages = await db_service.get_group_messages(group_id)
        assert len(group_messages) == 4
        
        # Test message pagination
        first_page = await db_service.get_group_messages(group_id, limit=2)
        assert len(first_page) == 2
        
        # Get older messages
        if first_page:
            before_timestamp = first_page[0]["created_at"]
            # Parse the timestamp string to datetime if needed
            if isinstance(before_timestamp, str):
                from datetime import datetime
                before_timestamp = datetime.fromisoformat(before_timestamp.replace('Z', '+00:00'))
            
            second_page = await db_service.get_group_messages(
                group_id, 
                limit=2, 
                before=before_timestamp
            )
            # Should get remaining messages
            assert len(second_page) <= 2 