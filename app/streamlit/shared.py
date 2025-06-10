"""
Shared utilities for SmashMate Streamlit app.
"""

import asyncio
from uuid import UUID

import streamlit as st
from supabase import create_client

from app.core import auth, venues
from app.services.database import DatabaseService

# Shared database service
DB_SERVICE = DatabaseService()

# Demo users to create
demo_users_data = [
    {"name": "Alice Chen", "email": "alice.chen@smashmate.demo", "desc": "Demo player who loves doubles"},
    {"name": "Bob Wilson", "email": "bob.wilson@smashmate.demo", "desc": "Regular at Downtown Sports Center"},
    {"name": "Carol Lee", "email": "carol.lee@smashmate.demo", "desc": "Competitive player with high ratings"},
    {"name": "David Park", "email": "david.park@smashmate.demo", "desc": "New player looking for partners"},
    {"name": "Ethan Chen", "email": "ethan.chen@smashmate.demo", "desc": "New player looking for partners"},
    {"name": "Fiona Wilson", "email": "fiona.wilson@smashmate.demo", "desc": "New player looking for partners"},
    {"name": "George Lee", "email": "george.lee@smashmate.demo", "desc": "New player looking for partners"},
    {"name": "Hannah Park", "email": "hannah.park@smashmate.demo", "desc": "New player looking for partners"},
    {"name": "Ian Chen", "email": "ian.chen@smashmate.demo", "desc": "New player looking for partners"},
    {"name": "Jenny Wilson", "email": "jenny.wilson@smashmate.demo", "desc": "New player looking for partners"},
    {"name": "Kevin Lee", "email": "kevin.lee@smashmate.demo", "desc": "New player looking for partners"},
]

def run_async(coro):
    """Run an async function synchronously."""
    return asyncio.run(coro)

@st.cache_data
def setup_demo_environment():
    """Set up demo users and clean database. Cached to run only once per session."""
    
    # Use local Supabase settings
    supabase_url = "http://127.0.0.1:54321"
    service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU"
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Create Supabase client
        supabase = create_client(supabase_url, service_key)
        
        status_text.text("🧹 Cleaning up existing data...")
        progress_bar.progress(15)
        
        # Clean up existing demo users (by email pattern)
        try:
            # Get existing demo users
            existing_users = supabase.auth.admin.list_users()
            demo_emails = [user.email for user in existing_users]
            
            for user in existing_users:
                if user.email in demo_emails:
                    supabase.auth.admin.delete_user(user.id)
        except:
            pass  # Ignore cleanup errors
        
        progress_bar.progress(25)
        status_text.text("👥 Creating demo users...")
        
        
        
        created_users = {}
        
        for i, user_data in enumerate(demo_users_data):
            n_demo_users = len(demo_users_data)
            try:
                # Create user in auth system - let Supabase generate UUID
                auth_response = supabase.auth.admin.create_user({
                    "email": user_data["email"],
                    "password": "demo_password123",
                    "email_confirm": True
                })
                
                created_users[user_data["name"]] = {
                    "id": auth_response.user.id,
                    "email": auth_response.user.email,
                    "desc": user_data["desc"]
                }
                
                progress_bar.progress(25 + (i + 1) * (100 / n_demo_users))
                
            except Exception as e:
                st.warning(f"Failed to create {user_data['name']}: {str(e)}")
        
        progress_bar.progress(58)
        status_text.text("👤 Creating user profiles...")
        
        # Create profiles for all demo users
        for i, (name, user_data) in enumerate(created_users.items()):
            try:
                user_id = UUID(user_data["id"])
                # Create profile using the same method as login
                profile = run_async(
                    auth.get_or_create_profile(
                        user_id, name, database=DB_SERVICE
                    )
                )
                progress_bar.progress(58 + (i + 1) * 6)
                
            except Exception as e:
                st.warning(f"Failed to create profile for {name}: {str(e)}")
        
        progress_bar.progress(82)
        status_text.text("🏟️ Creating demo venues...")
        
        # Create demo venues - use the first user as creator
        first_user_id = UUID(list(created_users.values())[0]["id"]) if created_users else None
        
        if first_user_id:
            demo_venues_data = [
                {
                    "name": "Downtown Sports Center",
                    "address": "123 Main St, San Francisco, CA 94102",
                    "lat": 37.7749,
                    "lng": -122.4194,
                    "desc": "Premier badminton facility with 8 courts"
                },
                {
                    "name": "Golden Gate Badminton Club", 
                    "address": "456 Park Ave, San Francisco, CA 94115",
                    "lat": 37.7849,
                    "lng": -122.4294,
                    "desc": "Community club with competitive leagues"
                },
                {
                    "name": "Mission Bay Recreation Center",
                    "address": "789 Bay St, San Francisco, CA 94158", 
                    "lat": 37.7649,
                    "lng": -122.3894,
                    "desc": "Public facility with affordable court rates"
                },
                {
                    "name": "Sunset District Sports Complex",
                    "address": "321 Sunset Blvd, San Francisco, CA 94122",
                    "lat": 37.7549,
                    "lng": -122.4694,
                    "desc": "Modern facility with excellent lighting"
                },
                {
                    "name": "Richmond Badminton Academy",
                    "address": "654 Richmond Ave, San Francisco, CA 94118",
                    "lat": 37.7949,
                    "lng": -122.4494,
                    "desc": "Professional training center with coaching"
                }
            ]
            
            created_venues = []
            for i, venue_data in enumerate(demo_venues_data):
                try:
                    venue = run_async(
                        venues.create_venue(
                            name=venue_data["name"],
                            latitude=venue_data["lat"],
                            longitude=venue_data["lng"],
                            address=venue_data["address"],
                            created_by=first_user_id,
                            database=DB_SERVICE
                        )
                    )
                    created_venues.append(venue)
                    progress_bar.progress(82 + (i + 1) * 3)
                    
                except Exception as e:
                    st.warning(f"Failed to create venue {venue_data['name']}: {str(e)}")
        
        progress_bar.progress(98)
        status_text.text("✅ Demo environment ready!")
        
        progress_bar.progress(100)
        
        # Clear progress indicators 
        progress_bar.empty()
        status_text.empty()
        
        return created_users
        
    except Exception as e:
        st.error(f"Failed to setup demo environment: {str(e)}")
        progress_bar.empty()
        status_text.empty()
        return {}

def init_session_state():
    """Initialize session state variables."""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_profile' not in st.session_state:
        st.session_state.user_profile = None
    if 'current_venue' not in st.session_state:
        st.session_state.current_venue = None
    if 'demo_users' not in st.session_state:
        st.session_state.demo_users = None

def require_login():
    """Redirect to login if user is not logged in."""
    if not st.session_state.logged_in:
        st.warning("🔒 Please log in first")
        st.info("👈 Go back to the main page to log in")
        st.stop()

def get_user_id():
    """Get current user ID from session state."""
    require_login()
    return UUID(st.session_state.user_profile['user_id'])

def setup_page(title: str, icon: str = "🏸"):
    """Common page setup."""
    st.set_page_config(
        page_title=f"{title} - SmashMate",
        page_icon=icon,
        layout="wide"
    )
    
    # Initialize session state
    init_session_state()
    
    # Check login
    require_login()
    
    # Add custom CSS
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