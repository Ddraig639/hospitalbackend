from uuid import UUID
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class InventoryBase(BaseModel):
    item_name: str
    category: Optional[str] = None
    quantity: Optional[int] = 0
    supplier: Optional[str] = None
    reorder_level: Optional[int] = 10


class InventoryCreate(InventoryBase):
    pass


class InventoryUpdate(BaseModel):
    item_name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[int] = None
    supplier: Optional[str] = None
    reorder_level: Optional[int] = None


class InventoryResponse(InventoryBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
