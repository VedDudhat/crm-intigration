"""
Smart Support Desk Chatbot Logic
Handles user interactions with Redis session management
"""
from backend.assistant.ai_tools import set_jwt_token
from backend.assistant.ai_agent import chain, format_agent_input,tools,llm_with_tools
from backend.assistant.conversation_memory import conversation_memory
from langchain_core.messages import HumanMessage, AIMessage,ToolMessage

class SupportDeskChatbot:
    """Main chatbot class with Redis session management and authentication"""

    def __init__(self, user_id: str, jwt_token=None):
        """
        Initialize chatbot for a user

        Args:
            user_id: User/admin ID/username from login
            jwt_token: Authentication cookies from Flask session
        """
        self.user_id = user_id
        self.session_id = None
        if jwt_token:
            set_jwt_token(jwt_token)

    def start_session(self) -> str:
        """
        Start a new chat session
        Returns session_id
        """
        self.session_id = conversation_memory.create_session(self.user_id)
        print(f"🚀 New chat session started for {self.user_id}: {self.session_id}")
        return self.session_id

    def chat(self, user_input: str) -> str:
        if not self.session_id:
            return "❌ Error: No active session. Please start a session first."

        try:
            # Get conversation history from Redis
            chat_history = conversation_memory.get_langchain_history(
                self.session_id,
                limit=20  # Last 20 messages for context
            )

            # Save user message to Redis
            conversation_memory.add_message(
                self.session_id,
                role="human",
                content=user_input
            )

            # Format input for agent
            agent_input = format_agent_input(user_input, chat_history)

            # Get response from agent
            print(f"🤖 Processing: {user_input[:50]}...")
            response = chain.invoke(agent_input)

            messages = [
                HumanMessage(content=user_input),
                response
            ]
            max_iterations = 5
            iteration = 0
            executed_calls = set()

            # Extract output
            while getattr(response, "tool_calls") and response.tool_calls and iteration < max_iterations:
                iteration+=1

                tool_map = {tool.name: tool for tool in tools}
                tool_messages = []

                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call.get("args", {})
                    tool_id = tool_call["id"]

                    signature = (tool_name, str(tool_args))

                    if signature in executed_calls:
                        print("⚠️ Duplicate tool call detected. Breaking loop.")
                        break

                    executed_calls.add(signature)

                    print(f"🛠 Executing tool: {tool_name}")
                    print(f"🛠 With args: {tool_args}")

                    if tool_name not in tool_map:
                        raise Exception(f"Tool {tool_name} not found.")

                    result = tool_map[tool_name].invoke(tool_args)

                    tool_message = ToolMessage(
                            content=str(result),
                            tool_call_id=tool_id
                    )
                    tool_messages.append(tool_message)
                    messages.append(tool_message)

                response = llm_with_tools.invoke(messages)
                print("FINAL CONTENT:", response.content)
                print("FINAL TOOL CALLS:", getattr(response, "tool_calls", None))

                messages.append(response)

            if isinstance(response.content, list):
                output = "".join(
                    block.get("text", "")
                    for block in response.content
                    if isinstance(block, dict)
                )
            else:
                output = response.content

            # Save AI response to Redis
            conversation_memory.add_message(
                self.session_id,
                role="ai",
                content=output
            )

            print(f"✅ Response generated successfully")
            return output

        except Exception as e:
            error_msg = (
                f"❌ I encountered an error while processing your request.\n\n"
                f"**Error:** {str(e)}\n\n"
                f"Please try again or rephrase your request. If the problem persists, "
                f"contact support."
            )

            # Log error
            print(f"❌ Chatbot error: {str(e)}")

            return error_msg

    def end_session(self):
        """End the current chat session (called on logout)"""
        if self.session_id:
            conversation_memory.end_session(self.session_id)
            print(f"🛑 Session ended: {self.session_id}")

    def get_session_info(self) -> dict:
        """Get current session information"""
        if self.session_id:
            return conversation_memory.get_session_info(self.session_id)
        return None

    def get_statistics(self) -> dict:
        """Get session statistics"""
        if self.session_id:
            return conversation_memory.get_session_statistics(self.session_id)
        return {}

    def clear_history(self):
        """Clear chat history for current session"""
        if self.session_id:
            conversation_memory.clear_history(self.session_id)
            return "✅ Chat history cleared!"
        return "❌ No active session."


# Helper function for testing without session management
def quick_chat(user_id: str, message: str, auth_cookies=None) -> str:
    """
    Quick chat without explicit session management
    Useful for testing

    Args:
        user_id: User identifier
        message: User's message
        auth_cookies: Authentication cookies

    Returns:
        AI response
    """
    chatbot = SupportDeskChatbot(user_id, auth_cookies)
    chatbot.start_session()
    response = chatbot.chat(message)
    chatbot.end_session()
    return response