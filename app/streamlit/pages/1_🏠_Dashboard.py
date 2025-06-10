"""
Dashboard page for SmashMate - Personal stats and overview.
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path to import shared utilities
sys.path.append(str(Path(__file__).parent.parent))

from app.streamlit.shared  import setup_page, get_user_id, run_async, DB_SERVICE
from app.core import matches, social

# Page setup
setup_page("Dashboard", "🏠")

def main():
    """Main dashboard showing user stats and recent activity."""
    st.title(f"Welcome back, {st.session_state.user_profile['display_name']}! 🏸")
    
    user_id = get_user_id()
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    
    try:
        # Get user stats
        player_matches = run_async(matches.get_player_matches(user_id, database=DB_SERVICE))
        followers = run_async(social.get_followers(user_id, database=DB_SERVICE))
        following = run_async(social.get_following(user_id, database=DB_SERVICE))
        
        with col1:
            st.metric("Matches Played", len(player_matches))
        with col2:
            st.metric("Followers", len(followers))
        with col3:
            st.metric("Following", len(following))
        with col4:
            # Get rating
            try:
                rating = run_async(DB_SERVICE.get_player_rating(user_id))
                if rating:
                    st.metric("Rating", f"{float(rating['mu']):.1f}")
                else:
                    st.metric("Rating", "Unrated")
            except:
                st.metric("Rating", "Unrated")
    
    except Exception as e:
        st.error(f"Error loading stats: {str(e)}")
    
    # Current venue selection
    st.subheader("🏟️ Current Venue")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.session_state.current_venue:
            st.success(f"Currently at: {st.session_state.current_venue['name']}")
        else:
            st.info("No venue selected. Visit the Venues page to find or create one.")
    
    with col2:
        if st.button("Clear Venue"):
            st.session_state.current_venue = None
            st.rerun()
    
    # Recent matches
    st.subheader("📊 Recent Matches")
    try:
        recent_matches = run_async(matches.get_player_matches(user_id, database=DB_SERVICE))
        if recent_matches:
            # Show only the last 5 matches
            for match in recent_matches[-5:]:
                with st.expander(f"Match at {match.get('venue_name', 'Unknown Venue')} - {match['played_at'][:10]}"):
                    st.write(f"**Team 1:** {match.get('team1_names', 'Unknown players')}")
                    st.write(f"**Team 2:** {match.get('team2_names', 'Unknown players')}")
                    st.write(f"**Score:** {match.get('final_score', 'N/A')}")
        else:
            st.info("No matches played yet. Record your first match!")
    except Exception as e:
        st.error(f"Error loading recent matches: {str(e)}")

if __name__ == "__main__":
    main() 