from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.schemas.patient import PatientCreate, PatientUpdate, PatientResponse
from app.core.security import get_current_user, require_role
from app.database import get_db
from app.models.patient import Patient
from app.models.user import User

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get("/", response_model=List[PatientResponse])
async def get_all_patients(
    current_user: dict = Depends(require_role(["Admin", "Doctor"])),
    db: Session = Depends(get_db),
):
    """Get all patients (Admin and Doctor only)"""

    patients = db.query(Patient).order_by(Patient.created_at.desc()).all()
    print(patients)
    return patients


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get patient by ID"""

    patient = db.query(Patient).filter(Patient.id == patient_id).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )

    return patient


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient: PatientCreate,
    current_user: dict = Depends(require_role(["Admin", "Doctor"])),
    db: Session = Depends(get_db),
):
    """Register a new patient"""

    # Verify user_id exists if provided
    if patient.user_id:
        user = db.query(User).filter(User.id == patient.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        if user.role.value != "Patient":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must have Patient role",
            )

    # Create new patient
    new_patient = Patient(
        user_id=patient.user_id,
        name=patient.name,
        age=patient.age,
        gender=patient.gender,
        contact=patient.contact,
        address=patient.address,
        email=patient.email,
        blood_type=patient.blood_type,
        medical_history=patient.medical_history,
    )

    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    return new_patient


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str,
    patient_data: PatientUpdate,
    current_user: dict = Depends(require_role(["Admin", "Doctor"])),
    db: Session = Depends(get_db),
):
    """Update patient information"""
    print(patient_data)

    # Get patient
    patient = db.query(Patient).filter(Patient.id == patient_id).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )

    # Update fields
    update_data = patient_data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update"
        )

    for field, value in update_data.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)

    return patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: str,
    current_user: dict = Depends(require_role(["Admin"])),
    db: Session = Depends(get_db),
):
    """Delete patient record (Admin only)"""

    patient = db.query(Patient).filter(Patient.id == patient_id).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )

    db.delete(patient)
    db.commit()

    return None


@router.get("/{patient_id}/appointments")
async def get_patient_appointments(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all appointments for a specific patient using relationships"""

    patient = (
        db.query(Patient)
        .options(joinedload(Patient.appointments))
        .filter(Patient.id == patient_id)
        .first()
    )

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )

    return {
        "patient_id": patient.id,
        "patient_name": patient.name,
        "appointments": patient.appointments,
    }
