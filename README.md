🔗 HubSpot CRM Integration Service
This project is a standalone FastAPI microservice designed to synchronize data between a local Help Desk system and HubSpot CRM. It handles the synchronization of Contacts and Tickets, ensuring that support agents and sales teams always see the same up-to-date information.

1. Which CRM I Chose & Why
I chose HubSpot CRM for this integration.

Why HubSpot?
Developer-Friendly API: HubSpot offers a robust, well-documented REST API (v3) with clear endpoints for standard objects like Contacts and Tickets.
Free Tier Access: The CRM functionality is available for free, making it ideal for development and testing without incurring costs.
Scalability: It supports custom properties and high API rate limits, which mimics a real-world enterprise environment.
Comprehensive Ecosystem: It includes built-in tools for email tracking, ticketing pipelines, and customer management, providing a complete "backend" for a support desk.

2. Configuration & Setup
Prerequisites
Python 3.9+

A HubSpot Developer Account (or a standard account with a Private App created)

pip (Python Package Manager)

Installation
Clone the Repository:

Bash
git clone <your-repo-url>
cd CRM-integration
Create a Virtual Environment:

Bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
Install Dependencies:

Bash
pip install -r requirements.txt
Setting up Credentials
Create a file named .env in the root directory.

Add your HubSpot Private App Access Token:

Code snippet
HUBSPOT_ACCESS_TOKEN=pat-na1-blablabla...
HUBSPOT_BASE_URL=https://api.hubapi.com
To get your token: Go to HubSpot Settings > Integrations > Private Apps > Create a Private App.

# Scopes required:

crm.objects.contacts.read

crm.objects.contacts.write

crm.objects.tickets.read

crm.objects.tickets.write

# How to Run the Sync & What to Expect
This service acts as a bridge. It does not run a continuous background loop; instead, it provides REST API endpoints that the main Support Desk application calls whenever data needs to be synced.
Start the Server
#Run the FastAPI server using Uvicorn:
uvicorn main:app --reload --port 8000
The API will be available at: http://localhost:8000
Interactive API Docs (Swagger UI): http://localhost:8000/docs
Action,API Endpoint,Behavior
Create Contact,POST /integrate/contact,"Creates a contact in HubSpot. If the email already exists, it returns the existing HubSpot ID to prevent duplicates."
Get Contact,GET /integrate/contact/{email},"Fetches contact details (ID, Name, Company) from HubSpot using the email address."
Create Ticket,POST /integrate/ticket,Creates a ticket in HubSpot and automatically associates it with the correct Contact ID.
Update Ticket,PATCH /integrate/ticket/{id},"Updates ticket status, priority, or description in HubSpot when changed in the local app."

Testing the Sync Manually
You can test the synchronization without the main app by using curl or Postman:

# Sync a New Ticket
curl -X 'POST' \
  'http://localhost:8000/integrate/ticket' \
  -H 'Content-Type: application/json' \
  -d '{
  "title": "Login Issue",
  "description": "User cannot reset password",
  "priority": "HIGH",
  "email": "customer@example.com"
}'

# Expected Output:
{
  "hubspot_ticket_id": "123456789",
  "status": "created",
  "link": "https://app.hubspot.com/contacts/..."
}

# Project Structure
CRM-integration/
├── main.py              # Entry point for FastAPI application
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (GitIgnored)
└── routes/
    ├── contacts.py      # Endpoints for syncing Customer data
    └── tickets.py       # Endpoints for syncing Support Tickets

# Key Functionalities
Contact Resolution: Automatically checks if a contact exists in HubSpot before creating a ticket. If not, it creates the contact first.

Ticket Association: Links every support ticket to the correct customer record in HubSpot, maintaining a clean history of interactions.

Real-time Updates: Changes made to ticket status or priority are pushed immediately to HubSpot via the PATCH endpoint.

Error Handling: Gracefully handles API rate limits and "Contact Not Found" errors, returning meaningful messages to the client.

