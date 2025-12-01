from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.schemas.bill import (
    BillCreate,
    BillUpdate,
    BillResponse,
    InsuranceCreate,
    InsuranceResponse,
)
from app.core.security import get_current_user, require_role
from app.database import get_db
from app.models.bill import Bill
from app.models.insurance import Insurance
from app.models.appointment import Appointment

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/", response_model=List[BillResponse])
async def get_all_bills(
    current_user: dict = Depends(require_role(["Admin", "Doctor"])),
    db: Session = Depends(get_db),
):
    """Get all bills (Admin and Doctor only)"""

    bills = db.query(Bill).order_by(Bill.created_at.desc()).all()
    return bills


@router.get("/{bill_id}", response_model=BillResponse)
async def get_bill(
    bill_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get bill by ID"""

    bill = db.query(Bill).filter(Bill.id == bill_id).first()

    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found"
        )

    return bill


@router.get("/{bill_id}/details")
async def get_bill_with_details(
    bill_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get bill with full appointment and insurance details using relationships"""

    bill = (
        db.query(Bill)
        .options(
            joinedload(Bill.appointment).joinedload(Appointment.patient),
            joinedload(Bill.appointment).joinedload(Appointment.doctor),
            joinedload(Bill.insurance),
        )
        .filter(Bill.id == bill_id)
        .first()
    )

    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found"
        )

    response = {
        "id": str(bill.id),
        "amount": float(bill.amount),
        "payment_status": bill.payment_status,
        "payment_method": bill.payment_method,
        "created_at": bill.created_at,
        "appointment": {
            "id": str(bill.appointment.id),
            "date": bill.appointment.appointment_date,
            "time": bill.appointment.appointment_time,
            "patient": {
                "id": str(bill.appointment.patient.id),
                "name": bill.appointment.patient.name,
            },
            "doctor": {
                "id": str(bill.appointment.doctor.id),
                "name": bill.appointment.doctor.name,
                "specialty": bill.appointment.doctor.specialty,
            },
        },
    }

    if bill.insurance:
        response["insurance"] = {
            "id": str(bill.insurance.id),
            "provider_name": bill.insurance.provider_name,
            "policy_number": bill.insurance.policy_number,
            "coverage_amount": (
                float(bill.insurance.coverage_amount)
                if bill.insurance.coverage_amount
                else None
            ),
        }

    return response


@router.post("/", response_model=BillResponse, status_code=status.HTTP_201_CREATED)
async def create_bill(
    bill: BillCreate,
    current_user: dict = Depends(require_role(["Admin", "Doctor"])),
    db: Session = Depends(get_db),
):
    print("Creating bill...")
    """Create new bill"""

    # Verify appointment exists
    appointment = (
        db.query(Appointment).filter(Appointment.id == bill.appointment_id).first()
    )
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found"
        )

    # Verify insurance exists if provided
    if bill.insurance_id:
        insurance = (
            db.query(Insurance).filter(Insurance.id == bill.insurance_id).first()
        )
        if not insurance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Insurance not found"
            )

    # Check if bill already exists for this appointment
    existing_bill = (
        db.query(Bill).filter(Bill.appointment_id == bill.appointment_id).first()
    )
    if existing_bill:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bill already exists for this appointment",
        )

    # Create new bill
    new_bill = Bill(
        appointment_id=bill.appointment_id,
        insurance_id=bill.insurance_id,
        amount=bill.amount,
        payment_status="Unpaid",
        payment_method=bill.payment_method,
    )

    db.add(new_bill)
    db.commit()
    db.refresh(new_bill)

    return new_bill


@router.put("/{bill_id}", response_model=BillResponse)
async def update_bill(
    bill_id: str,
    bill_data: BillUpdate,
    current_user: dict = Depends(require_role(["Admin", "Doctor"])),
    db: Session = Depends(get_db),
):
    """Update bill details"""

    # Get bill
    bill = db.query(Bill).filter(Bill.id == bill_id).first()

    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found"
        )

    # Update fields
    update_data = bill_data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update"
        )

    for field, value in update_data.items():
        setattr(bill, field, value)

    db.commit()
    db.refresh(bill)

    return bill


@router.get("/appointment/{appointment_id}")
async def get_bill_by_appointment(
    appointment_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get bill for a specific appointment using relationships"""

    appointment = (
        db.query(Appointment)
        .options(joinedload(Appointment.bills))
        .filter(Appointment.id == appointment_id)
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found"
        )

    return {"appointment_id": str(appointment.id), "bills": appointment.bills}


# Insurance Routes
insurance_router = APIRouter(prefix="/insurance", tags=["Insurance"])


@insurance_router.get("/", response_model=List[InsuranceResponse])
async def get_all_insurance(
    current_user: dict = Depends(require_role(["Admin", "Doctor"])),
    db: Session = Depends(get_db),
):
    """Get all insurance records"""

    insurance_records = db.query(Insurance).order_by(Insurance.provider_name).all()
    return insurance_records


@insurance_router.get("/{insurance_id}", response_model=InsuranceResponse)
async def get_insurance(
    insurance_id: str,
    current_user: dict = Depends(require_role(["Admin", "Doctor"])),
    db: Session = Depends(get_db),
):
    """Get insurance by ID"""

    insurance = db.query(Insurance).filter(Insurance.id == insurance_id).first()

    if not insurance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Insurance not found"
        )

    return insurance


@insurance_router.post(
    "/", response_model=InsuranceResponse, status_code=status.HTTP_201_CREATED
)
async def create_insurance(
    insurance: InsuranceCreate,
    current_user: dict = Depends(require_role(["Admin"])),
    db: Session = Depends(get_db),
):
    """Add new insurance provider"""

    # Create new insurance
    new_insurance = Insurance(
        provider_name=insurance.provider_name,
        policy_number=insurance.policy_number,
        coverage_amount=insurance.coverage_amount,
        expiry_date=insurance.expiry_date,
    )

    db.add(new_insurance)
    db.commit()
    db.refresh(new_insurance)

    return new_insurance


@insurance_router.get("/{insurance_id}/bills")
async def get_insurance_bills(
    insurance_id: str,
    current_user: dict = Depends(require_role(["Admin", "Doctor"])),
    db: Session = Depends(get_db),
):
    """Get all bills associated with an insurance using relationships"""

    insurance = (
        db.query(Insurance)
        .options(joinedload(Insurance.bills))
        .filter(Insurance.id == insurance_id)
        .first()
    )

    if not insurance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Insurance not found"
        )

    return {
        "insurance_id": str(insurance.id),
        "provider_name": insurance.provider_name,
        "policy_number": insurance.policy_number,
        "bills": insurance.bills,
    }
