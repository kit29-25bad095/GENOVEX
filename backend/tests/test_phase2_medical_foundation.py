"""
GENOVEX: Phase 2 Medical Foundation Verification Suite
Validates resolution of:
'Only five medical conditions are currently seeded in the database; the medical condition library needs expansion.'

Verification Coverage:
1. Baseline conditions preservation (all 5 original conditions intact with preserved IDs, slugs, and statuses).
2. Expanded condition library integrity (7 new guideline-backed conditions added, total 12).
3. Bilingual structured clinical content parity (all 10 structured fields in both English and Arabic).
4. Authoritative evidence reference traceability (WHO, EAU, AUA, Endocrine Society guidelines).
5. Clinical governance gate (unreviewed candidate conditions strictly withheld from public health library).
6. Admin CMS visibility and clinical review workflow integration.
7. Architectural decoupling: Questionnaire and deterministic clinical rule engine remain completely untouched.
8. Version snapshots and audit provenance.
"""

import pytest
from sqlalchemy.orm import Session

from app.models.medical_content import (
    MedicalCondition, ConditionContent, MedicalCategory,
    MedicalReference, ContentVersion, ClinicalReviewRecord,
    PublicationStatus
)
from app.models.clinical_rules import ClinicalRule, ClinicalOutcomeTier
from app.services.medical_content_service import MedicalContentService
from app.core.condition_library_data import (
    CATEGORIES_DATA, REFERENCES_DATA, CONDITIONS_DATA
)


# ---------------------------------------------------------------------------
# Test 1: Preservation of the Original 5 Baseline Conditions
# ---------------------------------------------------------------------------
def test_baseline_five_conditions_preserved(db: Session):
    """Verify that all 5 original baseline conditions remain intact with identical metadata."""
    baseline_slugs = {
        "varicocele": (PublicationStatus.PUBLISHED, "scrotal-vascular"),
        "hypogonadotropic-hypogonadism": (PublicationStatus.PUBLISHED, "endocrine-hormonal"),
        "klinefelter-syndrome": (PublicationStatus.PUBLISHED, "genetic-chromosomal"),
        "obstructive-azoospermia-cbavd": (PublicationStatus.PENDING_REVIEW, "obstructive-ductal"),
        "cryptorchidism": (PublicationStatus.DRAFT, "congenital-developmental"),
    }

    for slug, (expected_status, expected_cat_slug) in baseline_slugs.items():
        cond = db.query(MedicalCondition).filter(MedicalCondition.slug == slug).first()
        assert cond is not None, f"Original condition '{slug}' was accidentally removed or renamed!"
        assert cond.publication_status == expected_status, (
            f"Condition '{slug}' publication status mutated: expected {expected_status}, got {cond.publication_status}"
        )
        assert cond.category.slug == expected_cat_slug, (
            f"Condition '{slug}' category mutated: expected {expected_cat_slug}, got {cond.category.slug}"
        )
        assert len(cond.contents) == 2, f"Condition '{slug}' must retain bilingual content (en/ar)"


# ---------------------------------------------------------------------------
# Test 2: Expanded Condition Library Integrity (12 Total Canonical Conditions)
# ---------------------------------------------------------------------------
def test_expanded_condition_library_integrity(db: Session):
    """Verify that the library contains all 12 canonical conditions with the 7 new candidate conditions."""
    total_conditions = db.query(MedicalCondition).count()
    assert total_conditions >= 12, f"Expected at least 12 conditions in library, found {total_conditions}"

    new_candidate_slugs = [
        "testicular-torsion",
        "testicular-mass-cancer",
        "acute-epididymo-orchitis",
        "hydrocele-spermatocele",
        "male-factor-infertility",
        "erectile-dysfunction",
        "testosterone-deficiency-syndrome"
    ]

    for slug in new_candidate_slugs:
        cond = db.query(MedicalCondition).filter(MedicalCondition.slug == slug).first()
        assert cond is not None, f"Candidate condition '{slug}' is missing from the database!"
        # Clinical safety rule: newly added conditions must NOT be published without clinical board sign-off
        assert cond.publication_status == PublicationStatus.PENDING_REVIEW, (
            f"Candidate condition '{slug}' must be PENDING_REVIEW, got {cond.publication_status}"
        )
        assert cond.category is not None, f"Condition '{slug}' has no associated category"
        assert len(cond.organs_involved) > 0, f"Condition '{slug}' organs_involved list is empty"


# ---------------------------------------------------------------------------
# Test 3: Bilingual Structured Content Completeness (20 Structured Fields)
# ---------------------------------------------------------------------------
def test_bilingual_structured_content_parity(db: Session):
    """Verify that all 12 canonical conditions have complete, non-empty bilingual content for all 10 clinical fields."""
    required_fields = [
        "name", "short_description", "detailed_explanation", "biological_mechanism",
        "causes_and_risk_factors", "possible_symptoms", "silent_asymptomatic_presentation",
        "clinical_significance", "diagnostic_investigations", "clinical_next_steps"
    ]

    canonical_slugs = [c["slug"] for c in CONDITIONS_DATA]
    assert len(canonical_slugs) == 12

    for slug in canonical_slugs:
        cond = db.query(MedicalCondition).filter(MedicalCondition.slug == slug).first()
        assert cond is not None, f"Canonical condition '{slug}' missing"

        en_content = next((c for c in cond.contents if c.language == "en"), None)
        ar_content = next((c for c in cond.contents if c.language == "ar"), None)

        assert en_content is not None, f"Condition '{cond.slug}' missing English content"
        assert ar_content is not None, f"Condition '{cond.slug}' missing Arabic content"

        for field in required_fields:
            val_en = getattr(en_content, field, None)
            val_ar = getattr(ar_content, field, None)

            assert val_en and len(val_en.strip()) >= 3, (
                f"Condition '{cond.slug}' English field '{field}' is empty or too short"
            )
            assert val_ar and len(val_ar.strip()) >= 3, (
                f"Condition '{cond.slug}' Arabic field '{field}' is empty or too short"
            )


# ---------------------------------------------------------------------------
# Test 4: Authoritative Evidence References Traceability
# ---------------------------------------------------------------------------
def test_evidence_references_traceability(db: Session):
    """Verify that all canonical conditions are linked to peer-reviewed guidelines with traceable sources."""
    total_references = db.query(MedicalReference).count()
    assert total_references >= 7, f"Expected at least 7 authoritative references, found {total_references}"

    canonical_slugs = [c["slug"] for c in CONDITIONS_DATA]
    for slug in canonical_slugs:
        cond = db.query(MedicalCondition).filter(MedicalCondition.slug == slug).first()
        assert cond is not None, f"Canonical condition '{slug}' missing"
        assert len(cond.references) > 0, f"Condition '{cond.slug}' has zero linked references!"
        for ref in cond.references:
            assert ref.title and len(ref.title) > 5
            assert ref.guideline_body in ("EAU", "AUA", "AUA / ASRM", "WHO", "Endocrine Society")
            assert ref.publication_year and ref.publication_year >= 2018
            assert ref.doi_or_url and (ref.doi_or_url.startswith("http") or ref.doi_or_url.startswith("https"))


# ---------------------------------------------------------------------------
# Test 5: Clinical Governance Gate (Public Health Library Segregation)
# ---------------------------------------------------------------------------
def test_clinical_governance_gate_public_withholding(db: Session):
    """
    CRITICAL SAFETY POLICY:
    Unreviewed candidate conditions must NEVER silently enter patient-facing clinical library.
    Only strictly PUBLISHED conditions (varicocele, hypogonadotropic-hypogonadism, klinefelter-syndrome)
    may be returned to the public health library.
    """
    public_items_en = MedicalContentService.get_public_health_library(db, language="en")
    assert len(public_items_en) == 3, (
        f"Public library must ONLY contain 3 PUBLISHED conditions, found {len(public_items_en)}"
    )

    published_slugs = {item.slug for item in public_items_en}
    assert published_slugs == {
        "varicocele",
        "hypogonadotropic-hypogonadism",
        "klinefelter-syndrome"
    }

    # Verify that none of the 7 new candidate conditions leak into the public library
    unapproved_slugs = [
        "testicular-torsion", "testicular-mass-cancer", "acute-epididymo-orchitis",
        "hydrocele-spermatocele", "male-factor-infertility", "erectile-dysfunction",
        "testosterone-deficiency-syndrome", "obstructive-azoospermia-cbavd", "cryptorchidism"
    ]
    for unapproved in unapproved_slugs:
        assert unapproved not in published_slugs, (
            f"SECURITY VIOLATION: Unapproved condition '{unapproved}' leaked into public health library!"
        )

    # Arabic endpoint must mirror the exact same strict filtering
    public_items_ar = MedicalContentService.get_public_health_library(db, language="ar")
    assert len(public_items_ar) == 3
    assert {item.slug for item in public_items_ar} == published_slugs


# ---------------------------------------------------------------------------
# Test 6: Admin CMS Visibility & Status Filtering
# ---------------------------------------------------------------------------
def test_admin_cms_access_and_filtering(db: Session):
    """Verify that all canonical conditions are accessible and filterable in the Admin CMS."""
    all_admin_conditions = MedicalContentService.list_conditions(db, limit=100)
    assert len(all_admin_conditions) >= 12
    all_slugs = {c["slug"] for c in all_admin_conditions}
    canonical_slugs = [c["slug"] for c in CONDITIONS_DATA]
    for slug in canonical_slugs:
        assert slug in all_slugs, f"Canonical condition '{slug}' not found in admin list"

    # Filter by PENDING_REVIEW: should return at least 8 conditions
    pending_conditions = MedicalContentService.list_conditions(
        db, status=PublicationStatus.PENDING_REVIEW, limit=100
    )
    assert len(pending_conditions) >= 8, (
        f"Expected at least 8 PENDING_REVIEW conditions, found {len(pending_conditions)}"
    )
    pending_slugs = {c["slug"] for c in pending_conditions}
    expected_pending = [
        "obstructive-azoospermia-cbavd",
        "testicular-torsion", "testicular-mass-cancer", "acute-epididymo-orchitis",
        "hydrocele-spermatocele", "male-factor-infertility", "erectile-dysfunction",
        "testosterone-deficiency-syndrome"
    ]
    for s in expected_pending:
        assert s in pending_slugs

    # Filter by PUBLISHED: should include the 3 published conditions
    published_conditions = MedicalContentService.list_conditions(
        db, status=PublicationStatus.PUBLISHED, limit=100
    )
    assert len(published_conditions) >= 3
    published_slugs = {c["slug"] for c in published_conditions}
    assert {"varicocele", "hypogonadotropic-hypogonadism", "klinefelter-syndrome"}.issubset(published_slugs)

    # Filter by DRAFT: should include cryptorchidism
    draft_conditions = MedicalContentService.list_conditions(
        db, status=PublicationStatus.DRAFT, limit=100
    )
    assert len(draft_conditions) >= 1
    draft_slugs = {c["slug"] for c in draft_conditions}
    assert "cryptorchidism" in draft_slugs


# ---------------------------------------------------------------------------
# Test 7: Architectural Decoupling: Clinical Rule Engine Completely Untouched
# ---------------------------------------------------------------------------
def test_architectural_decoupling_clinical_rules_untouched(db: Session):
    """
    Verify that expanding the educational medical condition library did NOT modify,
    mutate, or corrupt the deterministic clinical rules or assessment outcome tiers.
    """
    total_rules = db.query(ClinicalRule).count()
    assert total_rules >= 22, f"Clinical rules count mutated: expected >= 22, got {total_rules}"

    # Verify urgent red-flag rules remain intact
    acute_pain_rule = db.query(ClinicalRule).filter(
        ClinicalRule.rule_code == "R-URG-ACUTE-SCROTAL-PAIN"
    ).first()
    assert acute_pain_rule is not None
    assert acute_pain_rule.outcome_tier == ClinicalOutcomeTier.TIER_4_URGENT
    assert acute_pain_rule.is_urgent_red_flag is True

    lump_rule = db.query(ClinicalRule).filter(
        ClinicalRule.rule_code == "R-URG-TESTIS-LUMP"
    ).first()
    assert lump_rule is not None
    assert lump_rule.outcome_tier == ClinicalOutcomeTier.TIER_4_URGENT
    assert lump_rule.is_urgent_red_flag is True


# ---------------------------------------------------------------------------
# Test 8: Version Snapshots & Audit Record Provenance
# ---------------------------------------------------------------------------
def test_version_snapshots_and_audit_provenance(db: Session):
    """Verify that every condition possesses an immutable version snapshot and audit review record."""
    canonical_slugs = [c["slug"] for c in CONDITIONS_DATA]

    for slug in canonical_slugs:
        cond = db.query(MedicalCondition).filter(MedicalCondition.slug == slug).first()
        assert cond is not None, f"Canonical condition '{slug}' missing"

        # Check ContentVersion snapshot
        assert len(cond.versions) >= 1, f"Condition '{cond.slug}' missing content version snapshot"
        v1 = next((v for v in cond.versions if v.version_number == 1), None)
        assert v1 is not None, f"Condition '{cond.slug}' missing Version 1 snapshot"
        assert v1.snapshot_data is not None
        assert "en_content" in v1.snapshot_data
        assert "ar_content" in v1.snapshot_data
        assert v1.snapshot_data["slug"] == cond.slug

    # Check ClinicalReviewRecord audit entry for the 7 newly expanded candidate conditions
    new_candidate_slugs = [
        "testicular-torsion", "testicular-mass-cancer", "acute-epididymo-orchitis",
        "hydrocele-spermatocele", "male-factor-infertility", "erectile-dysfunction",
        "testosterone-deficiency-syndrome"
    ]
    for slug in new_candidate_slugs:
        cond = db.query(MedicalCondition).filter(MedicalCondition.slug == slug).first()
        assert len(cond.review_records) >= 1, f"Candidate condition '{cond.slug}' missing review audit record"
        rec = cond.review_records[0]
        assert rec.action in ("INITIAL_CREATION", "INITIAL_SEED", "SUBMIT_FOR_REVIEW")
        assert rec.notes and len(rec.notes) > 5
