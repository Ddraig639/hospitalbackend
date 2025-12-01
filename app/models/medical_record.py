# app/models/medical_record.py
from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.sql import func
from app.models.base import Base


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    record_id = Column(String(10), primary_key=True)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    diagnosis = Column(Text, nullable=False)
    prescription = Column(JSONB)
    vital_signs = Column(JSONB)
    notes = Column(Text)
    date_time = Column(TIMESTAMP, server_default=func.now())
