from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn
import os
from backend.routes.customer import router as customer_router
# from backend.routes.ticket import router as ticket_router

load_dotenv()
app = FastAPI()
app.include_router(customer_router)
# app.include_router(ticket_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5000", "http://localhost:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
async def root():
    """Health check"""
    return {
        "service": "CRM Integration Service",
        "status": "running",
        "version": "2.0.0",
        "features": ["tickets", "contacts"],
        "hubspot_configured": bool(os.getenv("HUBSPOT_API_KEY"))
    }

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)


