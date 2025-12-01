from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.schemas.doctor import (
    DoctorCreate,
    DoctorUpdate,
    DoctorResponse,
    DoctorSchedule,
)
from app.core.security import get_current_user, require_role
from app.database import get_db
from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.appointment import AppointmentResponse

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.get("/", response_model=List[DoctorResponse])
async def get_all_doctors(
    current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get all doctors"""

    doctors = db.query(Doctor).order_by(Doctor.name).all()
    return doctors


@router.get("/{doctor_id}", response_model=DoctorResponse)
async def get_doctor(
    doctor_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get doctor by ID"""

    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found"
        )

    return doctor


@router.post("/", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
async def create_doctor(
    doctor: DoctorCreate,
    current_user: dict = Depends(require_role(["Admin"])),
    db: Session = Depends(get_db),
):
    """Create new doctor profile (Admin only)"""

    # Verify user_id exists if provided
    if doctor.user_id:
        user = db.query(User).filter(User.id == doctor.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        if user.role.value != "Doctor":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must have Doctor role",
            )

    # Create new doctor
    new_doctor = Doctor(
        user_id=doctor.user_id,
        name=doctor.name,
        specialty=doctor.specialty,
        phone=doctor.phone,
        email=doctor.email,
        available_from=doctor.available_from,
        available_to=doctor.available_to,
    )

    db.add(new_doctor)
    db.commit()
    db.refresh(new_doctor)

    return new_doctor


@router.put("/{doctor_id}", response_model=DoctorResponse)
async def update_doctor(
    doctor_id: str,
    doctor_data: DoctorUpdate,
    current_user: dict = Depends(require_role(["Admin", "Doctor"])),
    db: Session = Depends(get_db),
):
    """Update doctor details"""

    # Get doctor
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found"
        )

    # If current user is a doctor, only allow them to update their own profile
    if current_user["role"] == "Doctor":
        user_doctor = (
            db.query(Doctor).filter(Doctor.user_id == current_user["id"]).first()
        )
        if not user_doctor or str(user_doctor.id) != doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own profile",
            )

    # Update fields
    update_data = doctor_data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update"
        )

    for field, value in update_data.items():
        setattr(doctor, field, value)

    db.commit()
    db.refresh(doctor)

    return doctor


@router.delete("/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doctor(
    doctor_id: str,
    current_user: dict = Depends(require_role(["Admin"])),
    db: Session = Depends(get_db),
):
    """Delete doctor profile (Admin only)"""

    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found"
        )

    db.delete(doctor)
    db.commit()

    return None


@router.get("/{doctor_id}/schedule", response_model=DoctorSchedule)
async def get_doctor_schedule(
    doctor_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get doctor's schedule"""

    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found"
        )

    return {
        "available_from": doctor.available_from,
        "available_to": doctor.available_to,
    }


@router.post("/{doctor_id}/schedule", response_model=DoctorSchedule)
async def update_doctor_schedule(
    doctor_id: str,
    schedule: DoctorSchedule,
    current_user: dict = Depends(require_role(["Admin", "Doctor"])),
    db: Session = Depends(get_db),
):
    """Add or update doctor schedule"""

    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found"
        )

    # If current user is a doctor, only allow them to update their own schedule
    if current_user["role"] == "Doctor":
        user_doctor = (
            db.query(Doctor).filter(Doctor.user_id == current_user["id"]).first()
        )
        if not user_doctor or str(user_doctor.id) != doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own schedule",
            )

    # Update schedule
    doctor.available_from = schedule.available_from
    doctor.available_to = schedule.available_to

    db.commit()
    db.refresh(doctor)

    return {
        "available_from": doctor.available_from,
        "available_to": doctor.available_to,
    }


@router.get("/{doctor_id}/appointments", response_model=List[AppointmentResponse])
async def get_doctor_appointments(
    doctor_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all appointments for a specific doctor using relationships"""

    doctor = (
        db.query(Doctor)
        .options(joinedload(Doctor.appointments))
        .filter(Doctor.user_id == doctor_id)
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found"
        )

    return doctor.appointments
