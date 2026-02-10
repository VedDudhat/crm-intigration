from datetime import datetime

from fastapi import HTTPException, APIRouter
from starlette import status
from backend.schemas import TicketCreateRequest, TicketCreateResponse
import httpx,os
from backend.redis import get_crm_token,check_rate_limit,get_cached_hubspot_id,cache_id_mapping
from backend.routes.customer import find_hubspot_contact_by_email
router = APIRouter()

def create_hubspot_ticket(ticket_data: TicketCreateRequest) -> dict:

    if not check_rate_limit(limit=100, window_seconds=10):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    token = get_crm_token()
    if not token:
        raise HTTPException(status_code=500, detail="HubSpot API key not configured")

    if not os.getenv("HUBSPOT_API_KEY"):
        raise HTTPException(status_code=500, detail="HubSpot API key not configured")

    priority_mapping = {
        "LOW": "LOW",
        "MEDIUM": "MEDIUM",
        "HIGH": "HIGH"
    }

    hubspot_payload = {
        "properties": {
            "subject": ticket_data.title,
            "content": ticket_data.description,
            "hs_pipeline_stage": "1",
            "hs_ticket_priority": priority_mapping.get(ticket_data.priority,"HIGH"),
            "source_type": "CHAT",
        }
    }

    url = f"{os.getenv("HUBSPOT_BASE_URL")}/crm/v3/objects/tickets"
    headers = {
        "Authorization": f"Bearer {os.getenv("HUBSPOT_API_KEY")}",
        "Content-Type": "application/json"
    }

    try:
        with httpx.AsyncClient() as client:
            response = client.post(url, json=hubspot_payload, headers=headers, timeout=10.0)

            if response.status_code == 201:
                data = response.json()
                ticket_id = data["id"]

                contact = get_cached_hubspot_id("customer_email", ticket_data.email)
                linked = False

                if contact:
                    associate_ticket_with_contact(ticket_id, contact["id"])
                    linked = True
                else:
                    # Contact doesn't exist in HubSpot - create it first
                    print(f"Warning: Contact with email {ticket_data.email} not found in HubSpot")

                return {
                    "success": True,
                    "ticket_id": ticket_id,
                    "ticket_url": f"https://app.hubspot.com/contacts/YOUR_PORTAL_ID/ticket/{ticket_id}",
                    "linked_to_contact": linked,
                    "contact_email": ticket_data.email if linked else None
                }
            elif response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid HubSpot API key")
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"HubSpot API error: {response.text}"
                )

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="HubSpot API timeout")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Connection error: {str(e)}")


def associate_ticket_with_contact(ticket_id: str, contact_id: str):
    """Associate a ticket with a contact in HubSpot"""

    token = get_crm_token()
    if not token:
        print("⚠️ No token available for association")
        return False

    url = f"{os.getenv("HUBSPOT_BASE_URL")}/crm/v3/objects/tickets/{ticket_id}/associations/contacts/{contact_id}/ticket_to_contact"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        with httpx.AsyncClient() as client:
            response = client.put(url, headers=headers, timeout=10.0)
            if response.status_code in [200, 201]:
                print(f"✅ Successfully associated ticket {ticket_id} with contact {contact_id}")
            else:
                print(f"⚠️ Failed to associate ticket {ticket_id} with contact {contact_id}: {response.text}")
    except Exception as e:
        print(f"⚠️ Error associating ticket with contact: {str(e)}")


@router.post("/integrate/ticket",
    response_model=TicketCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Ticket in HubSpot",
    description="Creates a support ticket in HubSpot CRM and links to contact by email"
)
def create_ticket_in_crm(ticket_data: TicketCreateRequest):
    """
        Creates a ticket and links it to the customer via Email
        """
    if not check_rate_limit():
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    token = get_crm_token()
    if not token:
        raise HTTPException(status_code=500, detail="HubSpot configuration missing")

    priority_mapping = {"LOW": "LOW", "MEDIUM": "MEDIUM", "HIGH": "HIGH"}

    hubspot_payload = {
        "properties": {
            "subject": ticket_data.title,
            "content": ticket_data.description,
            "hs_pipeline_stage": "1",  # Ensure this stage ID exists in your HubSpot
            "hs_ticket_priority": priority_mapping.get(ticket_data.priority.upper(), "MEDIUM"),
            "source_type": "CHAT",
        }
    }

    url = f"{os.getenv('HUBSPOT_BASE_URL')}/crm/v3/objects/tickets"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        with httpx.AsyncClient() as client:
            # A. Create the Ticket
            response = client.post(url, json=hubspot_payload, headers=headers, timeout=10.0)

            if response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=f"HubSpot Error: {response.text}")

            ticket_json = response.json()
            ticket_id = ticket_json["id"]

            # B. Find the Contact (to associate with)
            linked = False

            # Step B1: Check Redis Cache first
            contact_hubspot_id = get_cached_hubspot_id("customer_email", ticket_data.email)

            # Step B2: If not in Redis, Search HubSpot
            if not contact_hubspot_id:
                print(f"🔍 Searching HubSpot for email: {ticket_data.email}")
                contact = find_hubspot_contact_by_email(ticket_data.email)
                if contact:
                    contact_hubspot_id = contact["id"]
                    # Cache it for next time
                    cache_id_mapping("customer_email", ticket_data.email, contact_hubspot_id)

            # Step C: Perform Association
            if contact_hubspot_id:
                success = associate_ticket_with_contact(ticket_id, contact_hubspot_id)
                linked = success
            else:
                print(f"⚠️ No contact found for {ticket_data.email}. Ticket created without association.")

        return TicketCreateResponse(
                success=True,
                message="Ticket created and linked" if linked else "Ticket created (Unlinked)",
                hubspot_ticket_id=ticket_id,
                ticket_url=f"https://app.hubspot.com/contacts/{os.getenv('HUBSPOT_PORTAL_ID')}/ticket/{ticket_id}",
                linked_to_contact=linked,
                contact_email=ticket_data.email,
                created_at=datetime.utcnow().isoformat()
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.patch("/integrate/ticket/{hubspot_ticket_id}")
def update_hubspot_ticket(hubspot_ticket_id: str, update_data: dict):
    token = get_crm_token()
    url = f"{os.getenv('HUBSPOT_BASE_URL')}/crm/v3/objects/tickets/{hubspot_ticket_id}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # HubSpot internal property names
    payload = {
        "properties": {
            "subject": update_data.get("title"),
            "content": update_data.get("description"),
            "hs_ticket_priority": update_data.get("priority")
        }
    }

    with httpx.AsyncClient() as client:
        response = client.patch(url, json=payload, headers=headers)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

    return {"success": True}