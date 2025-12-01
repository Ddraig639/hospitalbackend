# app/schemas/pharmacy.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class DrugBase(BaseModel):
    drug_name: str
    quantity: int
    unit_price: float
    reorder_level: int = 10
    supplier: Optional[str] = None


class DrugCreate(DrugBase):
    pass


class DrugUpdate(BaseModel):
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    reorder_level: Optional[int] = None
    supplier: Optional[str] = None


class DrugResponse(DrugBase):
    drug_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class DispenseDrugItem(BaseModel):
    drug_id: str
    quantity: int


class DispenseRequest(BaseModel):
    prescription_id: str  # e.g., "REC045" (from medical_records.record_id)
    drugs_list: List[DispenseDrugItem]


class DispenseResponse(BaseModel):
    status: str = "success"
    message: str
