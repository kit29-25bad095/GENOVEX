import pytest
import hashlib
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import AUTHORITATIVE_DB_PATH, settings
from app.core.database import SessionLocal, get_db
from app.core.security import User, RoleEnum, AuditLog
from app.models.questionnaire import (
    QuestionnaireVersion, Question, Assessment, AssessmentResponse,
    QuestionnaireStatus, QuestionDomain, QuestionType, AssessmentStatus
)
from app.models.assessment_report import AssessmentReport, ClinicalOutcomeTier
from app.models.clinical_rules import ClinicalRule, ClinicalRuleStatus
from app.schemas.questionnaire import (
    SaveDomainResponsesRequest, AnswerInput, QuestionResponse
)
from app.services.questionnaire_service import QuestionnaireService
from app.services.adaptive_branching import AdaptiveBranchingService
from app.services.clinical_rule_engine import ClinicalRuleEngineService
from main import app as fastapi_app

# =============================================================================
# Acceptance Criteria 1: Topological DAG Cycle Rejection
# =============================================================================
def test_topological_dag_cycle_rejection():
    """Validates that Kahn's algorithm detects circular dependencies and raises HTTP 400/422."""
    q1 = Question(id=1, question_key="Q1", conditional_parent_key="Q2", conditional_trigger_values=["yes"])
    q2 = Question(id=2, question_key="Q2", conditional_parent_key="Q1", conditional_trigger_values=["yes"])
    
    with pytest.raises(HTTPException) as exc_info:
        AdaptiveBranchingService.validate_questionnaire_dag([q1, q2])
    
    assert exc_info.value.status_code in (400, 422)
    assert "Circular dependency detected" in exc_info.value.detail


# =============================================================================
# Acceptance Criteria 2: Dangling Parent Rejection
# =============================================================================
def test_dangling_parent_rejection():
    """Validates that references to non-existent parent questions raise HTTP 400/422."""
    q1 = Question(id=1, question_key="Q1", conditional_parent_key="NON_EXISTENT_PARENT", conditional_trigger_values=["yes"])
    
    with pytest.raises(HTTPException) as exc_info:
        AdaptiveBranchingService.validate_questionnaire_dag([q1])
    
    assert exc_info.value.status_code in (400, 422)
    assert "non-existent parent" in exc_info.value.detail


# =============================================================================
# Acceptance Criteria 3: Single-Parent Conditional Delivery & Safe Answers
# =============================================================================
def test_conditional_question_visibility():
    """Validates that follow-up questions are delivered if and only if parent trigger matches."""
    child = Question(
        id=2,
        question_key="Q_CHILD",
        conditional_parent_key="Q_PARENT",
        conditional_trigger_values=["yes"]
    )

    # 1. Parent answer matches -> Visible
    saved_answers = {"Q_PARENT": {"answer_value": "yes", "is_unsure": False, "is_prefer_not_to_say": False}}
    assert AdaptiveBranchingService.evaluate_question_visibility(child, saved_answers) is True

    # 2. Parent answer does not match -> Hidden
    saved_answers = {"Q_PARENT": {"answer_value": "no", "is_unsure": False, "is_prefer_not_to_say": False}}
    assert AdaptiveBranchingService.evaluate_question_visibility(child, saved_answers) is False

    # 3. Safe Answer Principle: Unsure -> Hidden (never triggers child)
    saved_answers = {"Q_PARENT": {"answer_value": None, "is_unsure": True, "is_prefer_not_to_say": False}}
    assert AdaptiveBranchingService.evaluate_question_visibility(child, saved_answers) is False

    # 4. Safe Answer Principle: Prefer Not to Say -> Hidden
    saved_answers = {"Q_PARENT": {"answer_value": None, "is_unsure": False, "is_prefer_not_to_say": True}}
    assert AdaptiveBranchingService.evaluate_question_visibility(child, saved_answers) is False


# =============================================================================
# Acceptance Criteria 4: Contract Dual-Aliasing
# =============================================================================
def test_contract_dual_aliasing():
    """Validates that QuestionResponse outputs both conditional_trigger_values and conditional_parent_value."""
    db = SessionLocal()
    try:
        q = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY_TYPE").first()
        assert q is not None
        resp = QuestionResponse.model_validate(q)
        assert resp.conditional_trigger_values == ["yes"]
        assert resp.conditional_parent_value == "yes"
        assert resp.question_code == "Q_TESTIS_SURGERY_TYPE"
    finally:
        db.close()


# =============================================================================
# Acceptance Criteria 5: Canonical 5-State Database Persistence
# =============================================================================
def test_five_state_database_persistence():
    """Validates that all five states remain distinct in DB and null-flagged rows are rejected."""
    db = SessionLocal()
    try:
        start = QuestionnaireService.start_or_resume_assessment(db)
        aid = start.assessment_id

        # Look up question ID
        q_parent = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY").first()
        assert q_parent is not None

        # State 1: Concrete affirmative answer
        QuestionnaireService.save_domain_responses(
            db, assessment_id=aid,
            data=SaveDomainResponsesRequest(
                domain_code=QuestionDomain.TESTICULAR_HISTORY,
                answers=[AnswerInput(question_id=q_parent.id, question_key=q_parent.question_key, answer_value="yes")]
            )
        )
        r1 = db.query(AssessmentResponse).filter(
            AssessmentResponse.assessment_id == aid,
            AssessmentResponse.question_key == "Q_TESTIS_SURGERY"
        ).first()
        assert r1 is not None
        assert r1.answer_value == "yes"
        assert r1.is_unsure is False
        assert r1.is_prefer_not_to_say is False

        # State 2: Concrete negative answer
        QuestionnaireService.save_domain_responses(
            db, assessment_id=aid,
            data=SaveDomainResponsesRequest(
                domain_code=QuestionDomain.TESTICULAR_HISTORY,
                answers=[AnswerInput(question_id=q_parent.id, question_key=q_parent.question_key, answer_value="no")]
            )
        )
        r2 = db.query(AssessmentResponse).filter(
            AssessmentResponse.assessment_id == aid,
            AssessmentResponse.question_key == "Q_TESTIS_SURGERY"
        ).first()
        assert r2.answer_value == "no"
        assert r2.is_unsure is False

        # State 3: Unsure
        QuestionnaireService.save_domain_responses(
            db, assessment_id=aid,
            data=SaveDomainResponsesRequest(
                domain_code=QuestionDomain.TESTICULAR_HISTORY,
                answers=[AnswerInput(question_id=q_parent.id, question_key=q_parent.question_key, is_unsure=True)]
            )
        )
        r3 = db.query(AssessmentResponse).filter(
            AssessmentResponse.assessment_id == aid,
            AssessmentResponse.question_key == "Q_TESTIS_SURGERY"
        ).first()
        assert r3.is_unsure is True
        assert r3.is_prefer_not_to_say is False

        # State 4: Prefer Not to Say
        QuestionnaireService.save_domain_responses(
            db, assessment_id=aid,
            data=SaveDomainResponsesRequest(
                domain_code=QuestionDomain.TESTICULAR_HISTORY,
                answers=[AnswerInput(question_id=q_parent.id, question_key=q_parent.question_key, is_prefer_not_to_say=True)]
            )
        )
        r4 = db.query(AssessmentResponse).filter(
            AssessmentResponse.assessment_id == aid,
            AssessmentResponse.question_key == "Q_TESTIS_SURGERY"
        ).first()
        assert r4.is_prefer_not_to_say is True
        assert r4.is_unsure is False

        # State 5: Unanswered (absence of row)
        unanswered_row = db.query(AssessmentResponse).filter(
            AssessmentResponse.assessment_id == aid,
            AssessmentResponse.question_key == "Q_NOT_ANSWERED_YET"
        ).first()
        assert unanswered_row is None

        # Prohibited row: answer_value=None with is_unsure=False and is_prefer_not_to_say=False
        # Saving an empty answer deletes or rejects the row
        QuestionnaireService.save_domain_responses(
            db, assessment_id=aid,
            data=SaveDomainResponsesRequest(
                domain_code=QuestionDomain.TESTICULAR_HISTORY,
                answers=[AnswerInput(question_id=q_parent.id, question_key=q_parent.question_key, answer_value=None, is_unsure=False, is_prefer_not_to_say=False)]
            )
        )
        r_empty = db.query(AssessmentResponse).filter(
            AssessmentResponse.assessment_id == aid,
            AssessmentResponse.question_key == "Q_TESTIS_SURGERY"
        ).first()
        assert r_empty is None  # Absence of row represents unanswered
    finally:
        db.close()


# =============================================================================
# Acceptance Criteria 7: Atomic Downstream Invalidation
# =============================================================================
def test_transactional_invalidation():
    """Validates that changing a parent marks child conditional_pathway_active=False without deleting the row."""
    db = SessionLocal()
    try:
        start = QuestionnaireService.start_or_resume_assessment(db)
        aid = start.assessment_id

        q_parent = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY").first()
        q_child = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY_TYPE").first()

        # 1. Answer parent Q_TESTIS_SURGERY = yes, child Q_TESTIS_SURGERY_TYPE = varicocele_repair
        QuestionnaireService.save_domain_responses(
            db, assessment_id=aid,
            data=SaveDomainResponsesRequest(
                domain_code=QuestionDomain.TESTICULAR_HISTORY,
                answers=[
                    AnswerInput(question_id=q_parent.id, question_key="Q_TESTIS_SURGERY", answer_value="yes"),
                    AnswerInput(question_id=q_child.id, question_key="Q_TESTIS_SURGERY_TYPE", answer_value="varicocele_repair")
                ]
            )
        )
        child_row = db.query(AssessmentResponse).filter(
            AssessmentResponse.assessment_id == aid,
            AssessmentResponse.question_key == "Q_TESTIS_SURGERY_TYPE"
        ).first()
        assert child_row is not None
        assert child_row.conditional_pathway_active is True

        # 2. Change parent to "no"
        save_res = QuestionnaireService.save_domain_responses(
            db, assessment_id=aid,
            data=SaveDomainResponsesRequest(
                domain_code=QuestionDomain.TESTICULAR_HISTORY,
                answers=[AnswerInput(question_id=q_parent.id, question_key="Q_TESTIS_SURGERY", answer_value="no")]
            )
        )
        assert "Q_TESTIS_SURGERY_TYPE" in save_res.invalidated_question_keys

        # 3. Verify child row preserved with conditional_pathway_active = False
        db.expire_all()
        child_row_after = db.query(AssessmentResponse).filter(
            AssessmentResponse.assessment_id == aid,
            AssessmentResponse.question_key == "Q_TESTIS_SURGERY_TYPE"
        ).first()
        assert child_row_after is not None
        assert child_row_after.conditional_pathway_active is False
        assert child_row_after.answer_value == "varicocele_repair"
    finally:
        db.close()


# =============================================================================
# Acceptance Criteria 8: Privacy-Preserving Audit Logging
# =============================================================================
def test_privacy_audit_logging():
    """Validates that AuditLog records structural metadata only with zero plaintext clinical answers."""
    db = SessionLocal()
    try:
        start = QuestionnaireService.start_or_resume_assessment(db)
        aid = start.assessment_id

        q_parent = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY").first()
        q_child = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY_TYPE").first()

        # Trigger an invalidation event
        QuestionnaireService.save_domain_responses(
            db, assessment_id=aid,
            data=SaveDomainResponsesRequest(
                domain_code=QuestionDomain.TESTICULAR_HISTORY,
                answers=[
                    AnswerInput(question_id=q_parent.id, question_key="Q_TESTIS_SURGERY", answer_value="yes"),
                    AnswerInput(question_id=q_child.id, question_key="Q_TESTIS_SURGERY_TYPE", answer_value="varicocele_repair")
                ]
            )
        )
        QuestionnaireService.save_domain_responses(
            db, assessment_id=aid,
            data=SaveDomainResponsesRequest(
                domain_code=QuestionDomain.TESTICULAR_HISTORY,
                answers=[AnswerInput(question_id=q_parent.id, question_key="Q_TESTIS_SURGERY", answer_value="no")]
            )
        )

        audit_entry = db.query(AuditLog).filter(
            AuditLog.resource_id == aid,
            AuditLog.action == "QUESTIONNAIRE_PATHWAY_INVALIDATED"
        ).first()

        assert audit_entry is not None
        details = audit_entry.details
        assert details["parent_question_key"] == "Q_TESTIS_SURGERY"
        assert "Q_TESTIS_SURGERY_TYPE" in details["affected_keys"]
        assert "varicocele_repair" not in json.dumps(details)  # Zero sensitive answer values stored
    finally:
        db.close()


# =============================================================================
# Acceptance Criteria 9: Transactional Rollback on Error
# =============================================================================
def test_invalidation_rollback_on_failure():
    """Validates that simulated DB failure rolls back both response updates and audit entries atomically."""
    db = SessionLocal()
    try:
        start = QuestionnaireService.start_or_resume_assessment(db)
        aid = start.assessment_id

        q_parent = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY").first()

        # Seed initial response
        QuestionnaireService.save_domain_responses(
            db, assessment_id=aid,
            data=SaveDomainResponsesRequest(
                domain_code=QuestionDomain.TESTICULAR_HISTORY,
                answers=[AnswerInput(question_id=q_parent.id, question_key="Q_TESTIS_SURGERY", answer_value="yes")]
            )
        )

        # Simulate DB error during save
        with patch.object(db, "commit", side_effect=Exception("Simulated SQLite write error")):
            with pytest.raises(Exception):
                QuestionnaireService.save_domain_responses(
                    db, assessment_id=aid,
                    data=SaveDomainResponsesRequest(
                        domain_code=QuestionDomain.TESTICULAR_HISTORY,
                        answers=[AnswerInput(question_id=q_parent.id, question_key="Q_TESTIS_SURGERY", answer_value="no")]
                    )
                )

        # Verify rollback: parent response is still "yes"
        db.rollback()
        r = db.query(AssessmentResponse).filter(
            AssessmentResponse.assessment_id == aid,
            AssessmentResponse.question_key == "Q_TESTIS_SURGERY"
        ).first()
        assert r.answer_value == "yes"
    finally:
        db.close()


# =============================================================================
# Acceptance Criteria 10: Concurrent Conflicting Save Guard & Monotonic Timestamps
# =============================================================================
def test_concurrent_save_conflict():
    """Validates that concurrent save with stale client_last_saved_at raises HTTP 409."""
    db = SessionLocal()
    try:
        start = QuestionnaireService.start_or_resume_assessment(db)
        aid = start.assessment_id

        q_parent = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY").first()

        # First save
        res1 = QuestionnaireService.save_domain_responses(
            db, assessment_id=aid,
            data=SaveDomainResponsesRequest(
                domain_code=QuestionDomain.TESTICULAR_HISTORY,
                answers=[AnswerInput(question_id=q_parent.id, question_key="Q_TESTIS_SURGERY", answer_value="yes")]
            )
        )
        saved_timestamp_1 = res1.last_saved_at

        # Second save with current timestamp advances monotonically
        res2 = QuestionnaireService.save_domain_responses(
            db, assessment_id=aid,
            data=SaveDomainResponsesRequest(
                domain_code=QuestionDomain.TESTICULAR_HISTORY,
                answers=[AnswerInput(question_id=q_parent.id, question_key="Q_TESTIS_SURGERY", answer_value="yes")],
                client_last_saved_at=saved_timestamp_1
            )
        )
        assert res2.last_saved_at > saved_timestamp_1

        # Third concurrent save with STALE timestamp (saved_timestamp_1) -> HTTP 409 Conflict
        with pytest.raises(HTTPException) as exc_info:
            QuestionnaireService.save_domain_responses(
                db, assessment_id=aid,
                data=SaveDomainResponsesRequest(
                    domain_code=QuestionDomain.TESTICULAR_HISTORY,
                    answers=[AnswerInput(question_id=q_parent.id, question_key="Q_TESTIS_SURGERY", answer_value="no")],
                    client_last_saved_at=saved_timestamp_1
                )
            )
        assert exc_info.value.status_code == 409
        assert "Concurrent modification detected" in exc_info.value.detail
    finally:
        db.close()


def test_multithreaded_overlapping_concurrency_race():
    """Validates that genuinely overlapping concurrent requests with the same client_last_saved_at
    result in exactly 1 success (200 OK) and 1 rejection (409 Conflict), with zero partial mutations
    or orphan audit log entries left behind by the rejected transaction.
    """
    import threading
    db = SessionLocal()
    try:
        start = QuestionnaireService.start_or_resume_assessment(db)
        aid = start.assessment_id

        q_parent = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY").first()
        qid = q_parent.id
        qkey = q_parent.question_key

        # Establish initial response and known last_saved_at
        initial_res = QuestionnaireService.save_domain_responses(
            db,
            assessment_id=aid,
            data=SaveDomainResponsesRequest(
                domain_code=QuestionDomain.TESTICULAR_HISTORY,
                answers=[AnswerInput(question_id=qid, question_key=qkey, answer_value="initial_baseline")]
            )
        )
        initial_saved_at = initial_res.last_saved_at

        # Count baseline audit logs for this assessment
        baseline_audit_count = db.query(AuditLog).filter(AuditLog.resource_id == aid).count()

        # Set up synchronization barrier for 2 competing worker threads
        barrier = threading.Barrier(2)
        QuestionnaireService._test_concurrency_barrier = barrier

        results = {}
        exceptions = {}

        def worker(name, ans_value):
            worker_db = SessionLocal()
            try:
                req = SaveDomainResponsesRequest(
                    domain_code=QuestionDomain.TESTICULAR_HISTORY,
                    answers=[AnswerInput(question_id=qid, question_key=qkey, answer_value=ans_value)],
                    client_last_saved_at=initial_saved_at
                )
                res = QuestionnaireService.save_domain_responses(worker_db, assessment_id=aid, data=req)
                results[name] = res
            except Exception as e:
                exceptions[name] = e
            finally:
                worker_db.close()

        t1 = threading.Thread(target=worker, args=("Thread-1", "VALUE_THREAD_1"))
        t2 = threading.Thread(target=worker, args=("Thread-2", "VALUE_THREAD_2"))

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        # Teardown barrier
        QuestionnaireService._test_concurrency_barrier = None

        # Verify outcome: exactly 1 succeeded, exactly 1 received 409 Conflict
        assert len(results) == 1, f"Expected exactly 1 success, got {len(results)}"
        assert len(exceptions) == 1, f"Expected exactly 1 failure, got {len(exceptions)}"

        rejected_exception = list(exceptions.values())[0]
        assert isinstance(rejected_exception, HTTPException)
        assert rejected_exception.status_code == 409
        assert "Concurrent modification detected" in rejected_exception.detail

        winning_thread_name = list(results.keys())[0]
        winning_result = list(results.values())[0]
        assert winning_result.last_saved_at > initial_saved_at

        # Verify database integrity in a fresh session
        verify_db = SessionLocal()
        try:
            assessment = verify_db.query(Assessment).filter(Assessment.id == aid).first()
            db_ts = assessment.last_saved_at.replace(tzinfo=timezone.utc) if assessment.last_saved_at.tzinfo is None else assessment.last_saved_at
            win_ts = winning_result.last_saved_at.replace(tzinfo=timezone.utc) if winning_result.last_saved_at.tzinfo is None else winning_result.last_saved_at
            assert db_ts == win_ts

            response = verify_db.query(AssessmentResponse).filter(
                AssessmentResponse.assessment_id == aid,
                AssessmentResponse.question_key == qkey
            ).first()
            expected_winner_value = "VALUE_THREAD_1" if winning_thread_name == "Thread-1" else "VALUE_THREAD_2"
            assert response.answer_value == expected_winner_value

            # Exactly 1 new audit log entry should exist (from the winner), 0 from the rejected thread
            final_audit_count = verify_db.query(AuditLog).filter(AuditLog.resource_id == aid).count()
            assert final_audit_count == baseline_audit_count + 1
        finally:
            verify_db.close()
    finally:
        QuestionnaireService._test_concurrency_barrier = None
        db.close()


# =============================================================================
# Acceptance Criteria 11: Zero Automatic Reactivation
# =============================================================================
def test_no_automatic_reactivation():
    """Validates that flipping parent back leaves child inactive with needs_reconfirmation=True."""
    db = SessionLocal()
    try:
        start = QuestionnaireService.start_or_resume_assessment(db)
        aid = start.assessment_id

        q_parent = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY").first()
        q_child = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY_TYPE").first()

        # 1. Answer parent "yes", child "varicocele_repair"
        QuestionnaireService.save_domain_responses(
            db, assessment_id=aid,
            data=SaveDomainResponsesRequest(
                domain_code=QuestionDomain.TESTICULAR_HISTORY,
                answers=[
                    AnswerInput(question_id=q_parent.id, question_key="Q_TESTIS_SURGERY", answer_value="yes"),
                    AnswerInput(question_id=q_child.id, question_key="Q_TESTIS_SURGERY_TYPE", answer_value="varicocele_repair")
                ]
            )
        )

        # 2. Flip parent to "no" (invalidates child)
        QuestionnaireService.save_domain_responses(
            db, assessment_id=aid,
            data=SaveDomainResponsesRequest(
                domain_code=QuestionDomain.TESTICULAR_HISTORY,
                answers=[AnswerInput(question_id=q_parent.id, question_key="Q_TESTIS_SURGERY", answer_value="no")]
            )
        )

        # 3. Flip parent back to "yes"
        QuestionnaireService.save_domain_responses(
            db, assessment_id=aid,
            data=SaveDomainResponsesRequest(
                domain_code=QuestionDomain.TESTICULAR_HISTORY,
                answers=[AnswerInput(question_id=q_parent.id, question_key="Q_TESTIS_SURGERY", answer_value="yes")]
            )
        )

        # 4. Check DB row: child remains inactive (zero automatic reactivation)
        child_row = db.query(AssessmentResponse).filter(
            AssessmentResponse.assessment_id == aid,
            AssessmentResponse.question_key == "Q_TESTIS_SURGERY_TYPE"
        ).first()
        assert child_row.conditional_pathway_active is False

        # 5. Check domain questions: child has needs_reconfirmation = True
        domain_q = QuestionnaireService.get_domain_questions(db, assessment_id=aid, domain_index=2)
        saved_q = domain_q.saved_responses.get("Q_TESTIS_SURGERY_TYPE")
        assert saved_q["needs_reconfirmation"] is True
        assert saved_q["conditional_pathway_active"] is False
    finally:
        db.close()


# =============================================================================
# Acceptance Criteria 12: Explicit User Reconfirmation
# =============================================================================
def test_explicit_user_reconfirmation():
    """Validates that explicitly saving child answer restores conditional_pathway_active=True."""
    db = SessionLocal()
    try:
        start = QuestionnaireService.start_or_resume_assessment(db)
        aid = start.assessment_id

        q_parent = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY").first()
        q_child = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY_TYPE").first()

        # Set up child in inactive state (from Criteria 11 sequence)
        QuestionnaireService.save_domain_responses(
            db, assessment_id=aid,
            data=SaveDomainResponsesRequest(
                domain_code=QuestionDomain.TESTICULAR_HISTORY,
                answers=[
                    AnswerInput(question_id=q_parent.id, question_key="Q_TESTIS_SURGERY", answer_value="yes"),
                    AnswerInput(question_id=q_child.id, question_key="Q_TESTIS_SURGERY_TYPE", answer_value="varicocele_repair")
                ]
            )
        )
        QuestionnaireService.save_domain_responses(
            db, assessment_id=aid,
            data=SaveDomainResponsesRequest(
                domain_code=QuestionDomain.TESTICULAR_HISTORY,
                answers=[AnswerInput(question_id=q_parent.id, question_key="Q_TESTIS_SURGERY", answer_value="no")]
            )
        )
        QuestionnaireService.save_domain_responses(
            db, assessment_id=aid,
            data=SaveDomainResponsesRequest(
                domain_code=QuestionDomain.TESTICULAR_HISTORY,
                answers=[AnswerInput(question_id=q_parent.id, question_key="Q_TESTIS_SURGERY", answer_value="yes")]
            )
        )

        # Explicitly reconfirm child answer
        QuestionnaireService.save_domain_responses(
            db, assessment_id=aid,
            data=SaveDomainResponsesRequest(
                domain_code=QuestionDomain.TESTICULAR_HISTORY,
                answers=[AnswerInput(question_id=q_child.id, question_key="Q_TESTIS_SURGERY_TYPE", answer_value="varicocele_repair")]
            )
        )

        # Child is now active again
        child_row = db.query(AssessmentResponse).filter(
            AssessmentResponse.assessment_id == aid,
            AssessmentResponse.question_key == "Q_TESTIS_SURGERY_TYPE"
        ).first()
        assert child_row.conditional_pathway_active is True

        # AuditLog records QUESTIONNAIRE_RESPONSE_RECONFIRMED
        audit_reconfirm = db.query(AuditLog).filter(
            AuditLog.resource_id == aid,
            AuditLog.action == "QUESTIONNAIRE_RESPONSE_RECONFIRMED"
        ).first()
        assert audit_reconfirm is not None
    finally:
        db.close()


# =============================================================================
# Acceptance Criteria 13: Multi-Tier Cascade Handling
# =============================================================================
def test_multi_tier_cascade():
    """Validates that a 3-tier tree cascades invalidation properly across all levels."""
    q_gp = Question(id=1, question_key="Q_GP")
    q_p = Question(id=2, question_key="Q_P", conditional_parent_key="Q_GP", conditional_trigger_values=["yes"])
    q_c = Question(id=3, question_key="Q_C", conditional_parent_key="Q_P", conditional_trigger_values=["trigger_c"])
    all_q = [q_gp, q_p, q_c]

    # Transitive descendants of Grandparent include both Parent and Child
    descendants = AdaptiveBranchingService.get_descendant_tree("Q_GP", all_q)
    assert set(descendants) == {"Q_P", "Q_C"}

    # Transitive descendants of Parent include Child only
    assert set(AdaptiveBranchingService.get_descendant_tree("Q_P", all_q)) == {"Q_C"}


# =============================================================================
# Acceptance Criteria 14: Clinical Rule Isolation & Evidence Decoupling
# =============================================================================
def test_inactive_response_rule_isolation():
    """Validates that inactive child response does NOT trigger clinical rule and evidence is decoupled."""
    db = SessionLocal()
    try:
        start = QuestionnaireService.start_or_resume_assessment(db)
        aid = start.assessment_id

        q_parent = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY").first()
        q_child = db.query(Question).filter(Question.question_key == "Q_TESTIS_SURGERY_TYPE").first()

        # 1. Answer Q_TESTIS_SURGERY = yes, Q_TESTIS_SURGERY_TYPE = undescended_testis
        QuestionnaireService.save_domain_responses(
            db, assessment_id=aid,
            data=SaveDomainResponsesRequest(
                domain_code=QuestionDomain.TESTICULAR_HISTORY,
                answers=[
                    AnswerInput(question_id=q_parent.id, question_key="Q_TESTIS_SURGERY", answer_value="yes"),
                    AnswerInput(question_id=q_child.id, question_key="Q_TESTIS_SURGERY_TYPE", answer_value="undescended_testis")
                ]
            )
        )

        # 2. Invalidate child by changing parent to "no"
        QuestionnaireService.save_domain_responses(
            db, assessment_id=aid,
            data=SaveDomainResponsesRequest(
                domain_code=QuestionDomain.TESTICULAR_HISTORY,
                answers=[AnswerInput(question_id=q_parent.id, question_key="Q_TESTIS_SURGERY", answer_value="no")]
            )
        )

        # 3. Evaluate rules: Rule R-TST-CRYPTORCHIDISM must NOT trigger
        report = ClinicalRuleEngineService.compile_assessment_report(
            db=db,
            assessment_id=aid,
            session_token=start.session_token
        )

        triggered_rule_codes = [f["rule_code"] for f in report.identified_risk_factors_json]
        assert "R-TST-CRYPTORCHIDISM" not in triggered_rule_codes

        # 4. Safe Answer Principle: evaluate predicate with unsure/prefer_not_to_say
        mock_unsure_resp = {"Q_TEST": AssessmentResponse(is_unsure=True, is_prefer_not_to_say=False)}
        is_match, reason = ClinicalRuleEngineService.evaluate_predicate(
            {"question_key": "Q_TEST", "expected_value": "yes"},
            mock_unsure_resp
        )
        assert is_match is False
        assert "Unsure" in reason
    finally:
        db.close()


# =============================================================================
# Acceptance Criteria 15: Immutable Locked Report Verification
# =============================================================================
def test_historical_report_immutability():
    """
    5-step verification of immutable historical report protection:
    (1) Query locked report and compute SHA-256;
    (2) Invoke compilation;
    (3) Verify existing report returned without recalculation;
    (4) Verify zero DB mutation;
    (5) Compare metadata against baseline.
    """
    db = SessionLocal()
    try:
        # Step 1: Query an existing locked report
        report = db.query(AssessmentReport).filter(AssessmentReport.is_locked == True).first()
        assert report is not None, "At least one locked report must exist in test database"

        baseline_data = {
            "id": report.id,
            "report_reference": report.report_reference,
            "assessment_id": report.assessment_id,
            "session_token": report.session_token,
            "outcome_tier": report.outcome_tier.value,
            "identified_risk_factors_json": report.identified_risk_factors_json,
            "evidence_citations_json": report.evidence_citations_json,
            "generated_at": report.generated_at.isoformat() if report.generated_at else None
        }
        baseline_sha = hashlib.sha256(json.dumps(baseline_data, sort_keys=True).encode()).hexdigest()

        # Step 2: Invoke compilation on this assessment
        comp_report = ClinicalRuleEngineService.compile_assessment_report(
            db=db,
            assessment_id=report.assessment_id,
            session_token=report.session_token
        )

        # Step 3: Verify existing report returned without recalculation
        assert comp_report.id == report.id
        assert comp_report.report_reference == report.report_reference

        # Step 4: Verify zero DB mutation
        post_data = {
            "id": comp_report.id,
            "report_reference": comp_report.report_reference,
            "assessment_id": comp_report.assessment_id,
            "session_token": comp_report.session_token,
            "outcome_tier": comp_report.outcome_tier.value,
            "identified_risk_factors_json": comp_report.identified_risk_factors_json,
            "evidence_citations_json": comp_report.evidence_citations_json,
            "generated_at": comp_report.generated_at.isoformat() if comp_report.generated_at else None
        }
        post_sha = hashlib.sha256(json.dumps(post_data, sort_keys=True).encode()).hexdigest()

        # Step 5: Exact hash match
        assert baseline_sha == post_sha
    finally:
        db.close()


# =============================================================================
# Acceptance Criteria 16: URL Path Sanitization, HttpOnly Cookies & Genuine CSRF
# =============================================================================
def test_session_ownership_and_csrf_guard():
    """Validates URL path sanitization, HttpOnly cookies, genuine CSRF enforcement and ownership guard."""
    client = TestClient(fastapi_app)

    # 1. Start assessment -> receives HttpOnly genovex_session cookie and csrf_token
    start_res = client.post("/api/v1/questionnaire/assessments/start", json={})
    assert start_res.status_code == 200
    data = start_res.json()
    aid = data["assessment_id"]
    csrf_token = data["csrf_token"]
    assert csrf_token is not None
    assert "genovex_session" in client.cookies

    # 2. Mutating request with valid cookie and valid X-CSRF-Token -> 200 OK
    save_res = client.post(
        f"/api/v1/questionnaire/assessments/{aid}/save-domain",
        json={"domain_index": 0, "responses": {}},
        headers={"X-CSRF-Token": csrf_token}
    )
    assert save_res.status_code == 200

    # 3. Mutating request with valid cookie but MISSING CSRF token -> 403 Forbidden
    save_no_csrf = client.post(
        f"/api/v1/questionnaire/assessments/{aid}/save-domain",
        json={"domain_index": 0, "responses": {}}
    )
    assert save_no_csrf.status_code == 403
    assert "Invalid or missing CSRF token" in save_no_csrf.json()["detail"]

    # 4. Mutating request with INVALID CSRF token -> 403 Forbidden
    save_bad_csrf = client.post(
        f"/api/v1/questionnaire/assessments/{aid}/save-domain",
        json={"domain_index": 0, "responses": {}},
        headers={"X-CSRF-Token": "invalid_fake_token"}
    )
    assert save_bad_csrf.status_code == 403

    # 5. Mutating request with UNTRUSTED Origin header -> 403 Forbidden
    save_bad_origin = client.post(
        f"/api/v1/questionnaire/assessments/{aid}/save-domain",
        json={"domain_index": 0, "responses": {}},
        headers={"X-CSRF-Token": csrf_token, "Origin": "https://malicious-attacker.com"}
    )
    assert save_bad_origin.status_code == 403
    assert "Untrusted origin" in save_bad_origin.json()["detail"]

    # 6. Request with wrong assessment_id -> 404 Not Found (anti-enumeration)
    wrong_aid_res = client.get(
        "/api/v1/questionnaire/assessments/wrong-assessment-id-123/domain/0"
    )
    assert wrong_aid_res.status_code == 404

    # 7. Request with NO credentials -> 401 Unauthorized
    unauth_client = TestClient(fastapi_app)
    no_cred_res = unauth_client.get(
        f"/api/v1/questionnaire/assessments/{aid}/domain/0"
    )
    assert no_cred_res.status_code == 401
    assert "Assessment session credential required" in no_cred_res.json()["detail"]


# =============================================================================
# Acceptance Criteria 18: Zero Breaking DDL Parity
# =============================================================================
def test_zero_breaking_ddl_parity():
    """
    AC 18: Zero Breaking DDL Parity & Schema Compatibility.
    Validates:
    1. Schema Preservation: All 17 application tables exist without unauthorized DDL changes.
    2. Response Compatibility: Validates that all assessment responses conform to the 5-state response protocol.
    3. Historical Report Immutability: Validates that existing reports retain valid outcome tiers and non-null snapshots.
    4. Relational Integrity: PRAGMA integrity_check and foreign_key_check confirm zero corruption.
    5. Baseline Preservation: Historical responses and reports remain non-truncated and intact.
    """
    db = SessionLocal()
    try:
        conn = db.connection().connection
        cur = conn.cursor()

        # 1. Physical SQLite Integrity
        cur.execute("PRAGMA integrity_check;")
        integrity = cur.fetchall()
        assert integrity == [("ok",)], f"Integrity check failed: {integrity}"

        cur.execute("PRAGMA foreign_key_check;")
        fk_errors = cur.fetchall()
        assert fk_errors == [], f"Foreign key errors: {fk_errors}"

        # 2. Table count: Exactly 17 application tables (excluding alembic_version)
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        all_tables = [r[0] for r in cur.fetchall()]
        app_tables = [t for t in all_tables if t != 'alembic_version']
        assert len(app_tables) == 17, f"Expected exactly 17 application tables, found {len(app_tables)}: {app_tables}"

        # 3. Assessment Response 5-State Protocol Validation
        # Invariant: Every assessment response must possess a valid question_id and either an answer_value or safe answer flag
        cur.execute("SELECT count(*) FROM assessment_responses WHERE question_id IS NULL OR (answer_value IS NULL AND (is_unsure = 0 OR is_unsure IS NULL) AND (is_prefer_not_to_say = 0 OR is_prefer_not_to_say IS NULL));")
        malformed_responses = cur.fetchone()[0]
        assert malformed_responses == 0, f"Found {malformed_responses} malformed assessment responses violating schema"

        # Invariant: Historical responses must be intact (>= 178 responses)
        cur.execute("SELECT count(*) FROM assessment_responses;")
        resp_count = cur.fetchone()[0]
        assert resp_count >= 178, f"Expected at least 178 historical responses, found {resp_count}"

        # 4. Assessment Reports Invariant
        cur.execute("SELECT count(*) FROM assessment_reports WHERE report_reference IS NULL OR outcome_tier IS NULL;")
        invalid_reports = cur.fetchone()[0]
        assert invalid_reports == 0, f"Found {invalid_reports} invalid assessment reports violating schema"

        cur.execute("SELECT count(*) FROM assessment_reports;")
        report_count = cur.fetchone()[0]
        assert report_count >= 86, f"Expected at least 86 historical reports, found {report_count}"

        # 5. Assessments Invariant
        cur.execute("SELECT count(*) FROM assessments;")
        assessment_count = cur.fetchone()[0]
        assert assessment_count >= 87, f"Expected at least 87 historical assessments, found {assessment_count}"
    finally:
        db.close()
