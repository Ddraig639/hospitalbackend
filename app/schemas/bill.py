from uuid import UUID
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from decimal import Decimal


class InsuranceBase(BaseModel):
    provider_name: str
    policy_number: Optional[str] = None
    coverage_amount: Optional[Decimal] = None
    expiry_date: Optional[date] = None


class InsuranceCreate(InsuranceBase):
    pass


class InsuranceResponse(InsuranceBase):
    id: UUID

    class Config:
        from_attributes = True


class BillBase(BaseModel):
    appointment_id: UUID
    amount: Decimal
    payment_method: Optional[str] = None


class BillCreate(BillBase):
    insurance_id: Optional[UUID] = None
    notes: Optional[str] = None


class BillUpdate(BaseModel):
    amount: Optional[Decimal] = None
    payment_status: Optional[str] = None
    payment_method: Optional[str] = None


class BillResponse(BillBase):
    id: UUID
    insurance_id: Optional[UUID] = None
    payment_status: str
    created_at: datetime

    class Config:
        from_attributes = True
