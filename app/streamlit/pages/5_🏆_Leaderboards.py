"""
Leaderboards page for SmashMate - Rankings, ratings, and compatibility scores.
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from uuid import UUID

# Add parent directory to path to import shared utilities
sys.path.append(str(Path(__file__).parent.parent))

from app.streamlit.shared  import setup_page, get_user_id, run_async, DB_SERVICE
from app.core import matches, recommendations, social

# Page setup
setup_page("Leaderboards", "🏆")

def main():
    """Rankings, ratings, and compatibility scores."""
    st.title("🏆 Leaderboards & Stats")
    
    user_id = get_user_id()
    
    tab1, tab2, tab3 = st.tabs(["🥇 Player Rankings", "💑 Partner Compatibility", "🎯 Recommendations"])
    
    with tab1:
        st.subheader("Top Players")
        
        try:
            top_players = run_async(matches.get_top_players(limit=20, database=DB_SERVICE))
            
            if top_players:
                # Create DataFrame for better display
                df = pd.DataFrame(top_players)
                
                # Fetch player names for each player_id
                player_names = {}
                for player_data in top_players:
                    player_id = player_data['player_id']
                    try:
                        profile = run_async(DB_SERVICE.get_profile(UUID(player_id)))
                        if profile:
                            player_names[player_id] = profile.get('display_name', 'Unknown Player')
                        else:
                            player_names[player_id] = 'Unknown Player'
                    except Exception:
                        player_names[player_id] = 'Unknown Player'
                
                # Add player names to DataFrame
                df['display_name'] = df['player_id'].map(player_names)
                
                # Process the rating data
                df['rating'] = pd.to_numeric(df['mu'], errors='coerce').round(1)
                df['rank'] = range(1, len(df) + 1)
                
                # For now, we don't have wins/losses data, so we'll just show games played
                # You could calculate this from match history if needed
                
                # Highlight current user
                df['is_you'] = df['player_id'] == str(user_id)
                
                # Display table with available columns
                display_df = df[['rank', 'display_name', 'rating', 'games_played']].copy()
                
                st.dataframe(
                    display_df,
                    column_config={
                        "rank": "Rank",
                        "display_name": "Player",
                        "rating": "Rating",
                        "games_played": "Games Played"
                    },
                    hide_index=True
                )
                
                # Show user's position
                user_rank = df[df['player_id'] == str(user_id)]
                if not user_rank.empty:
                    rank = user_rank.iloc[0]['rank']
                    rating = user_rank.iloc[0]['rating']
                    games = user_rank.iloc[0]['games_played']
                    st.info(f"🎯 Your current rank: **#{rank}** with rating **{rating}** ({games} games played)")
                else:
                    st.info("🎯 You haven't played any ranked games yet. Record some matches to see your ranking!")
                    
            else:
                st.info("📊 No player rankings available yet. Record some matches to see rankings!")
                
        except Exception as e:
            st.error(f"Error loading rankings: {str(e)}")
            # Add more detailed error info for debugging
            import traceback
            with st.expander("🐛 Debug Information"):
                st.code(traceback.format_exc())
    
    with tab2:
        st.subheader("Your Partner Compatibility")
        
        try:
            compatibility_scores = run_async(
                recommendations.get_compatibility_scores(user_id, database=DB_SERVICE)
            )
            
            if compatibility_scores:
                # Extract display_name from partner
                for score in compatibility_scores:
                    score['partner'] = score['partner']['display_name']
                
                # Create DataFrame
                df = pd.DataFrame(compatibility_scores)
                df['compatibility'] = df['compatibility_score'].astype(float).round(2)
                df['team_rating'] = df['team_rating'].astype(float).round(1)
                df['avg_individual'] = df['avg_individual_rating'].astype(float).round(1)
                
                # Sort by compatibility score
                df = df.sort_values('compatibility', ascending=False)
                
                st.dataframe(
                    df[['partner', 'compatibility', 'team_rating', 'avg_individual']],
                    column_config={
                        "partner": "Partner",
                        "compatibility": "Compatibility Score",
                        "team_rating": "Team Rating",
                        "avg_individual": "Avg Individual Rating"
                    },
                    hide_index=True
                )
                
                # Show compatibility explanation
                st.info("""
                **Compatibility Score = Team Rating - Average Individual Rating**
                
                - **Positive score**: You work well together as a team
                - **Negative score**: You might need more practice together
                - **Higher score**: Better team chemistry
                """)
                
                # Show top partner
                if not df.empty:
                    best_partner = df.iloc[0]
                    st.success(f"🏆 Your best partner: **{best_partner['partner']}** (Score: {best_partner['compatibility']})")
                
            else:
                st.info("Play some matches with different partners to see compatibility scores!")
                
        except Exception as e:
            st.error(f"Error loading compatibility scores: {str(e)}")
    
    with tab3:
        st.subheader("Partner Recommendations")
        
        try:
            recommendations_list = run_async(
                recommendations.get_recommended_partners(
                    user_id, limit=10, min_games=1, database=DB_SERVICE
                )
            )
            
            if recommendations_list:
                st.write("Based on your play style and ratings, here are some recommended partners:")
                
                for i, rec in enumerate(recommendations_list, 1):
                    with st.expander(f"#{i} {rec.get('partner', 'Unknown')}"):
                        st.write(f"**Predicted Compatibility:** {rec.get('predicted_compatibility', 0):.2f}")
                        st.write(f"**Their Rating:** {rec.get('partner_rating', 0):.1f}")
                        st.write(f"**Games Played Together:** {rec.get('games_together', 0)}")
                        
                        # Add follow button if not already following
                        partner_id = rec.get('partner_id')
                        if partner_id:
                            if st.button(f"Follow {rec.get('partner', 'User')}", key=f"follow_rec_{partner_id}"):
                                try:
                                    run_async(social.follow_player(user_id, UUID(partner_id), database=DB_SERVICE))
                                    st.success("Now following!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to follow: {str(e)}")
            else:
                st.info("Play more matches to get partner recommendations!")
                
        except Exception as e:
            st.error(f"Error loading recommendations: {str(e)}")

if __name__ == "__main__":
    main() 