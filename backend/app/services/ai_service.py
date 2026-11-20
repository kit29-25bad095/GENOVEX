import time
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import User, AuditLog
from app.models.assessment_report import AssessmentReport
from app.models.questionnaire import Assessment, AssessmentResponse
from app.services.ai.guardrails import AIGuardrails, SAFE_FALLBACK_DISCLAIMER
from app.services.ai.provider import AIProvider, MockAIProvider, GeminiAIProvider, AIProviderError
from app.services.assessment_processing_service import ClinicalGovernanceGate
from app.schemas.ai import (
    HealthEducationResponse, TerminologyExplanationResponse,
    ResultExplanationResponse, PreparationQuestionsResponse,
    ClinicianSummaryResponse, AIMetadata
)


class AIService:
    """
    Centralized Backend AI Service.
    Enforces input sanitization, prompt injection resistance, schema validation,
    deterministic result preservation, and privacy-preserving operational audit logging.
    """

    _rate_limit_cache: Dict[str, List[float]] = {}

    @classmethod
    def _get_provider(cls, override_provider: Optional[AIProvider] = None) -> AIProvider:
        if override_provider:
            return override_provider
        provider_name = settings.AI_PROVIDER.lower()
        if provider_name == "gemini" and settings.AI_API_KEY:
            return GeminiAIProvider()
        return MockAIProvider()

    @classmethod
    def _check_rate_limit(cls, identifier: str) -> None:
        """Simple sliding-window in-memory rate limiter."""
        now = time.time()
        window = 60.0  # 1 minute
        limit = settings.AI_RATE_LIMIT_PER_MINUTE

        timestamps = cls._rate_limit_cache.get(identifier, [])
        # prune old timestamps
        timestamps = [t for t in timestamps if now - t < window]
        if len(timestamps) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "AI_RATE_LIMIT_EXCEEDED",
                    "message": "AI request rate limit exceeded. Please wait a moment before trying again."
                }
            )
        timestamps.append(now)
        cls._rate_limit_cache[identifier] = timestamps

    @classmethod
    def _log_ai_operation(
        cls,
        db: Session,
        action: str,
        user_id: Optional[int],
        provider: str,
        model: str,
        request_id: str,
        success: bool,
        duration_ms: float
    ) -> None:
        """Records categorical operational metadata without storing clinical answer text or PII."""
        try:
            audit = AuditLog(
                user_id=user_id,
                action=action,
                resource_type="AIService",
                resource_id=request_id,
                details={
                    "provider": provider,
                    "model": model,
                    "request_id": request_id,
                    "success": success,
                    "duration_ms": round(duration_ms, 2)
                },
                timestamp=datetime.now(timezone.utc)
            )
            db.add(audit)
            db.commit()
        except Exception:
            db.rollback()

    @classmethod
    async def explain_health_topic(
        cls,
        db: Session,
        topic: str,
        context: Optional[str] = None,
        language: str = "en",
        current_user: Optional[User] = None,
        override_provider: Optional[AIProvider] = None,
        caller_id: str = "anonymous"
    ) -> HealthEducationResponse:
        """Safe plain-language explanation of male reproductive health & lifestyle topics."""
        cls._check_rate_limit(caller_id)
        start_time = time.time()
        req_id = f"ai-edu-{uuid.uuid4().hex[:8]}"

        sanitized_topic, _ = AIGuardrails.sanitize_user_input(topic, max_chars=settings.AI_MAX_INPUT_CHARS)
        sanitized_context, _ = AIGuardrails.sanitize_user_input(context or "", max_chars=settings.AI_MAX_INPUT_CHARS)

        provider = cls._get_provider(override_provider)
        system_instruction = (
            "You are GENOVEX AI, a medical education assistant specializing in male reproductive health. "
            "Explain concepts using plain, accessible language anchored in EAU and AUA/ASRM clinical guidelines. "
            "NEVER provide medical diagnoses, treatment recommendations, or fertility probability estimates. "
            f"Respond in language '{language}'."
        )
        user_prompt = f"Topic: {sanitized_topic}\nContext: {sanitized_context}"

        try:
            raw_output = await provider.generate_structured(
                system_instruction=system_instruction,
                user_prompt=user_prompt,
                response_schema=HealthEducationResponse
            )
            # Ensure metadata
            raw_output["metadata"] = {
                "provider": settings.AI_PROVIDER,
                "model": settings.AI_MODEL,
                "prompt_version": "v1.0.0",
                "request_id": req_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "is_educational": True,
                "disclaimer": SAFE_FALLBACK_DISCLAIMER
            }
            # Guardrails check on explanation
            explanation = raw_output.get("explanation", "")
            safe_explanation, is_safe = AIGuardrails.validate_safety_invariants(explanation, language=language)
            if not is_safe:
                raw_output["explanation"] = safe_explanation

            response = HealthEducationResponse.model_validate(raw_output)
            cls._log_ai_operation(
                db=db,
                action="AI_HEALTH_EDUCATION",
                user_id=current_user.id if current_user else None,
                provider=settings.AI_PROVIDER,
                model=settings.AI_MODEL,
                request_id=req_id,
                success=True,
                duration_ms=(time.time() - start_time) * 1000
            )
            return response
        except AIProviderError as e:
            cls._log_ai_operation(
                db=db,
                action="AI_HEALTH_EDUCATION_FAILED",
                user_id=current_user.id if current_user else None,
                provider=settings.AI_PROVIDER,
                model=settings.AI_MODEL,
                request_id=req_id,
                success=False,
                duration_ms=(time.time() - start_time) * 1000
            )
            raise HTTPException(status_code=e.status_code, detail={"code": e.error_code, "message": e.message})

    @classmethod
    async def explain_terminology(
        cls,
        db: Session,
        term: str,
        language: str = "en",
        current_user: Optional[User] = None,
        override_provider: Optional[AIProvider] = None,
        caller_id: str = "anonymous"
    ) -> TerminologyExplanationResponse:
        """Explains clinical reproductive terms without diagnostic assertions."""
        cls._check_rate_limit(caller_id)
        start_time = time.time()
        req_id = f"ai-term-{uuid.uuid4().hex[:8]}"

        sanitized_term, _ = AIGuardrails.sanitize_user_input(term, max_chars=150)
        provider = cls._get_provider(override_provider)

        system_instruction = (
            "You are GENOVEX AI. Provide a clear, non-diagnostic definition of the specified male reproductive term. "
            f"Explain clinical relevance in simple terms in language '{language}'."
        )

        try:
            raw_output = await provider.generate_structured(
                system_instruction=system_instruction,
                user_prompt=f"Term to define: {sanitized_term}",
                response_schema=TerminologyExplanationResponse
            )
            raw_output["metadata"] = {
                "provider": settings.AI_PROVIDER,
                "model": settings.AI_MODEL,
                "prompt_version": "v1.0.0",
                "request_id": req_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "is_educational": True,
                "disclaimer": SAFE_FALLBACK_DISCLAIMER
            }
            # Guardrails validation
            def_text = raw_output.get("plain_language_definition", "")
            safe_def, is_safe = AIGuardrails.validate_safety_invariants(def_text, language=language)
            if not is_safe:
                raw_output["plain_language_definition"] = safe_def

            response = TerminologyExplanationResponse.model_validate(raw_output)
            cls._log_ai_operation(
                db=db,
                action="AI_TERMINOLOGY_EXPLANATION",
                user_id=current_user.id if current_user else None,
                provider=settings.AI_PROVIDER,
                model=settings.AI_MODEL,
                request_id=req_id,
                success=True,
                duration_ms=(time.time() - start_time) * 1000
            )
            return response
        except AIProviderError as e:
            raise HTTPException(status_code=e.status_code, detail={"code": e.error_code, "message": e.message})

    @classmethod
    async def explain_assessment_result(
        cls,
        db: Session,
        report_reference: str,
        session_token: Optional[str] = None,
        language: str = "en",
        current_user: Optional[User] = None,
        override_provider: Optional[AIProvider] = None
    ) -> ResultExplanationResponse:
        """
        Explains existing deterministic report results in plain language.
        STRICT CLINICAL GOVERNANCE:
        1. Consumes report snapshot as read-only.
        2. Enforces ClinicalGovernanceGate: withholds release if rules are unapproved or Tier 1 is indeterminate.
        3. Never alters tier, triggered rules, or emergency guidance.
        """
        report = db.query(AssessmentReport).filter(AssessmentReport.report_reference == report_reference).first()
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment report not found")

        # Verify caller authorization and server-side governance gate
        assessment = db.query(Assessment).filter(Assessment.id == report.assessment_id).first()
        ClinicalGovernanceGate.verify_assessment_ownership(
            assessment=assessment,
            current_user=current_user,
            session_token=session_token
        )
        ClinicalGovernanceGate.verify_report_access(
            db=db,
            report=report,
            current_user=current_user,
            assessment=assessment
        )

        start_time = time.time()
        req_id = f"ai-res-{uuid.uuid4().hex[:8]}"
        provider = cls._get_provider(override_provider)

        # Feed deterministic snapshot as read-only context
        tier_val = report.outcome_tier.value if hasattr(report.outcome_tier, "value") else str(report.outcome_tier)
        user_prompt = (
            f"Report Reference: {report.report_reference}\n"
            f"Outcome Tier: {tier_val}\n"
            f"Title: {report.outcome_title_en}\n"
            f"Urgent Flag: {report.is_urgent_red_flag}\n"
            f"Guidance: {report.urgent_emergency_guidance_en}\n"
            f"Factors: {report.identified_risk_factors_json}\n"
            f"Next Steps: {report.recommended_next_steps_en}"
        )

        system_instruction = (
            "You are GENOVEX AI. Provide a clear, non-diagnostic explanation of this finalized clinical report. "
            "You must PRESERVE the exact outcome tier and specialist recommendations. Do NOT diagnose, do NOT predict "
            f"fertility probabilities, and do NOT downplay urgent flags. Respond in language '{language}'."
        )

        try:
            raw_output = await provider.generate_structured(
                system_instruction=system_instruction,
                user_prompt=user_prompt,
                response_schema=ResultExplanationResponse
            )
            # Guardrails validation on plain_language_summary
            summary_text = raw_output.get("plain_language_summary", "")
            safe_summary, is_safe = AIGuardrails.validate_safety_invariants(summary_text, language=language)
            if not is_safe:
                raw_output["plain_language_summary"] = safe_summary

            raw_output["report_reference"] = report.report_reference
            raw_output["outcome_tier"] = tier_val
            raw_output["non_diagnostic_notice"] = SAFE_FALLBACK_DISCLAIMER
            raw_output["metadata"] = {
                "provider": settings.AI_PROVIDER,
                "model": settings.AI_MODEL,
                "prompt_version": "v1.0.0",
                "request_id": req_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "is_educational": True,
                "disclaimer": SAFE_FALLBACK_DISCLAIMER
            }

            response = ResultExplanationResponse.model_validate(raw_output)
            cls._log_ai_operation(
                db=db,
                action="AI_REPORT_EXPLANATION",
                user_id=current_user.id if current_user else report.user_id,
                provider=settings.AI_PROVIDER,
                model=settings.AI_MODEL,
                request_id=req_id,
                success=True,
                duration_ms=(time.time() - start_time) * 1000
            )
            return response
        except AIProviderError as e:
            raise HTTPException(status_code=e.status_code, detail={"code": e.error_code, "message": e.message})

    @classmethod
    async def generate_preparation_questions(
        cls,
        db: Session,
        report_reference: str,
        session_token: Optional[str] = None,
        language: str = "en",
        current_user: Optional[User] = None,
        override_provider: Optional[AIProvider] = None
    ) -> PreparationQuestionsResponse:
        """Generates patient discussion questions to take to their physician consultation."""
        report = db.query(AssessmentReport).filter(AssessmentReport.report_reference == report_reference).first()
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment report not found")

        assessment = db.query(Assessment).filter(Assessment.id == report.assessment_id).first()
        ClinicalGovernanceGate.verify_assessment_ownership(
            assessment=assessment,
            current_user=current_user,
            session_token=session_token
        )
        ClinicalGovernanceGate.verify_report_access(
            db=db,
            report=report,
            current_user=current_user,
            assessment=assessment
        )

        start_time = time.time()
        req_id = f"ai-prep-{uuid.uuid4().hex[:8]}"
        provider = cls._get_provider(override_provider)

        user_prompt = f"Report Reference: {report.report_reference}, Tier: {report.outcome_tier}, Specialties: {report.recommended_specialties}"
        system_instruction = (
            "You are GENOVEX AI. Suggest practical questions for a patient to ask their urologist or andrologist. "
            f"Include helpful preparation tips and documents to bring. Language: '{language}'."
        )

        try:
            raw_output = await provider.generate_structured(
                system_instruction=system_instruction,
                user_prompt=user_prompt,
                response_schema=PreparationQuestionsResponse
            )
            raw_output["report_reference"] = report.report_reference
            raw_output["metadata"] = {
                "provider": settings.AI_PROVIDER,
                "model": settings.AI_MODEL,
                "prompt_version": "v1.0.0",
                "request_id": req_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "is_educational": True,
                "disclaimer": SAFE_FALLBACK_DISCLAIMER
            }

            response = PreparationQuestionsResponse.model_validate(raw_output)
            cls._log_ai_operation(
                db=db,
                action="AI_PREPARATION_QUESTIONS",
                user_id=current_user.id if current_user else report.user_id,
                provider=settings.AI_PROVIDER,
                model=settings.AI_MODEL,
                request_id=req_id,
                success=True,
                duration_ms=(time.time() - start_time) * 1000
            )
            return response
        except AIProviderError as e:
            raise HTTPException(status_code=e.status_code, detail={"code": e.error_code, "message": e.message})

    @classmethod
    async def generate_clinician_assessment_summary(
        cls,
        db: Session,
        assessment: Assessment,
        clinician_user: User,
        focus_areas: Optional[List[str]] = None,
        override_provider: Optional[AIProvider] = None
    ) -> ClinicianSummaryResponse:
        """
        Generates clinician-facing structured synthesis of patient-reported assessment data.
        Clearly labeled as AI-generated; non-diagnostic; strictly audits clinician request.
        """
        start_time = time.time()
        req_id = f"ai-clin-sum-{uuid.uuid4().hex[:8]}"
        provider = cls._get_provider(override_provider)

        # Build response overview
        responses = assessment.responses or []
        unsure_count = sum(1 for r in responses if r.is_unsure)
        prefer_not_to_say_count = sum(1 for r in responses if r.is_prefer_not_to_say)
        active_responses = [r for r in responses if r.conditional_pathway_active]

        # Existing report if compiled
        report = db.query(AssessmentReport).filter(AssessmentReport.assessment_id == assessment.id).first()
        tier_str = getattr(report.outcome_tier, "value", str(report.outcome_tier)) if report else "NOT_YET_COMPILED"
        is_urgent = report.is_urgent_red_flag if report else False

        user_prompt = (
            f"Assessment ID: {assessment.id}\n"
            f"Status: {assessment.status.value}\n"
            f"Triage Tier: {tier_str}\n"
            f"Urgent Flag: {is_urgent}\n"
            f"Total Answered: {len(responses)}\n"
            f"Unsure Count: {unsure_count}\n"
            f"Active Conditional Responses: {len(active_responses)}\n"
            f"Focus Areas Requested: {focus_areas or 'Full Assessment'}"
        )

        system_instruction = (
            "You are GENOVEX Clinician Assistant. Synthesize patient questionnaire findings into an objective, "
            "clinical summary for an attending andrologist or urologist. Reference EAU and AUA guidelines where appropriate. "
            "Highlight incomplete or unsure answers distinctly. Clearly separate patient data from clinical suggestions."
        )

        try:
            raw_output = await provider.generate_structured(
                system_instruction=system_instruction,
                user_prompt=user_prompt,
                response_schema=ClinicianSummaryResponse
            )
            # Guardrails validation on executive_synthesis
            synth_text = raw_output.get("executive_synthesis", "")
            safe_synth, is_safe = AIGuardrails.validate_safety_invariants(synth_text)
            if not is_safe:
                raw_output["executive_synthesis"] = safe_synth

            raw_output["assessment_id"] = assessment.id
            raw_output["patient_reference"] = f"PT-{assessment.id[:8].upper()}"
            raw_output["clinical_triage_tier"] = tier_str
            raw_output["is_urgent_red_flag"] = is_urgent
            raw_output["response_overview"] = {
                "total_answered": len(responses),
                "unsure_count": unsure_count,
                "prefer_not_to_say_count": prefer_not_to_say_count,
                "active_responses_count": len(active_responses)
            }
            raw_output["is_ai_generated"] = True
            raw_output["metadata"] = {
                "provider": settings.AI_PROVIDER,
                "model": settings.AI_MODEL,
                "prompt_version": "v1.0.0",
                "request_id": req_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "is_educational": True,
                "disclaimer": "AI-Generated Clinician Review Assistance — Not a Medical Diagnosis or Decision."
            }

            response = ClinicianSummaryResponse.model_validate(raw_output)
            cls._log_ai_operation(
                db=db,
                action="CLINICIAN_AI_SUMMARY_REQUEST",
                user_id=clinician_user.id,
                provider=settings.AI_PROVIDER,
                model=settings.AI_MODEL,
                request_id=req_id,
                success=True,
                duration_ms=(time.time() - start_time) * 1000
            )
            return response
        except AIProviderError as e:
            raise HTTPException(status_code=e.status_code, detail={"code": e.error_code, "message": e.message})
