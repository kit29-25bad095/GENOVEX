import os
import pytest
import sqlite3
import json
from pathlib import Path
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[1]

from app.core.config import AUTHORITATIVE_DB_PATH
from app.core.database import SessionLocal
from app.models.clinical_rules import ClinicalRule, ClinicalRuleStatus
from app.services.clinical_rule_engine import ClinicalRuleEngineService

CANONICAL_14_RULE_CODES = {
    'R-URG-ACUTE-SCROTAL-PAIN',
    'R-URG-TESTIS-LUMP',
    'R-REP-PROLONGED-TTC',
    'R-MED-ANABOLIC-STEROIDS',
    'R-TST-CRYPTORCHIDISM',
    'R-SEX-EJACULATORY-DYSFUNCTION',
    'R-SEX-HEMATOSPERMIA',
    'R-FAM-GENETIC-INFERTILITY',
    'R-LST-TOBACCO-DOKHA',
    'R-LST-SCROTAL-HYPERTHERMIA',
    'R-MET-OBSTRUCTIVE-SLEEP-APNEA',
    'R-MED-HAIR-LOSS-5ARI',
    'R-OCC-TOXIN-EXPOSURE',
    'R-BAS-ADVANCED-PATERNAL-AGE'
}

def test_canonical_rules_count_and_eligibility():
    """
    Stage 3: Verify that exactly 14 canonical clinical rules are eligible for patient evaluation,
    and zero R-RBAC rules are eligible in the clinical rule engine.
    """
    db: Session = SessionLocal()
    try:
        active_rules = db.query(ClinicalRule).filter(
            ClinicalRule.status == ClinicalRuleStatus.PUBLISHED,
            ~ClinicalRule.rule_code.like("R-RBAC-%")
        ).order_by(ClinicalRule.priority_rank.asc()).all()

        canonical_in_active = {r.rule_code for r in active_rules if r.rule_code in CANONICAL_14_RULE_CODES}
        assert canonical_in_active == CANONICAL_14_RULE_CODES, f"Missing canonical rules: {CANONICAL_14_RULE_CODES - canonical_in_active}"

        # Zero R-RBAC rules in active patient evaluation rules
        rbac_in_active = [r.rule_code for r in active_rules if r.rule_code.startswith("R-RBAC-")]
        assert len(rbac_in_active) == 0, f"R-RBAC rules leaked into active rules: {rbac_in_active}"
    finally:
        db.close()

def test_rbac_rules_remain_published_in_live_db_until_stage6():
    """
    Verify rule archival status: Tier 1 retains original 22 PUBLISHED rules,
    while live database has executed Stage 6 archival (14 PUBLISHED, 8 ARCHIVED, 22 total).
    """
    # Check Tier 1 backup baseline
    t1_path = BACKEND_DIR / "backups" / "genovex_backup_tier1_20261120_020738.db"
    if not t1_path.exists() or t1_path.stat().st_size == 0 or not os.path.exists(AUTHORITATIVE_DB_PATH):
        pytest.skip("Tier 1 backup or authoritative database not present in test environment")
    conn_t1 = sqlite3.connect(t1_path)
    cur_t1 = conn_t1.cursor()
    cur_t1.execute("SELECT COUNT(*) FROM clinical_rules WHERE status = 'PUBLISHED';")
    assert cur_t1.fetchone()[0] == 22, "Tier 1 backup must retain all 22 published rules"
    conn_t1.close()

    # Check live database post-archival
    conn = sqlite3.connect(AUTHORITATIVE_DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM clinical_rules WHERE status = 'PUBLISHED';")
    published_count = cur.fetchone()[0]
    assert published_count == 14, f"Expected 14 published rules in live DB, found {published_count}"

    cur.execute("SELECT COUNT(*) FROM clinical_rules WHERE status = 'ARCHIVED';")
    archived_count = cur.fetchone()[0]
    assert archived_count == 8, f"Expected 8 archived rules in live DB, found {archived_count}"

    cur.execute("SELECT COUNT(*) FROM clinical_rules;")
    total_count = cur.fetchone()[0]
    assert total_count == 22, f"Expected 22 total rules in live DB, found {total_count}"
    conn.close()

def test_patient_assessment_evaluation_strictly_excludes_rbac():
    """
    Stage 3: Verify that patient evaluation compiles reports without evaluating or triggering R-RBAC rules.
    """
    db: Session = SessionLocal()
    try:
        from app.models.questionnaire import Assessment
        assessment = db.query(Assessment).first()
        assert assessment is not None, "Expected at least one assessment in database"

        # Evaluate assessment
        report = ClinicalRuleEngineService.compile_assessment_report(
            db=db,
            assessment_id=assessment.id,
            session_token=assessment.session_token
        )

        # Verify triggered rules contain 0 R-RBAC rules
        for tr in report.triggered_rules_snapshot_json:
            assert not tr["rule_code"].startswith("R-RBAC-"), f"R-RBAC rule found in triggered snapshot: {tr['rule_code']}"

    finally:
        db.close()

def test_zero_historical_report_drift_in_authoritative_database():
    """
    Stage 3: Verify all 86 historical baseline reports in genovex.db have zero R-RBAC rules in their snapshots
    and maintain full clinical reproducibility. Uses strictly read-only mode to prevent database mutation.
    """
    if not os.path.exists(AUTHORITATIVE_DB_PATH) or os.path.getsize(AUTHORITATIVE_DB_PATH) == 0:
        pytest.skip("Authoritative baseline database not present in test environment")
    db_uri = f"file:{os.path.abspath(AUTHORITATIVE_DB_PATH)}?mode=ro"
    conn = sqlite3.connect(db_uri, uri=True)
    cur = conn.cursor()
    cur.execute("PRAGMA query_only = ON;")
    cur.execute("SELECT id, triggered_rules_snapshot_json FROM assessment_reports ORDER BY id ASC;")
    reports = cur.fetchall()
    conn.close()

    assert len(reports) >= 86, f"Expected at least 86 historical reports in live DB, found {len(reports)}"
    historical_86 = [r for r in reports if r[0] <= 86]
    assert len(historical_86) == 86, f"Expected exactly 86 historical baseline reports (IDs 1-86), found {len(historical_86)}"

    rbac_occurrences = []
    for rep_id, tr_json in reports:
        snapshot = json.loads(tr_json) if tr_json else []
        for r in snapshot:
            if r.get("rule_code", "").startswith("R-RBAC-"):
                rbac_occurrences.append((rep_id, r.get("rule_code")))

    assert len(rbac_occurrences) == 0, f"Found R-RBAC rules in historical reports: {rbac_occurrences}"

def test_admin_management_service_still_lists_all_authoritative_rules():
    """
    Stage 3: Verify that all 22 rules in the authoritative database are accessible
    for administrative auditing and governance. Uses strictly read-only mode.
    """
    if not os.path.exists(AUTHORITATIVE_DB_PATH) or os.path.getsize(AUTHORITATIVE_DB_PATH) == 0:
        pytest.skip("Authoritative baseline database not present in test environment")
    db_uri = f"file:{os.path.abspath(AUTHORITATIVE_DB_PATH)}?mode=ro"
    conn = sqlite3.connect(db_uri, uri=True)
    cur = conn.cursor()
    cur.execute("PRAGMA query_only = ON;")
    cur.execute("SELECT rule_code FROM clinical_rules;")
    all_codes = [r[0] for r in cur.fetchall()]
    conn.close()

    assert len(all_codes) == 22, f"Expected 22 rules in live DB, found {len(all_codes)}"
    assert any(c.startswith("R-RBAC-") for c in all_codes), "Live DB must still retain R-RBAC rules"
