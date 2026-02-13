from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class CreateTicket(BaseModel):
    title: str = Field(...,description="Title of the ticket")
    description: str = Field(...,description="Description of the ticket")
    priority: str = Field(...,description="Priority level :low, Medium, High")
    email: EmailStr = Field(...,description="Email of the ticket")

class SearchTicket(BaseModel):
    email: EmailStr = Field(..., description="Customer email to search tickets for")

class ViewTicket(BaseModel):
    status: Optional[str] = Field(default=None)
    priority: Optional[str] = Field(default=None)

class UpdateTicket(BaseModel):
    ticket_id: int = Field(..., description="The ticket ID number to update (e.g., 5 for ticket #5)")
    status: Optional[str] = Field(default=None,description="New status: Open, In Progress, or Closed")
    priority: Optional[str] = Field(default=None,description="New priority: Low, Medium, or High")
    title: Optional[str] = Field(default=None,description="Updated ticket title")
    description: Optional[str] = Field(default=None,description="Updated ticket description")


class CreateCustomer(BaseModel):
    firstname: str = Field(..., description="Customer's first name")
    lastname: Optional[str] = Field(default=None, description="Customer's last name (optional)")
    email: EmailStr = Field(..., description="Customer's email address")
    company: str = Field(..., description="Company name")
    phone: Optional[str] = Field(default=None, description="Phone number (optional)")

class ViewCustomer(BaseModel):
    limit: Optional[int] = Field(
        default=5,
        description="Number of customers to return 5 customers"
    )


