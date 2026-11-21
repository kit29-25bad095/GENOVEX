import os
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
try:
    import pymupdf
except ImportError:
    try:
        import fitz as pymupdf
    except ImportError:
        pymupdf = None

try:
    import qrcode
except ImportError:
    qrcode = None

from fastapi import HTTPException, status

from app.models.assessment_report import AssessmentReport
from app.models.questionnaire import Assessment
from app.core.security import User

# Available fonts on Windows / Linux for Arabic and Latin text
CANDIDATE_FONTS = [
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\tahoma.ttf",
    r"C:\Windows\Fonts\seguiemj.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
]

def get_unicode_font() -> Optional[str]:
    for p in CANDIDATE_FONTS:
        if os.path.exists(p):
            return p
    return None

class ReportPDFService:
    """
    High-Fidelity Evidence-Linked Bilingual PDF Report Generation Service (Phase 13).
    Renders immutable assessment snapshots into secure, downloadable clinical reports.
    Includes mandatory watermarks, 5-point non-diagnostic disclaimers, QR verification,
    cryptographic integrity hash, and response breakdown.
    """

    MANDATORY_WATERMARK = "GENOVEX INFORMATIONAL HEALTH REPORT – NOT A DIAGNOSTIC OPINION"
    VERIFICATION_URL_BASE = "https://genovex.ae/verify?ref="

    @classmethod
    def compute_integrity_hash(cls, report: AssessmentReport) -> str:
        gen_str = report.generated_at.isoformat() if report.generated_at else "STATIC"
        tier_str = getattr(report.outcome_tier, "value", str(report.outcome_tier))
        payload = (
            f"{report.report_reference}:{report.assessment_id}:"
            f"{report.questionnaire_version_tag}:{report.rule_engine_version}:"
            f"{tier_str}:{gen_str}:{report.is_urgent_red_flag}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def generate_pdf_report(
        cls,
        report: AssessmentReport,
        user: Optional[User] = None
    ) -> bytes:
        """
        Renders a multi-page bilingual PDF document from an AssessmentReport record.
        """
        if pymupdf is None:
            return b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000053 00000 n \n0000000102 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF"

        doc = pymupdf.open()
        font_path = get_unicode_font()
        font_name = "report_font" if font_path else "helv"

        # -------------------------------------------------------------
        # Page 1: Header, Metadata, QR Verification, Tier & Clinical Narrative
        # -------------------------------------------------------------
        page1 = doc.new_page(width=595, height=842)  # Standard A4
        cls._draw_watermark(page1, font_path, font_name)
        y = cls._draw_header(page1, report, font_path, font_name)
        y = cls._draw_metadata_box_with_qr(page1, report, y, font_path, font_name)
        y = cls._draw_outcome_tier_card(page1, report, y, font_path, font_name)
        y = cls._draw_explanation_section(page1, report, y, font_path, font_name)
        cls._draw_footer(page1, 1, 2, font_path, font_name)

        # -------------------------------------------------------------
        # Page 2: Risk Factors, Response Summary, Next Steps, Evidence & Disclaimers
        # -------------------------------------------------------------
        page2 = doc.new_page(width=595, height=842)
        cls._draw_watermark(page2, font_path, font_name)
        y2 = 30
        y2 = cls._draw_risk_factors_section(page2, report, y2, font_path, font_name)
        y2 = cls._draw_response_summary_section(page2, report, y2, font_path, font_name)
        y2 = cls._draw_navigation_and_next_steps(page2, report, y2, font_path, font_name)
        y2 = cls._draw_evidence_citations(page2, report, y2, font_path, font_name)
        cls._draw_disclaimer_box(page2, report, font_path, font_name)
        cls._draw_footer(page2, 2, 2, font_path, font_name)

        return doc.tobytes()

    @classmethod
    def _draw_watermark(cls, page: pymupdf.Page, font_path: Optional[str], font_name: str) -> None:
        """
        Draws the mandatory Phase 13 watermark across the page.
        Appears in the header strip and as a diagonal background element.
        """
        # 1. Top Watermark Banner Strip
        page.draw_rect(pymupdf.Rect(0, 0, 595, 18), fill=(0.93, 0.95, 0.96), color=None)
        page.insert_text(
            pymupdf.Point(36, 12),
            cls.MANDATORY_WATERMARK,
            fontname=font_name,
            fontfile=font_path,
            fontsize=7.5,
            color=(0.35, 0.40, 0.45)
        )

        # 2. Subtle Diagonal Center Watermark
        try:
            page.insert_text(
                pymupdf.Point(50, 480),
                cls.MANDATORY_WATERMARK,
                fontname=font_name,
                fontfile=font_path,
                fontsize=11,
                morph=(pymupdf.Point(50, 480), pymupdf.Matrix(-35)),
                color=(0.88, 0.90, 0.92)
            )
        except Exception:
            pass

    @classmethod
    def _draw_header(cls, page: pymupdf.Page, report: AssessmentReport, font_path: Optional[str], font_name: str) -> float:
        # Header banner (Teal background, shifted down slightly for top watermark strip)
        page.draw_rect(pymupdf.Rect(0, 18, 595, 88), color=None, fill=(0.06, 0.45, 0.45))

        # Platform Brand
        page.insert_text(
            pymupdf.Point(36, 48),
            "GENOVEX",
            fontname=font_name,
            fontfile=font_path,
            fontsize=20,
            color=(1, 1, 1)
        )
        page.insert_text(
            pymupdf.Point(36, 66),
            "Male Reproductive Health Risk Identification & Clinical Navigation Platform",
            fontname=font_name,
            fontfile=font_path,
            fontsize=8.5,
            color=(0.85, 0.95, 0.95)
        )
        page.insert_text(
            pymupdf.Point(375, 54),
            "منصة جينوفيكس لصحة الرجال",
            fontname=font_name,
            fontfile=font_path,
            fontsize=12,
            color=(1, 1, 1)
        )
        return 100.0

    @classmethod
    def _draw_metadata_box_with_qr(cls, page: pymupdf.Page, report: AssessmentReport, y: float, font_path: Optional[str], font_name: str) -> float:
        box_height = 80
        box = pymupdf.Rect(36, y, 559, y + box_height)
        page.draw_rect(box, color=(0.82, 0.85, 0.88), fill=(0.96, 0.97, 0.98), width=0.8)

        # Left Column: References & Timestamp
        page.insert_text(pymupdf.Point(46, y + 18), f"Report Reference: {report.report_reference}", fontname=font_name, fontfile=font_path, fontsize=9.5, color=(0.1, 0.15, 0.2))
        page.insert_text(pymupdf.Point(46, y + 34), f"Assessment Reference ID: {report.assessment_id[:24]}", fontname=font_name, fontfile=font_path, fontsize=8, color=(0.3, 0.35, 0.4))
        date_str = report.generated_at.strftime("%Y-%m-%d %H:%M UTC") if report.generated_at else datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        page.insert_text(pymupdf.Point(46, y + 49), f"Report Generation: {date_str}", fontname=font_name, fontfile=font_path, fontsize=8, color=(0.3, 0.35, 0.4))
        
        # Integrity Hash
        hash_val = cls.compute_integrity_hash(report)
        page.insert_text(pymupdf.Point(46, y + 66), f"SHA-256 Hash: {hash_val[:32]}...", fontname=font_name, fontfile=font_path, fontsize=7.5, color=(0.2, 0.35, 0.4))

        # Middle Column: Version Tracking
        page.insert_text(pymupdf.Point(280, y + 18), f"Questionnaire Version: {report.questionnaire_version_tag}", fontname=font_name, fontfile=font_path, fontsize=8, color=(0.2, 0.25, 0.3))
        page.insert_text(pymupdf.Point(280, y + 34), f"Clinical Rule Version: {report.rule_engine_version}", fontname=font_name, fontfile=font_path, fontsize=8, color=(0.2, 0.25, 0.3))
        page.insert_text(pymupdf.Point(280, y + 49), "Snapshot: Immutable & Pinned", fontname=font_name, fontfile=font_path, fontsize=8, color=(0.06, 0.45, 0.45))
        page.insert_text(pymupdf.Point(280, y + 66), "Verification: genovex.ae/verify", fontname=font_name, fontfile=font_path, fontsize=7.5, color=(0.15, 0.35, 0.5))

        # Right Column: Vector QR Code / Verification Badge
        verify_url = f"{cls.VERIFICATION_URL_BASE}{report.report_reference}"
        cls._draw_qr_code(page, verify_url, x0=480, y0=y + 10, size=60)

        return y + box_height + 15.0

    @classmethod
    def _draw_qr_code(cls, page: pymupdf.Page, url: str, x0: float, y0: float, size: float) -> None:
        """
        Draws a crisp QR code matrix or stylized verification badge.
        """
        if qrcode is not None:
            try:
                qr = qrcode.QRCode(box_size=1, border=0)
                qr.add_data(url)
                qr.make(fit=True)
                matrix = qr.get_matrix()
                n = len(matrix)
                cell = size / n
                # White background padding
                page.draw_rect(pymupdf.Rect(x0 - 2, y0 - 2, x0 + size + 2, y0 + size + 2), fill=(1, 1, 1), color=(0.85, 0.85, 0.85), width=0.5)
                for r in range(n):
                    for c in range(n):
                        if matrix[r][c]:
                            page.draw_rect(
                                pymupdf.Rect(x0 + c * cell, y0 + r * cell, x0 + (c + 1) * cell, y0 + (r + 1) * cell),
                                fill=(0.06, 0.25, 0.25),
                                color=None
                            )
                return
            except Exception:
                pass

        # Fallback Stylized Verification Badge
        page.draw_rect(pymupdf.Rect(x0, y0, x0 + size, y0 + size), fill=(0.95, 0.98, 0.98), color=(0.06, 0.45, 0.45), width=0.8)
        page.insert_text(pymupdf.Point(x0 + 8, y0 + 25), "VERIFY", fontsize=8.5, color=(0.06, 0.45, 0.45))
        page.insert_text(pymupdf.Point(x0 + 4, y0 + 42), "GENOVEX", fontsize=7.5, color=(0.1, 0.2, 0.3))

    @classmethod
    def _draw_outcome_tier_card(cls, page: pymupdf.Page, report: AssessmentReport, y: float, font_path: Optional[str], font_name: str) -> float:
        tier_val = getattr(report.outcome_tier, "value", str(report.outcome_tier))
        is_urgent = bool(report.is_urgent_red_flag)

        if is_urgent or "URGENT" in tier_val:
            bg_color = (0.99, 0.93, 0.93)
            border_color = (0.85, 0.2, 0.2)
            badge_color = (0.75, 0.1, 0.1)
        elif "SPECIALIST" in tier_val or "TIER_3" in tier_val or "CLINICAL_EVALUATION" in tier_val:
            bg_color = (0.99, 0.96, 0.90)
            border_color = (0.85, 0.55, 0.1)
            badge_color = (0.75, 0.45, 0.05)
        elif "LIFESTYLE" in tier_val or "TIER_2" in tier_val or "RISK_FACTORS" in tier_val:
            bg_color = (0.92, 0.97, 0.95)
            border_color = (0.1, 0.55, 0.45)
            badge_color = (0.06, 0.45, 0.45)
        else:
            bg_color = (0.94, 0.96, 0.98)
            border_color = (0.25, 0.45, 0.7)
            badge_color = (0.15, 0.35, 0.6)

        card_height = 95
        card = pymupdf.Rect(36, y, 559, y + card_height)
        page.draw_rect(card, color=border_color, fill=bg_color, width=1.2)

        page.insert_text(pymupdf.Point(50, y + 22), "ASSESSMENT OUTCOME TIER / تصنيف النتيجة الإكلينيكية", fontname=font_name, fontfile=font_path, fontsize=8.5, color=badge_color)

        page.insert_text(pymupdf.Point(50, y + 46), report.outcome_title_en or tier_val, fontname=font_name, fontfile=font_path, fontsize=12.5, color=(0.1, 0.1, 0.15))
        if report.outcome_title_ar:
            page.insert_text(pymupdf.Point(50, y + 66), report.outcome_title_ar, fontname=font_name, fontfile=font_path, fontsize=10.5, color=badge_color)

        if is_urgent:
            page.insert_text(pymupdf.Point(50, y + 84), "CRITICAL SAFETY RED FLAG: Immediate In-Person Evaluation Advised (4-6 Hours)", fontname=font_name, fontfile=font_path, fontsize=8, color=(0.8, 0.05, 0.05))

        return y + card_height + 16.0

    @classmethod
    def _draw_explanation_section(cls, page: pymupdf.Page, report: AssessmentReport, y: float, font_path: Optional[str], font_name: str) -> float:
        page.insert_text(pymupdf.Point(36, y), "Clinical Assessment Summary & Non-Diagnostic Findings", fontname=font_name, fontfile=font_path, fontsize=10.5, color=(0.06, 0.45, 0.45))
        page.draw_line(pymupdf.Point(36, y + 5), pymupdf.Point(559, y + 5), color=(0.06, 0.45, 0.45), width=0.8)
        y += 20

        desc_en = report.outcome_description_en or "Assessment completed with evidence-linked risk stratification."
        rect_en = pymupdf.Rect(36, y, 559, y + 110)
        page.insert_textbox(rect_en, desc_en, fontname=font_name, fontfile=font_path, fontsize=8.5, color=(0.15, 0.2, 0.25))
        y += 115

        if report.outcome_description_ar:
            page.insert_text(pymupdf.Point(36, y), "الملخص الإكلينيكي باللغة العربية:", fontname=font_name, fontfile=font_path, fontsize=9, color=(0.2, 0.25, 0.3))
            y += 15
            rect_ar = pymupdf.Rect(36, y, 559, y + 90)
            page.insert_textbox(rect_ar, report.outcome_description_ar, fontname=font_name, fontfile=font_path, fontsize=8, color=(0.2, 0.25, 0.3))
            y += 95

        return y

    @classmethod
    def _draw_risk_factors_section(cls, page: pymupdf.Page, report: AssessmentReport, y: float, font_path: Optional[str], font_name: str) -> float:
        page.insert_text(pymupdf.Point(36, y), "Identified Contributing Factors & Health Indicators", fontname=font_name, fontfile=font_path, fontsize=10.5, color=(0.06, 0.45, 0.45))
        page.draw_line(pymupdf.Point(36, y + 5), pymupdf.Point(559, y + 5), color=(0.06, 0.45, 0.45), width=0.8)
        y += 18

        factors = report.identified_risk_factors_json or []
        if not factors:
            page.insert_text(pymupdf.Point(40, y + 12), "• No elevated clinical risk factors reported across surveyed lifestyle or reproductive domains.", fontname=font_name, fontfile=font_path, fontsize=8, color=(0.2, 0.3, 0.2))
            return y + 26.0

        for f in factors[:4]:
            title = f.get("title_en") or f.get("factor_code") or "Reported Indicator"
            domain = f.get("domain", "General")
            severity = f.get("severity", "MODERATE")
            page.insert_text(pymupdf.Point(40, y + 11), f"• [{domain.upper()}] {title} (Severity: {severity})", fontname=font_name, fontfile=font_path, fontsize=8, color=(0.15, 0.2, 0.25))
            y += 15

        return y + 10.0

    @classmethod
    def _draw_response_summary_section(cls, page: pymupdf.Page, report: AssessmentReport, y: float, font_path: Optional[str], font_name: str) -> float:
        page.insert_text(pymupdf.Point(36, y), "Summary of Submitted Responses & Survey Completeness", fontname=font_name, fontfile=font_path, fontsize=10.5, color=(0.06, 0.45, 0.45))
        page.draw_line(pymupdf.Point(36, y + 5), pymupdf.Point(559, y + 5), color=(0.06, 0.45, 0.45), width=0.8)
        y += 18

        responses = report.responses_summary_json or []
        total_q = len(responses)
        unsure_q = sum(1 for r in responses if r.get("is_unsure"))
        declined_q = sum(1 for r in responses if r.get("is_prefer_not_to_say"))
        missing_q = sum(1 for r in responses if r.get("is_missing"))
        answered_q = total_q - (unsure_q + declined_q + missing_q)

        metrics_text = (
            f"Evaluated Questions: {total_q} | Explicitly Answered: {answered_q} | "
            f"Unknown/Unsure: {unsure_q} | Declined: {declined_q} | Unanswered: {missing_q}"
        )
        page.insert_text(pymupdf.Point(40, y + 11), metrics_text, fontname=font_name, fontfile=font_path, fontsize=8, color=(0.1, 0.3, 0.35))
        y += 18

        # Display up to 3 response highlights
        for r in responses[:3]:
            key = r.get("question_key", "Item")
            ans = r.get("answer_display_en", "Recorded")
            prompt = r.get("prompt_en", key)
            if len(prompt) > 65:
                prompt = prompt[:62] + "..."
            page.insert_text(pymupdf.Point(40, y + 10), f"• {prompt}: {ans}", fontname=font_name, fontfile=font_path, fontsize=7.5, color=(0.25, 0.3, 0.35))
            y += 14

        return y + 10.0

    @classmethod
    def _draw_navigation_and_next_steps(cls, page: pymupdf.Page, report: AssessmentReport, y: float, font_path: Optional[str], font_name: str) -> float:
        page.insert_text(pymupdf.Point(36, y), "Recommended Clinical Navigation & Next Steps", fontname=font_name, fontfile=font_path, fontsize=10.5, color=(0.06, 0.45, 0.45))
        page.draw_line(pymupdf.Point(36, y + 5), pymupdf.Point(559, y + 5), color=(0.06, 0.45, 0.45), width=0.8)
        y += 18

        specialties = report.recommended_specialties or []
        if specialties:
            specs_str = ", ".join(specialties)
            page.insert_text(pymupdf.Point(40, y + 11), f"Recommended Medical Specialties: {specs_str}", fontname=font_name, fontfile=font_path, fontsize=8.5, color=(0.06, 0.45, 0.45))
            y += 16

        steps_en = report.recommended_next_steps_en or []
        for step in steps_en[:3]:
            page.insert_text(pymupdf.Point(40, y + 11), f"• {step}", fontname=font_name, fontfile=font_path, fontsize=8, color=(0.15, 0.2, 0.25))
            y += 14

        return y + 10.0

    @classmethod
    def _draw_evidence_citations(cls, page: pymupdf.Page, report: AssessmentReport, y: float, font_path: Optional[str], font_name: str) -> float:
        page.insert_text(pymupdf.Point(36, y), "Clinical Evidence Basis & Guideline Citations", fontname=font_name, fontfile=font_path, fontsize=10.5, color=(0.06, 0.45, 0.45))
        page.draw_line(pymupdf.Point(36, y + 5), pymupdf.Point(559, y + 5), color=(0.06, 0.45, 0.45), width=0.8)
        y += 18

        citations = report.evidence_citations_json or []
        default_cites = [
            "European Association of Urology (EAU) Guidelines on Sexual and Reproductive Health (2024)",
            "American Urological Association (AUA) / ASRM Diagnosis and Treatment of Infertility in Men (2021)",
            "World Health Organization (WHO) Laboratory Manual for the Examination of Human Semen (6th Edition)"
        ]
        used_cites = citations if citations else default_cites
        for c in used_cites[:3]:
            cite_title = c.get("title") if isinstance(c, dict) else str(c)
            page.insert_text(pymupdf.Point(40, y + 10), f"• {cite_title}", fontname=font_name, fontfile=font_path, fontsize=7.5, color=(0.3, 0.35, 0.4))
            y += 14

        return y + 10.0

    @classmethod
    def _draw_disclaimer_box(cls, page: pymupdf.Page, report: AssessmentReport, font_path: Optional[str], font_name: str) -> None:
        """
        Draws the mandatory 5-point non-diagnostic disclaimer in English and Arabic.
        """
        y = 560
        box = pymupdf.Rect(36, y, 559, 790)
        page.draw_rect(box, color=(0.8, 0.8, 0.8), fill=(0.97, 0.97, 0.97), width=0.8)

        page.insert_text(pymupdf.Point(46, y + 16), "MANDATORY CLINICAL & LEGAL DISCLAIMER / إخلاء المسؤولية الطبية والقانونية", fontname=font_name, fontfile=font_path, fontsize=8, color=(0.55, 0.1, 0.1))

        # 5 Mandatory Specific Clinical Disclaimers (English)
        disclaimers_en = [
            "1. GENOVEX does not diagnose infertility.",
            "2. GENOVEX does not measure sperm count, motility or morphology.",
            "3. A low-risk questionnaire outcome does not establish normal fertility.",
            "4. The report is not a replacement for professional medical evaluation.",
            "5. Clinical decisions must be made by qualified healthcare professionals."
        ]
        ey = y + 30
        for line in disclaimers_en:
            page.insert_text(pymupdf.Point(46, ey), line, fontname=font_name, fontfile=font_path, fontsize=7, color=(0.25, 0.3, 0.35))
            ey += 12

        # 5 Mandatory Specific Clinical Disclaimers (Arabic)
        disclaimers_ar = [
            "١. منصة جينوفيكس لا تشخّص العقم بأي حال من الأحوال.",
            "٢. جينوفيكس لا يقيس عدد الحيوانات المنوية أو حركتها أو شكلها.",
            "٣. نتيجة الاستبيان منخفضة الخطورة لا تثبت الخصوبة الطبيعية بأي شكل.",
            "٤. هذا التقرير ليس بديلاً عن التقييم والفحص الطبي السريري المتخصص.",
            "٥. يجب اتخاذ القرارات الإكلينيكية بواسطة ممارسي رعاية صحية مؤهلين."
        ]
        ey += 4
        page.insert_text(pymupdf.Point(46, ey), "النقاط الإلزامية غير التشخيصية باللغة العربية:", fontname=font_name, fontfile=font_path, fontsize=7.5, color=(0.4, 0.15, 0.15))
        ey += 12
        for line in disclaimers_ar:
            page.insert_text(pymupdf.Point(46, ey), line, fontname=font_name, fontfile=font_path, fontsize=6.5, color=(0.3, 0.35, 0.4))
            ey += 11

    @classmethod
    def _draw_footer(cls, page: pymupdf.Page, current_page: int, total_pages: int, font_path: Optional[str], font_name: str) -> None:
        page.draw_line(pymupdf.Point(36, 805), pymupdf.Point(559, 805), color=(0.85, 0.85, 0.85), width=0.5)
        page.insert_text(
            pymupdf.Point(36, 820),
            "GENOVEX Digital Health | Strictly Confidential Medical Risk Stratification Snapshot",
            fontname=font_name,
            fontfile=font_path,
            fontsize=7.5,
            color=(0.5, 0.55, 0.6)
        )
        page.insert_text(
            pymupdf.Point(490, 820),
            f"Page {current_page} of {total_pages}",
            fontname=font_name,
            fontfile=font_path,
            fontsize=7.5,
            color=(0.5, 0.55, 0.6)
        )
