import json
import uuid
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type
from datetime import datetime, timezone
from pydantic import BaseModel
import httpx

from app.core.config import settings
from app.services.ai.guardrails import AIGuardrails, SAFE_FALLBACK_DISCLAIMER


class AIProviderError(Exception):
    """Raised when an AI provider fails, times out, or returns invalid data."""
    def __init__(self, message: str, status_code: int = 502, error_code: str = "AI_PROVIDER_ERROR"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


class AIProvider(ABC):
    """Abstract interface for AI Providers."""

    @abstractmethod
    async def generate_structured(
        self,
        system_instruction: str,
        user_prompt: str,
        response_schema: Type[BaseModel],
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """Generates structured response validated against response_schema."""
        pass


class MockAIProvider(AIProvider):
    """
    Deterministic, offline AI provider for safe testing and production fallback.
    Guarantees 100% predictable, non-diagnostic, guideline-anchored educational responses.
    """
    def __init__(
        self,
        simulate_error: bool = False,
        simulate_timeout: bool = False,
        simulate_rate_limit: bool = False,
        simulate_invalid_json: bool = False
    ):
        self.simulate_error = simulate_error
        self.simulate_timeout = simulate_timeout
        self.simulate_rate_limit = simulate_rate_limit
        self.simulate_invalid_json = simulate_invalid_json

    async def generate_structured(
        self,
        system_instruction: str,
        user_prompt: str,
        response_schema: Type[BaseModel],
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        if self.simulate_timeout:
            raise AIProviderError("AI Provider request timed out after 15s", status_code=504, error_code="AI_TIMEOUT")
        if self.simulate_rate_limit:
            raise AIProviderError("AI Provider rate limit exceeded", status_code=429, error_code="AI_RATE_LIMIT")
        if self.simulate_error:
            raise AIProviderError("AI Provider upstream service unavailable", status_code=502, error_code="AI_UNAVAILABLE")
        if self.simulate_invalid_json:
            raise AIProviderError("AI Provider returned unparseable malformed output", status_code=502, error_code="AI_MALFORMED_OUTPUT")

        req_id = f"mock-req-{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        metadata_dict = {
            "provider": "mock",
            "model": "genovex-educational-v1",
            "prompt_version": "v1.0.0",
            "request_id": req_id,
            "timestamp": now_iso,
            "is_educational": True,
            "disclaimer": SAFE_FALLBACK_DISCLAIMER
        }

        schema_name = response_schema.__name__

        if "HealthEducationResponse" in schema_name:
            return {
                "topic": user_prompt[:80],
                "title": f"Clinical Education: Understanding {user_prompt[:50]}",
                "explanation": (
                    "Male reproductive health is influenced by testicular physiology, hormonal regulation "
                    "(hypothalamic-pituitary-gonadal axis), and modifiable lifestyle factors. According to EAU "
                    "and AUA/ASRM clinical guidelines, early evaluation helps identify modifiable risk elements."
                ),
                "key_points": [
                    "Spermatogenesis requires an optimal intratesticular temperature (2-3°C below core body temperature).",
                    "Endocrine balance (LH, FSH, Testosterone) regulates sperm production and maturation.",
                    "Evaluation by a qualified andrologist or urologist is recommended for personalized assessment."
                ],
                "guideline_sources": [
                    "EAU Guidelines on Sexual and Reproductive Health (2024)",
                    "AUA/ASRM Guideline on Diagnosis and Treatment of Infertility in Men (2021)"
                ],
                "metadata": metadata_dict
            }

        elif "TerminologyExplanationResponse" in schema_name:
            clean_term = user_prompt.replace("Term to define: ", "").strip()
            return {
                "term": clean_term[:60],
                "plain_language_definition": (
                    f"The term '{clean_term[:40]}' refers to an anatomical, hormonal, or physiological "
                    "concept in male reproductive medicine."
                ),
                "clinical_context": (
                    "In clinical practice, andrologists evaluate this parameter in conjunction with "
                    "standardized semen analysis (WHO 6th edition) and scrotal physical examination."
                ),
                "common_misconceptions": (
                    "This term describes a clinical finding or anatomical state; it is not on its own "
                    "a definitive diagnosis of irreversible infertility."
                ),
                "metadata": metadata_dict
            }

        elif "ResultExplanationResponse" in schema_name:
            return {
                "report_reference": "GNX-RPT-EXPLAINED",
                "outcome_tier": "SPECIALIST_EVALUATION_RECOMMENDED",
                "plain_language_summary": (
                    "Your assessment responses were matched against codified clinical guidelines. "
                    "One or more responses indicate factors that warrant formal discussion with a "
                    "reproductive urologist or andrologist."
                ),
                "identified_factors_explained": [
                    {
                        "factor": "Reported Factor",
                        "explanation": "This factor was flagged according to EAU/AUA clinical evidence."
                    }
                ],
                "next_steps_explained": [
                    "Schedule an in-person physical consultation with a male reproductive specialist.",
                    "Request two baseline laboratory semen analyses spaced 2-4 weeks apart."
                ],
                "non_diagnostic_notice": SAFE_FALLBACK_DISCLAIMER,
                "metadata": metadata_dict
            }

        elif "PreparationQuestionsResponse" in schema_name:
            return {
                "report_reference": "GNX-RPT-PREP",
                "questions_for_clinician": [
                    "Based on my questionnaire responses, what specific laboratory tests (e.g. semen analysis, hormones) do you recommend?",
                    "Do any of the lifestyle or medical factors I reported require targeted management?",
                    "Should an anatomical examination or scrotal ultrasound be performed?"
                ],
                "suggested_specialties": [
                    "Male Reproductive Urologist",
                    "Andrologist / Sexual Medicine Specialist"
                ],
                "recommended_documents_to_bring": [
                    "Previous semen analysis reports, if any",
                    "List of current medications and dietary supplements",
                    "Relevant medical or surgical history records"
                ],
                "metadata": metadata_dict
            }

        elif "ClinicianSummaryResponse" in schema_name:
            return {
                "assessment_id": "assessment-summary",
                "patient_reference": "PT-CONFIDENTIAL",
                "clinical_triage_tier": "CLINICAL_EVALUATION_RECOMMENDED",
                "is_urgent_red_flag": False,
                "response_overview": {
                    "total_answered": 19,
                    "unsure_count": 0,
                    "prefer_not_to_say_count": 0
                },
                "synthesized_risk_narrative": (
                    "Automated clinical synthesis of patient-reported data: Patient reported affirmative history "
                    "relevant to reproductive health. Responses are consistent with EAU male infertility guidelines "
                    "recommending endocrine workup (morning total testosterone, FSH, LH) and scrotal examination."
                ),
                "suggested_diagnostic_workup": [
                    "Comprehensive semen analysis in accredited laboratory (WHO 6th ed)",
                    "Endocrine profile: Morning Total Testosterone, FSH, LH, Prolactin",
                    "High-frequency scrotal ultrasonography to assess testicular volume and varicocele"
                ],
                "is_ai_generated": True,
                "metadata": metadata_dict
            }

        # Generic fallback
        return {
            "content": "Educational summary generated by GENOVEX AI.",
            "metadata": metadata_dict
        }


class GeminiAIProvider(AIProvider):
    """
    Integration with Google Gemini API via official REST endpoint using backend-only API key.
    Enforces strict timeouts, retries, and JSON output parsing.
    """
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.AI_API_KEY
        self.model = model or settings.AI_MODEL

    async def generate_structured(
        self,
        system_instruction: str,
        user_prompt: str,
        response_schema: Type[BaseModel],
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        if not self.api_key:
            # Fallback to mock provider if API key is not configured in environment
            mock = MockAIProvider()
            return await mock.generate_structured(system_instruction, user_prompt, response_schema, temperature)

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"System Directive:\n{system_instruction}\n\nTask:\n{user_prompt}"}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json"
            }
        }

        timeout = httpx.Timeout(settings.AI_REQUEST_TIMEOUT_SECONDS, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            retries = settings.AI_MAX_RETRIES
            last_err = None
            for attempt in range(retries + 1):
                try:
                    resp = await client.post(endpoint, json=payload)
                    if resp.status_code == 429:
                        raise AIProviderError("Gemini rate limit exceeded", status_code=429, error_code="AI_RATE_LIMIT")
                    if resp.status_code != 200:
                        raise AIProviderError(f"Gemini API returned error HTTP {resp.status_code}", status_code=502)
                    
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise AIProviderError("Gemini API returned empty candidate set", status_code=502)
                    
                    content_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
                    parsed = json.loads(content_text)
                    return parsed
                except (httpx.TimeoutException, asyncio.TimeoutError) as e:
                    last_err = AIProviderError(f"Gemini API timed out: {str(e)}", status_code=504, error_code="AI_TIMEOUT")
                    if attempt < retries:
                        await asyncio.sleep(1.0 * (attempt + 1))
                        continue
                    raise last_err
                except json.JSONDecodeError:
                    raise AIProviderError("Gemini API returned unparseable JSON", status_code=502, error_code="AI_MALFORMED_OUTPUT")
                except AIProviderError:
                    raise
                except Exception as e:
                    last_err = AIProviderError(f"Gemini API call failed: {str(e)}", status_code=502)
                    if attempt < retries:
                        await asyncio.sleep(1.0 * (attempt + 1))
                        continue
                    raise last_err

        raise last_err or AIProviderError("Failed to communicate with AI provider")
