# app/api/v1/routes/pharmacy.py
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db.session import get_db
from app.models.drug import Drug
from app.models.medical_record import MedicalRecord
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.pharmacy import (
    DrugCreate,
    DrugUpdate,
    DrugResponse,
    DispenseRequest,
    DispenseResponse,
)
from app.api.deps import require_pharmacist, get_current_user
from app.core.config import settings
from typing import List, Optional

router = APIRouter(prefix="/api/pharmacy", tags=["Pharmacy"])


# === 1. Dispense Drugs ===
@router.post("/dispense", response_model=DispenseResponse)
def dispense_drugs(
    request: DispenseRequest,
    db: Session = Depends(get_db),
    pharmacist: User = Depends(require_pharmacist),
):
    # Fetch medical record (acts as prescription)
    record = (
        db.query(MedicalRecord)
        .filter(MedicalRecord.record_id == request.prescription_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Prescription not found")

    if record.status == "Dispensed":  # You may store status in MedicalRecord
        raise HTTPException(status_code=400, detail="Already dispensed")

    try:
        for item in request.drugs_list:
            # Lock row for update to prevent race conditions
            drug = (
                db.query(Drug)
                .filter(Drug.drug_id == item.drug_id)
                .with_for_update()
                .first()
            )
            if not drug:
                raise HTTPException(
                    status_code=404, detail=f"Drug {item.drug_id} not found"
                )
            if drug.quantity < item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for {drug.drug_name}. Available: {drug.quantity}",
                )

            # Deduct stock
            drug.quantity -= item.quantity

            # Log dispensing
            log = AuditLog(
                action="Drug Dispensed",
                target_id=item.drug_id,
                user_id=pharmacist.user_id,
                ip_address=None,  # Optional: get from request
            )
            db.add(log)

            # Check reorder level
            if drug.quantity <= drug.reorder_level:
                # In real system: send email/SMS to manager
                print(
                    f"⚠️ LOW STOCK ALERT: {drug.drug_name} ({drug.quantity} units left)"
                )

        # Mark prescription as dispensed
        record.status = "Dispensed"  # Add `status` column to MedicalRecord if needed
        db.commit()

        return DispenseResponse(message="Drugs dispensed successfully")

    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error")


# === 2. View Inventory ===
@router.get("/inventory", response_model=List[DrugResponse])
def get_inventory(
    low_stock_only: bool = False,
    db: Session = Depends(get_db),
    pharmacist: User = Depends(require_pharmacist),
):
    query = db.query(Drug)
    if low_stock_only:
        query = query.filter(Drug.quantity <= Drug.reorder_level)
    return query.all()


# === 3. Add New Drug ===
@router.post(
    "/inventory", response_model=DrugResponse, status_code=status.HTTP_201_CREATED
)
def add_drug(
    drug_in: DrugCreate,
    db: Session = Depends(get_db),
    pharmacist: User = Depends(require_pharmacist),
):
    # Generate drug_id: DRG001, DRG002, ...
    last_drug = db.query(Drug).order_by(Drug.drug_id.desc()).first()
    if last_drug and last_drug.drug_id.startswith("DRG"):
        num = int(last_drug.drug_id[3:]) + 1
    else:
        num = 1
    drug_id = f"DRG{num:03d}"

    new_drug = Drug(
        drug_id=drug_id,
        drug_name=drug_in.drug_name,
        quantity=drug_in.quantity,
        unit_price=drug_in.unit_price,
        reorder_level=drug_in.reorder_level,
        supplier=drug_in.supplier,
    )
    db.add(new_drug)
    db.commit()
    db.refresh(new_drug)
    return new_drug


# === 4. Update Drug Stock ===
@router.put("/inventory/{drug_id}", response_model=DrugResponse)
def update_drug(
    drug_id: str,
    drug_update: DrugUpdate,
    db: Session = Depends(get_db),
    pharmacist: User = Depends(require_pharmacist),
):
    drug = db.query(Drug).filter(Drug.drug_id == drug_id).first()
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")

    update_data = drug_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(drug, field, value)

    db.commit()
    db.refresh(drug)
    return drug


# === 5. View Pending Prescriptions ===
@router.get("/prescriptions/pending")
def get_pending_prescriptions(
    db: Session = Depends(get_db), pharmacist: User = Depends(require_pharmacist)
):
    # Assuming: status = 'Pending' or NULL means not dispensed
    records = (
        db.query(MedicalRecord)
        .filter((MedicalRecord.status == None) | (MedicalRecord.status == "Pending"))
        .all()
    )

    result = []
    for r in records:
        result.append(
            {
                "prescription_id": r.record_id,
                "patient_name": r.patient.full_name,
                "doctor_name": r.doctor.name,
                "drugs": r.prescription,  # JSONB field
                "date_issued": r.date_time,
            }
        )
    return result


# === 6. Dashboard Summary ===
@router.get("/dashboard")
def get_pharmacist_dashboard(
    db: Session = Depends(get_db), pharmacist: User = Depends(require_pharmacist)
):
    total_drugs = db.query(Drug).count()
    low_stock_count = db.query(Drug).filter(Drug.quantity <= Drug.reorder_level).count()
    pending_prescriptions = (
        db.query(MedicalRecord)
        .filter((MedicalRecord.status == None) | (MedicalRecord.status == "Pending"))
        .count()
    )

    return {
        "total_drugs": total_drugs,
        "low_stock_count": low_stock_count,
        "pending_prescriptions": pending_prescriptions,
        # Add more as needed
    }
