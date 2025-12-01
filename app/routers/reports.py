from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import case, func, and_
from typing import List, Optional
from datetime import date
from app.core.security import get_current_user, require_role
from app.database import get_db
from app.models.appointment import Appointment
from app.models.bill import Bill
from app.models.inventory import Inventory
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.report import Report
import json

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/appointments")
async def generate_appointment_report(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    current_user: dict = Depends(require_role(["Admin", "Doctor"])),
    db: Session = Depends(get_db),
):
    """Generate appointment reports with filters"""

    # Build query with filters
    query = db.query(Appointment).options(
        joinedload(Appointment.patient), joinedload(Appointment.doctor)
    )

    if start_date:
        query = query.filter(Appointment.appointment_date >= start_date)

    if end_date:
        query = query.filter(Appointment.appointment_date <= end_date)

    if status:
        query = query.filter(Appointment.status == status)

    appointments = query.order_by(Appointment.appointment_date.desc()).all()

    # Generate summary using SQLAlchemy aggregations
    total_appointments = len(appointments)

    # Status breakdown
    status_breakdown = db.query(
        Appointment.status, func.count(Appointment.id).label("count")
    )

    if start_date:
        status_breakdown = status_breakdown.filter(
            Appointment.appointment_date >= start_date
        )
    if end_date:
        status_breakdown = status_breakdown.filter(
            Appointment.appointment_date <= end_date
        )

    status_breakdown = status_breakdown.group_by(Appointment.status).all()
    status_dict = {status: count for status, count in status_breakdown}

    # Doctor-wise breakdown
    doctor_breakdown = db.query(
        Doctor.name, func.count(Appointment.id).label("count")
    ).join(Appointment)

    if start_date:
        doctor_breakdown = doctor_breakdown.filter(
            Appointment.appointment_date >= start_date
        )
    if end_date:
        doctor_breakdown = doctor_breakdown.filter(
            Appointment.appointment_date <= end_date
        )

    doctor_breakdown = doctor_breakdown.group_by(Doctor.name).all()
    doctor_dict = {name: count for name, count in doctor_breakdown}

    return {
        "report_type": "appointments",
        "filters": {"start_date": start_date, "end_date": end_date, "status": status},
        "summary": {
            "total_appointments": total_appointments,
            "status_breakdown": status_dict,
            "doctor_breakdown": doctor_dict,
        },
        "data": [
            {
                "id": str(apt.id),
                "date": apt.appointment_date,
                "time": apt.appointment_time,
                "status": apt.status,
                "patient_name": apt.patient.name,
                "doctor_name": apt.doctor.name,
                "doctor_specialty": apt.doctor.specialty,
            }
            for apt in appointments
        ],
    }


@router.get("/financial")
async def generate_financial_report(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    payment_status: Optional[str] = Query(None),
    current_user: dict = Depends(require_role(["Admin"])),
    db: Session = Depends(get_db),
):
    """Generate billing/finance reports"""

    # Build query with relationships
    query = (
        db.query(Bill)
        .join(Appointment)
        .options(
            joinedload(Bill.appointment).joinedload(Appointment.patient),
            joinedload(Bill.appointment).joinedload(Appointment.doctor),
            joinedload(Bill.insurance),
        )
    )

    if start_date:
        query = query.filter(Appointment.appointment_date >= start_date)

    if end_date:
        query = query.filter(Appointment.appointment_date <= end_date)

    if payment_status:
        query = query.filter(Bill.payment_status == payment_status)

    bills = query.order_by(Bill.created_at.desc()).all()

    # Calculate financial summary using SQLAlchemy aggregations
    summary_query = db.query(
        func.count(Bill.id).label("total_bills"),
        func.sum(Bill.amount).label("total_revenue"),
        func.sum(case((Bill.payment_status == "Paid", Bill.amount), else_=0)).label(
            "paid_amount"
        ),
        func.sum(case((Bill.payment_status == "Unpaid", Bill.amount), else_=0)).label(
            "unpaid_amount"
        ),
    ).join(Appointment)

    if start_date:
        summary_query = summary_query.filter(Appointment.appointment_date >= start_date)
    if end_date:
        summary_query = summary_query.filter(Appointment.appointment_date <= end_date)

    summary = summary_query.first()

    # Payment method breakdown
    payment_methods = db.query(
        Bill.payment_method,
        func.count(Bill.id).label("count"),
        func.sum(Bill.amount).label("total"),
    ).join(Appointment)

    if start_date:
        payment_methods = payment_methods.filter(
            Appointment.appointment_date >= start_date
        )
    if end_date:
        payment_methods = payment_methods.filter(
            Appointment.appointment_date <= end_date
        )

    payment_methods = (
        payment_methods.filter(Bill.payment_method.isnot(None))
        .group_by(Bill.payment_method)
        .all()
    )

    return {
        "report_type": "financial",
        "filters": {
            "start_date": start_date,
            "end_date": end_date,
            "payment_status": payment_status,
        },
        "summary": {
            "total_bills": summary.total_bills or 0,
            "total_revenue": float(summary.total_revenue or 0),
            "paid_amount": float(summary.paid_amount or 0),
            "unpaid_amount": float(summary.unpaid_amount or 0),
            "payment_methods": [
                {"method": method, "count": count, "total": float(total)}
                for method, count, total in payment_methods
            ],
        },
        "data": [
            {
                "id": str(bill.id),
                "amount": float(bill.amount),
                "payment_status": bill.payment_status,
                "payment_method": bill.payment_method,
                "appointment_date": bill.appointment.appointment_date,
                "patient_name": bill.appointment.patient.name,
                "doctor_name": bill.appointment.doctor.name,
                "insurance": bill.insurance.provider_name if bill.insurance else None,
            }
            for bill in bills
        ],
    }


@router.get("/inventory")
async def generate_inventory_report(
    category: Optional[str] = Query(None),
    low_stock_only: bool = Query(False),
    current_user: dict = Depends(require_role(["Admin", "Doctor"])),
    db: Session = Depends(get_db),
):
    """Generate inventory usage report"""

    # Build query
    query = db.query(Inventory)

    if category:
        query = query.filter(Inventory.category == category)

    if low_stock_only:
        query = query.filter(Inventory.quantity <= Inventory.reorder_level)

    items = query.order_by(Inventory.item_name).all()

    # Generate summary using SQLAlchemy aggregations
    summary_query = db.query(
        func.count(Inventory.id).label("total_items"),
        func.sum(Inventory.quantity).label("total_quantity"),
    )

    if category:
        summary_query = summary_query.filter(Inventory.category == category)
    if low_stock_only:
        summary_query = summary_query.filter(
            Inventory.quantity <= Inventory.reorder_level
        )

    summary = summary_query.first()

    # Low stock count
    low_stock_count = (
        db.query(func.count(Inventory.id))
        .filter(Inventory.quantity <= Inventory.reorder_level)
        .scalar()
    )

    # Category breakdown
    category_breakdown = (
        db.query(
            Inventory.category,
            func.count(Inventory.id).label("item_count"),
            func.sum(Inventory.quantity).label("total_quantity"),
        )
        .group_by(Inventory.category)
        .all()
    )

    return {
        "report_type": "inventory",
        "filters": {"category": category, "low_stock_only": low_stock_only},
        "summary": {
            "total_items": summary.total_items or 0,
            "total_quantity": summary.total_quantity or 0,
            "low_stock_count": low_stock_count,
            "category_breakdown": [
                {
                    "category": cat or "Uncategorized",
                    "item_count": count,
                    "total_quantity": qty or 0,
                }
                for cat, count, qty in category_breakdown
            ],
        },
        "data": [
            {
                "id": str(item.id),
                "item_name": item.item_name,
                "category": item.category,
                "quantity": item.quantity,
                "supplier": item.supplier,
                "reorder_level": item.reorder_level,
                "needs_reorder": item.quantity <= item.reorder_level,
            }
            for item in items
        ],
    }


@router.get("/patients/summary")
async def generate_patient_summary_report(
    current_user: dict = Depends(require_role(["Admin", "Doctor"])),
    db: Session = Depends(get_db),
):
    """Generate patient summary report"""

    # Total patients
    total_patients = db.query(func.count(Patient.id)).scalar()

    # Gender distribution
    gender_distribution = (
        db.query(Patient.gender, func.count(Patient.id).label("count"))
        .group_by(Patient.gender)
        .all()
    )

    # Age groups
    age_groups = (
        db.query(
            func.case(
                (Patient.age < 18, "Under 18"),
                (Patient.age.between(18, 35), "18-35"),
                (Patient.age.between(36, 50), "36-50"),
                (Patient.age.between(51, 65), "51-65"),
                else_="Over 65",
            ).label("age_group"),
            func.count(Patient.id).label("count"),
        )
        .filter(Patient.age.isnot(None))
        .group_by("age_group")
        .all()
    )

    # Patients with most appointments
    top_patients = (
        db.query(Patient.name, func.count(Appointment.id).label("appointment_count"))
        .join(Appointment)
        .group_by(Patient.id, Patient.name)
        .order_by(func.count(Appointment.id).desc())
        .limit(10)
        .all()
    )

    return {
        "report_type": "patient_summary",
        "summary": {
            "total_patients": total_patients,
            "gender_distribution": {
                gender or "Not specified": count
                for gender, count in gender_distribution
            },
            "age_distribution": {age_group: count for age_group, count in age_groups},
            "top_patients": [
                {"name": name, "appointment_count": count}
                for name, count in top_patients
            ],
        },
    }


@router.get("/doctors/performance")
async def generate_doctor_performance_report(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: dict = Depends(require_role(["Admin"])),
    db: Session = Depends(get_db),
):
    """Generate doctor performance report"""

    # Build query
    query = db.query(
        Doctor.id,
        Doctor.name,
        Doctor.specialty,
        func.count(Appointment.id).label("total_appointments"),
        func.sum(func.case((Appointment.status == "Completed", 1), else_=0)).label(
            "completed"
        ),
        func.sum(func.case((Appointment.status == "Cancelled", 1), else_=0)).label(
            "cancelled"
        ),
    ).join(Appointment)

    if start_date:
        query = query.filter(Appointment.appointment_date >= start_date)
    if end_date:
        query = query.filter(Appointment.appointment_date <= end_date)

    doctor_stats = (
        query.group_by(Doctor.id, Doctor.name, Doctor.specialty)
        .order_by(func.count(Appointment.id).desc())
        .all()
    )

    return {
        "report_type": "doctor_performance",
        "filters": {"start_date": start_date, "end_date": end_date},
        "data": [
            {
                "doctor_id": str(doc_id),
                "name": name,
                "specialty": specialty,
                "total_appointments": total,
                "completed": completed,
                "cancelled": cancelled,
                "completion_rate": round(
                    (completed / total * 100) if total > 0 else 0, 2
                ),
            }
            for doc_id, name, specialty, total, completed, cancelled in doctor_stats
        ],
    }


@router.get("/custom")
async def generate_custom_report(
    report_type: str = Query(
        ..., description="Type: patients, doctors, appointments, billing, inventory"
    ),
    filters: Optional[str] = Query(None, description="JSON string of custom filters"),
    current_user: dict = Depends(require_role(["Admin"])),
    db: Session = Depends(get_db),
):
    """Generate custom report by filters"""

    valid_types = ["patients", "doctors", "appointments", "billing", "inventory"]
    if report_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid report type. Must be one of: {', '.join(valid_types)}",
        )

    # Map report types to models
    model_map = {
        "patients": Patient,
        "doctors": Doctor,
        "appointments": Appointment,
        "billing": Bill,
        "inventory": Inventory,
    }

    model = model_map[report_type]
    data = db.query(model).order_by(model.created_at.desc()).all()

    # Save report metadata
    new_report = Report(
        type=report_type,
        generated_by=current_user["id"],
        filters_applied=json.loads(filters) if filters else None,
        data_summary=f"Total records: {len(data)}",
    )

    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    return {
        "report_id": str(new_report.id),
        "report_type": report_type,
        "generated_at": new_report.created_at,
        "generated_by": current_user["id"],
        "summary": {"total_records": len(data)},
        "data": data,
    }


@router.get("/history")
async def get_report_history(
    current_user: dict = Depends(require_role(["Admin"])), db: Session = Depends(get_db)
):
    """Get history of generated reports"""

    reports = db.query(Report).order_by(Report.created_at.desc()).limit(50).all()

    return {
        "reports": [
            {
                "id": str(report.id),
                "type": report.type,
                "generated_by": (
                    str(report.generated_by) if report.generated_by else None
                ),
                "generated_at": report.created_at,
                "filters": report.filters_applied,
                "summary": report.data_summary,
            }
            for report in reports
        ]
    }
