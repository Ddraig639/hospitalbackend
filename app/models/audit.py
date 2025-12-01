from sqlalchemy import Column, String, Numeric, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action = Column(String(200), nullable=False)
    target_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    timestamp = Column(Date, nullable=False)

    def __repr__(self):
        return f"<AuditLog {self.action} on {self.target_id} by {self.user_id}>"
