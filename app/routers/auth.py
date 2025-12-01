from fastapi import APIRouter, Form, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.database import get_db
from app.models.user import User
from datetime import timedelta
from app.core.config import settings
from app.models.doctor import Doctor
from app.models.patient import Patient


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user (Admin, Doctor, or Patient)"""
    record = None
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user.email).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    if user.role == "Doctor":
        record = (
            db.query(Doctor)
            .filter(Doctor.email == user.email, Doctor.name == user.name)
            .first()
        )
        print(record)
        if not record:
            print("here")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No matching doctor profile found. Please contact admin.",
            )

    elif user.role == "Patient":
        record = (
            db.query(Patient)
            .filter(Patient.email == user.email, Patient.name == user.name)
            .first()
        )
        if not record:
            print("herdde")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No matching patient profile found. Please contact admin.",
            )

    # Create new user
    new_user = User(
        name=user.name,
        email=user.email,
        password_hash=get_password_hash(user.password),
        role=user.role,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    if record:
        record.user_id = new_user.id
        db.commit()
        db.refresh(record)

    return new_user


@router.post("/login")
async def login(
    username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)
):
    """Login and receive JWT token"""
    credentials = UserLogin(email=username, password=password)

    # Get user from database
    user = db.query(User).filter(User.email == credentials.email).first()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value},
        expires_delta=access_token_expires,
    )
    print("Generated Access Token:", access_token)  # Debug log
    print("User ID:", user.id)  # Debug log
    print("User Role:", user.role.value)  # Debug log
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "role": user.role.value,
        },
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get current logged-in user details"""

    user = db.query(User).filter(User.id == current_user["id"]).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return user


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout (token invalidation handled on client side)"""
    return {"message": "Successfully logged out"}
