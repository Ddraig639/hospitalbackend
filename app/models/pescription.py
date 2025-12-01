# # app/models/prescription.py
# from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum
# from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy.orm import relationship
# from sqlalchemy.sql import func
# import uuid
# from app.models.base import Base


# class PrescriptionStatus(str, enum.Enum):
#     PENDING = "Pending"
#     DISPENSED = "Dispensed"
#     CANCELLED = "Cancelled"


# class Prescription(Base):
#     __tablename__ = "prescriptions"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     patient_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
#     pharmacist_id = Column(
#         UUID(as_uuid=True), ForeignKey("Pharmacists.id"), nullable=True
#     )
#     status = Column(
#         Enum(PrescriptionStatus), default=PrescriptionStatus.PENDING, index=True
#     )
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     dispensed_at = Column(DateTime(timezone=True), nullable=True)

#     # Relationship
#     pharmacist = relationship("Pharmacist", back_populates="prescriptions")
