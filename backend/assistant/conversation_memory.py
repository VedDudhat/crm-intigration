"""
Redis Conversation Memory Manager
Stores and retrieves chat history per user session
"""

import redis
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from langchain_core.messages import HumanMessage, AIMessage


class ConversationMemory:
    """Manages conversation history in Redis with session tracking"""

    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=0,
            decode_responses=True
        )
        self.session_prefix = "chat:session:"
        self.history_prefix = "chat:history:"

    def create_session(self, user_id: str) -> str:
        """
        Create a new chat session for user
        Returns session_id
        """
        timestamp = int(datetime.now().timestamp())
        session_id = f"{user_id}_{timestamp}"
        key = f"{self.session_prefix}{session_id}"

        session_data = {
            "user_id": user_id,
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "message_count": 0,
            "status": "active"
        }

        self.redis_client.set(key, json.dumps(session_data))
        print(f"✅ Session created: {session_id}")
        return session_id

    def add_message(
            self,
            session_id: str,
            role: str,
            content: str
    ) -> bool:
        """
        Add a message to conversation history
        role: "human" or "ai"
        """

        history_key = f"{self.history_prefix}{session_id}"

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }

        # Add to list (Redis list for ordered messages)
        self.redis_client.rpush(history_key, json.dumps(message))

        # Update session metadata
        session_key = f"{self.session_prefix}{session_id}"
        session_data = self.redis_client.get(session_key)

        if session_data:
            session_dict = json.loads(session_data)
            session_dict["message_count"] = session_dict.get("message_count", 0) + 1
            session_dict["last_activity"] = datetime.now().isoformat()
            self.redis_client.set(session_key, json.dumps(session_dict))
            return True

        return False

    def get_history(
            self,
            session_id: str,
            limit: int = 20
    ) -> List[Dict]:
        """
        Get conversation history for a session
        Returns last N messages
        """
        history_key = f"{self.history_prefix}{session_id}"

        # Get all messages
        messages = self.redis_client.lrange(history_key, 0, -1)

        # Parse JSON
        parsed_messages = []
        for msg in messages:
            try:
                parsed_messages.append(json.loads(msg))
            except json.JSONDecodeError:
                continue

        # Return last N messages
        return parsed_messages[-limit:] if len(parsed_messages) > limit else parsed_messages

    def get_langchain_history(
            self,
            session_id: str,
            limit: int = 20
    ) -> List:
        """
        Get history in LangChain message format
        Returns list of HumanMessage and AIMessage objects
        """
        messages = self.get_history(session_id, limit)

        langchain_messages = []
        for msg in messages:
            if msg["role"] == "human":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "ai":
                langchain_messages.append(AIMessage(content=msg["content"]))

        return langchain_messages

    def end_session(self, session_id: str) -> bool:
        """Mark session as ended (on logout)"""
        session_key = f"{self.session_prefix}{session_id}"
        session_data = self.redis_client.get(session_key)

        if session_data:
            session_dict = json.loads(session_data)
            session_dict["ended_at"] = datetime.now().isoformat()
            session_dict["status"] = "ended"
            self.redis_client.set(session_key, json.dumps(session_dict))
            print(f"✅ Session ended: {session_id}")
            return True

        return False

    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get session metadata"""
        session_key = f"{self.session_prefix}{session_id}"
        session_data = self.redis_client.get(session_key)

        if session_data:
            return json.loads(session_data)
        return None

    def clear_history(self, session_id: str) -> bool:
        """Clear conversation history for a session"""
        history_key = f"{self.history_prefix}{session_id}"
        self.redis_client.delete(history_key)

        # Reset message count in session
        session_key = f"{self.session_prefix}{session_id}"
        session_data = self.redis_client.get(session_key)

        if session_data:
            session_dict = json.loads(session_data)
            session_dict["message_count"] = 0
            self.redis_client.set(session_key, json.dumps(session_dict))
            return True

        return False

    def get_user_sessions(self, user_id: str) -> List[Dict]:
        """Get all sessions for a user"""
        pattern = f"{self.session_prefix}{user_id}_*"

        sessions = []
        for key in self.redis_client.scan_iter(match=pattern):
            session_data = self.redis_client.get(key)
            if session_data:
                sessions.append(json.loads(session_data))

        # Sort by created_at descending
        sessions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return sessions

    def get_session_statistics(self, session_id: str) -> Dict:
        """Get statistics for a session"""
        session_info = self.get_session_info(session_id)
        if not session_info:
            return {}

        history = self.get_history(session_id)

        human_messages = sum(1 for m in history if m['role'] == 'human')
        ai_messages = sum(1 for m in history if m['role'] == 'ai')

        return {
            "session_id": session_id,
            "user_id": session_info.get("user_id"),
            "status": session_info.get("status"),
            "created_at": session_info.get("created_at"),
            "ended_at": session_info.get("ended_at"),
            "total_messages": len(history),
            "human_messages": human_messages,
            "ai_messages": ai_messages,
            "last_activity": session_info.get("last_activity")
        }

    def ping(self) -> bool:
        """Check if Redis is connected"""
        try:
            self.redis_client.ping()
            return True
        except:
            return False


# Global instance
conversation_memory = ConversationMemory()