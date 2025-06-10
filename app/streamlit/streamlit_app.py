"""
SmashMate - Badminton Companion App
Main entry point with login functionality.
"""

import streamlit as st
from uuid import UUID
import logging

from shared import setup_demo_environment, init_session_state, run_async, DB_SERVICE
from app.core import auth

# Configure page
st.set_page_config(
    page_title="SmashMate - Badminton Companion",
    page_icon="🏸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
init_session_state()

# Set up logging
logger = logging.getLogger(__name__)

async def comprehensive_database_cleanup(db_service) -> int:
    """
    Comprehensive database cleanup for Streamlit demo environment.
    
    This function performs a thorough cleanup of all demo-related data,
    including attempts to handle constraint violations and orphaned records.
    
    Args:
        db_service: DatabaseService instance to perform the cleanup
        
    Returns:
        Total number of records cleaned
    """
    # Step 1: Delete all records in dependency order
    # Each tuple contains (table_name, primary_key_field, has_timestamp)
    cleanup_operations = [
        # Delete message and group data first (most dependent)
        ("group_messages", "id", True),
        ("group_members", "group_id", False),  # composite key
        ("messages", "id", True),
        
        # Delete match-related data
        ("match_players", "match_id", False),  # composite key
        ("matches", "id", False),
        
        # Delete rating and team data
        ("player_ratings", "player_id", False),
        ("teams", "id", False),
        
        # Delete social connections
        ("follows", "follower", True),  # composite key with timestamp
        
        # Delete groups
        ("groups", "id", True),
        
        # Delete venue data
        ("venues", "id", False),
        
        # Finally delete profiles (least dependent)
        ("profiles", "user_id", False),
    ]
    
    total_cleaned = 0
    
    for table, key_field, has_timestamp in cleanup_operations:
        try:
            # Try different approaches based on table structure
            if has_timestamp:
                # For tables with created_at timestamp, delete records after year 1900
                result = await db_service.client.table(table).delete().gte("created_at", "1900-01-01T00:00:00Z").execute()
            elif table in ["follows", "match_players", "group_members"]:
                # For composite key tables, use a different approach
                # Get all records first, then delete
                select_result = await db_service.client.table(table).select("*").execute()
                if hasattr(select_result, 'data') and select_result.data:
                    # Delete all records by selecting all and then deleting
                    result = await db_service.client.table(table).delete().in_(key_field, [row[key_field] for row in select_result.data[:100]]).execute()
                else:
                    result = None
            else:
                # For tables with UUID primary keys, delete where key is not null
                result = await db_service.client.table(table).delete().not_.is_(key_field, "null").execute()
            
            if result and hasattr(result, 'data') and result.data:
                cleaned_count = len(result.data)
                total_cleaned += cleaned_count
                logger.debug(f"Cleaned {cleaned_count} records from {table}")
            
        except Exception as e:
            logger.warning(f"Cleanup failed for {table}: {str(e)}")
            # Try a simple fallback - delete a few records at a time
            try:
                # Get a small sample of records and delete them
                select_result = await db_service.client.table(table).select(key_field).limit(10).execute()
                if hasattr(select_result, 'data') and select_result.data:
                    for row in select_result.data:
                        try:
                            await db_service.client.table(table).delete().eq(key_field, row[key_field]).execute()
                            total_cleaned += 1
                        except Exception:
                            pass  # Skip individual failures
            except Exception:
                logger.debug(f"Fallback cleanup also failed for {table}")
                pass
    
    return total_cleaned

def login_page():
    """User login/registration page."""
    st.title("🏸 Welcome to SmashMate")
    st.subheader("Your Badminton Companion App")
    
    # Setup demo environment if not already done
    if st.session_state.demo_users is None:
        st.info("🚀 Setting up demo environment...")
        st.session_state.demo_users = setup_demo_environment()
        if st.session_state.demo_users:
            st.success("✅ Demo environment ready!")
            st.rerun()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Sign In")
        with st.form("login_form"):
            user_id_input = st.text_input("User ID", help="Enter your user ID")
            display_name = st.text_input("Display Name")
            submitted = st.form_submit_button("Sign In / Register")
            
            if submitted and user_id_input and display_name:
                try:
                    # Try to parse as UUID
                    user_id = UUID(user_id_input)
                    
                    profile = run_async(
                        auth.get_or_create_profile(
                            user_id, display_name, database=DB_SERVICE
                        )
                    )
                    
                    st.session_state.logged_in = True
                    st.session_state.user_profile = profile
                    st.success(f"Welcome, {profile['display_name']}!")
                    st.rerun()
                    
                except ValueError:
                    st.error("Invalid User ID format. Please enter a valid UUID.")
                except Exception as e:
                    st.error(f"Login failed: {str(e)}")
                    if "foreign key constraint" in str(e):
                        st.warning("This User ID doesn't exist in the auth system.")
                        st.info("💡 Try one of the demo users below!")
    
    with col2:
        st.markdown("### Demo Users")
        st.info("👥 **Ready-to-Use Demo Accounts**")
        
        if st.session_state.demo_users:
            for name, user_data in st.session_state.demo_users.items():
                # Create columns for expander and quick login button
                col_expander, col_login = st.columns([3, 1])
                
                with col_expander:
                    with st.expander(f"🏸 {name}"):
                        st.code(user_data["id"], language=None)
                        st.caption(user_data["desc"])
                
                with col_login:
                    if st.button("⚡ Quick Login", key=f"demo_{name}"):
                        try:
                            user_id = UUID(user_data["id"])
                            
                            profile = run_async(
                                auth.get_or_create_profile(
                                    user_id, name, database=DB_SERVICE
                                )
                            )
                            
                            st.session_state.logged_in = True
                            st.session_state.user_profile = profile
                            st.success(f"Logged in as {name}")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Demo login failed: {str(e)}")
        else:
            st.warning("Demo users not available. Check your Supabase connection.")
        
        st.markdown("---")
        st.markdown("**🎯 Fresh Demo Environment**")
        st.markdown("• Demo users are created automatically")
        st.markdown("• User profiles are set up for all demo users")
        st.markdown("• Sample venues are created across San Francisco")
        st.markdown("• Database is cleaned on each app restart") 
        st.markdown("• All UUIDs are properly generated by Supabase")
        
        # Reset and cleanup buttons
        col_reset, col_cleanup = st.columns(2)
        
        with col_reset:
            if st.button("🔄 Reset Demo Environment"):
                setup_demo_environment.clear()
                st.session_state.demo_users = None
                st.rerun()
        
        with col_cleanup:
            if st.button("🧹 Clean Database", help="Remove all data from database"):
                with st.spinner("Cleaning database..."):
                    try:
                        total_cleaned = run_async(comprehensive_database_cleanup(DB_SERVICE))
                        st.success(f"✅ Database cleaned! Removed {total_cleaned} records.")
                        
                        # Clear demo environment cache to force recreation
                        setup_demo_environment.clear()
                        st.session_state.demo_users = None
                        
                        # If user was logged in, log them out since their data is gone
                        if st.session_state.logged_in:
                            st.session_state.logged_in = False
                            st.session_state.user_profile = None
                            st.session_state.current_venue = None
                            st.info("Logged out due to database cleanup")
                        
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Database cleanup failed: {str(e)}")

def main():
    """Main app logic."""
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #ff6b35 0%, #004d40 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #ff6b35;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Sidebar with logout
    with st.sidebar:
        st.title("SmashMate")
        
        if st.session_state.logged_in:
            st.success(f"Logged in as: {st.session_state.user_profile['display_name']}")
            st.markdown("---")
            # Logout button
            if st.button("🚪 Logout"):
                st.session_state.logged_in = False
                st.session_state.user_profile = None
                st.session_state.current_venue = None
                st.rerun()
        else:
            st.info("Please log in to continue")
    
    # Main content - show login or welcome message
    if not st.session_state.logged_in:
        login_page()
    else:
        # Show welcome message and instructions
        st.title(f"Welcome to SmashMate, {st.session_state.user_profile['display_name']}! 🏸")
        
        st.markdown("""
        ### 🎯 Getting Started
        
        Your badminton companion app is ready! Use the pages in the sidebar to:
        
        1. **🏠 Dashboard** - See your stats and recent matches
        2. **👥 Social** - Connect with other players and chat
        3. **🏟️ Venues** - Find or add badminton courts
        4. **🏸 Matches** - Record your game results  
        5. **🏆 Leaderboards** - Check rankings and partner compatibility
        
        ### 🌟 What's New
        - **Multi-page navigation** for better organization
        - **Real-time social features** with follow/unfollow
        - **Smart partner recommendations** based on compatibility
        - **Interactive venue maps** for court discovery
        - **Comprehensive match tracking** with TrueSkill ratings
        """)
        
        # Quick stats in welcome
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info("🏸 **Start by finding friends!**\nGo to Social → Discover Players")
        
        with col2:
            st.info("🏟️ **Select a venue**\nGo to Venues → Find Venues")
            
        with col3:
            st.info("📊 **Record matches**\nGo to Matches → Record Match")

if __name__ == "__main__":
    main()
