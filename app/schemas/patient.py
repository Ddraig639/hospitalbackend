from uuid import UUID
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PatientBase(BaseModel):
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    contact: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    blood_type: Optional[str] = None
    medical_history: Optional[str] = None


class PatientCreate(PatientBase):
    user_id: Optional[UUID] = None


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    contact: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    blood_type: Optional[str] = None
    medical_history: Optional[str] = None


class PatientResponse(PatientBase):
    id: UUID
    user_id: Optional[UUID] = None
    created_at: datetime
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    contact: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    blood_type: Optional[str] = None
    medical_history: Optional[str] = None

    class Config:
        from_attributes = True
