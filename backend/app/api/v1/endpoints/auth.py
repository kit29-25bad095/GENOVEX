from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.core.security import (
    User, AuditLog, RoleEnum, verify_password, get_password_hash, create_access_token,
    get_current_user, require_roles
)
from app.schemas.auth import (
    UserLoginRequest, UserRegisterRequest, UserUpdateRequest, ChangePasswordRequest,
    TokenResponse, UserResponse, AuditLogResponse
)

router = APIRouter(prefix="/auth", tags=["Authentication & Security"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(register_req: UserRegisterRequest, request: Request, db: Session = Depends(get_db)):
    """Registers a new user (default role: PATIENT). Administrative roles require invite."""
    existing = db.query(User).filter(User.email == register_req.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists"
        )
    
    new_user = User(
        email=register_req.email.lower(),
        hashed_password=get_password_hash(register_req.password),
        full_name=register_req.full_name,
        role=RoleEnum.PATIENT,
        credentials_summary=register_req.credentials_summary or "Registered Health Seeker",
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    audit_entry = AuditLog(
        user_id=new_user.id,
        user_email=new_user.email,
        user_role=new_user.role.value,
        action="USER_REGISTRATION",
        resource_type="User",
        resource_id=str(new_user.id),
        details={"status": "REGISTERED"},
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    db.add(audit_entry)
    db.commit()

    return new_user

@router.post("/login", response_model=TokenResponse)
def login(login_req: UserLoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticate user with email and password, issuing a signed JWT token"""
    user = db.query(User).filter(User.email == login_req.email.lower()).first()
    if not user or not verify_password(login_req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    # Log successful login
    audit_entry = AuditLog(
        user_id=user.id,
        user_email=user.email,
        user_role=user.role.value,
        action="USER_LOGIN",
        resource_type="User",
        resource_id=str(user.id),
        details={"login_status": "SUCCESS"},
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    db.add(audit_entry)
    db.commit()

    token = create_access_token(data={"sub": user.email, "role": user.role.value, "uid": user.id})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        credentials_summary=user.credentials_summary
    )

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Retrieve profile and assigned role of authenticated user"""
    return current_user

@router.put("/me", response_model=UserResponse)
def update_user_profile(
    update_req: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates user profile details (full_name, credentials_summary)"""
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if update_req.full_name is not None:
        user.full_name = update_req.full_name.strip()
    if update_req.credentials_summary is not None:
        user.credentials_summary = update_req.credentials_summary.strip()
    db.commit()
    db.refresh(user)
    return user

@router.post("/change-password")
def change_user_password(
    password_req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Securely updates password for authenticated user"""
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user or not verify_password(password_req.old_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    if len(password_req.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long"
        )
    user.hashed_password = get_password_hash(password_req.new_password)
    db.commit()
    return {"status": "success", "message": "Password updated successfully"}

@router.get("/users", response_model=List[UserResponse])
def list_system_users(db: Session = Depends(get_db)):
    """Lists available system personas (Admin, Clinician, Superadmin, Patient) for role verification"""
    return db.query(User).filter(User.is_active == True).all()

@router.get("/privacy/export-data", summary="Export personal data (UAE PDPL / GDPR)")
def export_user_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Exports all personal account data, associated assessments, and activity logs
    in compliance with UAE Personal Data Protection Law and international privacy standards.
    """
    user_record = {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "is_active": current_user.is_active
    }

    from app.models.questionnaire import Assessment
    assessments = db.query(Assessment).filter(Assessment.user_id == current_user.id).all()
    assessment_data = [
        {
            "id": a.id,
            "session_token": a.session_token,
            "status": a.status.value if hasattr(a.status, "value") else str(a.status),
            "started_at": a.started_at.isoformat() if a.started_at else None,
            "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None
        }
        for a in assessments
    ]

    return {
        "export_timestamp": datetime.now(timezone.utc).isoformat(),
        "regulatory_framework": "UAE Federal Decree-Law No. 45 of 2021 on Personal Data Protection",
        "user_profile": user_record,
        "assessments": assessment_data
    }

@router.post("/privacy/delete-account", summary="Request account deletion & data erasure")
def request_account_deletion(
    confirm: bool = Query(..., description="Explicit confirmation of account deletion"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Executes a formal account deletion and de-identification workflow.
    Deactivates user access, redacts email and profile identifiers, and logs compliance audit.
    """
    if not confirm:
        raise HTTPException(status_code=400, detail="Explicit confirmation required to delete account")

    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent deletion of final active superadmin
    if user.role == RoleEnum.SUPERADMIN:
        active_superadmins = db.query(User).filter(
            User.role == RoleEnum.SUPERADMIN,
            User.is_active == True
        ).count()
        if active_superadmins <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last remaining active SuperAdmin account"
            )

    user.is_active = False
    anonymized_tag = f"deleted_user_{user.id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    user.email = f"{anonymized_tag}@redacted.local"
    user.full_name = "Redacted User"

    audit_entry = AuditLog(
        user_id=user.id,
        user_email=user.email,
        user_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        action="USER_DATA_ERASURE",
        resource_type="User",
        resource_id=str(user.id),
        details={"status": "ANONYMIZED_AND_DEACTIVATED"},
        timestamp=datetime.now(timezone.utc)
    )
    db.add(audit_entry)
    db.commit()

    return {
        "status": "success",
        "message": "Account has been permanently deactivated and personal identifiers anonymized in accordance with privacy laws."
    }

# Audit Log Route (Protected: Admin & SuperAdmin only)
audit_router = APIRouter(prefix="/admin", tags=["Security & Audit Logs"])

@audit_router.get("/audit-logs", response_model=List[AuditLogResponse])
def get_system_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action code"),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """
    Retrieves immutable audit trail logs for clinical and security oversight.
    Requires ADMIN or SUPERADMIN role.
    """
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    return query.order_by(desc(AuditLog.timestamp)).limit(limit).all()


@audit_router.get("/users", response_model=List[UserResponse])
def get_all_users_admin(
    role: Optional[RoleEnum] = None,
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """
    Retrieves all registered users for administration.
    Requires ADMIN or SUPERADMIN role.
    """
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    return query.order_by(User.id.asc()).all()


@audit_router.put("/users/{user_id}", response_model=UserResponse)
def update_user_role_and_status(
    user_id: int,
    req: UserUpdateRequest,
    request: Request,
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """
    Updates user account role, credentials summary, or active status.
    Emits an immutable AuditLog entry with actor details.
    """
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Superadmin safety check: only superadmin can modify another superadmin or grant superadmin
    if target_user.role == RoleEnum.SUPERADMIN and current_user.role != RoleEnum.SUPERADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Superadmins can modify Superadmin accounts")
    if req.role == RoleEnum.SUPERADMIN and current_user.role != RoleEnum.SUPERADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Superadmins can assign Superadmin role")

    prev_role = target_user.role.value
    prev_status = target_user.is_active

    if req.role is not None:
        target_user.role = req.role
    if req.credentials_summary is not None:
        target_user.credentials_summary = req.credentials_summary
    if req.is_active is not None:
        target_user.is_active = req.is_active
    if req.full_name is not None:
        target_user.full_name = req.full_name

    audit_entry = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=current_user.role.value,
        action="UPDATE_USER_ROLE",
        resource_type="User",
        resource_id=str(target_user.id),
        details={
            "target_email": target_user.email,
            "old_role": prev_role,
            "new_role": target_user.role.value,
            "old_active": prev_status,
            "new_active": target_user.is_active
        },
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(target_user)
    return target_user
