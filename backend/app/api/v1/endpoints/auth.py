from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.core.security import (
    User, AuditLog, RoleEnum, verify_password, create_access_token,
    get_current_user, require_roles
)
from app.schemas.auth import UserLoginRequest, TokenResponse, UserResponse, AuditLogResponse

router = APIRouter(prefix="/auth", tags=["Authentication & Security"])

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

@router.get("/users", response_model=List[UserResponse])
def list_system_users(db: Session = Depends(get_db)):
    """Lists available system personas (Admin, Clinician, Superadmin, Patient) for role verification"""
    return db.query(User).filter(User.is_active == True).all()

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
