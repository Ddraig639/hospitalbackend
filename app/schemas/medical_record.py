# app/schemas/medical_record.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

from uuid import UUID


class PrescriptionItem(BaseModel):
    inventory_item_id: Optional[UUID] = None
    drug_name: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None


class VitalSigns(BaseModel):
    blood_pressure: Optional[str] = None
    temperature: Optional[str] = None
    pulse: Optional[str] = None
    respiratory_rate: Optional[int] = None


class MedicalRecordCreate(BaseModel):
    patient_id: str
    diagnosis: str
    prescription: Optional[list[PrescriptionItem]] = None
    vital_signs: Optional[VitalSigns] = None
    notes: Optional[str] = None


class MedicalRecordUpdate(BaseModel):
    diagnosis: Optional[str] = None
    prescription: Optional[list[PrescriptionItem]] = None
    vital_signs: Optional[VitalSigns] = None
    notes: Optional[str] = None


class MedicalRecordResponse(BaseModel):
    record_id: str
    patient_id: UUID
    doctor_id: UUID
    diagnosis: str
    prescription: Optional[list[PrescriptionItem]] = None
    vital_signs: Optional[VitalSigns] = None
    notes: Optional[str] = None
    date_time: datetime

    class Config:
        from_attributes = True
