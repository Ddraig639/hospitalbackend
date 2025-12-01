# app/models/drug.py
from sqlalchemy import Column, String, Integer, Numeric, DateTime
from sqlalchemy.sql import func
from app.models.base import Base


class Drug(Base):
    __tablename__ = "drugs"

    drug_id = Column(String(10), primary_key=True)
    drug_name = Column(String(100), nullable=False)
    quantity = Column(Integer, default=0, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    reorder_level = Column(Integer, default=10)
    supplier = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
