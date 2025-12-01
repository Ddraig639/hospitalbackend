from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.user import User

from app.models.inventory import Inventory


# from app.models.audit_log import AuditLog
from app.schemas.medical_record import (
    MedicalRecordCreate,
    MedicalRecordUpdate,
    MedicalRecordResponse,
    PrescriptionItem,
    VitalSigns,
)

# from app.api.deps import require_doctor, require_clinical_staff, get_current_user
from typing import List

from app.models.audit import AuditLog
from app.core.security import require_role
from app.models.doctor import Doctor

router = APIRouter(prefix="/records", tags=["Medical Records"])


# def require_doctor(current_user: User = Depends(get_db)) -> User:
#     if current_user.role != "Doctor":
#         raise HTTPException(status_code=403, detail="Doctor access required")
#     return current_user


# def require_clinical_staff(current_user: User = Depends(get_db)) -> User:
#     if current_user.role not in ["Doctor", "Nurse"]:
#         raise HTTPException(status_code=403, detail="Clinical staff access required")
#     return current_user


# === 1. Create Medical Record (Doctor Only) ===
@router.post(
    "/", response_model=MedicalRecordResponse, status_code=status.HTTP_201_CREATED
)
def create_medical_record(
    record_in: MedicalRecordCreate,
    db: Session = Depends(get_db),
    # doctor: User = Depends(require_doctor),
    current_user: dict = Depends(require_role(["Doctor"])),
):
    print("hi")
    user = db.query(User).filter(User.id == current_user["id"]).first()
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    # Validate patient exists
    patient = db.query(Patient).filter(Patient.id == record_in.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Generate record_id: REC001, REC002, ...
    last_record = (
        db.query(MedicalRecord).order_by(MedicalRecord.record_id.desc()).first()
    )
    num = (
        int(last_record.record_id[3:]) + 1
        if last_record and last_record.record_id.startswith("REC")
        else 1
    )
    record_id = f"REC{num:03d}"

    # Convert Pydantic models to dict for JSONB storage
    prescription_data = []
    if record_in.prescription:
        for item in record_in.prescription:
            # Check inventory item exists
            inv = (
                db.query(Inventory)
                .filter(Inventory.id == item.inventory_item_id)
                .first()
            )

            if not inv:
                raise HTTPException(
                    status_code=400,
                    detail=f"Inventory item not found: {item.inventory_item_id}",
                )

            # Add drug_name automatically if missing
            drug_name = item.drug_name or inv.item_name

            prescription_data.append(
                {
                    "inventory_item_id": str(inv.id),
                    "drug_name": drug_name,
                    "dosage": item.dosage,
                    "frequency": item.frequency,
                    "duration": item.duration,
                }
            )

    vital_signs_data = (
        record_in.vital_signs.model_dump() if record_in.vital_signs else None
    )

    new_record = MedicalRecord(
        record_id=record_id,
        patient_id=record_in.patient_id,
        doctor_id=doctor.id,
        diagnosis=record_in.diagnosis,
        prescription=prescription_data,
        vital_signs=vital_signs_data,
        notes=record_in.notes,
    )

    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    # Log event
    # log = AuditLog(
    #     action="Medical Record Created", target_id=record_id, user_id=doctor.id
    # )
    # db.add(log)
    # db.commit()

    return new_record


# === 2. View Medical Record by ID (Doctor & Nurse) ===
@router.get("/{record_id}", response_model=MedicalRecordResponse)
def get_medical_record(
    record_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["Doctor", "Nurse", "Patient"])),
):
    record = (
        db.query(MedicalRecord).filter(MedicalRecord.record_id == record_id).first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Medical record not found")
    return record


# === 3. View All Records for a Patient (Clinical Staff) ===
@router.get("/patient/{patient_id}", response_model=List[MedicalRecordResponse])
def get_patient_records(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["Doctor", "Nurse", "Patient"])),
):
    records = (
        db.query(MedicalRecord)
        .filter(MedicalRecord.patient_id == patient_id)
        .order_by(MedicalRecord.date_time.desc())
        .all()
    )
    if not records:
        raise HTTPException(
            status_code=404, detail="No medical records found for this patient"
        )
    return records


# === 4. Update Medical Record (Doctor Only) ===
@router.put("/{record_id}", response_model=MedicalRecordResponse)
def update_medical_record(
    record_id: str,
    update_data: MedicalRecordUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["Doctor"])),
):
    user = db.query(User).filter(User.id == current_user["id"]).first()
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()

    record = (
        db.query(MedicalRecord).filter(MedicalRecord.record_id == record_id).first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    # Ensure only the treating doctor can edit
    if record.doctor_id != doctor.id:
        raise HTTPException(
            status_code=403, detail="You can only edit records you created"
        )

    # Update fields
    if update_data.diagnosis is not None:
        record.diagnosis = update_data.diagnosis
    if update_data.prescription is not None:
        updated_list = []
        for item in update_data.prescription:
            inv = (
                db.query(Inventory)
                .filter(Inventory.id == item.inventory_item_id)
                .first()
            )

            if not inv:
                raise HTTPException(
                    status_code=400,
                    detail=f"Inventory item not found: {item.inventory_item_id}",
                )

            drug_name = item.drug_name or inv.item_name

            updated_list.append(
                {
                    "inventory_item_id": str(inv.id),
                    "drug_name": drug_name,
                    "dosage": item.dosage,
                    "frequency": item.frequency,
                    "duration": item.duration,
                }
            )

        record.prescription = updated_list
    if update_data.vital_signs is not None:
        record.vital_signs = update_data.vital_signs.model_dump()
    if update_data.notes is not None:
        record.notes = update_data.notes

    db.commit()
    db.refresh(record)

    # Log update
    # log = AuditLog(
    #     action="Medical Record Updated", target_id=record_id, user_id=doctor.id
    # )
    # db.add(log)
    # db.commit()

    return record


# === 5. Export as PDF (Optional Enhancement) ===
@router.get("/{record_id}/pdf")
def export_record_as_pdf(
    record_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["Doctor"])),
):
    # In real system: use `pdfkit` or `weasyprint` to render HTML → PDF
    raise HTTPException(status_code=501, detail="PDF export not implemented yet")
