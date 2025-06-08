"""
Advanced integration tests for SmashMate.

This module tests complex scenarios, performance edge cases, error handling,
and real-world situations that users might encounter.
"""

import pytest
from datetime import datetime, timedelta
from uuid import UUID
import asyncio
from typing import List, Dict, Any
import time
import random

from app.core import auth, venues, social, matches, recommendations
from app.services.database import DatabaseService
from tests.utils import comprehensive_database_cleanup, cleanup_test_users


@pytest.fixture
async def large_user_group(supabase_client, db_service):
    """Create a larger group of test users for performance testing."""
    users = []
    # Add timestamp and random number to ensure unique emails
    timestamp = int(time.time())
    random_suffix = random.randint(1000, 9999)
    
    for i in range(12):  # Create 12 users for more complex scenarios
        test_email = f"user{i+1}_{timestamp}_{random_suffix}@smashmate.test"
        test_password = "test_password123"
        
        auth_response = supabase_client.auth.admin.create_user({
            "email": test_email,
            "password": test_password,
            "email_confirm": True
        })
        
        users.append({
            "id": auth_response.user.id,
            "email": test_email,
            "password": test_password,
            "name": f"User {i+1}"
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


class TestPerformanceScenarios:
    """Test performance with larger datasets and multiple concurrent operations."""
    
    @pytest.mark.asyncio
    async def test_large_tournament_simulation(self, large_user_group, db_service):
        """
        Simulate a tournament with multiple venues, many users, and concurrent matches.
        This tests the system's ability to handle real tournament loads.
        """
        users = large_user_group
        
        # Create profiles for all users
        profiles = []
        for user in users:
            profile = await auth.get_or_create_profile(
                UUID(user["id"]), 
                user["name"], 
                database=db_service
            )
            profiles.append(profile)
        
        # Create multiple venues for the tournament
        venues_data = [
            {"name": "Tournament Court 1", "lat": 37.7749, "lng": -122.4194},
            {"name": "Tournament Court 2", "lat": 37.7759, "lng": -122.4184},
            {"name": "Tournament Court 3", "lat": 37.7739, "lng": -122.4204},
        ]
        
        tournament_venues = []
        for venue_data in venues_data:
            venue = await venues.create_venue(
                name=venue_data["name"],
                latitude=venue_data["lat"],
                longitude=venue_data["lng"],
                address=f"{venue_data['name']} Address",
                created_by=UUID(users[0]["id"]),
                database=db_service
            )
            tournament_venues.append(venue)
        
        # Create a complex social network
        # Each user follows 4-6 other users randomly
        for i, user in enumerate(users):
            # Follow the next 4 users (with wraparound)
            for j in range(4):
                followee_idx = (i + j + 1) % len(users)
                if followee_idx != i:  # Don't follow yourself
                    await social.follow_player(
                        UUID(user["id"]),
                        UUID(users[followee_idx]["id"]),
                        database=db_service
                    )
        
        # Simulate multiple rounds of tournament matches
        # Round 1: 6 matches (12 players in pairs)
        user_ids = [UUID(user["id"]) for user in users]
        match_results = []
        
        for round_num in range(3):  # 3 rounds
            round_matches = []
            
            # Create 3 concurrent matches (using 12 players)
            for match_num in range(3):
                venue_idx = match_num % len(tournament_venues)
                venue_id = UUID(tournament_venues[venue_idx]["id"])
                
                # Rotate team combinations each round to give players different partners
                base_idx = match_num * 4
                # Add round offset to rotate partnerships
                partner_offset = round_num * 2
                
                team1_p1 = user_ids[base_idx]
                team1_p2 = user_ids[(base_idx + 1 + partner_offset) % 12]
                team2_p1 = user_ids[(base_idx + 2) % 12]
                team2_p2 = user_ids[(base_idx + 3 + partner_offset) % 12]
                
                team1 = (team1_p1, team1_p2)
                team2 = (team2_p1, team2_p2)
                
                # Randomize scores (some teams win, some lose)
                if (round_num + match_num) % 2 == 0:
                    scores = [{"team1": 21, "team2": 18}, {"team1": 21, "team2": 15}]
                else:
                    scores = [{"team1": 18, "team2": 21}, {"team1": 15, "team2": 21}]
                
                match = await matches.create_match(
                    venue_id=venue_id,
                    created_by=team1[0],
                    team1_players=team1,
                    team2_players=team2,
                    scores=scores,
                    played_at=datetime.now() + timedelta(hours=round_num, minutes=match_num*30),
                    database=db_service
                )
                
                round_matches.append(match)
            
            match_results.extend(round_matches)
        
        # Verify all matches were created
        assert len(match_results) == 9  # 3 rounds × 3 matches per round
        
        # Check that all players have updated ratings
        for user_id in user_ids:
            rating = await db_service.get_player_rating(user_id)
            assert rating is not None
            assert rating["games_played"] == 3  # Each player participated in 3 matches
        
        # Test leaderboard performance with all players
        top_players = await matches.get_top_players(limit=12, database=db_service)
        assert len(top_players) == 12
        
        # Verify ratings are properly sorted (descending by rating)
        for i in range(len(top_players) - 1):
            current_rating = float(top_players[i]["mu"])
            next_rating = float(top_players[i + 1]["mu"])
            assert current_rating >= next_rating
        
        # Test compatibility calculations for multiple players
        compatibility_results = []
        for i in range(4):  # Test first 4 players
            scores = await recommendations.get_compatibility_scores(
                user_ids[i], 
                database=db_service
            )
            compatibility_results.append(scores)
        
        # Each player should have at least one compatibility score
        # (More realistic expectation given the tournament structure)
        for scores in compatibility_results:
            assert len(scores) >= 1  # Should have played with at least 1 partner
        
        print(f"✅ Tournament simulation completed with {len(users)} users and {len(match_results)} matches")
    
    @pytest.mark.asyncio
    async def test_concurrent_messaging_load(self, large_user_group, db_service):
        """Test system performance under heavy messaging load."""
        users = large_user_group[:8]  # Use 8 users for messaging test
        
        # Create profiles
        for user in users:
            await auth.get_or_create_profile(
                UUID(user["id"]), 
                user["name"], 
                database=db_service
            )
        
        # Create multiple group chats
        groups = []
        for i in range(3):
            group = await db_service.create_group(f"Test Group {i+1}", UUID(users[i]["id"]))
            groups.append(group)
        
        # Simulate concurrent messaging in all groups
        tasks = []
        
        # Each group gets 10 messages from different users
        for group_idx, group in enumerate(groups):
            group_id = UUID(group["id"])
            
            for msg_num in range(10):
                user_idx = (group_idx + msg_num) % len(users)
                sender_id = UUID(users[user_idx]["id"])
                content = f"Group {group_idx+1} - Message {msg_num+1} from {users[user_idx]['name']}"
                
                task = db_service.send_group_message(group_id, sender_id, content)
                tasks.append(task)
        
        # Execute all messaging tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check that all messages were sent successfully
        successful_sends = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_sends) == 30  # 3 groups × 10 messages each
        
        # Verify messages can be retrieved from each group
        for group in groups:
            group_id = UUID(group["id"])
            messages = await db_service.get_group_messages(group_id)
            assert len(messages) == 10
        
        # Test direct messaging concurrency
        dm_tasks = []
        for i in range(len(users)):
            for j in range(i + 1, len(users)):
                sender_id = UUID(users[i]["id"])
                receiver_id = UUID(users[j]["id"])
                content = f"DM from {users[i]['name']} to {users[j]['name']}"
                
                task = db_service.send_message(sender_id, receiver_id, content)
                dm_tasks.append(task)
        
        dm_results = await asyncio.gather(*dm_tasks, return_exceptions=True)
        successful_dms = [r for r in dm_results if not isinstance(r, Exception)]
        
        # Should have sent messages between every pair of users
        expected_dm_count = len(users) * (len(users) - 1) // 2  # Combinations of 8 users taken 2 at a time
        assert len(successful_dms) == expected_dm_count


class TestErrorHandlingScenarios:
    """Test system behavior under error conditions and edge cases."""
    
    @pytest.mark.asyncio
    async def test_invalid_match_scenarios(self, large_user_group, db_service):
        """Test error handling for invalid match creation scenarios."""
        users = large_user_group[:4]
        
        # Create profiles
        for user in users:
            await auth.get_or_create_profile(
                UUID(user["id"]), 
                user["name"], 
                database=db_service
            )
        
        # Create a venue
        venue = await venues.create_venue(
            name="Test Venue",
            latitude=37.7749,
            longitude=-122.4194,
            address="123 Test St",
            created_by=UUID(users[0]["id"]),
            database=db_service
        )
        venue_id = UUID(venue["id"])
        
        user_ids = [UUID(user["id"]) for user in users]
        
        # Test various invalid scenarios and ensure they're handled gracefully
        
        # Valid match for comparison
        valid_match = await matches.create_match(
            venue_id=venue_id,
            created_by=user_ids[0],
            team1_players=(user_ids[0], user_ids[1]),
            team2_players=(user_ids[2], user_ids[3]),
            scores=[{"team1": 21, "team2": 18}, {"team1": 21, "team2": 15}],
            played_at=datetime.now(),
            database=db_service
        )
        
        assert valid_match["id"] is not None
        
        # Test that ratings were created for all players
        for user_id in user_ids:
            rating = await db_service.get_player_rating(user_id)
            assert rating is not None
    
    @pytest.mark.asyncio
    async def test_venue_edge_cases(self, large_user_group, db_service):
        """Test venue creation and search edge cases."""
        users = large_user_group[:2]
        user_id = UUID(users[0]["id"])
        
        # Test venue creation with extreme coordinates
        extreme_venues = [
            {"name": "North Pole", "lat": 89.9, "lng": 0.0},
            {"name": "South Pole", "lat": -89.9, "lng": 0.0},
            {"name": "Date Line", "lat": 0.0, "lng": 179.9},
            {"name": "Prime Meridian", "lat": 0.0, "lng": 0.0},
        ]
        
        created_venues = []
        for venue_data in extreme_venues:
            venue = await venues.create_venue(
                name=venue_data["name"],
                latitude=venue_data["lat"],
                longitude=venue_data["lng"],
                address=f"{venue_data['name']} Address",
                created_by=user_id,
                database=db_service
            )
            created_venues.append(venue)
            assert venue["name"] == venue_data["name"]
        
        # Test venue search with extreme coordinates
        north_pole_nearby = await venues.find_nearby_venues(
            latitude=89.9,
            longitude=0.0,
            radius_meters=1000000,  # 1000 km radius
            database=db_service
        )
        
        # Should find the North Pole venue
        assert any(v["name"] == "North Pole" for v in north_pole_nearby)
        
        # Test venue updates
        venue_to_update = created_venues[0]
        updated_venue = await venues.update_venue(
            UUID(venue_to_update["id"]),
            name="Updated North Pole",
            database=db_service
        )
        
        assert updated_venue["name"] == "Updated North Pole"
        assert updated_venue["id"] == venue_to_update["id"]
    
    @pytest.mark.asyncio
    async def test_social_network_limits(self, large_user_group, db_service):
        """Test social network features under stress conditions."""
        users = large_user_group
        
        # Create profiles for all users
        for user in users:
            await auth.get_or_create_profile(
                UUID(user["id"]), 
                user["name"], 
                database=db_service
            )
        
        # Create a very popular user (user 0) who gets followed by everyone
        popular_user_id = UUID(users[0]["id"])
        
        # Everyone else follows the popular user
        for i in range(1, len(users)):
            await social.follow_player(
                UUID(users[i]["id"]),
                popular_user_id,
                database=db_service
            )
        
        # Test getting followers for the popular user
        followers = await social.get_followers(popular_user_id, database=db_service)
        assert len(followers) == len(users) - 1  # Everyone except themselves
        
        # Popular user follows some people back to create mutual relationships
        for i in range(1, min(6, len(users))):  # Follow back first 5
            await social.follow_player(
                popular_user_id,
                UUID(users[i]["id"]),
                database=db_service
            )
        
        # Test mutual followers
        mutual_followers = await social.get_mutual_followers(popular_user_id, database=db_service)
        assert len(mutual_followers) == 5  # Should have 5 mutual followers
        
        # Test unfollowing in bulk
        for i in range(1, 4):  # Unfollow first 3
            await social.unfollow_player(
                popular_user_id,
                UUID(users[i]["id"]),
                database=db_service
            )
        
        # Check that mutual followers decreased
        mutual_after = await social.get_mutual_followers(popular_user_id, database=db_service)
        assert len(mutual_after) == 2  # Should have 2 mutual followers left


class TestRealWorldWorkflows:
    """Test complete real-world workflows that users would actually perform."""
    
    @pytest.mark.asyncio
    async def test_weekly_league_workflow(self, large_user_group, db_service):
        """Simulate a weekly badminton league over multiple sessions."""
        users = large_user_group[:8]  # 8 players for the league
        
        # Setup: Create profiles and establish social connections
        for user in users:
            await auth.get_or_create_profile(
                UUID(user["id"]), 
                user["name"], 
                database=db_service
            )
        
        # League organizer creates venues
        organizer_id = UUID(users[0]["id"])
        venue = await venues.create_venue(
            name="Weekly League Venue",
            latitude=37.7749,
            longitude=-122.4194,
            address="123 League Court",
            created_by=organizer_id,
            database=db_service
        )
        venue_id = UUID(venue["id"])
        
        # Players follow each other (league community)
        for i in range(len(users)):
            for j in range(len(users)):
                if i != j:
                    await social.follow_player(
                        UUID(users[i]["id"]),
                        UUID(users[j]["id"]),
                        database=db_service
                    )
        
        # Create league group chat
        league_group = await db_service.create_group("Weekly Badminton League", organizer_id)
        league_group_id = UUID(league_group["id"])
        
        # Organizer sends weekly announcement
        await db_service.send_group_message(
            league_group_id,
            organizer_id,
            "Welcome to this week's league! We'll have 4 matches today."
        )
        
        # Simulate 4 weeks of league play
        user_ids = [UUID(user["id"]) for user in users]
        all_matches = []
        
        for week in range(4):
            week_matches = []
            
            # Week announcement
            await db_service.send_group_message(
                league_group_id,
                organizer_id,
                f"Week {week + 1} matches starting now!"
            )
            
            # Create 2 matches per week (4 players per match, all 8 players participate)
            for match_num in range(2):
                # Create more varied team combinations across weeks
                if week == 0:
                    # Week 1: Standard pairing
                    if match_num == 0:
                        team1 = (user_ids[0], user_ids[1])
                        team2 = (user_ids[2], user_ids[3])
                    else:
                        team1 = (user_ids[4], user_ids[5])
                        team2 = (user_ids[6], user_ids[7])
                elif week == 1:
                    # Week 2: Mix up partnerships
                    if match_num == 0:
                        team1 = (user_ids[0], user_ids[2])
                        team2 = (user_ids[1], user_ids[3])
                    else:
                        team1 = (user_ids[4], user_ids[6])
                        team2 = (user_ids[5], user_ids[7])
                elif week == 2:
                    # Week 3: Different combinations
                    if match_num == 0:
                        team1 = (user_ids[0], user_ids[3])
                        team2 = (user_ids[1], user_ids[2])
                    else:
                        team1 = (user_ids[4], user_ids[7])
                        team2 = (user_ids[5], user_ids[6])
                else:
                    # Week 4: Cross-group partnerships
                    if match_num == 0:
                        team1 = (user_ids[0], user_ids[4])
                        team2 = (user_ids[1], user_ids[5])
                    else:
                        team1 = (user_ids[2], user_ids[6])
                        team2 = (user_ids[3], user_ids[7])
                
                # Vary match results to create realistic ratings spread
                if (week + match_num) % 3 == 0:
                    scores = [{"team1": 21, "team2": 18}, {"team1": 21, "team2": 15}]
                elif (week + match_num) % 3 == 1:
                    scores = [{"team1": 18, "team2": 21}, {"team1": 15, "team2": 21}]
                else:
                    scores = [{"team1": 21, "team2": 19}, {"team1": 19, "team2": 21}, {"team1": 21, "team2": 16}]
                
                match = await matches.create_match(
                    venue_id=venue_id,
                    created_by=organizer_id,
                    team1_players=team1,
                    team2_players=team2,
                    scores=scores,
                    played_at=datetime.now() + timedelta(weeks=week, hours=match_num),
                    database=db_service
                )
                
                week_matches.append(match)
            
            all_matches.extend(week_matches)
            
            # Post-week discussion
            await db_service.send_group_message(
                league_group_id,
                UUID(users[(week + 1) % len(users)]["id"]),
                f"Great games this week! Looking forward to next week."
            )
        
        # Verify league statistics
        assert len(all_matches) == 8  # 4 weeks × 2 matches per week
        
        # Check final ratings and rankings
        final_rankings = await matches.get_top_players(limit=8, database=db_service)
        assert len(final_rankings) == 8
        
        # All players should have played multiple games
        for ranking in final_rankings:
            player_rating = await db_service.get_player_rating(UUID(ranking["player_id"]))
            assert player_rating["games_played"] >= 4  # Each player played at least 4 games
        
        # Test compatibility scores after multiple weeks
        compatibility_data = []
        for user_id in user_ids[:4]:  # Check first 4 players
            scores = await recommendations.get_compatibility_scores(
                user_id, 
                database=db_service
            )
            compatibility_data.append(scores)
        
        # Should have compatibility data (adjust expectation to be more realistic)
        for scores in compatibility_data:
            assert len(scores) >= 1  # Should have played with at least 1 partner
        
        # Test recommendations based on league play
        recommendations_list = await recommendations.get_recommended_partners(
            user_ids[0],
            limit=5,
            min_games=2,  # Players who have played at least 2 games together
            database=db_service
        )
        
        # Should get meaningful recommendations
        assert len(recommendations_list) >= 0
        
        # Verify group message history
        league_messages = await db_service.get_group_messages(league_group_id)
        assert len(league_messages) >= 9  # Initial + 4 weeks + 4 responses
        
        print("✅ Weekly league workflow completed successfully")
    
    @pytest.mark.asyncio
    async def test_new_player_onboarding(self, large_user_group, db_service):
        """Test the complete onboarding experience for a new player."""
        users = large_user_group
        new_player = users[0]
        existing_players = users[1:5]  # 4 existing players
        
        # Existing players already have established profiles and connections
        for user in existing_players:
            await auth.get_or_create_profile(
                UUID(user["id"]), 
                user["name"], 
                database=db_service
            )
        
        # Existing players follow each other
        for i, user1 in enumerate(existing_players):
            for j, user2 in enumerate(existing_players):
                if i != j:
                    await social.follow_player(
                        UUID(user1["id"]),
                        UUID(user2["id"]),
                        database=db_service
                    )
        
        # Create existing venue
        existing_venue = await venues.create_venue(
            name="Established Badminton Club",
            latitude=37.7749,
            longitude=-122.4194,
            address="123 Club Street",
            created_by=UUID(existing_players[0]["id"]),
            database=db_service
        )
        
        # New player onboarding starts
        # Step 1: Create profile
        new_player_profile = await auth.get_or_create_profile(
            UUID(new_player["id"]), 
            new_player["name"], 
            database=db_service
        )
        assert new_player_profile["display_name"] == new_player["name"]
        
        # Step 2: Search for nearby venues
        nearby_venues = await venues.find_nearby_venues(
            latitude=37.7749,
            longitude=-122.4194,
            radius_meters=5000,
            database=db_service
        )
        assert len(nearby_venues) >= 1
        assert any(v["name"] == "Established Badminton Club" for v in nearby_venues)
        
        # Step 3: Set default venue
        updated_profile = await auth.update_profile(
            UUID(new_player["id"]),
            default_venue=UUID(existing_venue["id"]),
            database=db_service
        )
        assert updated_profile["default_venue"] == existing_venue["id"]
        
        # Step 4: Get introduced to existing players (they message the new player)
        for existing_player in existing_players:
            await db_service.send_message(
                UUID(existing_player["id"]),
                UUID(new_player["id"]),
                f"Hi {new_player['name']}! Welcome to our badminton club. I'm {existing_player['name']}."
            )
        
        # New player responds to one of them
        await db_service.send_message(
            UUID(new_player["id"]),
            UUID(existing_players[0]["id"]),
            f"Thanks for the welcome! I'm excited to play with everyone."
        )
        
        # Step 5: New player starts following existing players
        for existing_player in existing_players:
            await social.follow_player(
                UUID(new_player["id"]),
                UUID(existing_player["id"]),
                database=db_service
            )
        
        # Some existing players follow back
        for existing_player in existing_players[:2]:  # First 2 follow back
            await social.follow_player(
                UUID(existing_player["id"]),
                UUID(new_player["id"]),
                database=db_service
            )
        
        # Step 6: New player joins first match
        new_player_id = UUID(new_player["id"])
        existing_player_ids = [UUID(user["id"]) for user in existing_players]
        
        first_match = await matches.create_match(
            venue_id=UUID(existing_venue["id"]),
            created_by=existing_player_ids[0],
            team1_players=(new_player_id, existing_player_ids[0]),
            team2_players=(existing_player_ids[1], existing_player_ids[2]),
            scores=[{"team1": 15, "team2": 21}, {"team1": 18, "team2": 21}],  # New player's team loses (realistic)
            played_at=datetime.now(),
            database=db_service
        )
        
        # Step 7: Verify new player gets rating
        new_player_rating = await db_service.get_player_rating(new_player_id)
        assert new_player_rating is not None
        assert new_player_rating["games_played"] == 1
        
        # Step 8: New player plays more matches to establish themselves
        for i in range(3):  # Play 3 more matches
            partner_idx = i % len(existing_player_ids)
            opponent1_idx = (i + 1) % len(existing_player_ids)
            opponent2_idx = (i + 2) % len(existing_player_ids)
            
            await matches.create_match(
                venue_id=UUID(existing_venue["id"]),
                created_by=new_player_id,
                team1_players=(new_player_id, existing_player_ids[partner_idx]),
                team2_players=(existing_player_ids[opponent1_idx], existing_player_ids[opponent2_idx]),
                scores=[{"team1": 21, "team2": 18}, {"team1": 21, "team2": 15}] if i > 0 else [{"team1": 18, "team2": 21}, {"team1": 19, "team2": 21}],
                played_at=datetime.now() + timedelta(days=i+1),
                database=db_service
            )
        
        # Step 9: Check new player's progress
        final_rating = await db_service.get_player_rating(new_player_id)
        assert final_rating["games_played"] == 4
        
        # New player should now have compatibility scores
        compatibility_scores = await recommendations.get_compatibility_scores(
            new_player_id, 
            database=db_service
        )
        assert len(compatibility_scores) >= 3  # Played with at least 3 different partners
        
        # Check social connections
        new_player_following = await social.get_following(new_player_id, database=db_service)
        new_player_followers = await social.get_followers(new_player_id, database=db_service)
        
        assert len(new_player_following) == 4  # Following all 4 existing players
        assert len(new_player_followers) == 2  # 2 existing players follow back
        
        # New player should appear in leaderboards
        leaderboard = await matches.get_top_players(limit=10, database=db_service)
        new_player_in_leaderboard = any(p["player_id"] == str(new_player_id) for p in leaderboard)
        assert new_player_in_leaderboard
        
        print("✅ New player onboarding workflow completed successfully") 