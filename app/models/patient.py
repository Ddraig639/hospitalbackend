from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.models.base import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name = Column(String(100), nullable=False, index=True)
    age = Column(Integer)
    gender = Column(String(10))
    contact = Column(String(50))
    address = Column(Text)
    email = Column(String(100), nullable=True)
    blood_type = Column(String(100), nullable=True)
    medical_history = Column(String(200), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    appointments = relationship(
        "Appointment", back_populates="patient", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Patient {self.name}>"
