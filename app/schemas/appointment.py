from uuid import UUID
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date, time

from app.schemas.patient import PatientResponse
from app.schemas.doctor import DoctorResponse


class AppointmentBase(BaseModel):
    patient_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    appointment_date: Optional[date] = None
    appointment_time: Optional[time] = None
    notes: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    appointment_date: Optional[date] = None
    appointment_time: Optional[time] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class AppointmentResponse(AppointmentBase):
    id: UUID
    status: str
    created_at: datetime
    appointment_date: date
    appointment_time: time
    patient: PatientResponse
    doctor: DoctorResponse

    class Config:
        from_attributes = True


class DoctorAppointmentResponse(BaseModel):
    doctor_id: UUID
    doctor_name: str
    specialty: Optional[str] = None
    appointments: list[AppointmentResponse]

    class Config:
        from_attributes = True
