"""
Venues page for SmashMate - Venue discovery and management.
"""

import streamlit as st
import plotly.express as px
import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path to import shared utilities
sys.path.append(str(Path(__file__).parent.parent))

from app.streamlit.shared import setup_page, get_user_id, run_async, DB_SERVICE
from app.core import venues

# Page setup
setup_page("Venues", "🏟️")

def main():
    """Venue management and discovery."""
    st.title("🏟️ Venues")
    
    user_id = get_user_id()
    
    tab1, tab2, tab3 = st.tabs(["🔍 Find Venues", "➕ Add Venue", "🗺️ Venue Map"])
    
    with tab1:
        st.subheader("Find Nearby Venues")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            search_lat = st.number_input("Latitude", value=37.7749, format="%.6f")
        with col2:
            search_lng = st.number_input("Longitude", value=-122.4194, format="%.6f")
        with col3:
            radius = st.number_input("Search Radius (km)", value=5.0, min_value=0.1, max_value=50.0)
        
        if st.button("Search Venues"):
            try:
                nearby_venues = run_async(
                    venues.find_nearby_venues(
                        search_lat, search_lng, radius * 1000, database=DB_SERVICE
                    )
                )
                
                if nearby_venues:
                    st.success(f"Found {len(nearby_venues)} venues")
                    
                    for venue in nearby_venues:
                        with st.expander(f"{venue['name']} - {venue.get('distance_km', 0):.1f} km away"):
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(f"**Address:** {venue['address']}")
                                st.write(f"**Location:** {venue['latitude']}, {venue['longitude']}")
                            with col2:
                                if st.button("Select Venue", key=f"select_{venue['id']}"):
                                    st.session_state.current_venue = venue
                                    st.success(f"Selected {venue['name']}")
                                    st.rerun()
                else:
                    st.info("No venues found in this area")
            except Exception as e:
                st.error(f"Search failed: {str(e)}")
    
    with tab2:
        st.subheader("Add New Venue")
        
        with st.form("add_venue"):
            venue_name = st.text_input("Venue Name*")
            venue_address = st.text_input("Address*")
            venue_lat = st.number_input("Latitude*", format="%.6f")
            venue_lng = st.number_input("Longitude*", format="%.6f")
            
            st.caption("💡 Tip: You can get coordinates from Google Maps by right-clicking on a location")
            
            submitted = st.form_submit_button("Add Venue")
            
            if submitted and venue_name and venue_address:
                try:
                    new_venue = run_async(
                        venues.create_venue(
                            venue_name, venue_lat, venue_lng, venue_address, user_id, database=DB_SERVICE
                        )
                    )
                    st.success(f"Added venue: {venue_name}")
                    st.json(new_venue)
                except Exception as e:
                    st.error(f"Failed to add venue: {str(e)}")
    
    with tab3:
        st.subheader("Venue Locations")
        
        try:
            # Get some nearby venues to display
            nearby_venues = run_async(
                venues.find_nearby_venues(37.7749, -122.4194, 50000, database=DB_SERVICE)
            )
            
            if nearby_venues:
                # Create map data
                venue_data = []
                for venue in nearby_venues:
                    venue_data.append({
                        'name': venue['name'],
                        'lat': venue['latitude'],
                        'lon': venue['longitude'],
                        'address': venue['address']
                    })
                
                df = pd.DataFrame(venue_data)
                
                if not df.empty:
                    # Create map using the newer scatter_map function
                    fig = px.scatter_map(
                        df, 
                        lat="lat", 
                        lon="lon", 
                        hover_name="name",
                        hover_data=["address"],
                        zoom=10, 
                        height=400,
                        map_style="open-street-map"
                    )
                    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No venue data to display on map")
            else:
                st.info("No venues found to display")
        except Exception as e:
            st.error(f"Error loading map: {str(e)}")

if __name__ == "__main__":
    main() 