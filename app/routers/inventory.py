from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app.schemas.inventory import InventoryCreate, InventoryUpdate, InventoryResponse
from app.core.security import get_current_user, require_role
from app.database import get_db
from app.models.inventory import Inventory

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("/", response_model=List[InventoryResponse])
async def get_all_inventory(
    current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """List all inventory items"""

    items = db.query(Inventory).order_by(Inventory.item_name).all()
    return items


@router.get("/category/{category}")
async def get_inventory_by_category(
    category: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get inventory items by category"""

    items = (
        db.query(Inventory)
        .filter(Inventory.category == category)
        .order_by(Inventory.item_name)
        .all()
    )

    return {
        "category": category,
        "total_items": len(items),
        "total_quantity": sum(item.quantity for item in items),
        "items": items,
    }


@router.get("/stats/summary")
async def get_inventory_stats(
    current_user: dict = Depends(require_role(["Admin", "Doctor"])),
    db: Session = Depends(get_db),
):
    """Get inventory statistics"""

    total_items = db.query(func.count(Inventory.id)).scalar()
    total_quantity = db.query(func.sum(Inventory.quantity)).scalar() or 0

    low_stock_count = (
        db.query(func.count(Inventory.id))
        .filter(Inventory.quantity <= Inventory.reorder_level)
        .scalar()
    )

    categories = (
        db.query(
            Inventory.category,
            func.count(Inventory.id).label("item_count"),
            func.sum(Inventory.quantity).label("total_quantity"),
        )
        .group_by(Inventory.category)
        .all()
    )

    category_stats = [
        {
            "category": cat or "Uncategorized",
            "item_count": count,
            "total_quantity": qty or 0,
        }
        for cat, count, qty in categories
    ]

    return {
        "total_items": total_items,
        "total_quantity": total_quantity,
        "low_stock_count": low_stock_count,
        "categories": category_stats,
    }


@router.get("/{item_id}", response_model=InventoryResponse)
async def get_inventory_item(
    item_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """View a specific inventory item"""

    item = db.query(Inventory).filter(Inventory.id == item_id).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found"
        )

    return item


@router.post("/", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
async def create_inventory_item(
    item: InventoryCreate,
    current_user: dict = Depends(require_role(["Admin"])),
    db: Session = Depends(get_db),
):
    print(item)
    """Add new inventory item (Admin only)"""

    # Check if item already exists
    existing_item = (
        db.query(Inventory)
        .filter(
            Inventory.item_name == item.item_name, Inventory.category == item.category
        )
        .first()
    )

    if existing_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item with this name and category already exists",
        )

    # Create new inventory item
    new_item = Inventory(
        item_name=item.item_name,
        category=item.category,
        quantity=item.quantity,
        supplier=item.supplier,
        reorder_level=item.reorder_level,
    )

    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return new_item


@router.put("/{item_id}", response_model=InventoryResponse)
async def update_inventory_item(
    item_id: str,
    item_data: InventoryUpdate,
    current_user: dict = Depends(require_role(["Admin", "Doctor"])),
    db: Session = Depends(get_db),
):
    """Update stock levels or item details"""

    # Get item
    item = db.query(Inventory).filter(Inventory.id == item_id).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found"
        )

    # Update fields
    update_data = item_data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update"
        )

    for field, value in update_data.items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)

    return item


@router.patch("/{item_id}/adjust-quantity")
async def adjust_inventory_quantity(
    item_id: str,
    adjustment: int,
    current_user: dict = Depends(require_role(["Admin", "Doctor"])),
    db: Session = Depends(get_db),
):
    """Adjust inventory quantity (add or subtract)"""

    item = db.query(Inventory).filter(Inventory.id == item_id).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found"
        )

    new_quantity = item.quantity + adjustment

    if new_quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity cannot be negative",
        )

    item.quantity = new_quantity
    db.commit()
    db.refresh(item)

    return {
        "item_id": str(item.id),
        "item_name": item.item_name,
        "previous_quantity": item.quantity - adjustment,
        "adjustment": adjustment,
        "new_quantity": item.quantity,
        "below_reorder_level": item.quantity <= item.reorder_level,
    }


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory_item(
    item_id: str,
    current_user: dict = Depends(require_role(["Admin"])),
    db: Session = Depends(get_db),
):
    """Remove inventory item (Admin only)"""

    item = db.query(Inventory).filter(Inventory.id == item_id).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found"
        )

    db.delete(item)
    db.commit()

    return None


@router.get("/low-stock/alert", response_model=List[InventoryResponse])
async def get_low_stock_items(
    current_user: dict = Depends(require_role(["Admin", "Doctor"])),
    db: Session = Depends(get_db),
):
    """Get items that are below reorder level"""

    low_stock_items = (
        db.query(Inventory)
        .filter(Inventory.quantity <= Inventory.reorder_level)
        .order_by(Inventory.quantity.asc())
        .all()
    )

    return low_stock_items
