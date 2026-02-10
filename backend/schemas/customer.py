from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class CustomerCreateRequest(BaseModel):
    email: EmailStr = Field(...,min_length=5,description="Email Address")
    firstname: str = Field(..., min_length=1, description="First name")
    lastname: str = Field(default="", description="Last name (optional)")
    company:str = Field(...,description="Company")
    phone: Optional[str] = Field(default=None, description="Phone Number")

class CustomerCreateResponse(BaseModel):
    success: bool
    message: str
    hubspot_contact_id: Optional[str] = None
    contact_url: Optional[str] = None
    created_at: str
    email: str