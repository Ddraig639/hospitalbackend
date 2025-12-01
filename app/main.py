from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database import connect_db, disconnect_db

# Import routers
from app.routers import (
    auth,
    doctors,
    patients,
    appointments,
    billing,
    inventory,
    reports,
    medical_records,
)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Hospital Management System API",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database events (optional - only if using async database queries)
# @app.on_event("startup")
# async def startup():
#     await connect_db()

# @app.on_event("shutdown")
# async def shutdown():
#     await disconnect_db()

# Include routers
app.include_router(auth.router)
app.include_router(doctors.router)
app.include_router(patients.router)
app.include_router(appointments.router)
app.include_router(billing.router)
app.include_router(billing.insurance_router)  # Insurance routes
app.include_router(inventory.router)
app.include_router(reports.router)
app.include_router(medical_records.router)


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to Hospital Management System API",
        "version": settings.VERSION,
        "docs": "/docs",
    }


# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
