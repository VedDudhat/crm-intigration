# Smart AI Support Assistant
The Smart AI Support Assistant is an intelligent conversational agent designed to automate ticket operations for the Smart Support Desk. Powered by Large Language Models (LLMs) and LangChain, it acts as a "Tier 1" support agent that can understand natural language requests and execute real actions in the database.

# 1. What The Assistant Can Do
This assistant is specialized for Ticket Operations. It is not a general-purpose chatbot; it is a functional tool that can:
 #Create Tickets: Extracts details (Title, Priority, Description) from user chat and creates a valid ticket in the system.
Example: "My internet is down, please mark this as High priority."
# Check Ticket Status: Looks up existing tickets by ID or email to provide real-time status updates.
Example: "What is the status of ticket #102?"
# Update Tickets: Modifies ticket details such as Status (Open/Closed) or Priority based on user commands.
Example: "Change the priority of ticket #45 to Low."
# Validate Customers: Ensures a ticket is always linked to a valid customer email before creation.
Search History: Can search for past tickets raised by a specific customer.

# How It Interacts with Projects 1 and 2
This AI service sits in the middle of your architecture:

# Interacts with Smart Support Desk (Project 1):

The AI uses Tools (Python functions) that directly call the Support Desk API or Database.
When the AI says "I have created the ticket," it has actually executed a function that inserted a row into the Support Desk MySQL database.

# Interacts with HubSpot CRM (Project 2):

When the AI creates or updates a ticket in the Support Desk, the Support Desk automatically triggers a sync to the HubSpot Integration Service.
This ensures that any action taken by the AI is instantly reflected in both the local dashboard and the HubSpot CRM.

# How to Configure LLM Credentials (Securely)
Security Warning: Never hardcode your API keys (e.g., OpenAI, Anthropic, Gemini) directly into the Python code. This project uses environment variables to keep secrets safe.

# Step 1: Create a .env file
In the root directory of this project (where main.py is), create a file named .env.

# Step 2: Add Your Keys
Add your specific LLM provider's API key. This project supports standard providers via LangChain.

# For OpenAI (GPT-3.5/4)
OPENAI_API_KEY=sk-proj-123456789...

# For Google Gemini
GOOGLE_API_KEY=AIzaSyD...

# For Anthropic (Claude)
ANTHROPIC_API_KEY=sk-ant-...

# Step 3: Verify Configuration
The application automatically loads these keys using python-dotenv. You do not need to change any code.

# 4. How to Run the Assistant
Prerequisites
Python 3.10+
An active API Key (OpenAI/Google/Anthropic)
Project 1 (Support Desk) must be running for database access.

# installation
# 1. Install Dependencies:
pip install -r requirements.txt

# Project Structure
ai-assistant/
├── backend/
│   ├── assistant/
│   │   ├── ai_tools.py      # Defines tools (CreateTicket, ViewTicket)
│   │   ├── logic.py         # Main Agent Logic (Prompt + LLM Binding)
│   │   └── __init__.py
├── requirements.txt         # Dependencies (langchain, openai, etc.)
└── .env                     # API Keys (Do NOT commit this file)
