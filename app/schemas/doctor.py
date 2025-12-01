from uuid import UUID
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, time


class DoctorBase(BaseModel):
    name: str
    specialty: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    available_from: Optional[time] = None
    available_to: Optional[time] = None


class DoctorCreate(DoctorBase):
    user_id: Optional[str] = None


class DoctorUpdate(BaseModel):
    name: Optional[str] = None
    specialty: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    available_from: Optional[time] = None
    available_to: Optional[time] = None


class DoctorResponse(DoctorBase):
    id: UUID
    user_id: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DoctorSchedule(BaseModel):
    available_from: time
    available_to: time
