"""
Social page for SmashMate - Messaging, following, and friend network.
"""

import streamlit as st
import sys
from pathlib import Path
from uuid import UUID

# Add parent directory to path to import shared utilities
sys.path.append(str(Path(__file__).parent.parent))

from app.streamlit.shared  import setup_page, get_user_id, run_async, DB_SERVICE
from app.core import social

# Page setup
setup_page("Social Hub", "👥")

def main():
    """Social features: messaging, following, group chats."""
    st.title("👥 Social Hub")
    
    user_id = get_user_id()
    
    tab1, tab2, tab3 = st.tabs(["💬 Messages", "👥 Friends", "💌 Group Chats"])
    
    with tab1:
        st.subheader("Direct Messages")
        
        # Get following list for messaging
        try:
            following = run_async(social.get_following(user_id, database=DB_SERVICE))
            
            if following:
                # Select recipient
                recipient_options = {f"{f['display_name']} ({f['user_id'][:8]}...)": f['user_id'] for f in following}
                recipient_name = st.selectbox("Send message to:", list(recipient_options.keys()))
                
                if recipient_name:
                    recipient_id = UUID(recipient_options[recipient_name])
                    
                    # Message input
                    message_text = st.text_area("Your message:")
                    if st.button("Send Message"):
                        try:
                            run_async(DB_SERVICE.send_message(user_id, recipient_id, message_text))
                            st.success("Message sent!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to send message: {str(e)}")
                    
                    # Show conversation
                    st.subheader(f"Conversation with {recipient_name}")
                    try:
                        messages = run_async(DB_SERVICE.get_messages(user_id, recipient_id))
                        for msg in messages[-10:]:  # Show last 10 messages
                            sender = "You" if msg['sender_id'] == str(user_id) else recipient_name.split(' (')[0]
                            st.write(f"**{sender}:** {msg['content']}")
                            st.caption(msg['created_at'])
                    except Exception as e:
                        st.error(f"Error loading messages: {str(e)}")
            else:
                st.info("Follow some players first to start messaging!")
        except Exception as e:
            st.error(f"Error loading social data: {str(e)}")
    
    with tab2:
        st.subheader("Friend Network")
        
        # All Users Section - Enhanced section
        st.markdown("### 🌟 Discover Players")
        
        try:
            # Get all users from demo users (since those are the ones we created)
            if st.session_state.demo_users:
                # Get current user's following and mutual friends
                following = run_async(social.get_following(user_id, database=DB_SERVICE))
                followers = run_async(social.get_followers(user_id, database=DB_SERVICE))
                mutual = run_async(social.get_mutual_followers(user_id, database=DB_SERVICE))
                
                # Create sets for quick lookup
                following_ids = {f['followee'] if 'followee' in f else f['user_id'] for f in following}
                follower_ids = {f['follower'] if 'follower' in f else f['user_id'] for f in followers}
                mutual_ids = {m['user_id'] for m in mutual}
                
                st.markdown("Click to follow players:")
                
                for name, user_data in st.session_state.demo_users.items():
                    # Skip current user
                    if user_data["id"] == str(user_id):
                        continue
                    
                    # Determine status and emoji
                    user_uuid = user_data["id"]
                    is_following = user_uuid in following_ids
                    is_follower = user_uuid in follower_ids
                    is_mutual = user_uuid in mutual_ids
                    
                    # Choose emoji and status
                    if is_mutual:
                        emoji = "🤝"
                        status = "Mutual Friends"
                        button_text = "Unfollow"
                        button_type = "unfollow"
                    elif is_following:
                        emoji = "➡️"
                        status = "Following"
                        button_text = "Unfollow"
                        button_type = "unfollow"
                    elif is_follower:
                        emoji = "⬅️"
                        status = "Follows You"
                        button_text = "Follow Back"
                        button_type = "follow"
                    else:
                        emoji = "👤"
                        status = ""
                        button_text = "Follow"
                        button_type = "follow"
                    
                    # Display user row
                    col1, col2, col3 = st.columns([1, 3, 2])
                    
                    with col1:
                        st.write(f"{emoji}")
                    
                    with col2:
                        st.write(f"**{name}**")
                        if status:
                            st.caption(status)
                        else:
                            st.caption(user_data["desc"])
                    
                    with col3:
                        if st.button(button_text, key=f"btn_{user_uuid}", type="primary" if button_type == "follow" else "secondary"):
                            try:
                                if button_type == "follow":
                                    run_async(social.follow_player(user_id, UUID(user_uuid), database=DB_SERVICE))
                                    st.success(f"Now following {name}!")
                                else:
                                    run_async(social.unfollow_player(user_id, UUID(user_uuid), database=DB_SERVICE))
                                    st.success(f"Unfollowed {name}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Action failed: {str(e)}")
                
                st.markdown("---")
        
        except Exception as e:
            st.error(f"Error loading users: {str(e)}")
        
        # Existing sections - made more compact
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 👥 Your Followers")
            try:
                followers = run_async(social.get_followers(user_id, database=DB_SERVICE))
                if followers:
                    for follower in followers:
                        # Try to get display name from demo users
                        display_name = "Unknown User"
                        if st.session_state.demo_users:
                            for name, user_data in st.session_state.demo_users.items():
                                if user_data["id"] == follower.get('follower', follower.get('user_id')):
                                    display_name = name
                                    break
                        st.write(f"👤 {display_name}")
                else:
                    st.info("No followers yet")
            except Exception as e:
                st.error(f"Error loading followers: {str(e)}")
        
        with col2:
            st.markdown("### 💫 You're Following")
            try:
                following = run_async(social.get_following(user_id, database=DB_SERVICE))
                if following:
                    for friend in following:
                        # Try to get display name from demo users
                        display_name = "Unknown User"
                        if st.session_state.demo_users:
                            for name, user_data in st.session_state.demo_users.items():
                                if user_data["id"] == friend.get('followee', friend.get('user_id')):
                                    display_name = name
                                    break
                        st.write(f"➡️ {display_name}")
                else:
                    st.info("Not following anyone yet")
            except Exception as e:
                st.error(f"Error loading following: {str(e)}")
        
        # Mutual followers section
        st.markdown("### 🤝 Mutual Friends")
        try:
            mutual = run_async(social.get_mutual_followers(user_id, database=DB_SERVICE))
            if mutual:
                mutual_names = []
                for friend in mutual:
                    # Try to get display name from demo users
                    display_name = "Unknown User"
                    if st.session_state.demo_users:
                        for name, user_data in st.session_state.demo_users.items():
                            if user_data["id"] == friend['user_id']:
                                display_name = name
                                break
                    mutual_names.append(display_name)
                
                if mutual_names:
                    st.write("🤝 " + ", ".join(mutual_names))
                else:
                    st.info("No mutual friends yet")
            else:
                st.info("No mutual friends yet")
        except Exception as e:
            st.error(f"Error loading mutual friends: {str(e)}")
    
    with tab3:
        st.subheader("Group Chats")
        
        # Create new group
        with st.expander("Create New Group"):
            group_name = st.text_input("Group Name:")
            if st.button("Create Group"):
                try:
                    group = run_async(DB_SERVICE.create_group(group_name, user_id))
                    st.success(f"Created group: {group_name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to create group: {str(e)}")
        
        st.info("Group messaging features coming soon!")

if __name__ == "__main__":
    main() 