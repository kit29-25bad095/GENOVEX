import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import User, RoleEnum, get_password_hash, create_access_token
from app.models.facility import HealthcareFacility
from app.models.assessment_report import AssessmentReport, ClinicalOutcomeTier
from app.models.questionnaire import Assessment, AssessmentStatus
from main import app

client = TestClient(app)

@pytest.fixture
def auth_headers(db: Session):
    # Patient user
    patient = db.query(User).filter(User.email == "patient_nav_test@genovex.ae").first()
    if not patient:
        patient = User(
            email="patient_nav_test@genovex.ae",
            hashed_password=get_password_hash("PatientPass123!"),
            full_name="Nav Test Patient",
            role=RoleEnum.PATIENT,
            is_active=True
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

    # Admin user
    admin = db.query(User).filter(User.email == "admin_nav_test@genovex.ae").first()
    if not admin:
        admin = User(
            email="admin_nav_test@genovex.ae",
            hashed_password=get_password_hash("AdminPass123!"),
            full_name="Nav Test Admin",
            role=RoleEnum.ADMIN,
            is_active=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

    patient_token = create_access_token(data={"sub": patient.email, "role": patient.role.value, "uid": patient.id})
    admin_token = create_access_token(data={"sub": admin.email, "role": admin.role.value, "uid": admin.id})

    return {
        "patient": {"Authorization": f"Bearer {patient_token}"},
        "admin": {"Authorization": f"Bearer {admin_token}"},
        "patient_user": patient,
        "admin_user": admin
    }

def test_list_facilities_public():
    """Verifies that the healthcare facility directory is publicly accessible and paginated."""
    response = client.get("/api/v1/navigation/facilities?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 8
    assert len(data["items"]) <= 10
    assert "emirates" in data
    assert "specialties" in data

def test_filter_facilities_by_emirate():
    """Verifies filtering healthcare facilities by UAE Emirate."""
    response = client.get("/api/v1/navigation/facilities?emirate=DUBAI")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for item in data["items"]:
        assert item["emirate"] == "DUBAI"

def test_filter_facilities_by_specialty():
    """Verifies filtering facilities by offered clinical specialty."""
    response = client.get("/api/v1/navigation/facilities?specialty=Andrology")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for item in data["items"]:
        specs = [s.lower() for s in item["offered_specialties"]]
        assert any("androlog" in s for s in specs)

def test_filter_facilities_by_emergency():
    """Verifies filtering for facilities with 24/7 emergency service capability."""
    response = client.get("/api/v1/navigation/facilities?has_emergency=true")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for item in data["items"]:
        assert item["has_24_7_emergency"] is True

def test_search_facilities_text():
    """Verifies search by facility name or location."""
    response = client.get("/api/v1/navigation/facilities?search=Cleveland")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert "Cleveland" in data["items"][0]["name_en"]

def test_get_facility_detail_by_slug():
    """Verifies retrieving facility details by slug."""
    response = client.get("/api/v1/navigation/facilities/cleveland-clinic-abu-dhabi")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "cleveland-clinic-abu-dhabi"
    assert data["emirate"] == "ABU_DHABI"
    assert data["has_24_7_emergency"] is True
    assert data["phone_number"] is not None

def test_get_facility_not_found():
    """Verifies 404 response when querying non-existent facility."""
    response = client.get("/api/v1/navigation/facilities/non-existent-clinic-slug-999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_navigation_recommendations_for_report(db: Session):
    """
    Verifies that clinical navigation recommendations:
    1. Match recommended specialties from assessment report snapshot.
    2. Identify 24/7 emergency facilities if red flag is active.
    3. Distinctly assert that is_formal_referral is False.
    4. Provide non-diagnostic patient safety notices in EN and AR.
    """
    token = "test_nav_rec_token_123"
    # Create assessment & report in sandbox
    assessment = Assessment(
        id="test-nav-assessment-uuid",
        session_token=token,
        questionnaire_version_id=1,
        status=AssessmentStatus.SUBMITTED
    )
    db.add(assessment)
    db.commit()

    report = AssessmentReport(
        report_reference="GNX-RPT-NAV-TEST-01",
        assessment_id=assessment.id,
        session_token=token,
        questionnaire_version_tag="v1.0.0",
        rule_engine_version="v1.0.0",
        outcome_tier=ClinicalOutcomeTier.TIER_4_URGENT,
        outcome_title_en="Urgent Medical Assessment Required",
        outcome_title_ar="تقييم طبي عاجل",
        outcome_description_en="Clinical evaluation required for reported symptoms.",
        outcome_description_ar="فحص طبي عاجل مطلوب.",
        is_urgent_red_flag=True,
        recommended_specialties=["Male Reproductive Urologist / Andrologist"],
        recommended_next_steps_en=["Seek immediate emergency evaluation"],
        recommended_next_steps_ar=["مراجعة الطوارئ فوراً"],
        clinical_disclaimer_en="Non-diagnostic advice.",
        clinical_disclaimer_ar="إخلاء مسؤولية طبي."
    )
    db.add(report)
    db.commit()

    response = client.get(f"/api/v1/navigation/recommendations/{token}")
    assert response.status_code == 200
    data = response.json()

    assert data["report_reference"] == "GNX-RPT-NAV-TEST-01"
    assert data["is_urgent_red_flag"] is True
    assert data["is_formal_referral"] is False
    assert len(data["emergency_facilities"]) > 0
    assert len(data["recommended_facilities"]) > 0
    assert "CLINICAL NAVIGATION NOTICE" in data["navigation_notice_en"]
    assert "إشعار التوجيه السريري" in data["navigation_notice_ar"]

def test_create_facility_admin_only(auth_headers):
    """Verifies RBAC protection on administrative facility creation."""
    payload = {
        "slug": "test-new-andrology-center",
        "name_en": "New Emirates Andrology Clinic",
        "name_ar": "مركز الإمارات الجديد للذكورة",
        "emirate": "DUBAI",
        "regulatory_authority": "DHA",
        "facility_type": "SPECIALIZED_ANDROLOGY_CENTER",
        "address_en": "Dubai Healthcare City, Building 64",
        "address_ar": "مدينة دبي الطبية، مبنى 64",
        "city_en": "Dubai",
        "city_ar": "دبي",
        "phone_number": "+971-4-555-1234",
        "has_24_7_emergency": False,
        "has_andrology_specialist": True,
        "offered_specialties": ["Andrology", "Urology"],
        "is_verified": True,
        "is_active": True
    }

    # 1. Unauthenticated -> 401
    res_unauth = client.post("/api/v1/navigation/facilities", json=payload)
    assert res_unauth.status_code == 401

    # 2. Patient role -> 403
    res_patient = client.post("/api/v1/navigation/facilities", json=payload, headers=auth_headers["patient"])
    assert res_patient.status_code == 403

    # 3. Admin role -> 201
    res_admin = client.post("/api/v1/navigation/facilities", json=payload, headers=auth_headers["admin"])
    assert res_admin.status_code == 201
    data = res_admin.json()
    assert data["slug"] == "test-new-andrology-center"
    assert data["is_verified"] is True

def test_update_facility_admin_only(auth_headers, db: Session):
    """Verifies RBAC protection on administrative facility modification."""
    facility = db.query(HealthcareFacility).first()
    assert facility is not None

    update_payload = {
        "notes_en": "Updated by administrative governance audit."
    }

    # Patient -> 403
    res_patient = client.put(f"/api/v1/navigation/facilities/{facility.id}", json=update_payload, headers=auth_headers["patient"])
    assert res_patient.status_code == 403

    # Admin -> 200
    res_admin = client.put(f"/api/v1/navigation/facilities/{facility.id}", json=update_payload, headers=auth_headers["admin"])
    assert res_admin.status_code == 200
    assert res_admin.json()["notes_en"] == "Updated by administrative governance audit."
