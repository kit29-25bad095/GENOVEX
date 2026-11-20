import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import pymupdf
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
    High-Fidelity Evidence-Linked Bilingual PDF Report Generation Service.
    Compiles immutable assessment snapshots into secure, downloadable clinical reports.
    """

    @classmethod
    def generate_pdf_report(
        cls,
        report: AssessmentReport,
        user: Optional[User] = None
    ) -> bytes:
        """
        Renders a multi-page bilingual PDF document from an AssessmentReport record.
        """
        doc = pymupdf.open()
        font_path = get_unicode_font()
        font_name = "report_font" if font_path else "helv"

        # Page 1: Executive Clinical Summary & Risk Tier
        page1 = doc.new_page(width=595, height=842)  # Standard A4
        y = cls._draw_header(page1, report, font_path, font_name)
        y = cls._draw_metadata_box(page1, report, y, font_path, font_name)
        y = cls._draw_outcome_tier_card(page1, report, y, font_path, font_name)
        y = cls._draw_explanation_section(page1, report, y, font_path, font_name)
        cls._draw_footer(page1, 1, 2, font_path, font_name)

        # Page 2: Risk Factors, Evidence Citations, Next Steps & Disclaimers
        page2 = doc.new_page(width=595, height=842)
        y2 = 40
        y2 = cls._draw_risk_factors_section(page2, report, y2, font_path, font_name)
        y2 = cls._draw_navigation_and_next_steps(page2, report, y2, font_path, font_name)
        y2 = cls._draw_evidence_citations(page2, report, y2, font_path, font_name)
        cls._draw_disclaimer_box(page2, report, font_path, font_name)
        cls._draw_footer(page2, 2, 2, font_path, font_name)

        return doc.tobytes()

    @classmethod
    def _draw_header(cls, page: pymupdf.Page, report: AssessmentReport, font_path: Optional[str], font_name: str) -> float:
        # Header banner (Teal background)
        page.draw_rect(pymupdf.Rect(0, 0, 595, 80), color=None, fill=(0.06, 0.45, 0.45))
        
        # Platform Brand
        page.insert_text(
            pymupdf.Point(36, 38),
            "GENOVEX",
            fontname=font_name,
            fontfile=font_path,
            fontsize=20,
            color=(1, 1, 1)
        )
        page.insert_text(
            pymupdf.Point(36, 56),
            "Male Reproductive Health Risk Identification & Clinical Navigation Platform",
            fontname=font_name,
            fontfile=font_path,
            fontsize=9,
            color=(0.85, 0.95, 0.95)
        )
        page.insert_text(
            pymupdf.Point(380, 48),
            "منصة جينوفيكس لصحة الرجال",
            fontname=font_name,
            fontfile=font_path,
            fontsize=12,
            color=(1, 1, 1)
        )
        return 95.0

    @classmethod
    def _draw_metadata_box(cls, page: pymupdf.Page, report: AssessmentReport, y: float, font_path: Optional[str], font_name: str) -> float:
        box = pymupdf.Rect(36, y, 559, y + 65)
        page.draw_rect(box, color=(0.82, 0.85, 0.88), fill=(0.96, 0.97, 0.98), width=0.8)

        # Left Column: References
        page.insert_text(pymupdf.Point(50, y + 20), f"Report Reference: {report.report_reference}", fontname=font_name, fontfile=font_path, fontsize=9.5, color=(0.1, 0.15, 0.2))
        page.insert_text(pymupdf.Point(50, y + 36), f"Assessment ID: {report.assessment_id[:18]}...", fontname=font_name, fontfile=font_path, fontsize=8.5, color=(0.3, 0.35, 0.4))
        date_str = report.generated_at.strftime("%Y-%m-%d %H:%M UTC") if report.generated_at else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        page.insert_text(pymupdf.Point(50, y + 52), f"Generated: {date_str}", fontname=font_name, fontfile=font_path, fontsize=8.5, color=(0.3, 0.35, 0.4))

        # Right Column: Engine Versions
        page.insert_text(pymupdf.Point(340, y + 20), f"Questionnaire Version: {report.questionnaire_version_tag}", fontname=font_name, fontfile=font_path, fontsize=8.5, color=(0.2, 0.25, 0.3))
        page.insert_text(pymupdf.Point(340, y + 36), f"Rule Engine Version: {report.rule_engine_version}", fontname=font_name, fontfile=font_path, fontsize=8.5, color=(0.2, 0.25, 0.3))
        page.insert_text(pymupdf.Point(340, y + 52), "Clinical Snapshot: Immutable & Pinned", fontname=font_name, fontfile=font_path, fontsize=8.5, color=(0.06, 0.45, 0.45))

        return y + 80.0

    @classmethod
    def _draw_outcome_tier_card(cls, page: pymupdf.Page, report: AssessmentReport, y: float, font_path: Optional[str], font_name: str) -> float:
        tier_val = getattr(report.outcome_tier, "value", str(report.outcome_tier))
        is_urgent = bool(report.is_urgent_red_flag)

        # Color mapping based on tier
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

        # Tier Category Label
        page.insert_text(pymupdf.Point(50, y + 24), "ASSESSMENT OUTCOME TIER / تصنيف النتيجة الإكلينيكية", fontname=font_name, fontfile=font_path, fontsize=8.5, color=badge_color)

        # Outcome Titles
        page.insert_text(pymupdf.Point(50, y + 48), report.outcome_title_en or tier_val, fontname=font_name, fontfile=font_path, fontsize=13, color=(0.1, 0.1, 0.15))
        if report.outcome_title_ar:
            page.insert_text(pymupdf.Point(50, y + 68), report.outcome_title_ar, fontname=font_name, fontfile=font_path, fontsize=11, color=badge_color)

        # Urgent Banner if applicable
        if is_urgent:
            page.insert_text(pymupdf.Point(50, y + 86), "CRITICAL SAFETY RED FLAG: Immediate In-Person Evaluation Advised (4-6 Hours)", fontname=font_name, fontfile=font_path, fontsize=8.5, color=(0.8, 0.05, 0.05))

        return y + card_height + 18.0

    @classmethod
    def _draw_explanation_section(cls, page: pymupdf.Page, report: AssessmentReport, y: float, font_path: Optional[str], font_name: str) -> float:
        page.insert_text(pymupdf.Point(36, y), "Clinical Assessment Summary & Non-Diagnostic Findings", fontname=font_name, fontfile=font_path, fontsize=11, color=(0.06, 0.45, 0.45))
        page.draw_line(pymupdf.Point(36, y + 5), pymupdf.Point(559, y + 5), color=(0.06, 0.45, 0.45), width=0.8)
        y += 22

        desc_en = report.outcome_description_en or "Assessment completed with evidence-linked risk stratification."
        # Wrap English description
        rect_en = pymupdf.Rect(36, y, 559, y + 120)
        page.insert_textbox(rect_en, desc_en, fontname=font_name, fontfile=font_path, fontsize=9, color=(0.15, 0.2, 0.25))
        y += 130

        if report.outcome_description_ar:
            page.insert_text(pymupdf.Point(36, y), "الملخص الإكلينيكي باللغة العربية:", fontname=font_name, fontfile=font_path, fontsize=9.5, color=(0.2, 0.25, 0.3))
            y += 16
            rect_ar = pymupdf.Rect(36, y, 559, y + 100)
            page.insert_textbox(rect_ar, report.outcome_description_ar, fontname=font_name, fontfile=font_path, fontsize=8.5, color=(0.2, 0.25, 0.3))
            y += 110

        return y

    @classmethod
    def _draw_risk_factors_section(cls, page: pymupdf.Page, report: AssessmentReport, y: float, font_path: Optional[str], font_name: str) -> float:
        page.insert_text(pymupdf.Point(36, y), "Identified Contributing Factors & Health Indicators", fontname=font_name, fontfile=font_path, fontsize=11, color=(0.06, 0.45, 0.45))
        page.draw_line(pymupdf.Point(36, y + 5), pymupdf.Point(559, y + 5), color=(0.06, 0.45, 0.45), width=0.8)
        y += 20

        factors = report.identified_risk_factors_json or []
        if not factors:
            page.insert_text(pymupdf.Point(40, y + 15), "• No elevated clinical risk factors reported across surveyed lifestyle or reproductive domains.", fontname=font_name, fontfile=font_path, fontsize=8.5, color=(0.2, 0.3, 0.2))
            return y + 35.0

        for f in factors[:5]:  # Top factors
            title = f.get("title_en") or f.get("factor_code") or "Reported Indicator"
            domain = f.get("domain", "General")
            severity = f.get("severity", "MODERATE")
            page.insert_text(pymupdf.Point(40, y + 12), f"• [{domain.upper()}] {title} (Severity: {severity})", fontname=font_name, fontfile=font_path, fontsize=8.5, color=(0.15, 0.2, 0.25))
            y += 18

        return y + 15.0

    @classmethod
    def _draw_navigation_and_next_steps(cls, page: pymupdf.Page, report: AssessmentReport, y: float, font_path: Optional[str], font_name: str) -> float:
        page.insert_text(pymupdf.Point(36, y), "Recommended Clinical Navigation & Next Steps", fontname=font_name, fontfile=font_path, fontsize=11, color=(0.06, 0.45, 0.45))
        page.draw_line(pymupdf.Point(36, y + 5), pymupdf.Point(559, y + 5), color=(0.06, 0.45, 0.45), width=0.8)
        y += 20

        specialties = report.recommended_specialties or []
        if specialties:
            specs_str = ", ".join(specialties)
            page.insert_text(pymupdf.Point(40, y + 12), f"Recommended Medical Specialties: {specs_str}", fontname=font_name, fontfile=font_path, fontsize=9, color=(0.06, 0.45, 0.45))
            y += 20

        steps_en = report.recommended_next_steps_en or []
        for step in steps_en[:4]:
            page.insert_text(pymupdf.Point(40, y + 12), f"• {step}", fontname=font_name, fontfile=font_path, fontsize=8.5, color=(0.15, 0.2, 0.25))
            y += 16

        return y + 15.0

    @classmethod
    def _draw_evidence_citations(cls, page: pymupdf.Page, report: AssessmentReport, y: float, font_path: Optional[str], font_name: str) -> float:
        page.insert_text(pymupdf.Point(36, y), "Clinical Evidence Basis & Guideline Citations", fontname=font_name, fontfile=font_path, fontsize=11, color=(0.06, 0.45, 0.45))
        page.draw_line(pymupdf.Point(36, y + 5), pymupdf.Point(559, y + 5), color=(0.06, 0.45, 0.45), width=0.8)
        y += 20

        citations = report.evidence_citations_json or []
        default_cites = [
            "European Association of Urology (EAU) Guidelines on Sexual and Reproductive Health (2024)",
            "American Urological Association (AUA) / ASRM Diagnosis and Treatment of Infertility in Men (2021)",
            "World Health Organization (WHO) Laboratory Manual for the Examination of Human Semen (6th Edition)"
        ]
        used_cites = citations if citations else default_cites
        for c in used_cites[:4]:
            cite_title = c.get("title") if isinstance(c, dict) else str(c)
            page.insert_text(pymupdf.Point(40, y + 12), f"• {cite_title}", fontname=font_name, fontfile=font_path, fontsize=8, color=(0.3, 0.35, 0.4))
            y += 16

        return y + 15.0

    @classmethod
    def _draw_disclaimer_box(cls, page: pymupdf.Page, report: AssessmentReport, font_path: Optional[str], font_name: str) -> None:
        y = 660
        box = pymupdf.Rect(36, y, 559, 790)
        page.draw_rect(box, color=(0.8, 0.8, 0.8), fill=(0.97, 0.97, 0.97), width=0.8)

        page.insert_text(pymupdf.Point(46, y + 18), "MANDATORY CLINICAL & LEGAL DISCLAIMER / إخلاء المسؤولية الطبية والقانونية", fontname=font_name, fontfile=font_path, fontsize=8, color=(0.5, 0.1, 0.1))

        disclaimer_text = (
            "GENOVEX provides evidence-linked digital health risk identification, health education, and clinical navigation assistance. "
            "This report does NOT constitute a formal medical diagnosis, prognosis, treatment prescription, or physician referral. "
            "It does NOT replace an in-person physical clinical examination by a licensed urologist, andrologist, or fertility specialist, "
            "nor does it replace laboratory semen analysis. If you experience acute scrotal pain, swelling, or trauma, seek emergency medical care immediately."
        )
        rect = pymupdf.Rect(46, y + 25, 549, 785)
        page.insert_textbox(rect, disclaimer_text, fontname=font_name, fontfile=font_path, fontsize=7.5, color=(0.3, 0.35, 0.4))

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
