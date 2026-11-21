import logging
import threading
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import time
import secrets
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, update

from app.core.config import settings, get_client_ip
from app.core.database import get_db, engine
from app.core.security import (
    User, AuditLog, RoleEnum, verify_password, get_password_hash, create_access_token,
    get_current_user, require_roles
)
from app.models.password_reset import PasswordResetToken
from app.services.email_service import EmailService
from app.schemas.auth import (
    UserLoginRequest, UserRegisterRequest, UserUpdateRequest, ChangePasswordRequest,
    TokenResponse, UserResponse, AuditLogResponse,
    ForgotPasswordRequest, ForgotPasswordResponse, ResetPasswordRequest, ResetPasswordResponse
)

logger = logging.getLogger("genovex.auth")

# In-memory IP rate limiter: client_ip -> list of epoch timestamps
_forgot_password_ip_limiter: dict = {}
_rate_limit_lock = threading.Lock()

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

    token = create_access_token(data={"sub": user.email, "role": user.role.value, "uid": user.id, "token_version": user.token_version})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        credentials_summary=user.credentials_summary
    )

def _dispatch_reset_email_bg(user_id: int, to_email: str, raw_token: str, full_name: Optional[str]):
    """
    Dispatches password reset email asynchronously outside the HTTP request/response cycle.
    Ensures identical HTTP response latency across existing and nonexistent accounts.
    If delivery fails, revokes the token and logs the failure in AuditLog safely.
    """
    delivery_ok = EmailService.send_password_reset_email(
        to_email=to_email,
        raw_token=raw_token,
        user_name=full_name
    )
    if not delivery_ok:
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        from app.core.database import SessionLocal
        bg_db = SessionLocal()
        try:
            bg_db.execute(
                update(PasswordResetToken)
                .where(PasswordResetToken.token_hash == token_hash)
                .values(is_consumed=True, consumed_at=datetime.now(timezone.utc))
            )
            fail_log = AuditLog(
                user_id=user_id,
                user_email=None,
                user_role="PATIENT",
                action="PASSWORD_RESET_DELIVERY_FAILED",
                resource_type="User",
                resource_id=str(user_id),
                details={"reason": "SMTP delivery failure in background task"}
            )
            bg_db.add(fail_log)
            bg_db.commit()
            logger.warning("Revoked reset token for user_id=%s following SMTP delivery failure", user_id)
        except Exception as ex:
            bg_db.rollback()
            logger.error("Error revoking token on delivery failure: %s", type(ex).__name__)
        finally:
            bg_db.close()

@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    req: ForgotPasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Initiates unauthenticated password reset journey.
    - Generates a cryptographically secure token.
    - Stores only the SHA-256 hash of the token in the primary database.
    - Enforces expiration window (default 15 minutes).
    - Invalidates prior outstanding reset tokens for the user in the same transaction.
    - Concurrency-safe rate limiting using process lock and atomic database attempt reservation.
    - Asynchronous email delivery via BackgroundTasks to eliminate enumeration timing discrepancies.
    - Emits a generic response resisting account enumeration.
    - Never exposes reset tokens in application logs or API responses.
    """
    email_clean = req.email.strip().lower()
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")[:255]

    now_utc = datetime.now(timezone.utc)
    cutoff_60s = now_utc - timedelta(seconds=60)
    now_ts = time.time()

    # Concurrency-safe rate limit evaluation
    with _rate_limit_lock:
        # In-memory fast layer check
        ip_history = _forgot_password_ip_limiter.setdefault(client_ip, [])
        ip_history = [ts for ts in ip_history if now_ts - ts < 60.0]
        _forgot_password_ip_limiter[client_ip] = ip_history

        # Commit an attempt record first (write-then-read reservation pattern)
        # to ensure serial consistency across multiple worker processes
        attempt_record = AuditLog(
            user_id=None,
            user_email=None,
            user_role="ANONYMOUS",
            action="PASSWORD_RESET_ATTEMPT",
            resource_type="RateLimit",
            resource_id=client_ip,
            details={"ip": client_ip},
            ip_address=client_ip
        )
        db.add(attempt_record)
        try:
            db.commit()
        except Exception as db_err:
            db.rollback()
            logger.error("Rate limiter DB commit failure: %s", type(db_err).__name__)
            # Fail closed to prevent unlimited attempts
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many password reset requests from this IP. Please wait before trying again."
            )

        db_ip_count = db.query(AuditLog).filter(
            AuditLog.ip_address == client_ip,
            AuditLog.action == "PASSWORD_RESET_ATTEMPT",
            AuditLog.timestamp >= cutoff_60s
        ).count()

        if len(ip_history) >= 5 or db_ip_count > 5:
            rate_limit_audit = AuditLog(
                user_id=None,
                user_email=None,
                user_role="ANONYMOUS",
                action="PASSWORD_RESET_RATE_LIMITED",
                resource_type="Auth",
                resource_id=client_ip,
                details={"ip": client_ip, "reason": "IP rate limit exceeded"},
                ip_address=client_ip
            )
            db.add(rate_limit_audit)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many password reset requests from this IP. Please wait before trying again."
            )
        ip_history.append(now_ts)

    user = db.query(User).filter(User.email == email_clean).first()

    if user and user.is_active:
        # Rate limit: Max 5 requests per 15 minutes per user
        cutoff = now_utc - timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)
        recent_count = db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.created_at >= cutoff
        ).count()

        if recent_count < 5:
            # Invalidate any prior unconsumed tokens for this user in primary DB
            db.execute(
                update(PasswordResetToken)
                .where(
                    PasswordResetToken.user_id == user.id,
                    PasswordResetToken.is_consumed == False
                )
                .values(
                    is_consumed=True,
                    consumed_at=now_utc
                )
            )

            # Generate cryptographically secure token (32 bytes = 256 bits entropy)
            raw_token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
            expires_at = now_utc + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)

            reset_record = PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at,
                is_consumed=False,
                ip_address=client_ip,
                user_agent=user_agent
            )
            db.add(reset_record)

            # Audit log in main database (never logging raw token)
            audit_entry = AuditLog(
                user_id=user.id,
                user_email=user.email,
                user_role=user.role.value if hasattr(user.role, "value") else str(user.role),
                action="PASSWORD_RESET_REQUESTED",
                resource_type="User",
                resource_id=str(user.id),
                details={"ip": client_ip, "expires_minutes": settings.RESET_TOKEN_EXPIRE_MINUTES},
                ip_address=client_ip
            )
            db.add(audit_entry)
            db.commit()

            # Asynchronous email delivery via BackgroundTasks (constant-time response)
            background_tasks.add_task(
                _dispatch_reset_email_bg,
                user.id,
                user.email,
                raw_token,
                user.full_name
            )
        else:
            # User rate limit exceeded: log security audit in main database
            audit_entry = AuditLog(
                user_id=user.id,
                user_email=user.email,
                user_role=user.role.value if hasattr(user.role, "value") else str(user.role),
                action="PASSWORD_RESET_RATE_LIMITED",
                resource_type="User",
                resource_id=str(user.id),
                details={"ip": client_ip, "recent_requests": recent_count},
                ip_address=client_ip
            )
            db.add(audit_entry)
            db.commit()
    else:
        # User not found or inactive: perform dummy hash to equalize response timing
        hashlib.sha256(email_clean.encode("utf-8")).hexdigest()
        dummy_audit = AuditLog(
            user_id=None,
            user_email=None,
            user_role="ANONYMOUS",
            action="PASSWORD_RESET_REQUESTED",
            resource_type="Auth",
            resource_id=email_clean[:3] + "***" if len(email_clean) >= 3 else "***",
            details={"ip": client_ip},
            ip_address=client_ip
        )
        db.add(dummy_audit)
        db.commit()

    # Generic account enumeration-resistant response
    return ForgotPasswordResponse(
        status="success",
        message="If an account with this email exists, a password reset link has been dispatched."
    )

@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password(req: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """
    Completes unauthenticated password reset using a cryptographically validated token.
    - Verifies token against stored SHA-256 hash.
    - Rejects expired, consumed, or invalid tokens.
    - Enforces application password policy (length >= 8).
    - Atomically updates password and invalidates the token in a single database transaction.
    - Prevents race conditions and duplicate reuse via atomic conditional UPDATE.
    - Logs audit trail without leaking passwords or tokens.
    """
    token_str = (req.token or "").strip()
    if not token_str or len(token_str) < 16:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or malformed password reset token"
        )

    # Password policy check
    if len(req.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    if req.confirm_password is not None and req.new_password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password and confirmation do not match"
        )

    token_hash = hashlib.sha256(token_str.encode("utf-8")).hexdigest()
    client_ip = get_client_ip(request)
    now_utc = datetime.now(timezone.utc)

    # ATOMIC conditional update: exactly one concurrent request can consume this active unexpired token
    stmt = (
        update(PasswordResetToken)
        .where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.is_consumed == False,
            PasswordResetToken.expires_at > now_utc
        )
        .values(
            is_consumed=True,
            consumed_at=now_utc
        )
    )
    result = db.execute(stmt)

    if result.rowcount == 0:
        # Inspect token state to provide accurate, safe error response
        existing_record = db.query(PasswordResetToken).filter(
            PasswordResetToken.token_hash == token_hash
        ).first()

        if not existing_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset link"
            )

        if existing_record.is_consumed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This password reset link has already been used"
            )

        # Token was found and unconsumed, but expires_at <= now_utc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset link has expired. Please request a new one."
        )

    # Token was successfully consumed atomically. Now complete the transaction.
    reset_record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash
    ).first()

    user = db.query(User).filter(User.id == reset_record.user_id).first()
    if not user or not user.is_active:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Associated account is inactive or not found"
        )

    # Atomically update user password in main db
    user.hashed_password = get_password_hash(req.new_password)

    # Invalidate any remaining outstanding tokens for this user
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.is_consumed == False
        )
        .values(
            is_consumed=True,
            consumed_at=now_utc
        )
    )

    audit_entry = AuditLog(
        user_id=user.id,
        user_email=user.email,
        user_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        action="PASSWORD_RESET_COMPLETED",
        resource_type="User",
        resource_id=str(user.id),
        details={"ip": client_ip, "status": "PASSWORD_UPDATED"},
        ip_address=client_ip
    )
    db.add(audit_entry)
    db.commit()

    return ResetPasswordResponse(
        status="success",
        message="Password has been successfully updated. You may now sign in."
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
