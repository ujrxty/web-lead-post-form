from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import csv
import io
from fastapi.responses import StreamingResponse

from database import get_db, Lead, create_tables

# Create FastAPI app
app = FastAPI(
    title="Lead Management API",
    description="API for managing and tracking submitted leads",
    version="1.0.0"
)

# CORS middleware - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup templates
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Create tables on startup
@app.on_event("startup")
def startup_event():
    create_tables()


# Pydantic models for request/response
class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None
    phone: str
    mobile_phone: Optional[str] = None
    email: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    primary_insurance: Optional[str] = None
    total_med_count: Optional[int] = None
    list_affiliate_name: Optional[str] = None
    salesforce_status: Optional[str] = "success"


class LeadResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    gender: Optional[str]
    date_of_birth: Optional[str]
    phone: str
    mobile_phone: Optional[str]
    email: Optional[str]
    street: Optional[str]
    city: Optional[str]
    state: Optional[str]
    postal_code: Optional[str]
    primary_insurance: Optional[str]
    total_med_count: Optional[int]
    list_affiliate_name: Optional[str]
    submitted_at: datetime
    salesforce_status: Optional[str]

    class Config:
        from_attributes = True


class CheckResponse(BaseModel):
    exists: bool
    message: str


# API Endpoints

@app.get("/api/check/{phone}", response_model=CheckResponse)
def check_phone(phone: str, db: Session = Depends(get_db)):
    """Check if a phone number has already been submitted"""
    # Clean phone number - remove non-digits
    clean_phone = ''.join(filter(str.isdigit, phone))

    # Check if lead exists
    existing_lead = db.query(Lead).filter(Lead.phone == clean_phone).first()

    if existing_lead:
        return CheckResponse(
            exists=True,
            message=f"Lead with phone {phone} was already submitted on {existing_lead.submitted_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    return CheckResponse(
        exists=False,
        message="Phone number not found. Safe to submit."
    )


@app.post("/api/leads", response_model=LeadResponse)
def create_lead(lead: LeadCreate, db: Session = Depends(get_db)):
    """Store a new lead in the database"""
    # Clean phone number
    clean_phone = ''.join(filter(str.isdigit, lead.phone))

    # Check for duplicate
    existing_lead = db.query(Lead).filter(Lead.phone == clean_phone).first()
    if existing_lead:
        raise HTTPException(
            status_code=400,
            detail=f"Lead with phone {lead.phone} already exists"
        )

    # Create new lead
    db_lead = Lead(
        first_name=lead.first_name,
        last_name=lead.last_name,
        gender=lead.gender,
        date_of_birth=lead.date_of_birth,
        phone=clean_phone,
        mobile_phone=lead.mobile_phone,
        email=lead.email,
        street=lead.street,
        city=lead.city,
        state=lead.state,
        postal_code=lead.postal_code,
        primary_insurance=lead.primary_insurance,
        total_med_count=lead.total_med_count,
        list_affiliate_name=lead.list_affiliate_name,
        salesforce_status=lead.salesforce_status
    )

    db.add(db_lead)
    db.commit()
    db.refresh(db_lead)

    return db_lead


@app.get("/api/leads", response_model=list[LeadResponse])
def get_leads(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all leads with optional pagination and search"""
    query = db.query(Lead)

    # Apply search filter if provided
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Lead.phone.like(search_term)) |
            (Lead.first_name.like(search_term)) |
            (Lead.last_name.like(search_term)) |
            (Lead.email.like(search_term))
        )

    # Order by newest first and apply pagination
    leads = query.order_by(desc(Lead.submitted_at)).offset(skip).limit(limit).all()

    return leads


@app.get("/api/leads/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    """Get a specific lead by ID"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return lead


@app.delete("/api/leads/{lead_id}")
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    """Delete a lead by ID"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    db.delete(lead)
    db.commit()

    return {"message": "Lead deleted successfully", "id": lead_id}


@app.get("/api/leads/export/csv")
def export_leads_csv(db: Session = Depends(get_db)):
    """Export all leads as CSV"""
    leads = db.query(Lead).order_by(desc(Lead.submitted_at)).all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "ID", "First Name", "Last Name", "Gender", "Date of Birth",
        "Phone", "Mobile Phone", "Email", "Street", "City", "State",
        "Postal Code", "Primary Insurance", "Total Med Count",
        "List Affiliate Name", "Submitted At", "Salesforce Status"
    ])

    # Write data
    for lead in leads:
        writer.writerow([
            lead.id, lead.first_name, lead.last_name, lead.gender,
            lead.date_of_birth, lead.phone, lead.mobile_phone, lead.email,
            lead.street, lead.city, lead.state, lead.postal_code,
            lead.primary_insurance, lead.total_med_count,
            lead.list_affiliate_name,
            lead.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if lead.submitted_at else "",
            lead.salesforce_status
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_export.csv"}
    )


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get statistics about leads"""
    total_leads = db.query(Lead).count()
    successful_leads = db.query(Lead).filter(Lead.salesforce_status == "success").count()
    failed_leads = db.query(Lead).filter(Lead.salesforce_status == "failed").count()

    return {
        "total_leads": total_leads,
        "successful_leads": successful_leads,
        "failed_leads": failed_leads
    }


# Admin Panel Route
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    """Render the admin dashboard"""
    return templates.TemplateResponse("admin.html", {"request": request})


# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
