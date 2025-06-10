"""
Matches page for SmashMate - Match recording and history.
"""

import streamlit as st
import sys
from pathlib import Path
from uuid import UUID
from datetime import datetime

# Add parent directory to path to import shared utilities
sys.path.append(str(Path(__file__).parent.parent))

from app.streamlit.shared  import setup_page, get_user_id, run_async, DB_SERVICE
from app.core import matches, social, venues

# Page setup
setup_page("Matches", "🏸")

def main():
    """Match recording and history."""
    st.title("🏸 Matches")
    
    user_id = get_user_id()
    
    tab1, tab2 = st.tabs(["📝 Record Match", "📊 Match History"])
    
    with tab1:
        st.subheader("Record New Match")
        
        # Venue Selection Section
        st.markdown("#### 🏟️ Select Venue")
        
        venue_tab1, venue_tab2 = st.tabs(["🔍 Find Venue", "🎯 Current Selection"])
        
        with venue_tab1:
            # First, show available venues without requiring search
            st.markdown("**Available Demo Venues:**")
            try:
                # Get all venues in San Francisco area (large radius to catch all demo venues)
                all_venues = run_async(
                    venues.find_nearby_venues(37.7749, -122.4194, 50000, database=DB_SERVICE)
                )
                
                if all_venues:
                    st.success(f"Found {len(all_venues)} available venues")
                    
                    # Display all venues
                    for venue in all_venues:
                        with st.container():
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(f"**{venue['name']}**")
                                st.caption(f"{venue['address']}")
                                # Debug info
                                st.caption(f"ID: {venue.get('id', 'No ID')} | Lat: {venue.get('latitude', 'N/A')} | Lon: {venue.get('longitude', 'N/A')}")
                            with col2:
                                if st.button("Select", key=f"select_venue_{venue.get('id', 'unknown')}"):
                                    st.session_state.current_venue = venue
                                    st.success(f"✅ Selected {venue['name']}")
                                    st.rerun()
                            st.markdown("---")
                else:
                    st.warning("❌ No venues found! This might be a database issue.")
                    st.info("💡 Try clicking 'Reset Demo Environment' on the main page.")
                    
            except Exception as e:
                st.error(f"Error loading venues: {str(e)}")
                st.info("💡 Try clicking 'Reset Demo Environment' on the main page.")
            
            # Custom search section
            st.markdown("**🔍 Custom Search:**")
            col1, col2, col3 = st.columns(3)
            with col1:
                search_lat = st.number_input("Latitude", value=37.7749, format="%.6f", key="match_lat")
            with col2:
                search_lng = st.number_input("Longitude", value=-122.4194, format="%.6f", key="match_lng")
            with col3:
                radius = st.number_input("Search Radius (km)", value=10.0, min_value=0.1, max_value=50.0, key="match_radius")
            
            if st.button("🔍 Search Venues", key="search_venues_match"):
                try:
                    nearby_venues = run_async(
                        venues.find_nearby_venues(
                            search_lat, search_lng, radius * 1000, database=DB_SERVICE
                        )
                    )
                    
                    if nearby_venues:
                        st.success(f"Search found {len(nearby_venues)} venues")
                        
                        # Display venues in a more compact format
                        for venue in nearby_venues:
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(f"**{venue['name']}**")
                                st.caption(f"{venue['address']} • {venue.get('distance_km', 0):.1f} km away")
                            with col2:
                                if st.button("Select", key=f"select_search_{venue.get('id', 'unknown')}"):
                                    st.session_state.current_venue = venue
                                    st.success(f"✅ Selected {venue['name']}")
                                    st.rerun()
                    else:
                        st.info("No venues found in this area. Try expanding your search radius.")
                except Exception as e:
                    st.error(f"Search failed: {str(e)}")
        
        with venue_tab2:
            if st.session_state.current_venue:
                venue = st.session_state.current_venue
                st.success(f"✅ **Selected Venue:** {venue['name']}")
                st.write(f"📍 **Address:** {venue['address']}")
                st.write(f"🗺️ **Location:** {venue.get('latitude', 'N/A')}, {venue.get('longitude', 'N/A')}")
                st.write(f"🆔 **Venue ID:** {venue.get('id', 'No ID')}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 Change Venue"):
                        st.session_state.current_venue = None
                        st.rerun()
                with col2:
                    if st.button("🚀 Proceed to Match Recording"):
                        # Scroll down to match form or use some visual indicator
                        st.balloons()
                        st.success("Great! Now fill out the match details below.")
            else:
                st.info("🎯 No venue selected yet. Use the 'Find Venue' tab to search and select a venue.")
        
        st.markdown("---")
        
        # Only show match recording form if venue is selected
        if not st.session_state.current_venue:
            st.warning("👆 Please select a venue above before recording a match")
            st.stop()
        
        st.markdown("#### 📝 Match Details")
        st.info(f"🏟️ Recording match at: **{st.session_state.current_venue['name']}**")
        
        with st.form("record_match"):
            st.markdown("##### Players")
            
            # Get following list for player selection
            try:
                following = run_async(social.get_following(user_id, database=DB_SERVICE))
                player_options = {f"{f['display_name']}": f['user_id'] for f in following}
                player_names = list(player_options.keys())
                
                if len(player_names) < 3:
                    st.error("You need to follow at least 3 other players to record a match")
                    st.info("💡 Go to the Social page to follow more players!")
                    st.stop()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Team 1**")
                    team1_player1 = st.selectbox("Player 1 (You)", [st.session_state.user_profile['display_name']], disabled=True)
                    team1_player2 = st.selectbox("Partner", player_names, key="team1_p2")
                
                with col2:
                    st.markdown("**Team 2**")
                    remaining_players = [p for p in player_names if p != team1_player2]
                    team2_player1 = st.selectbox("Player 1", remaining_players, key="team2_p1")
                    final_remaining = [p for p in remaining_players if p != team2_player1]
                    team2_player2 = st.selectbox("Player 2", final_remaining, key="team2_p2")
                
                st.markdown("##### Match Information")
                played_date = st.date_input("Date Played", datetime.now().date())
                
                st.markdown("##### Match Result")
                st.caption("Who won the match?")
                
                winner_option = st.radio(
                    "Select the winning team:",
                    options=[
                        f"Team 1 ({st.session_state.user_profile['display_name']} + {team1_player2})",
                        f"Team 2 ({team2_player1} + {team2_player2})"
                    ],
                    key="winner_selection"
                )
                
                submitted = st.form_submit_button("🏸 Record Match", type="primary")
                
                if submitted:
                    try:
                        # Convert player names to IDs
                        team1_ids = (user_id, UUID(player_options[team1_player2]))
                        team2_ids = (UUID(player_options[team2_player1]), UUID(player_options[team2_player2]))
                        
                        # Use current date with default time (noon)
                        played_at = datetime.combine(played_date, datetime.min.time().replace(hour=12))
                        
                        # Create simple score based on winner (1-0)
                        team1_won = winner_option.startswith("Team 1")
                        scores = [{"team1": 1 if team1_won else 0, "team2": 0 if team1_won else 1}]
                        
                        # Debug venue ID
                        venue_id = st.session_state.current_venue.get('id')
                        if not venue_id:
                            st.error("Venue ID is missing! This is a data issue.")
                            st.stop()
                        
                        match = run_async(
                            matches.create_match(
                                UUID(venue_id),
                                user_id,
                                team1_ids,
                                team2_ids,
                                scores,
                                played_at,
                                database=DB_SERVICE
                            )
                        )
                        
                        st.success("Match recorded successfully! 🎉")
                        st.balloons()
                        
                        # Show match summary
                        winning_team = "Team 1 (Your team)" if team1_won else "Team 2"
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Winner", winning_team)
                        with col2:
                            st.metric("Your Team", "Won! 🏆" if team1_won else "Lost 😔")
                        with col3:
                            st.metric("Date", played_date.strftime("%Y-%m-%d"))
                        
                    except Exception as e:
                        st.error(f"Failed to record match: {str(e)}")
            
            except Exception as e:
                st.error(f"Error loading players: {str(e)}")
    
    with tab2:
        st.subheader("Your Match History")
        
        try:
            user_matches = run_async(matches.get_player_matches(user_id, database=DB_SERVICE))
            
            if user_matches:
                st.write(f"📊 **Total matches played:** {len(user_matches)}")
                
                # Add filter options
                col1, col2 = st.columns(2)
                with col1:
                    show_recent = st.checkbox("Show only recent matches (last 10)", value=True)
                with col2:
                    reverse_order = st.checkbox("Show newest first", value=True)
                
                # Filter and sort matches
                display_matches = user_matches
                if reverse_order:
                    display_matches = list(reversed(display_matches))
                if show_recent:
                    display_matches = display_matches[:10]
                
                for i, match in enumerate(display_matches):
                    with st.expander(f"🏸 Match #{len(user_matches) - i if reverse_order else i + 1} • {match['played_at'][:10]} at {match.get('venue_name', 'Unknown Venue')}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Team 1:** {match.get('team1_names', 'Unknown')}")
                            st.write(f"**Team 2:** {match.get('team2_names', 'Unknown')}")
                        
                        with col2:
                            st.write(f"**Final Score:** {match.get('final_score', 'N/A')}")
                            st.write(f"**Date:** {match['played_at'][:10]}")
                        
                        if 'scores' in match and match['scores']:
                            st.write("**Set-by-Set Scores:**")
                            score_cols = st.columns(len(match['scores']))
                            for j, score in enumerate(match['scores']):
                                with score_cols[j]:
                                    st.metric(f"Set {j+1}", f"{score.get('team1', 0)} - {score.get('team2', 0)}")
            else:
                st.info("📝 No matches recorded yet. Record your first match above!")
                
        except Exception as e:
            st.error(f"Error loading match history: {str(e)}")

if __name__ == "__main__":
    main() 