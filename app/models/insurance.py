from sqlalchemy import Column, String, Numeric, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.models.base import Base


class Insurance(Base):
    __tablename__ = "insurance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_name = Column(String(100), nullable=False, index=True)
    policy_number = Column(String(100))
    coverage_amount = Column(Numeric(10, 2))
    expiry_date = Column(Date)

    # Relationships
    bills = relationship("Bill", back_populates="insurance")

    def __repr__(self):
        return f"<Insurance {self.provider_name} - {self.policy_number}>"
