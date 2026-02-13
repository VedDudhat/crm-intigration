"""
Streamlit Chatbot Interface for Smart Support Desk
Integrates with existing Streamlit app and Flask backend
"""
import requests
import streamlit as st
import sys
import os

from backend.assistant.config import FLASK_BACKEND_URL

# Add parent directory to path to import from backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.assistant.logic import SupportDeskChatbot
from backend.assistant.conversation_memory import conversation_memory

FLASK_URL = "http://127.0.0.1:5000"

def login_page():
    st.title("🔐 Login to Smart Support Desk")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        try:
            response = requests.post(
                f"{FLASK_BACKEND_URL}/api/login",
                json={"username": username, "password": password}
            )

            if response.status_code == 200:
                data = response.json()
                st.session_state.user = username
                st.session_state.jwt_token = data.get('access_token')
                st.success("✅ Login successful")
                st.rerun()
            else:
                st.error("❌ Invalid credentials")

        except Exception as e:
            st.error(f"Error connecting to backend: {str(e)}")

def get_auth_cookies():
    """
    Get authentication cookies from Streamlit session
    Alternative to importing from api_client
    """
    # Method 1: If you have requests_session in st.session_state
    if 'requests_session' in st.session_state and st.session_state.requests_session:
        return st.session_state.requests_session.cookies.get_dict()

    # Method 2: If you have cookies stored directly
    if 'auth_cookies' in st.session_state:
        return st.session_state.auth_cookies

    # Method 3: Return None and let tools handle it
    return None


def chatbot_interface():
    """
    Render the AI chatbot interface in Streamlit
    Must be called after user login
    """

    # Check if user is logged in
    if 'user' not in st.session_state or not st.session_state.user:
        st.error("⚠️ Please log in to access the AI Assistant")
        st.info("Use the login page to authenticate first.")
        return

    st.title("AI Support Assistant")
    st.markdown("*Specialized AI for ticket management and customer operations*")

    # Get user ID from session
    user_id = st.session_state.get('user', 'unknown')

    # Initialize chatbot in session state
    if 'chatbot' not in st.session_state:
        token = st.session_state.get('jwt_token')

        st.session_state.chatbot = SupportDeskChatbot(user_id, token)

        # Start session
        session_id = st.session_state.chatbot.start_session()
        st.session_state.chat_session_id = session_id

    # Initialize messages in session state
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": (
                    "👋 **Hello! I'm your AI Support Assistant.**\n\n"
                    "I specialize in helping you manage support tickets and customers.\n\n"
                    "**What I can help you with:**\n"
                    "- 🎫 **Create tickets** - I'll ask for title, description, priority, and customer email\n"
                    "- 📋 **View tickets** - Show all tickets or filter by status/priority\n"
                    "- 🔍 **Search tickets** - Find tickets by customer email\n"
                    "- ✏️ **Update tickets** - Change status, priority, or details\n"
                    "- 👤 **Manage customers** - Create new customers or view existing ones\n\n"
                    "**Important:** I only answer questions related to ticketing and customer management. "
                    "For other queries, I'll politely redirect you.\n\n"
                    "**How can I help you today?**"
                )
            }
        ]

    # Display chat messages
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Type your message here...", key="assistant_chat_input"):
        # Add user message to chat
        st.session_state.chat_messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # Get bot response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                # Run async function
                response = st.session_state.chatbot.chat(prompt)

                st.markdown(response)

        # Add assistant response to chat
        st.session_state.chat_messages.append({"role": "assistant", "content": response})

    # Sidebar with chat controls
    with st.sidebar:
        st.subheader("💬 Chat Controls")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔄 New Chat", use_container_width=True):
                st.session_state.chatbot.end_session()
                new_session_id = st.session_state.chatbot.start_session()
                st.session_state.chat_session_id = new_session_id

                st.session_state.chat_messages = [
                    {
                        "role": "assistant",
                        "content": "✅ **New chat started!**\n\nHow can I help you?"
                    }
                ]
                st.rerun()

        with col2:
            if st.button("🗑️ Clear", use_container_width=True):
                # Clear UI but keep session
                st.session_state.chat_messages = [
                    {
                        "role": "assistant",
                        "content": "✅ **Chat cleared!**\n\nHow can I help you?"
                    }
                ]
                st.rerun()

        # Session info
        if st.session_state.get('chat_session_id'):
            with st.expander("📊 Session Info"):

                try:
                    stats = st.session_state.chatbot.get_statistics()

                    if stats:
                        st.write(f"**User:** {stats.get('user_id', 'N/A')}")
                        st.write(f"**Session ID:** {str(stats.get('session_id', ''))[:20]}...")
                        st.write(f"**Status:** {stats.get('status', 'N/A')}")
                        st.write(f"**Messages:** {stats.get('total_messages', 0)}")
                        st.write(f"**Started:** {str(stats.get('created_at', 'N/A'))[:19]}")

                        if stats.get('last_activity'):
                            st.write(f"**Last Activity:** {str(stats.get('last_activity'))[:19]}")

                except Exception as e:
                    st.error(f"Error loading stats: {e}")

        st.markdown("---")

        if st.button("🚪 Logout", use_container_width=True):
            try:
                # End chatbot session
                st.session_state.chatbot.end_session()
            except:
                pass

            # Cleanup chatbot session memory
            cleanup_chatbot_session()

            # Clear authentication session
            if "auth_session" in st.session_state:
                del st.session_state.auth_session

            if "user" in st.session_state:
                del st.session_state.user

            st.success("✅ Logged out successfully")
            st.rerun()


        st.subheader("💡 Quick Examples")

        with st.expander("Creating Tickets"):
            st.markdown("""
            - "Create a ticket for login issue"
            - "I need to report a bug"
            - "Open a new ticket"
            - "Create high priority ticket for john@example.com"
            """)

        with st.expander("Viewing Tickets"):
            st.markdown("""
            - "Show me all tickets"
            - "View open tickets"
            - "List high priority tickets"
            - "Show closed tickets"
            """)

        with st.expander("Searching Tickets"):
            st.markdown("""
            - "Find tickets for john@example.com"
            - "Show all tickets of alice@company.com"
            - "Get tickets assigned to bob@test.com"
            """)

        with st.expander("Updating Tickets"):
            st.markdown("""
            - "Close ticket #5"
            - "Mark ticket 3 as in progress"
            - "Change ticket #7 priority to high"
            - "Update ticket 2 status to closed"
            """)

        with st.expander("Managing Customers"):
            st.markdown("""
            - "Create a customer"
            - "Add customer John Doe"
            - "Show all customers"
            - "List customer database"
            """)

        st.markdown("---")

        st.subheader("⚠️ Important Notes")
        st.info(
            "**Scope:** This AI assistant is specialized in ticketing operations only. "
            "It will politely decline off-topic questions like weather, jokes, general knowledge, etc."
        )

        st.warning(
            "**Customer Email:** When creating tickets, the customer must exist in the system. "
            "If not, the bot will guide you to create the customer first."
        )


def cleanup_chatbot_session():
    """
    Call this when user logs out
    Ends the chat session and saves to Redis
    """

    if 'chatbot' in st.session_state:
        try:
            st.session_state.chatbot.end_session()
            print("✅ Chatbot session cleaned up on logout")
        except Exception as e:
            print(f"⚠️ Error cleaning up chatbot session: {e}")


        if 'chatbot' in st.session_state:
            del st.session_state.chatbot
        if 'chat_messages' in st.session_state:
            del st.session_state.chat_messages
        if 'chat_session_id' in st.session_state:
            del st.session_state.chat_session_id


def add_chatbot_to_navigation():
    """
    Helper function to add chatbot button to sidebar navigation
    Call this in your main streamlit_ui.py
    """

    if st.sidebar.button("🤖 AI Assistant", use_container_width=True, key="nav_chatbot"):
        st.session_state.current_view = "chatbot"
        st.rerun()


# For testing standalone
if __name__ == "__main__":
    st.set_page_config(page_title="AI Support Assistant")

    if 'user' not in st.session_state:
        login_page()
    else:
        chatbot_interface()