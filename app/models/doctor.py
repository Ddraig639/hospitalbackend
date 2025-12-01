from sqlalchemy import Column, String, Time, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.models.base import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name = Column(String(100), nullable=False, index=True)
    specialty = Column(String(100), index=True)
    phone = Column(String(50))
    email = Column(String(100))
    available_from = Column(Time)
    available_to = Column(Time)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    appointments = relationship(
        "Appointment", back_populates="doctor", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Doctor {self.name} - {self.specialty}>"
