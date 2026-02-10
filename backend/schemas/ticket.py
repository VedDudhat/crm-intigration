from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field

ALLOWED_STATUSES = Literal['Open', 'In Progress', 'Closed']


class TicketCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, description="Ticket Subject")
    description: str = Field(default="", description="Ticket Content")
    priority: str = Field(default="MEDIUM", description="Priority (LOW, MEDIUM, HIGH)")
    email: EmailStr = Field(..., description="The email of the customer to associate with")
    customer_firstname: Optional[str] = None
    customer_lastname: Optional[str] = None

class TicketCreateResponse(BaseModel):
    success: bool
    message: str
    hubspot_ticket_id: str
    ticket_url: str
    linked_to_contact: bool
    contact_email: Optional[str] = None
    created_at: str
