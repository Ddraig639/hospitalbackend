from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse,
)
from app.core.security import get_current_user, require_role
from app.database import get_db
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.doctor import Doctor

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("/", response_model=List[AppointmentResponse])
async def get_all_appointments(
    current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get all appointments with filtering based on role"""
    print(current_user)

    # Filter based on role using relationships
    if current_user["role"] == "Patient":
        # Get patient record from user_id
        patient = (
            db.query(Patient).filter(Patient.user_id == current_user["id"]).first()
        )

        if patient:
            print("hello")
            appointments = (
                db.query(Appointment)
                .filter(Appointment.patient_id == patient.id)
                .order_by(Appointment.appointment_date.desc())
                .all()
            )
        else:
            appointments = []

    elif current_user["role"] == "Doctor":
        # Get doctor record from user_id
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user["id"]).first()

        if doctor:
            appointments = (
                db.query(Appointment)
                .filter(Appointment.doctor_id == doctor.id)
                .order_by(Appointment.appointment_date.desc())
                .all()
            )
        else:
            appointments = []

    else:  # Admin
        appointments = (
            db.query(Appointment).order_by(Appointment.appointment_date.desc()).all()
        )
    print(appointments)

    return appointments


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get appointment by ID with related patient and doctor info"""

    appointment = (
        db.query(Appointment)
        .options(joinedload(Appointment.patient), joinedload(Appointment.doctor))
        .filter(Appointment.id == appointment_id)
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found"
        )

    return appointment


@router.get("/{appointment_id}/details")
async def get_appointment_with_details(
    appointment_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get appointment with full patient and doctor details using relationships"""

    appointment = (
        db.query(Appointment)
        .options(joinedload(Appointment.patient), joinedload(Appointment.doctor))
        .filter(Appointment.id == appointment_id)
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found"
        )

    return {
        "id": str(appointment.id),
        "appointment_date": appointment.appointment_date,
        "appointment_time": appointment.appointment_time,
        "status": appointment.status,
        "notes": appointment.notes,
        "patient": {
            "id": str(appointment.patient.id),
            "name": appointment.patient.name,
            "age": appointment.patient.age,
            "contact": appointment.patient.contact,
        },
        "doctor": {
            "id": str(appointment.doctor.id),
            "name": appointment.doctor.name,
            "specialty": appointment.doctor.specialty,
            "phone": appointment.doctor.phone,
        },
    }


@router.post(
    "/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED
)
async def create_appointment(
    appointment: AppointmentCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new appointment"""
    print("helly")

    # Verify patient exists
    patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )

    # Verify doctor exists
    doctor = db.query(Doctor).filter(Doctor.id == appointment.doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found"
        )
    print(appointment.appointment_time)
    print(doctor.available_from)
    print(doctor.available_to)
    # # Check if doctor is available at the requested time
    # if doctor.available_from and doctor.available_to:
    #     if not (
    #         doctor.available_from <= appointment.appointment_time <= doctor.available_to
    #     ):
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail=f"Doctor is not available at this time. Available: {doctor.available_from} - {doctor.available_to}",
    #         )

    # Check for conflicting appointments
    existing_appointment = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == appointment.doctor_id,
            Appointment.appointment_date == appointment.appointment_date,
            Appointment.appointment_time == appointment.appointment_time,
            Appointment.status != "Cancelled",
        )
        .first()
    )

    if existing_appointment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctor already has an appointment at this time",
        )

    # Create new appointment
    new_appointment = Appointment(
        patient_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        appointment_date=appointment.appointment_date,
        appointment_time=appointment.appointment_time,
        notes=appointment.notes,
        status="Pending",
    )

    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment)

    return new_appointment


@router.put("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: str,
    appointment_data: AppointmentUpdate,
    current_user: dict = Depends(require_role(["Admin", "Doctor"])),
    db: Session = Depends(get_db),
):
    """Update appointment status or details"""

    # Get appointment
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found"
        )

    # Update fields
    update_data = appointment_data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update"
        )

    for field, value in update_data.items():
        setattr(appointment, field, value)

    db.commit()
    db.refresh(appointment)

    return appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_appointment(
    appointment_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel appointment"""

    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found"
        )

    # Check permissions - patients can only cancel their own appointments
    if current_user["role"] == "Patient":
        patient = (
            db.query(Patient).filter(Patient.user_id == current_user["id"]).first()
        )
        if not patient or str(appointment.patient_id) != str(patient.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only cancel your own appointments",
            )

    db.delete(appointment)
    db.commit()

    return None


# get all doctor appointments
@router.get("/doctor/{doctor_id}", response_model=List[AppointmentResponse])
async def get_appointments_by_doctor(
    doctor_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    print(doctor_id)
    """Get all appointments for a specific doctor"""
    # Only Admins and the Doctor themselves can access this
    if current_user["role"] not in ["Admin", "Doctor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view these appointments",
        )
    print(current_user)

    if current_user["role"] == "Doctor":
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user["id"]).first()
        if not doctor or str(doctor.id) != doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view these appointments",
            )
    print("here")

    appointments = (
        db.query(Appointment)
        .filter(Appointment.doctor_id == doctor_id)
        .order_by(Appointment.appointment_date.desc())
        .all()
    )

    return appointments
