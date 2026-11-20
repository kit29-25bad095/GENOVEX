from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import json
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from fastapi import HTTPException, status

from app.models.facility import HealthcareFacility
from app.models.assessment_report import AssessmentReport
from app.models.questionnaire import Assessment
from app.schemas.clinical_navigation import (
    FacilityCreateRequest, FacilityUpdateRequest, FacilityResponse,
    FacilityListResponse, NavigationRecommendationResponse
)
from app.core.security import User, AuditLog

class ClinicalNavigationService:
    """
    Clinical Navigation & Healthcare Provider Directory Service.
    Enforces safe, non-diagnostic guidance, verified UAE facility matching,
    and clear separation from formal clinician referrals.
    """

    @classmethod
    def list_facilities(
        cls,
        db: Session,
        specialty: Optional[str] = None,
        emirate: Optional[str] = None,
        facility_type: Optional[str] = None,
        has_emergency: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> FacilityListResponse:
        """Queries and filters healthcare facilities in the UAE."""
        query = db.query(HealthcareFacility).filter(HealthcareFacility.is_active == True)

        if emirate:
            query = query.filter(HealthcareFacility.emirate == emirate.upper())
        if facility_type:
            query = query.filter(HealthcareFacility.facility_type == facility_type.upper())
        if has_emergency is not None:
            query = query.filter(HealthcareFacility.has_24_7_emergency == has_emergency)
        if is_verified is not None:
            query = query.filter(HealthcareFacility.is_verified == is_verified)

        if search:
            s = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    HealthcareFacility.name_en.ilike(s),
                    HealthcareFacility.name_ar.ilike(s),
                    HealthcareFacility.city_en.ilike(s),
                    HealthcareFacility.city_ar.ilike(s),
                    HealthcareFacility.address_en.ilike(s)
                )
            )

        all_facilities = query.order_by(
            HealthcareFacility.has_24_7_emergency.desc(),
            HealthcareFacility.name_en.asc()
        ).all()

        def _get_specs_list(val) -> List[str]:
            if not val:
                return []
            if isinstance(val, list):
                return [str(x) for x in val]
            if isinstance(val, str):
                try:
                    p = json.loads(val)
                    if isinstance(p, list):
                        return [str(x) for x in p]
                except Exception:
                    pass
            return []

        # If specialty filter requested, check JSON list in memory for broad SQLite/Postgres compatibility
        if specialty:
            target_spec = specialty.lower().strip()
            stem = target_spec[:-1] if target_spec.endswith("y") else target_spec
            filtered = []
            for f in all_facilities:
                specs = [x.lower() for x in _get_specs_list(f.offered_specialties)]
                if any(target_spec in x or stem in x for x in specs):
                    filtered.append(f)
            all_facilities = filtered

        total = len(all_facilities)
        start = (page - 1) * page_size
        end = start + page_size
        paged_items = all_facilities[start:end]

        # Gather distinct metadata for filter pills
        raw_emirates = db.query(HealthcareFacility.emirate).distinct().all()
        emirates_list = sorted([r[0] for r in raw_emirates if r[0]])

        # Gather distinct specialties
        all_specs_set = set()
        for f in db.query(HealthcareFacility.offered_specialties).filter(HealthcareFacility.is_active == True).all():
            for item in _get_specs_list(f[0]):
                all_specs_set.add(item)
        specialties_list = sorted(list(all_specs_set))

        return FacilityListResponse(
            items=[FacilityResponse.model_validate(f) for f in paged_items],
            total=total,
            page=page,
            page_size=page_size,
            emirates=emirates_list,
            specialties=specialties_list
        )

    @classmethod
    def get_facility(cls, db: Session, identifier: str) -> FacilityResponse:
        """Retrieves a single facility by slug or primary key ID."""
        query = db.query(HealthcareFacility)
        if identifier.isdigit():
            facility = query.filter(HealthcareFacility.id == int(identifier)).first()
        else:
            facility = query.filter(HealthcareFacility.slug == identifier).first()

        if not facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Healthcare facility '{identifier}' not found"
            )
        return FacilityResponse.model_validate(facility)

    @classmethod
    def get_recommendations_for_report(
        cls,
        db: Session,
        session_token_or_ref: str,
        current_user: Optional[User] = None
    ) -> NavigationRecommendationResponse:
        """
        Generates safe, non-diagnostic clinical navigation recommendations matching an assessment report.
        Prioritizes verified facilities offering relevant specialties, and identifies 24/7 emergency centers.
        """
        # Lookup report
        report = (
            db.query(AssessmentReport)
            .filter(
                or_(
                    AssessmentReport.session_token == session_token_or_ref,
                    AssessmentReport.report_reference == session_token_or_ref,
                    AssessmentReport.assessment_id == session_token_or_ref
                )
            )
            .first()
        )

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment report snapshot not found for clinical navigation"
            )

        recommended_specialties = report.recommended_specialties or []
        is_urgent = bool(report.is_urgent_red_flag)
        tier_val = getattr(report.outcome_tier, "value", str(report.outcome_tier))

        # Query all verified active facilities
        verified_facilities = (
            db.query(HealthcareFacility)
            .filter(
                HealthcareFacility.is_active == True,
                HealthcareFacility.is_verified == True
            )
            .all()
        )

        matched_facilities: List[HealthcareFacility] = []
        emergency_facilities: List[HealthcareFacility] = []

        # Keywords from recommended specialties
        target_keywords = set()
        for s in recommended_specialties:
            for word in s.lower().replace("/", " ").replace("-", " ").split():
                if len(word) > 3 and word not in ("male", "health", "care", "clinic"):
                    target_keywords.add(word)

        for f in verified_facilities:
            if f.has_24_7_emergency:
                emergency_facilities.append(f)

            raw_specs = f.offered_specialties
            if isinstance(raw_specs, str):
                try:
                    raw_specs = json.loads(raw_specs)
                except Exception:
                    raw_specs = []
            f_specs_text = " ".join([str(x).lower() for x in (raw_specs or [])])
            if any(k in f_specs_text for k in target_keywords) or not target_keywords:
                matched_facilities.append(f)

        # Fallback: if no specific match, provide specialized andrology & tertiary centers
        if not matched_facilities:
            matched_facilities = [
                f for f in verified_facilities
                if f.has_andrology_specialist or f.facility_type in ("SPECIALIZED_ANDROLOGY_CENTER", "TERTIARY_HOSPITAL")
            ]

        notice_en = (
            "CLINICAL NAVIGATION NOTICE: This directory is provided solely for educational navigation and "
            "identifying licensed UAE healthcare facilities with specialized andrology and reproductive medicine services. "
            "This does NOT constitute a doctor-patient relationship, medical diagnosis, or formal physician referral. "
            "In emergency situations with acute scrotal pain or swelling, immediately visit a 24/7 emergency hospital department."
        )
        notice_ar = (
            "إشعار التوجيه السريري: يتم توفير هذا الدليل فقط لغايات التوجيه الإكلينيكي وتحديد المنشآت الصحية "
            "المرخصة في دولة الإمارات التي تضم خدمات الذكورة وطب الإنجاب التخصصي. لا تشكل هذه المعلومات علاقة "
            "بين طبيب ومريض أو تشخيصاً طبياً أو إحالة طبية رسمية. في الحالات الطارئة المصحوبة بآلام حادة أو تورم، "
            "يرجى التوجه فوراً إلى قسم الطوارئ (24/7)."
        )

        return NavigationRecommendationResponse(
            assessment_id=report.assessment_id,
            report_reference=report.report_reference,
            outcome_tier=tier_val,
            is_urgent_red_flag=is_urgent,
            recommended_specialties=recommended_specialties,
            recommended_facilities=[FacilityResponse.model_validate(f) for f in matched_facilities[:10]],
            emergency_facilities=[FacilityResponse.model_validate(f) for f in emergency_facilities[:5]],
            is_formal_referral=False,
            navigation_notice_en=notice_en,
            navigation_notice_ar=notice_ar
        )

    @classmethod
    def create_facility(
        cls,
        db: Session,
        facility_req: FacilityCreateRequest,
        admin_user: User
    ) -> FacilityResponse:
        """Administrative creation of a new healthcare facility entry."""
        existing = db.query(HealthcareFacility).filter(HealthcareFacility.slug == facility_req.slug).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Facility with slug '{facility_req.slug}' already exists"
            )

        new_facility = HealthcareFacility(**facility_req.model_dump())
        db.add(new_facility)
        db.commit()
        db.refresh(new_facility)

        try:
            audit = AuditLog(
                user_id=admin_user.id,
                user_email=admin_user.email,
                user_role=admin_user.role.value if hasattr(admin_user.role, "value") else str(admin_user.role),
                action="CREATE_HEALTHCARE_FACILITY",
                resource_type="HealthcareFacility",
                resource_id=str(new_facility.id),
                details={"slug": new_facility.slug, "name_en": new_facility.name_en},
                timestamp=datetime.now(timezone.utc)
            )
            db.add(audit)
            db.commit()
        except Exception:
            pass

        return FacilityResponse.model_validate(new_facility)

    @classmethod
    def update_facility(
        cls,
        db: Session,
        facility_id: int,
        facility_req: FacilityUpdateRequest,
        admin_user: User
    ) -> FacilityResponse:
        """Administrative modification of an existing healthcare facility entry."""
        facility = db.query(HealthcareFacility).filter(HealthcareFacility.id == facility_id).first()
        if not facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Healthcare facility with ID {facility_id} not found"
            )

        update_data = facility_req.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(facility, key, value)

        facility.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(facility)

        try:
            audit = AuditLog(
                user_id=admin_user.id,
                user_email=admin_user.email,
                user_role=admin_user.role.value if hasattr(admin_user.role, "value") else str(admin_user.role),
                action="UPDATE_HEALTHCARE_FACILITY",
                resource_type="HealthcareFacility",
                resource_id=str(facility.id),
                details={"updated_fields": list(update_data.keys())},
                timestamp=datetime.now(timezone.utc)
            )
            db.add(audit)
            db.commit()
        except Exception:
            pass

        return FacilityResponse.model_validate(facility)
