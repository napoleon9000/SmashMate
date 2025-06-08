import asyncio
from datetime import datetime
from uuid import UUID

import streamlit as st

from app.core import auth, matches, recommendations, social, venues
from app.services.database import DatabaseService

# Shared database service for all operations
DB_SERVICE = DatabaseService()


def run_async(coro):
    """Run an async function synchronously."""
    return asyncio.run(coro)


st.set_page_config(page_title="SmashMate Debug", page_icon="🏸")
st.title("SmashMate Local Debug App")

page = st.sidebar.selectbox(
    "Select Tool",
    [
        "Profiles",
        "Venues",
        "Matches",
        "Social",
        "Recommendations",
    ],
)

if page == "Profiles":
    st.header("Profiles")
    tab1, tab2 = st.tabs(["Create/Get", "Update"])

    with tab1:
        st.subheader("Get or Create Profile")
        user_id = st.text_input("User ID (UUID)")
        display_name = st.text_input("Display Name", key="profile_name")
        if st.button("Submit", key="create_profile"):
            try:
                profile = run_async(
                    auth.get_or_create_profile(
                        UUID(user_id), display_name or None, database=DB_SERVICE
                    )
                )
                st.json(profile)
            except Exception as e:
                st.error(str(e))

    with tab2:
        st.subheader("Update Profile")
        user_id_upd = st.text_input("User ID (UUID)", key="update_user")
        display_name_upd = st.text_input("New Display Name", key="update_display")
        avatar_url = st.text_input("Avatar URL", key="update_avatar")
        default_venue = st.text_input("Default Venue ID (optional)", key="update_venue")
        if st.button("Update", key="update_profile_btn"):
            try:
                dv = UUID(default_venue) if default_venue else None
                profile = run_async(
                    auth.update_profile(
                        UUID(user_id_upd),
                        display_name_upd or None,
                        avatar_url or None,
                        dv,
                        database=DB_SERVICE,
                    )
                )
                st.json(profile)
            except Exception as e:
                st.error(str(e))

elif page == "Venues":
    st.header("Venues")
    tab1, tab2 = st.tabs(["Create", "Search Nearby"])

    with tab1:
        st.subheader("Create Venue")
        name = st.text_input("Name")
        lat = st.number_input("Latitude", format="%f")
        lng = st.number_input("Longitude", format="%f")
        address = st.text_input("Address")
        creator = st.text_input("Creator ID (UUID)")
        if st.button("Create Venue"):
            try:
                venue = run_async(
                    venues.create_venue(
                        name,
                        float(lat),
                        float(lng),
                        address,
                        UUID(creator),
                        database=DB_SERVICE,
                    )
                )
                st.json(venue)
            except Exception as e:
                st.error(str(e))

    with tab2:
        st.subheader("Find Nearby Venues")
        lat_q = st.number_input("Latitude", format="%f", key="search_lat")
        lng_q = st.number_input("Longitude", format="%f", key="search_lng")
        radius = st.number_input("Radius (meters)", value=5000)
        if st.button("Search Venues"):
            try:
                results = run_async(
                    venues.find_nearby_venues(
                        float(lat_q), float(lng_q), float(radius), database=DB_SERVICE
                    )
                )
                st.json(results)
            except Exception as e:
                st.error(str(e))

elif page == "Matches":
    st.header("Matches")
    with st.form("create_match"):
        st.subheader("Create Match")
        venue_id = st.text_input("Venue ID (UUID)")
        creator_id = st.text_input("Created By (UUID)")
        team1_player1 = st.text_input("Team1 Player A")
        team1_player2 = st.text_input("Team1 Player B")
        team2_player1 = st.text_input("Team2 Player A")
        team2_player2 = st.text_input("Team2 Player B")
        scores_json = st.text_area(
            "Scores JSON",
            '[{"team1":21, "team2":18}, {"team1":21, "team2":15}]',
        )
        played_at = st.datetime_input("Played At", datetime.now())
        submit = st.form_submit_button("Create")

    if submit:
        try:
            scores = eval(scores_json)
            match = run_async(
                matches.create_match(
                    UUID(venue_id),
                    UUID(creator_id),
                    (UUID(team1_player1), UUID(team1_player2)),
                    (UUID(team2_player1), UUID(team2_player2)),
                    scores,
                    played_at,
                    database=DB_SERVICE,
                )
            )
            st.json(match)
        except Exception as e:
            st.error(str(e))

elif page == "Social":
    st.header("Social")
    tab1, tab2, tab3 = st.tabs(["Follow", "Followers", "Following"])

    with tab1:
        follower = st.text_input("Follower ID", key="follow_follower")
        followee = st.text_input("Followee ID", key="follow_followee")
        if st.button("Follow"):
            try:
                result = run_async(
                    social.follow_player(
                        UUID(follower), UUID(followee), database=DB_SERVICE
                    )
                )
                st.json(result)
            except Exception as e:
                st.error(str(e))
        if st.button("Unfollow"):
            try:
                run_async(
                    social.unfollow_player(
                        UUID(follower), UUID(followee), database=DB_SERVICE
                    )
                )
                st.success("Unfollowed")
            except Exception as e:
                st.error(str(e))

    with tab2:
        uid = st.text_input("User ID", key="followers_id")
        if st.button("Get Followers"):
            try:
                followers = run_async(
                    social.get_followers(UUID(uid), database=DB_SERVICE)
                )
                st.json(followers)
            except Exception as e:
                st.error(str(e))

    with tab3:
        uid2 = st.text_input("User ID", key="following_id")
        if st.button("Get Following"):
            try:
                following = run_async(
                    social.get_following(UUID(uid2), database=DB_SERVICE)
                )
                st.json(following)
            except Exception as e:
                st.error(str(e))

elif page == "Recommendations":
    st.header("Recommendations")
    uid = st.text_input("User ID", key="rec_user")
    if st.button("Get Compatibility Scores"):
        try:
            scores = run_async(
                recommendations.get_compatibility_scores(UUID(uid), database=DB_SERVICE)
            )
            st.json(scores)
        except Exception as e:
            st.error(str(e))
    if st.button("Get Recommended Partners"):
        try:
            recs = run_async(
                recommendations.get_recommended_partners(UUID(uid), database=DB_SERVICE)
            )
            st.json(recs)
        except Exception as e:
            st.error(str(e))
