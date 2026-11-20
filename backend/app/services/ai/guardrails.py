import re
import unicodedata
from typing import Tuple

INJECTION_PATTERNS = [
    # English prompt injection & jailbreak patterns
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"you\s+are\s+now\s+(a\s+)?(doctor|physician|unrestricted|dan)",
    r"act\s+as\s+(a\s+)?(doctor|physician|unrestricted|dan)",
    r"override\s+(the\s+)?(clinical|safety|system|rule)\s+(engine|rules?|tier)",
    r"bypass\s+(safety|governance|restrictions)",
    r"<\|(system|user|assistant|im_start|im_end)\|>",
    r"\[\/?INST\]",
    # System prompt & secret extraction
    r"(reveal|show|print|leak|output)\s+(the\s+)?(system\s+prompt|developer\s+instructions|secret\s+key|internal\s+instructions)",
    r"repeat\s+(all\s+)?(text\s+)?above",
    # Multilingual Arabic prompt injection patterns
    r"تجاهل\s+(جميع\s+)?(التعليمات|الأوامر)\s+(السابقة|أعلاه)",
    r"تجاوز\s+(قواعد|قيود)\s+(السلامة|النظام|الحوكمة)",
    r"أنت\s+الآن\s+(طبيب|غير\s+مقيد|دان)",
    r"تصرف\s+كـ?\s*(طبيب|غير\s+مقيد|دان)",
    r"تجاوز\s+(محرك|قواعد)\s+التقييم",
]

FORBIDDEN_DIAGNOSTIC_PATTERNS = [
    # English diagnostic & certainty patterns
    r"you\s+have\s+been\s+diagnosed\s+with",
    r"your\s+diagnosis\s+is",
    r"you\s+are\s+definitely\s+(infertile|fertile)",
    r"fertility\s+(probability|chance|rate)\s+is\s+\d+%",
    r"your\s+fertility\s+score\s+is",
    r"confirmed\s+absence\s+of\s+any\s+disease",
    r"guarantee(d)?\s+normal\s+fertility",
    r"you\s+do\s+not\s+need\s+to\s+see\s+a\s+doctor",
    r"ignore\s+the\s+urologist",
    # Multilingual Arabic diagnostic & certainty patterns
    r"تم\s+تشخيصك\s+بـ",
    r"تشخيصك\s+هو",
    r"أنت\s+(عقيم|خصب)\s+(بالتأكيد|تماما|تماماً)",
    r"احتمال(ية)?\s+الخصوبة\s+(\d+%)?",
    r"درجة\s+الخصوبة\s+لديك\s+هي",
    r"(تأكيد|نضمن)\s+(عدم\s+وجود|غياب)\s+أي\s+مرض",
    r"خصوبة\s+طبيعية\s+مضمونة",
    r"لا\s+داعي\s+لمراجعة\s+(طبيب|أخصائي|دكتور)",
    r"تجاهل\s+(طبيب|أخصائي)\s+المسالك",
]

COMPILED_INJECTION = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]
COMPILED_DIAGNOSTIC = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_DIAGNOSTIC_PATTERNS]

# Base64 high-entropy instruction detector
BASE64_PATTERN = re.compile(r"(?:[A-Za-z0-9+/]{20,}={0,2})")

SAFE_FALLBACK_DISCLAIMER = (
    "GENOVEX AI provides non-diagnostic educational information only and does not establish "
    "a medical diagnosis, calculate fertility probabilities, or confirm normal fertility. "
    "Please consult a qualified urologist or andrologist for individualized medical care."
)

SAFE_FALLBACK_DISCLAIMER_AR = (
    "يقدم نظام GENOVEX AI معلومات تعليمية غير تشخيصية فقط، ولا يقدم تشخيصاً طبياً، "
    "أو حساباً لاحتمالات الخصوبة، أو تأكيداً للخصوبة الطبيعية. "
    "يرجى استشارة طبيب مسالك بولية أو أخصائي أمراض ذكورة مؤهل للحصول على رعاية طبية متخصصة."
)


class AIGuardrails:
    """Enforces prompt injection resistance and clinical safety invariants across English and Arabic."""

    @staticmethod
    def sanitize_user_input(text: str, max_chars: int = 2000) -> Tuple[str, bool]:
        """
        Sanitizes text by normalizing Unicode, disarming base64 chunks,
        stripping prompt injection patterns across English/Arabic, and truncating.
        Returns (sanitized_text, was_flagged).
        """
        if not text:
            return "", False

        # 1. Unicode normalization (NFKC) prevents homoglyph and zero-width bypasses
        normalized = unicodedata.normalize("NFKC", text).strip()

        # 2. Length truncation
        if len(normalized) > max_chars:
            normalized = normalized[:max_chars]

        was_flagged = False

        # 3. Disarm suspicious raw base64 instruction chunks
        if BASE64_PATTERN.search(normalized):
            was_flagged = True
            normalized = BASE64_PATTERN.sub("[REDACTED_ENCODED_PAYLOAD]", normalized)

        # 4. Pattern redaction for prompt injection
        for pattern in COMPILED_INJECTION:
            if pattern.search(normalized):
                was_flagged = True
                normalized = pattern.sub("[REDACTED_INJECTION_ATTEMPT]", normalized)

        return normalized, was_flagged

    @staticmethod
    def validate_safety_invariants(content: str, language: str = "en") -> Tuple[str, bool]:
        """
        Validates model output across English and Arabic.
        If forbidden diagnostic assertions, certainty statements, or fertility probability claims
        are detected, replaces output with the safe fallback disclaimer.
        Returns (validated_content, is_safe).
        """
        fallback = SAFE_FALLBACK_DISCLAIMER_AR if language == "ar" else SAFE_FALLBACK_DISCLAIMER
        if not content:
            return fallback, False

        # Normalize Unicode before scanning
        normalized = unicodedata.normalize("NFKC", content)

        for pattern in COMPILED_DIAGNOSTIC:
            if pattern.search(normalized):
                # Safety violation detected in output: replace with safe educational guidance
                return fallback, False

        return content, True

