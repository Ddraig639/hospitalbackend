from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.models.base import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_name = Column(String(100), nullable=False, index=True)
    category = Column(String(100), index=True)
    quantity = Column(Integer, default=0, index=True)
    supplier = Column(String(100))
    reorder_level = Column(Integer, default=10)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Inventory {self.item_name} - Qty: {self.quantity}>"
