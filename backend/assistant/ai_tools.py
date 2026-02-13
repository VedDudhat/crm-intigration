from typing import Type, Optional, Any
import pandas as pd
from backend.assistant.config import FLASK_BACKEND_URL
import requests
from pydantic import BaseModel, EmailStr
from langchain_core.tools import BaseTool
from backend.schemas.ai_assistant import CreateTicket,ViewTicket,SearchTicket,UpdateTicket,CreateCustomer,ViewCustomer

_JWT_TOKEN = None

def set_jwt_token(token): # Renamed
    global _JWT_TOKEN
    _JWT_TOKEN = token

def get_auth_headers(): # Helper function
    if _JWT_TOKEN:
        return {"Authorization": f"Bearer {_JWT_TOKEN}"}
    return {}

class create_ticket(BaseTool):
    """ Create ticket """
    name: str = "create_ticket"
    description: str = """use this tool when user wants to
    Required information:
    - title: Brief summary of the issue
    - description: Detailed explanation of the problem
    - priority: Must be one of: Low, Medium, High
    - email: Customer's email address to assign the ticket
    
    IMPORTANT: 
    - If customer email is not provided, ask for it before calling this tool
    - If customer doesn't exist, first tell user to create the customer with the given email
    
    Examples of when to use:
    - "Create a ticket for login issue"
    - "I need to report a bug"
    - "Open a new ticket"
    """
    args_schema: Type[BaseModel] = CreateTicket
    def _run(self, title:str, description:str, priority:str, email:EmailStr) -> str:
        from backend.assistant.config import FLASK_BACKEND_URL
        try:
            customer_response=requests.get(
                f"{FLASK_BACKEND_URL}/api/view_customers",
                timeout=10,
            )
            if customer_response.status_code != 200:
                return f"❌ Error: Unable to fetch customers. Status: {customer_response.status_code}"

            customers = customer_response.json()
            customer = next((c for c in customers if c['email'] == email), None)

            if not customer:
                return (
                    f"❌ **Customer Not Found**\n\n"
                    f"No customer with email `{email}` exists in the system.\n\n"
                    f"**Options:**\n"
                    f"1. Verify the email address is correct\n"
                    f"2. Create a new customer first (ask me to create a customer)\n"
                    f"3. Use a different customer email"
                )

            payload = {
                "title": title,
                "description": description,
                "priority": priority,
                "customer_id": customer['id']
            }

            response = requests.post(
                f"{FLASK_BACKEND_URL}/api/add_tickets",
                json=payload,
                headers=get_auth_headers(),
                timeout=10
            )

            if response.status_code == 201:
                data = response.json()

                customer_name = f"{customer.get('firstname', '')} {customer.get('lastname', '')}".strip()

                result = (
                    f"✅ **Ticket Created Successfully!**\n\n"
                    f"**Ticket Details:**\n"
                    f"- **Ticket ID:** #{data.get('ticket_id')}\n"
                    f"- **Title:** {title}\n"
                    f"- **Priority:** {priority}\n"
                    f"- **Status:** Open\n"
                    f"- **Assigned to:** {customer_name} ({email})\n"
                )

                if data.get('saved_to_hubspot'):
                    result += f"\n**HubSpot Integration:**\n"
                    result += f"- HubSpot Ticket ID: {data.get('hubspot_ticket_id')}\n"
                    if data.get('linked_to_contact'):
                        result += f"- ✅ Successfully linked to HubSpot contact\n"
                    else:
                        result += f"- ⚠️ Created but not linked to contact\n"

                result += (f"\n📧 The customer will be notified about this ticket.\n\n"
                          f"✅ TASK COMPLETE. No further action required.")
                return result
            else:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                error = error_data.get('error', f'HTTP {response.status_code}')
                return f"❌ Failed to create ticket: {error}"

        except requests.exceptions.ConnectionError:
            return "❌ Cannot connect to backend server. Please ensure Flask is running on port 5000."

        except Exception as e:
            return f"❌ Error creating ticket: {str(e)}"


class view_tickets(BaseTool):
    """Tool for viewing tickets with filters"""

    name: str = "view_tickets"
    description: str = """Use this tool to view support tickets with optional filters.

    Optional filters:
    - status: Filter by status (Open, In Progress, or Closed)
    - priority: Filter by priority (Low, Medium, or High)

    If no filters provided, shows all tickets.

    Examples:
    - "Show me all tickets"
    - "View open tickets"
    - "Show high priority tickets"
    - "List closed tickets with medium priority"

    Returns first 5 matching tickets in a formatted table.
    """
    args_schema: Type[BaseModel] = ViewTicket

    def _run(self, status: Optional[str] = None, priority: Optional[str] = None) -> str | dict[
        str, str | int | None | list[Any]]:
        """View tickets with optional filters"""

        try:
            params = {}
            if status:
                params['status'] = status
            if priority:
                params['priority'] = priority

            response = requests.get(
                f"{FLASK_BACKEND_URL}/api/view_tickets",
                params=params,
                headers=get_auth_headers(),
                timeout=10
            )

            if response.status_code == 200:
                tickets = response.json()

                if not tickets:
                    filter_desc = []
                    if status:
                        filter_desc.append(f"status '{status}'")
                    if priority:
                        filter_desc.append(f"priority '{priority}'")

                    filter_str = " and ".join(filter_desc) if filter_desc else ""
                    return f"📋 No tickets found{' with ' + filter_str if filter_str else ''}."


                # Prepare table data
                display_tickets = tickets[:5]

                table_data = []
                for t in display_tickets:
                    table_data.append({
                        "ID": t["id"],
                        "Title": t["title"],
                        "Status": t["status"],
                        "Priority": t["priority"],
                        "Customer": t.get("customer_name", "N/A")
                    })

                return {
                    "type": "tickets",
                    "count": len(tickets),
                    "status": status,
                    "priority": priority,
                    "data": table_data
                }
            elif response.status_code == 401:
                return "❌ Authentication required. Please ensure you're logged in."
            else:
                return f"❌ Failed to retrieve tickets. Status: {response.status_code}"

        except requests.exceptions.ConnectionError:
            return "❌ Cannot connect to backend server."
        except Exception as e:
            return f"❌ Error viewing tickets: {str(e)}"


class search_tickets_by_email(BaseTool):
    """Tool for searching tickets by customer email"""

    name: str = "search_tickets_by_email"
    description: str = """Use this tool to find all tickets assigned to a specific customer by their email address.

    Required: email address

    Examples:
    - "Show tickets for johndoe@example.com"
    - "Find all tickets assigned to alice@company.com"
    - "Get John Doe's tickets" (if you know their email)
    - "Show me all open tickets of johndoe@example.com"
    """
    args_schema: Type[BaseModel] = SearchTicket

    def _run(self, email: EmailStr) -> str | dict[str, str | int | list[Any] | Any]:
        """Search tickets by customer email"""

        try:
            # Get all tickets
            response = requests.get(
                f"{FLASK_BACKEND_URL}/api/view_tickets",
                headers=get_auth_headers(),
                timeout=10
            )

            if response.status_code == 200:
                all_tickets = response.json()

                # Filter by email
                customer_tickets = [t for t in all_tickets if t.get('customer_email') == email]

                if not customer_tickets:
                    return (
                        f"📋 **No tickets found for:** {email}\n\n"
                        f"**Possible reasons:**\n"
                        f"- The customer has no tickets yet\n"
                        f"- The email address is incorrect\n"
                        f"- The customer doesn't exist in the system"
                    )

                # Group by status
                open_tickets = [t for t in customer_tickets if t['status'] == 'Open']
                in_progress = [t for t in customer_tickets if t['status'] == 'In Progress']
                closed_tickets = [t for t in customer_tickets if t['status'] == 'Closed']

                # Prepare table for first 5
                display_tickets = customer_tickets[:5]
                table_data = []
                for t in display_tickets:
                    table_data.append({
                        "ID": t["id"],
                        "Title": t["title"],
                        "Status": t["status"],
                        "Priority": t["priority"],
                        "Customer": t.get("customer_name", "N/A")
                    })

                return {
                    "type": "tickets_by_email",
                    "email": email,
                    "summary": {
                        "total": len(customer_tickets),
                        "open": len(open_tickets),
                        "in_progress": len(in_progress),
                        "closed": len(closed_tickets)
                    },
                    "data": table_data
                }
            else:
                return "❌ Failed to retrieve tickets."

        except Exception as e:
            return f"❌ Error searching tickets: {str(e)}"


class update_ticket(BaseTool):
    """Tool for updating ticket details"""

    name: str = "update_ticket"
    description: str = """Use this tool to update ticket information.

    Required: ticket_id (the ticket number, e.g., 5 for ticket #5)
    Optional updates (provide at least one):
    - status: New status (Open, In Progress, or Closed)
    - priority: New priority (Low, Medium, or High)
    - title: Updated title
    - description: Updated description

    Examples:
    - "Close ticket #5"
    - "Mark ticket 3 as in progress"
    - "Change ticket #7 priority to high"
    - "Update ticket 2 status to closed and priority to low"
    """
    args_schema: Type[BaseModel] = UpdateTicket

    def _run(
            self,
            ticket_id: int,
            status: Optional[str] = None,
            priority: Optional[str] = None,
            title: Optional[str] = None,
            description: Optional[str] = None
    ) -> str:
        """Update ticket details"""

        try:
            payload = {}
            updates = []

            if status:
                payload['status'] = status
                updates.append(f"Status → {status}")
            if priority:
                payload['priority'] = priority
                updates.append(f"Priority → {priority}")
            if title:
                payload['title'] = title
                updates.append("Title updated")
            if description:
                payload['description'] = description
                updates.append("Description updated")

            if not payload:
                return "⚠️ No updates specified. Please provide at least one field to update (status, priority, title, or description)."

            response = requests.put(
                f"{FLASK_BACKEND_URL}/api/tickets/{ticket_id}",
                json=payload,
                headers=get_auth_headers(),
                timeout=10
            )

            if response.status_code == 200:
                result = (
                    f"✅ **Ticket #{ticket_id} Updated Successfully!**\n\n"
                    f"**Changes Made:**\n"
                )
                for update in updates:
                    result += f"- {update}\n"

                result += f"\n_Ticket has been updated in both local database and HubSpot CRM._"
                return result
            elif response.status_code == 404:
                return f"❌ Ticket #{ticket_id} not found. Please verify the ticket ID."
            else:
                return f"❌ Failed to update ticket. Status: {response.status_code}"

        except Exception as e:
            return f"❌ Error updating ticket: {str(e)}"


class create_customer(BaseTool):
    """Tool for creating new customers"""

    name: str = "create_customer"
    description: str = """Use this tool to create a new customer in the system.

    Required information:
    - firstname: Customer's first name
    - email: Customer's email address
    - company: Company name

    Optional:
    - lastname: Customer's last name
    - phone: Phone number

    Examples:
    - "Create a customer for John Doe at Acme Corp"
    - "Add customer john@example.com from Tech Inc"
    - "Register new customer"

    This also creates a contact in HubSpot CRM automatically.
    """
    args_schema: Type[BaseModel] = CreateCustomer

    def _run(
            self,
            firstname: str,
            email: EmailStr,
            company: str,
            lastname: Optional[str] = None,
            phone: Optional[str] = None
    ) -> str:
        """Create a new customer"""

        try:
            payload = {
                "firstname": firstname,
                "lastname": lastname or "",
                "email": email,
                "company": company,
                "phone": phone
            }

            response = requests.post(
                f"{FLASK_BACKEND_URL}/api/add_customers",
                json=payload,
                headers=get_auth_headers(),
                timeout=10
            )

            if response.status_code == 201:
                data = response.json()

                full_name = f"{firstname} {lastname}" if lastname else firstname

                result = (
                    f"✅ **Customer Created Successfully!**\n\n"
                    f"**Customer Details:**\n"
                    f"- **Name:** {full_name}\n"
                    f"- **Email:** {email}\n"
                    f"- **Company:** {company}\n"
                )

                if phone:
                    result += f"- **Phone:** {phone}\n"

                result += f"- **Customer ID:** {data.get('customer_id')}\n"

                if data.get('saved_to_hubspot'):
                    result += f"\n**HubSpot Integration:**\n"
                    result += f"- ✅ Contact created in HubSpot CRM\n"
                    result += f"- HubSpot Contact ID: {data.get('hubspot_contact_id')}\n"

                result += f"\n_You can now create tickets for this customer._"
                return result
            elif response.status_code == 409:
                return f"❌ Customer with email `{email}` already exists in the system."
            else:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                error = error_data.get('error', 'Unknown error')
                return f"❌ Failed to create customer: {error}"

        except Exception as e:
            return f"❌ Error creating customer: {str(e)}"


class view_customers(BaseTool):
    """Tool for viewing all customers"""

    name: str = "view_customers"
    description: str = """Use this tool to view all customers in the system.

    Examples:
    - "Show me all customers"
    - "List customers"
    - "View customer database"

    Returns first 10 customers in a formatted table.
    """
    args_schema: Type[BaseModel] = ViewCustomer

    def _run(self,limit:int = 5) -> str | dict[str, str | int | list[Any]]:
        """View all customers"""

        try:
            response = requests.post(
                f"{FLASK_BACKEND_URL}/api/add_tickets",
                headers=get_auth_headers(),  # CHANGED
                timeout=10
            )

            if response.status_code == 200:
                customers = response.json()

                if not customers:
                    return "📋 No customers found in the system."

                # Limit to first 10
                display_customers = customers[:5]

                table_data = []
                for c in display_customers:
                    full_name = f"{c.get('firstname', '')} {c.get('lastname', '')}".strip()

                    table_data.append({
                        "ID": c["id"],
                        "Name": full_name or "N/A",
                        "Email": c["email"],
                        "Company": c.get("company", "N/A")
                    })

                return {
                    "type": "customers",
                    "count": len(customers),
                    "data": table_data
                }
            else:
                return "❌ Failed to retrieve customers."

        except Exception as e:
            return f"❌ Error viewing customers: {str(e)}"