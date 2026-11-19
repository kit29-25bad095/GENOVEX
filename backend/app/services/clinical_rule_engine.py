import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.questionnaire import (
    Assessment, AssessmentResponse, Question, QuestionnaireVersion,
    AssessmentStatus, QuestionType
)
from app.models.clinical_rules import (
    ClinicalRule, ClinicalOutcomeTier, ClinicalRuleStatus, ClinicalRuleVersionRecord
)
from app.models.assessment_report import AssessmentReport
from app.core.security import User, RoleEnum

MANDATORY_DISCLAIMER_EN = (
    "CLINICAL & REGULATORY NOTICE: GENOVEX is an educational male reproductive health risk-identification "
    "and clinical navigation platform designed for the United Arab Emirates. It is NOT a diagnostic medical device "
    "and does NOT diagnose infertility, measure sperm count, motility, or morphology, or predict an individual's fertility probability. "
    "The absence of reported risk factors does NOT establish normal male fertility or exclude underlying pathology. "
    "Formal fertility evaluation requires comprehensive clinical examination and laboratory semen analysis by a licensed physician."
)

MANDATORY_DISCLAIMER_AR = (
    "إشعار سريري وتنظيمي: منصة جينوفيكس (GENOVEX) هي منصة رقمية تعليمية لتحديد عوامل الخطورة والتوجيه السريري "
    "في دولة الإمارات العربية المتحدة. المنصة ليست جهازاً طبياً تشخيصياً ولا تقوم بتشخيص العقم، أو قياس خصائص السائل المنوي "
    "(العدد، الحركة، والتشوهات)، أو التنبؤ بنسب الخصوبة الفردية. عدم تسجيل عوامل خطورة لا يعني بالضرورة الخصوبة الطبيعية "
    "أو استبعاد وجود حالات باطنية. يتطلب التقييم الطبي الدقيق فحصاً سريرياً شاملاً وتحليلاً مخبرياً للسائل المنوي تحت إشراف طبيب مختص."
)

class ClinicalRuleEngineService:
    """
    Deterministic Clinical Rule Engine & Evidence-Linked Report Compiler.
    Evaluates assessment responses against clinician-approved, versioned clinical rules.
    Pure deterministic logic — zero LLM in outcome determination.
    """

    @staticmethod
    def evaluate_predicate(
        trigger: Dict[str, Any],
        responses_by_key: Dict[str, AssessmentResponse]
    ) -> Tuple[bool, Optional[str]]:
        """
        Deterministically evaluates a rule trigger predicate against patient responses.
        Respects the Safe Answer Principle: missing or unsure answers never evaluate to true
        nor are they treated as negative findings.
        Returns (is_triggered, match_reason).
        """
        question_key = trigger.get("question_key")
        operator = trigger.get("operator", "equals").lower()
        expected_value = trigger.get("expected_value")
        expected_values = trigger.get("expected_values", [])

        if not question_key or question_key not in responses_by_key:
            return False, "Response not provided"

        resp = responses_by_key[question_key]

        # Safe Answer Principle: if user selected Unsure or Prefer Not to Say, do NOT trigger ordinary rule
        if resp.is_unsure or resp.is_prefer_not_to_say:
            return False, "User selected Unsure or Prefer not to say (Preserved as safe unknown)"

        # Extract concrete value
        val = None
        if hasattr(resp, "answer_value") and resp.answer_value is not None:
            val = resp.answer_value
        elif hasattr(resp, "response_value_json") and resp.response_value_json is not None:
            val = resp.response_value_json
        elif hasattr(resp, "value_bool") and resp.value_bool is not None:
            val = resp.value_bool
        elif hasattr(resp, "value_numeric") and resp.value_numeric is not None:
            val = resp.value_numeric
        elif hasattr(resp, "value_text") and resp.value_text is not None:
            val = resp.value_text

        if val is None:
            return False, "Null value"

        # Normalization for string/boolean comparisons
        str_val = str(val).lower() if isinstance(val, (str, bool)) else val

        if operator == "equals":
            exp_str = str(expected_value).lower() if isinstance(expected_value, (str, bool)) else expected_value
            if str_val == exp_str:
                return True, f"{question_key} equals {expected_value}"
        elif operator == "in":
            exp_list = [str(x).lower() if isinstance(x, (str, bool)) else x for x in expected_values]
            if str_val in exp_list:
                return True, f"{question_key} in {expected_values}"
        elif operator == "contains":
            # For MULTIPLE_CHOICE lists
            if isinstance(val, list):
                val_list = [str(x).lower() if isinstance(x, (str, bool)) else x for x in val]
                for exp in expected_values:
                    exp_s = str(exp).lower() if isinstance(exp, (str, bool)) else exp
                    if exp_s in val_list:
                        return True, f"{question_key} contains {exp}"
            elif isinstance(expected_value, str) and expected_value.lower() in str_val:
                return True, f"{question_key} contains {expected_value}"
        elif operator == "greater_than":
            try:
                if float(val) > float(expected_value):
                    return True, f"{question_key} ({val}) > {expected_value}"
            except (ValueError, TypeError):
                return False, "Numeric conversion error"
        elif operator == "less_than":
            try:
                if float(val) < float(expected_value):
                    return True, f"{question_key} ({val}) < {expected_value}"
            except (ValueError, TypeError):
                return False, "Numeric conversion error"

        return False, "Criteria not met"

    @classmethod
    def compile_assessment_report(
        cls,
        db: Session,
        assessment_id: int,
        session_token: str,
        user_id: Optional[int] = None
    ) -> AssessmentReport:
        """
        Executes full deterministic rule evaluation and compiles an immutable AssessmentReport snapshot.
        """
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment record not found")

        # Check if an existing locked report already exists (guaranteeing reproducibility)
        existing_report = db.query(AssessmentReport).filter(AssessmentReport.assessment_id == assessment_id).first()
        if existing_report and existing_report.is_locked:
            return existing_report

        # Load all responses for this assessment
        responses = db.query(AssessmentResponse).filter(AssessmentResponse.assessment_id == assessment_id).all()
        responses_by_key: Dict[str, AssessmentResponse] = {}
        
        # Load questions for response summary
        all_questions = db.query(Question).filter(Question.version_id == assessment.questionnaire_version_id).all()
        questions_by_id = {q.id: q for q in all_questions}
        questions_by_key = {q.question_key: q for q in all_questions}

        for r in responses:
            q = questions_by_id.get(r.question_id)
            if q:
                responses_by_key[q.question_key] = r

        # Retrieve all active published clinical rules, ordered by priority rank (1 = highest precedence)
        active_rules = db.query(ClinicalRule).filter(
            ClinicalRule.status == ClinicalRuleStatus.PUBLISHED
        ).order_by(ClinicalRule.priority_rank.asc()).all()

        triggered_rules: List[ClinicalRule] = []
        triggered_rules_snapshot: List[Dict[str, Any]] = []
        all_evidence_citations: List[Dict[str, Any]] = []

        # PART 4 & 5: Evaluate Rules deterministically (Urgent rules evaluated first due to priority_rank)
        for rule in active_rules:
            is_match, reason = cls.evaluate_predicate(rule.trigger_criteria, responses_by_key)
            if is_match:
                triggered_rules.append(rule)
                triggered_rules_snapshot.append({
                    "rule_code": rule.rule_code,
                    "rule_version": rule.rule_version,
                    "title_en": rule.title_en,
                    "title_ar": rule.title_ar,
                    "domain_code": rule.domain_code.value,
                    "outcome_tier": rule.outcome_tier.value,
                    "is_urgent_red_flag": rule.is_urgent_red_flag,
                    "priority_rank": rule.priority_rank,
                    "recommended_specialty": rule.recommended_specialty,
                    "clinical_rationale_en": rule.clinical_rationale_en,
                    "clinical_rationale_ar": rule.clinical_rationale_ar,
                    "evidence_references": rule.evidence_references,
                    "evidence_classification": rule.evidence_classification,
                    "matched_criteria": reason
                })
                # Collect evidence citations
                for ev in rule.evidence_references:
                    if ev not in all_evidence_citations:
                        all_evidence_citations.append(ev)

        # PART 4: URGENT SAFETY CIRCUIT PRIORITY CHECK
        urgent_rules = [r for r in triggered_rules if r.is_urgent_red_flag]
        has_urgent_red_flag = len(urgent_rules) > 0

        # Outcome Tier Categorization (1: None, 2: Identified, 3: Recommended, 4: Urgent)
        if has_urgent_red_flag:
            outcome_tier = ClinicalOutcomeTier.TIER_4_URGENT
            outcome_title_en = "URGENT MEDICAL ASSESSMENT REQUIRED"
            outcome_title_ar = "تقييم طبي طارئ مطلوب فوراً"
            
            # Differentiate emergency testicular torsion vs prompt testicular lump evaluation
            torsion_concerns = [r for r in urgent_rules if "PAIN" in r.rule_code]
            lump_concerns = [r for r in urgent_rules if "LUMP" in r.rule_code]

            emergency_guidance_parts_en = []
            emergency_guidance_parts_ar = []

            if torsion_concerns:
                emergency_guidance_parts_en.append(
                    "EMERGENCY SCROTAL EVALUATION: Reported acute, severe testicular pain requires immediate emergency evaluation "
                    "within 6 hours to assess testicular blood flow and exclude testicular torsion (UAE Emergency: 998 / 999). "
                    "Do not wait or delay in-person emergency examination."
                )
                emergency_guidance_parts_ar.append(
                    "تقييم طارئ لكيس الصفن: يتطلب ألم الخصية الحاد والمفاجئ فحصاً طبياً طارئاً وفورياً خلال 6 ساعات لتقييم التروية الدموية "
                    "واستبعاد التواء الخصية الحاد (طوارئ الإمارات: 998 / 999). تجنب الانتظار أو تأجيل الفحص."
                )

            if lump_concerns:
                emergency_guidance_parts_en.append(
                    "PROMPT UROLOGICAL EVALUATION: A new or firm, painless testicular mass warrants prompt clinical examination "
                    "and urgent high-resolution scrotal Doppler ultrasound to rule out testicular neoplasm. "
                    "Please schedule an in-person consultation with a Urologist as soon as possible."
                )
                emergency_guidance_parts_ar.append(
                    "تقييم مسالك بولية عاجل: وجود كتلة صلبة أو غير مؤلمة في الخصية يستدعي فحصاً سريرياً عاجلاً وفحص سونار دوبلر دقيق للصفن "
                    "لاستبعاد أورام الخصية. يرجى مراجعة طبيب المسالك البولية في أقرب وقت."
                )

            urgent_guidance_en = "\n\n".join(emergency_guidance_parts_en)
            urgent_guidance_ar = "\n\n".join(emergency_guidance_parts_ar)

            outcome_desc_en = (
                "Based on the clinical answers submitted, one or more high-priority symptoms requiring urgent medical attention "
                "have been reported. Ordinary fertility subspecialty navigation is paused in favor of immediate physical evaluation."
            )
            outcome_desc_ar = (
                "بناءً على الإجابات المسجلة، تم رصد أعراض سريرية ذات أولوية قصوى تتطلب تدخلاً طبياً عاجلاً. "
                "يتم إيقاف التقييم الإنجابي الروتيني مؤقتاً لصالح الفحص الطبي العاجل."
            )

        else:
            urgent_guidance_en = None
            urgent_guidance_ar = None

            eval_recommended_rules = [r for r in triggered_rules if r.outcome_tier == ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED]
            risk_identified_rules = [r for r in triggered_rules if r.outcome_tier == ClinicalOutcomeTier.TIER_2_RISK_FACTORS]

            if eval_recommended_rules:
                outcome_tier = ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED
                outcome_title_en = "CLINICAL EVALUATION RECOMMENDED"
                outcome_title_ar = "يوصى بالتقييم السريري لدى طبيب مختص"
                outcome_desc_en = (
                    "Reported responses indicate one or more significant male reproductive health factors where formal clinical consultation "
                    "and diagnostic evaluation (e.g. comprehensive physical exam, semen analysis, or hormonal panel) are guideline-indicated."
                )
                outcome_desc_ar = (
                    "تشير الإجابات المسجلة إلى وجود مؤشرات سريرية هامة في الصحة الإنجابية تستدعي التقييم الطبي المتخصص "
                    "(مثل الفحص السريري الشامل، فحص السائل المنوي المخبري، أو التحاليل الهرمونية) وفق الإرشادات السريرية المعتمدة."
                )
            elif risk_identified_rules:
                outcome_tier = ClinicalOutcomeTier.TIER_2_RISK_FACTORS
                outcome_title_en = "REPRODUCTIVE HEALTH RISK FACTORS IDENTIFIED"
                outcome_title_ar = "تم تحديد عوامل خطورة متعلقة بالصحة الإنجابية"
                outcome_desc_en = (
                    "Specific lifestyle, environmental, metabolic, or medical risk factors were identified that may influence male reproductive health "
                    "or semen parameters over time. While not constituting an infertility diagnosis, addressing these factors can optimize reproductive health."
                )
                outcome_desc_ar = (
                    "تم تحديد عوامل خطورة تتعلق بنمط الحياة أو البيئة أو الصحة الأيضية قد تؤثر على جودة النطاف والصحة الإنجابية على المدى الطويل. "
                    "هذه المؤشرات لا تعني تشخيص العقم، ولكن تعديلها والاهتمام بها يساهم في تحسين الصحة العامة والإنجابية."
                )
            else:
                outcome_tier = ClinicalOutcomeTier.TIER_1_NO_RISK
                outcome_title_en = "NO REPORTED RISK FACTORS IDENTIFIED"
                outcome_title_ar = "لم يتم تسجيل عوامل خطورة واضحة"
                outcome_desc_en = (
                    "Based strictly on the questionnaire responses provided, no overt risk factors were identified. "
                    "CRITICAL NOTE: Normal questionnaire answers do not measure microscopic sperm parameters or confirm normal fertility. "
                    "If you and your partner have been trying to conceive for 12 months (or 6 months if female partner is over 35), "
                    "formal clinical evaluation remains recommended regardless of questionnaire findings."
                )
                outcome_desc_ar = (
                    "بناءً على الإجابات المقدمة فقط، لم يتم رصد عوامل خطورة واضحة. "
                    "ملاحظة سريرية هامة: الإجابات الطبيعية في الاستبيان لا تقيس معايير السائل المنوي المخبرية ولا تؤكد الخصوبة الطبيعية. "
                    "في حال محاولة الإنجاب لمدة 12 شهراً (أو 6 أشهر إذا كان عمر الزوجة فوق 35)، يوصى بإجراء الفحص الطبي المخبري بغض النظر عن نتائج الاستبيان."
                )

        # Deduplicate and compile recommended clinical specialties
        specialties_set = set()
        for r in triggered_rules:
            if r.recommended_specialty:
                specialties_set.add(r.recommended_specialty)

        if outcome_tier == ClinicalOutcomeTier.TIER_4_URGENT:
            if torsion_concerns:
                specialties_list = ["Emergency Medicine / Acute Urology"]
            else:
                specialties_list = ["Urologist (Oncologic / General)", "Scrotal Doppler Ultrasound"]
        elif outcome_tier == ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED:
            specialties_list = sorted(list(specialties_set)) if specialties_set else ["Male Reproductive Urologist / Andrologist"]
        elif outcome_tier == ClinicalOutcomeTier.TIER_2_RISK_FACTORS:
            specialties_list = sorted(list(specialties_set)) if specialties_set else ["Primary Care / Lifestyle Medicine", "Urologist"]
        else:
            specialties_list = ["Primary Care / General Practice (Preventive Care)"]

        # Compile Recommended Next Steps
        recommended_next_steps_en: List[str] = []
        recommended_next_steps_ar: List[str] = []

        if outcome_tier == ClinicalOutcomeTier.TIER_4_URGENT:
            recommended_next_steps_en = [
                "Seek immediate in-person medical evaluation without delay.",
                "Visit the nearest hospital emergency department (Call 998 / 999 in UAE) if experiencing sudden severe scrotal pain.",
                "Do not take pain medication that might mask acute symptoms before physician examination."
            ]
            recommended_next_steps_ar = [
                "التوجه فوراً للفحص الطبي المباشر دون تأخير.",
                "مراجعة قسم الطوارئ في أقرب مستشفى (الاتصال بـ 998 / 999 في دولة الإمارات) عند وجود ألم حاد ومفاجئ.",
                "تجنب تناول المسكنات القوية قبل الفحص الطبي حتى لا تخفي الأعراض الحادة."
            ]
        elif outcome_tier == ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED:
            recommended_next_steps_en = [
                "Schedule a clinical consultation with a board-certified Male Reproductive Urologist / Andrologist in the UAE.",
                "Request a comprehensive physical examination including scrotal palpation.",
                "Obtain a standardized laboratory semen analysis in accordance with WHO 6th Edition guidelines.",
                "Review any current medications, anabolic substances, or supplements with your treating physician."
            ]
            recommended_next_steps_ar = [
                "حجز استشارة سريرية مع طبيب مسالك بولية وأمراض ذكورة مرخص في دولة الإمارات.",
                "إجراء فحص سريري شامل يشمل فحص كيس الصفن والخصيتين.",
                "إجراء تحليل مخبري معياري للسائل المنوي وفق معايير منظمة الصحة العالمية (الإصدار السادس).",
                "مراجعة جميع الأدوية والمنشطات والمكملات الغذائية المستخدمة مع الطبيب المختص."
            ]
        elif outcome_tier == ClinicalOutcomeTier.TIER_2_RISK_FACTORS:
            recommended_next_steps_en = [
                "Consult with a healthcare provider regarding identified lifestyle and metabolic factors.",
                "Implement evidence-based modifications: eliminate tobacco / dokha / shisha use, avoid scrotal heat sources.",
                "Optimize metabolic health through nutritional counseling and regular physical activity.",
                "Consider baseline preventive reproductive health screening if planning conception."
            ]
            recommended_next_ar = [
                "استشارة مقدم الرعاية الصحية حول عوامل نمط الحياة والصحة الأيضية المسجلة.",
                "تطبيق تعديلات قائمة على الأدلة: الإقلاع عن التدخين والدوخة والشيشة، وتجنب تعريض الخصيتين للحرارة المرتفعة.",
                "تحسين الصحة الأيضية من خلال التغذية السليمة والنشاط البدني المنتظم.",
                "النظر في إجراء فحص استباقي للاطمئنان على الصحة الإنجابية عند التخطيط للإنجاب."
            ]
            recommended_next_steps_ar = recommended_next_ar
        else:
            recommended_next_steps_en = [
                "Maintain healthy lifestyle habits supporting general and reproductive health.",
                "Continue tracking time to pregnancy; if unprotected intercourse exceeds 12 months, seek clinical evaluation.",
                "Share this report with your family physician during regular annual check-ups."
            ]
            recommended_next_steps_ar = [
                "الحفاظ على نمط حياة صحي يدعم الصحة العامة والإنجابية.",
                "متابعة فترة محاولة الحمل؛ إذا تجاوزت المحاولة المنتظمة 12 شهراً، يوصى بمراجعة الطبيب المختص.",
                "مشاركة هذا التقرير مع طبيب الأسرة أثناء الفحوصات الدورية."
            ]

        # Consolidate distinct, deduplicated risk factors
        identified_risk_factors: List[Dict[str, Any]] = []
        seen_factors = set()

        for r in triggered_rules:
            factor_code = r.target_condition_slug or r.rule_code
            if factor_code not in seen_factors:
                seen_factors.add(factor_code)
                severity = "MODERATE"
                if r.is_urgent_red_flag:
                    severity = "CRITICAL_URGENT"
                elif r.outcome_tier == ClinicalOutcomeTier.TIER_3_EVAL_RECOMMENDED:
                    severity = "HIGH"

                identified_risk_factors.append({
                    "factor_code": factor_code,
                    "rule_code": r.rule_code,
                    "domain": r.domain_code.value,
                    "title_en": r.title_en,
                    "title_ar": r.title_ar,
                    "description_en": r.clinical_rationale_en,
                    "description_ar": r.clinical_rationale_ar,
                    "severity": severity,
                    "clinical_specialty": r.recommended_specialty,
                    "evidence_classification": r.evidence_classification
                })

        # Responses Summary Snapshot (Preserving safe answer flags)
        responses_summary: List[Dict[str, Any]] = []
        for q in all_questions:
            resp = responses_by_key.get(q.question_key)
            if resp:
                raw_val = getattr(resp, 'answer_value', None)
                if raw_val is None:
                    raw_val = getattr(resp, 'value_bool', None) or getattr(resp, 'value_numeric', None) or getattr(resp, 'value_text', None) or getattr(resp, 'response_value_json', None)
                val_display_en = str(raw_val) if raw_val is not None else ""
                val_display_ar = val_display_en
                if resp.is_unsure:
                    val_display_en = "Unsure / Do not know"
                    val_display_ar = "غير متأكد / لا أعلم"
                elif resp.is_prefer_not_to_say:
                    val_display_en = "Prefer not to answer"
                    val_display_ar = "أفضل عدم الإجابة"

                responses_summary.append({
                    "question_key": q.question_key,
                    "domain_code": q.domain_code.value,
                    "prompt_en": q.text_en,
                    "prompt_ar": q.text_ar,
                    "answer_display_en": val_display_en,
                    "answer_display_ar": val_display_ar,
                    "is_unsure": resp.is_unsure,
                    "is_prefer_not_to_say": resp.is_prefer_not_to_say,
                    "is_missing": False
                })
            else:
                responses_summary.append({
                    "question_key": q.question_key,
                    "domain_code": q.domain_code.value,
                    "prompt_en": q.text_en,
                    "prompt_ar": q.text_ar,
                    "answer_display_en": "Not answered (Preserved as safe missing)",
                    "answer_display_ar": "لم تتم الإجابة (محفوظة كغير محددة بأمان)",
                    "is_unsure": False,
                    "is_prefer_not_to_say": False,
                    "is_missing": True
                })

        # Generate unique report reference ID (e.g. GNX-RPT-2026-XXXXX)
        ref_suffix = uuid.uuid4().hex[:6].upper()
        report_reference = f"GNX-RPT-2026-{ref_suffix}"

        # Fetch questionnaire version tag
        q_version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.id == assessment.questionnaire_version_id).first()
        version_tag = q_version.version_tag if q_version else "v1.0.0"

        # Create immutable AssessmentReport
        report = AssessmentReport(
            report_reference=report_reference,
            assessment_id=assessment_id,
            user_id=user_id or assessment.user_id,
            session_token=session_token,
            questionnaire_version_tag=version_tag,
            rule_engine_version="v1.0.0",
            outcome_tier=outcome_tier,
            outcome_title_en=outcome_title_en,
            outcome_title_ar=outcome_title_ar,
            outcome_description_en=outcome_desc_en,
            outcome_description_ar=outcome_desc_ar,
            is_urgent_red_flag=has_urgent_red_flag,
            urgent_emergency_guidance_en=urgent_guidance_en,
            urgent_emergency_guidance_ar=urgent_guidance_ar,
            recommended_specialties=specialties_list,
            recommended_next_steps_en=recommended_next_steps_en,
            recommended_next_steps_ar=recommended_next_steps_ar,
            identified_risk_factors_json=identified_risk_factors,
            triggered_rules_snapshot_json=triggered_rules_snapshot,
            responses_summary_json=responses_summary,
            evidence_citations_json=all_evidence_citations,
            clinical_disclaimer_en=MANDATORY_DISCLAIMER_EN,
            clinical_disclaimer_ar=MANDATORY_DISCLAIMER_AR,
            is_locked=True,
            generated_at=datetime.now(timezone.utc)
        )
        db.add(report)

        # Mark assessment as SUBMITTED / LOCKED
        assessment.status = AssessmentStatus.SUBMITTED
        assessment.progress_percentage = 100
        assessment.has_urgent_red_flags = has_urgent_red_flag
        if has_urgent_red_flag:
            assessment.red_flag_details_json = [r.rule_code for r in urgent_rules]

        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def get_report_by_session(db: Session, session_token: str) -> AssessmentReport:
        report = db.query(AssessmentReport).filter(AssessmentReport.session_token == session_token).first()
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment report not found for this session")
        return report
