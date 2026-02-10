import os
from datetime import datetime
import httpx
from fastapi import HTTPException, APIRouter
from starlette import status
from backend.schemas import CustomerCreateRequest, CustomerCreateResponse
from backend.redis import cache_id_mapping, get_crm_token, check_rate_limit
router = APIRouter()

def create_hubspot_contact(contact_data: CustomerCreateRequest) -> dict:

    if not check_rate_limit(limit=100, window_seconds=10):  # Adjust limits as needed
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")

    token = get_crm_token()
    if not token:
        raise HTTPException(status_code=500, detail="HubSpot API key not configured")

    if not os.getenv("HUBSPOT_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="HubSpot API key not configured"
        )
    # Prepare HubSpot contact payload
    hubspot_payload = {
        "properties": {
            "email": contact_data.email,
            "firstname": contact_data.firstname,
            "lastname": contact_data.lastname,
            "company": contact_data.company,
            'phone': contact_data.phone,
        }
    }

    if contact_data.phone:
        hubspot_payload["properties"]["phone"] = contact_data.phone

    base_url = os.getenv("HUBSPOT_BASE_URL", "https://api.hubapi.com")
    url = f"{base_url}/crm/v3/objects/contacts"
    headers = {
        "Authorization": f"Bearer {os.getenv("HUBSPOT_API_KEY")}",
        "Content-Type": "application/json"
    }

    try:
        with httpx.AsyncClient() as client:
            search_url = f"{os.getenv("HUBSPOT_BASE_URL")}/crm/v3/objects/contacts/search"
            search_payload = {
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "email",
                        "operator": "EQ",
                        "value": contact_data.email
                    }]
                }]
            }

            search_response = client.post(
                search_url,
                json=search_payload,
                headers=headers,
                timeout=10.0
            )

            # If contact exists, update it instead
            if search_response.status_code == 200:
                results = search_response.json()
                if results.get("total", 0) > 0:
                    contact_id = results["results"][0]["id"]
                    update_url = f"{os.getenv('HUBSPOT_BASE_URL')}/crm/v3/objects/contacts/{contact_id}"
                    client.patch(update_url, json=hubspot_payload, headers=headers)
                    cache_id_mapping("customer_email", contact_data.email, contact_id)

                    return {
                        "success": True,
                        "contact_id": contact_id,
                        "contact_url": f"https://app.hubspot.com/contacts/{os.getenv('HUBSPOT_PORTAL_ID', 'NA')}/contact/{contact_id}",
                        "action": "updated"
                    }

            # Contact doesn't exist - create new
            url = f"{os.getenv('HUBSPOT_BASE_URL')}/crm/v3/objects/contacts"
            response = client.post(url, json=hubspot_payload, headers=headers, timeout=10.0)

            if response.status_code == 201:
                data = response.json()
                contact_id = data["id"]
                cache_id_mapping("customer_email", contact_data.email, contact_id)
                return {
                    "success": True,
                    "contact_id": data["id"],
                    "contact_url": f"https://app.hubspot.com/contacts/{os.getenv('HUBSPOT_PORTAL_ID', 'NA')}/contact/{data['id']}",
                    "action": "created"
                }
            elif response.status_code == 409:
                # Conflict - contact already exists (race condition)
                return {
                    "success": True,
                    "contact_id": "existing",
                    "contact_url": None,
                    "action": "already_exists"
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


def find_hubspot_contact_by_email(email: str) -> dict | None:
    if not os.getenv("HUBSPOT_API_KEY"):
        return None

    url = f"{os.getenv("HUBSPOT_BASE_URL")}/crm/v3/objects/contacts/search"
    headers = {
        "Authorization": f"Bearer {os.getenv("HUBSPOT_API_KEY")}",
        "Content-Type": "application/json"
    }

    payload = {
        "filterGroups": [{
            "filters": [{
                "propertyName": "email",
                "operator": "EQ",
                "value": email
            }]
        }]
    }

    try:
        with httpx.AsyncClient() as client:
            response = client.post(url, json=payload, headers=headers, timeout=10.0)

            if response.status_code == 200:
                results = response.json()
                if results.get("total", 0) > 0:
                    return results["results"][0]
    except:
        pass

    return None

def associate_ticket_with_contact(ticket_id: str, contact_id: str):
    token = get_crm_token()
    if not token:
        return

    url = f"{os.getenv('HUBSPOT_BASE_URL')}/crm/v3/objects/tickets/{ticket_id}/associations/contacts/{contact_id}/ticket_to_contact"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        with httpx.AsyncClient() as client:
            response = client.put(url, headers=headers, timeout=10.0)
            if response.status_code in [200, 201]:
                print(f"✅ Successfully associated ticket {ticket_id} with contact {contact_id}")
            else:
                print(f"⚠️ Failed to associate ticket {ticket_id} with contact {contact_id}: {response.text}")
    except Exception as e:
        print(f"⚠️ Error associating ticket with contact: {str(e)}")


@router.post("/integrate/customer",
    response_model=CustomerCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Contact in HubSpot",
    description="Creates a customer as a contact in HubSpot CRM"
)
def create_contact_in_crm(contact: CustomerCreateRequest):
    try:
        print(f"DEBUG: Received data from Flask: {contact.model_dump()}")
        result = create_hubspot_contact(contact)

        action = result.get("action", "created")
        message_map = {
            "created": "Contact created successfully in HubSpot",
            "updated": "Contact already existed - updated in HubSpot",
            "already_exists": "Contact already exists in HubSpot"
        }

        return CustomerCreateResponse(
            success=True,
            message=message_map.get(action, "Contact processed"),
            hubspot_contact_id=str(result["contact_id"]),
            contact_url=result["contact_url"],
            created_at=datetime.utcnow().isoformat(),
            email=contact.email
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
