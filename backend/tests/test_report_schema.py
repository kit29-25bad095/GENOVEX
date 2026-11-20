import pytest
from datetime import datetime, timezone
from app.models.clinical_rules import ClinicalOutcomeTier
from app.schemas.assessment_report import AssessmentReportResponse

def test_assessment_report_schema_db_alias_deserialization():
    """Verify that AssessmentReportResponse successfully deserializes from DB JSON column names."""
    db_payload = {
        "id": 1,
        "report_reference": "REP-2026-0001",
        "assessment_id": "3f98c628-912b-4e41-bce2-6b95d9a9cb71",
        "session_token": "token-12345",
        "questionnaire_version_tag": "v1.0.0",
        "rule_engine_version": "v1.0.0",
        "outcome_tier": ClinicalOutcomeTier.TIER_2_RISK_FACTORS,
        "outcome_title_en": "Lifestyle Risk Identified",
        "outcome_title_ar": "تم تحديد مخاطر نمط الحياة",
        "outcome_description_en": "Clinical assessment indicates lifestyle optimization opportunities.",
        "outcome_description_ar": "يشير التقييم السريري إلى فرص تحسين نمط الحياة.",
        "is_urgent_red_flag": False,
        "urgent_emergency_guidance_en": None,
        "urgent_emergency_guidance_ar": None,
        "recommended_specialties": ["Andrology", "Lifestyle Medicine"],
        "recommended_next_steps_en": ["Consult an andrologist"],
        "recommended_next_steps_ar": ["استشر طبيب أمراض الذكورة"],
        "identified_risk_factors_json": [{"factor_code": "RF-SMOKE", "severity": "MODERATE"}],
        "triggered_rules_snapshot_json": [{"rule_code": "R-LIFE-01", "is_urgent_red_flag": False}],
        "responses_summary_json": [{"question_key": "smoke_habit", "answer_display_en": "Yes"}],
        "evidence_citations_json": [{"source": "EAU Guidelines 2024"}],
        "clinical_disclaimer_en": "This is an educational risk assessment, not a medical diagnosis.",
        "clinical_disclaimer_ar": "هذا تقييم تعليمي للمخاطر وليس تشخيصاً طبياً.",
        "is_locked": True,
        "generated_at": datetime.now(timezone.utc)
    }

    report = AssessmentReportResponse.model_validate(db_payload)

    # 1. Assessment id is string
    assert isinstance(report.assessment_id, str)
    assert report.assessment_id == "3f98c628-912b-4e41-bce2-6b95d9a9cb71"

    # 2. Wire serialization uses canonical keys
    serialized = report.model_dump(by_alias=True)
    assert "identified_risk_factors" in serialized
    assert "triggered_rules" in serialized
    assert "responses_summary" in serialized
    assert "evidence_citations" in serialized

    # Ensure no leaked internal _json suffixes in output
    assert "identified_risk_factors_json" not in serialized
    assert "triggered_rules_snapshot_json" not in serialized
    assert "responses_summary_json" not in serialized
    assert "evidence_citations_json" not in serialized

def test_assessment_report_schema_canonical_field_names():
    """Verify that AssessmentReportResponse accepts canonical field names directly (populate_by_name)."""
    payload = {
        "id": 2,
        "report_reference": "REP-2026-0002",
        "assessment_id": "7b84c8a1-8742-43bb-a53d-2490333b28f5",
        "session_token": "token-67890",
        "questionnaire_version_tag": "v1.0.0",
        "rule_engine_version": "v1.0.0",
        "outcome_tier": ClinicalOutcomeTier.TIER_4_URGENT,
        "outcome_title_en": "Specialist Evaluation Recommended",
        "outcome_title_ar": "يوصى بالتقييم التخصصي",
        "outcome_description_en": "Identified risks warrant specialist consultation.",
        "outcome_description_ar": "المخاطر المحددة تستدعي استشارة متخصصة.",
        "is_urgent_red_flag": True,
        "urgent_emergency_guidance_en": "Seek immediate evaluation.",
        "urgent_emergency_guidance_ar": "يجب مراجعة الطبيب فورا.",
        "recommended_specialties": ["Reproductive Urology"],
        "recommended_next_steps_en": ["Schedule clinical exam"],
        "recommended_next_steps_ar": ["حجز موعد فحص سريري"],
        "identified_risk_factors": [{"factor_code": "RF-VARICO", "severity": "HIGH"}],
        "triggered_rules": [{"rule_code": "R-TEST-02", "is_urgent_red_flag": True}],
        "responses_summary": [{"question_key": "varicocele_history", "answer_display_en": "Yes"}],
        "evidence_citations": [{"source": "WHO Laboratory Manual 6th Edition"}],
        "clinical_disclaimer_en": "Educational risk report only.",
        "clinical_disclaimer_ar": "تقرير تعليمي للمخاطر فقط.",
        "is_locked": True,
        "generated_at": datetime.now(timezone.utc)
    }

    report = AssessmentReportResponse.model_validate(payload)
    assert report.assessment_id == "7b84c8a1-8742-43bb-a53d-2490333b28f5"
    assert report.is_urgent_red_flag is True
    assert len(report.identified_risk_factors) == 1
    assert report.identified_risk_factors[0]["factor_code"] == "RF-VARICO"
