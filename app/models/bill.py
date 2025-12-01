from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.models.base import Base


class Bill(Base):
    __tablename__ = "bills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    insurance_id = Column(
        UUID(as_uuid=True), ForeignKey("insurance.id", ondelete="SET NULL"), index=True
    )
    amount = Column(Numeric(10, 2), nullable=False)
    payment_status = Column(String(20), default="Unpaid", index=True)
    payment_method = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    appointment = relationship("Appointment", back_populates="bills")
    insurance = relationship("Insurance", back_populates="bills")

    def __repr__(self):
        return f"<Bill {self.amount} - {self.payment_status}>"
