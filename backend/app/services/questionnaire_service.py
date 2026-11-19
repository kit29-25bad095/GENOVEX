from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, desc
from fastapi import HTTPException, status
import uuid

from app.models.questionnaire import (
    QuestionnaireVersion, Question, Assessment, AssessmentResponse,
    QuestionnaireStatus, QuestionDomain, QuestionType, AssessmentStatus
)
from app.core.security import User, RoleEnum, AuditLog
from app.schemas.questionnaire import (
    QuestionCreate, QuestionUpdate, QuestionnaireVersionCreate,
    AnswerInput, SaveDomainResponsesRequest, SaveDomainResponsesResponse,
    AssessmentStartResponse, DomainQuestionsResponse, QuestionResponse,
    ReviewDomainGroup, ReviewQuestionAnswerItem, AssessmentReviewResponse,
    AssessmentSubmitResponse
)

DOMAINS_METADATA = [
    {"code": QuestionDomain.BASIC_HEALTH, "index": 0, "title_en": "Basic Health Information", "title_ar": "المعلومات الصحية الأساسية"},
    {"code": QuestionDomain.REPRODUCTIVE_HISTORY, "index": 1, "title_en": "Reproductive History", "title_ar": "التاريخ الإنجابي"},
    {"code": QuestionDomain.TESTICULAR_HISTORY, "index": 2, "title_en": "Testicular History", "title_ar": "التاريخ الخصوي والجراحي"},
    {"code": QuestionDomain.MEDICAL_HISTORY, "index": 3, "title_en": "Medical History", "title_ar": "التاريخ الطبي العام"},
    {"code": QuestionDomain.HORMONAL_HEALTH, "index": 4, "title_en": "Hormonal Health", "title_ar": "الصحة الهرمونية والغدد الصماء"},
    {"code": QuestionDomain.METABOLIC_HEALTH, "index": 5, "title_en": "Metabolic Health", "title_ar": "الصحة الأيضية ونمط الغذاء"},
    {"code": QuestionDomain.LIFESTYLE_HABITS, "index": 6, "title_en": "Lifestyle & Habits", "title_ar": "العادات ونمط الحياة"},
    {"code": QuestionDomain.MEDICATION_SUBSTANCE, "index": 7, "title_en": "Medication & Substance History", "title_ar": "الأدوية والمستحضرات الهرمونية"},
    {"code": QuestionDomain.OCCUPATIONAL_EXPOSURE, "index": 8, "title_en": "Occupational & Environmental Exposure", "title_ar": "التعرض المهني والبيئي"},
    {"code": QuestionDomain.SEXUAL_EJACULATORY, "index": 9, "title_en": "Sexual & Ejaculatory Health", "title_ar": "الصحة الجنسية والقذف"},
    {"code": QuestionDomain.FAMILY_GENETIC, "index": 10, "title_en": "Family & Genetic History", "title_ar": "التاريخ العائلي والجيني"},
]

class QuestionnaireService:

    # =========================================================================
    # Questionnaire Versioning & CMS Operations
    # =========================================================================

    @classmethod
    def create_version(cls, db: Session, data: QuestionnaireVersionCreate, user: Optional[User] = None) -> QuestionnaireVersion:
        existing = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.version_tag == data.version_tag).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Questionnaire version '{data.version_tag}' already exists")

        version = QuestionnaireVersion(
            version_tag=data.version_tag,
            title_en=data.title_en,
            title_ar=data.title_ar,
            status=QuestionnaireStatus.DRAFT
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        return version

    @classmethod
    def list_versions(cls, db: Session) -> List[Dict[str, Any]]:
        versions = db.query(QuestionnaireVersion).options(joinedload(QuestionnaireVersion.questions)).order_by(desc(QuestionnaireVersion.created_at)).all()
        results = []
        for v in versions:
            results.append({
                "id": v.id,
                "version_tag": v.version_tag,
                "title_en": v.title_en,
                "title_ar": v.title_ar,
                "status": v.status,
                "published_at": v.published_at,
                "archived_at": v.archived_at,
                "clinical_reviewer_id": v.clinical_reviewer_id,
                "clinical_reviewer_notes": v.clinical_reviewer_notes,
                "questions_count": len(v.questions),
                "created_at": v.created_at,
                "updated_at": v.updated_at
            })
        return results

    @classmethod
    def add_question(cls, db: Session, data: QuestionCreate, user: Optional[User] = None) -> Question:
        version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.id == data.version_id).first()
        if not version:
            raise HTTPException(status_code=404, detail="Questionnaire version not found")
        if version.status == QuestionnaireStatus.PUBLISHED:
            raise HTTPException(status_code=400, detail="Cannot modify a published questionnaire version. Create a new draft version.")

        existing_key = db.query(Question).filter(
            Question.version_id == data.version_id,
            Question.question_key == data.question_key
        ).first()
        if existing_key:
            raise HTTPException(status_code=400, detail=f"Question key '{data.question_key}' already exists in this version")

        question = Question(
            version_id=data.version_id,
            domain_code=data.domain_code,
            question_key=data.question_key,
            text_en=data.text_en,
            text_ar=data.text_ar,
            help_text_en=data.help_text_en,
            help_text_ar=data.help_text_ar,
            question_type=data.question_type,
            options_json=[opt.model_dump() for opt in data.options_json],
            is_required=data.is_required,
            allows_unsure=data.allows_unsure,
            allows_prefer_not_to_say=data.allows_prefer_not_to_say,
            clinical_rationale_en=data.clinical_rationale_en,
            clinical_rationale_ar=data.clinical_rationale_ar,
            evidence_references=data.evidence_references,
            display_order=data.display_order,
            is_urgent_red_flag=data.is_urgent_red_flag,
            conditional_parent_key=data.conditional_parent_key,
            conditional_trigger_values=data.conditional_trigger_values
        )
        db.add(question)
        db.commit()
        db.refresh(question)
        return question

    @classmethod
    def publish_version(cls, db: Session, version_id: int, user: Optional[User], notes: Optional[str] = None) -> QuestionnaireVersion:
        version = db.query(QuestionnaireVersion).filter(QuestionnaireVersion.id == version_id).first()
        if not version:
            raise HTTPException(status_code=404, detail="Version not found")

        # Clinical Role Guard: Only clinicians or superadmins can approve & publish questionnaires
        if user and user.role not in [RoleEnum.CLINICIAN, RoleEnum.SUPERADMIN]:
            raise HTTPException(status_code=403, detail="Unauthorized: Only clinicians or superadmins can approve and publish questionnaire versions")

        # Archive any previously published versions
        db.query(QuestionnaireVersion).filter(
            QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED,
            QuestionnaireVersion.id != version_id
        ).update({
            "status": QuestionnaireStatus.ARCHIVED,
            "archived_at": datetime.now(timezone.utc)
        })

        version.status = QuestionnaireStatus.PUBLISHED
        version.published_at = datetime.now(timezone.utc)
        version.clinical_reviewer_id = user.id if user else None
        version.clinical_reviewer_notes = notes or "Clinically approved for production use"

        db.commit()
        db.refresh(version)
        return version

    # =========================================================================
    # Adaptive Questionnaire Assessment Engine
    # =========================================================================

    @classmethod
    def start_or_resume_assessment(
        cls, db: Session, user: Optional[User] = None, session_token: Optional[str] = None
    ) -> AssessmentStartResponse:
        # 1. Check if existing active assessment exists for this session token
        if session_token:
            existing = db.query(Assessment).options(
                joinedload(Assessment.questionnaire_version)
            ).filter(
                Assessment.session_token == session_token,
                Assessment.status.in_([AssessmentStatus.IN_PROGRESS, AssessmentStatus.REVIEW_READY])
            ).first()
            if existing:
                return AssessmentStartResponse(
                    assessment_id=existing.id,
                    session_token=existing.session_token,
                    questionnaire_version_id=existing.questionnaire_version_id,
                    version_tag=existing.questionnaire_version.version_tag,
                    status=existing.status,
                    current_domain_index=existing.current_domain_index,
                    total_domains=existing.total_domains,
                    domains_meta=DOMAINS_METADATA
                )

        # 2. Get active published version, or fallback to latest version
        active_version = db.query(QuestionnaireVersion).filter(
            QuestionnaireVersion.status == QuestionnaireStatus.PUBLISHED
        ).order_by(desc(QuestionnaireVersion.published_at)).first()

        if not active_version:
            active_version = db.query(QuestionnaireVersion).order_by(desc(QuestionnaireVersion.created_at)).first()

        if not active_version:
            raise HTTPException(status_code=500, detail="No active questionnaire version found in platform")

        # 3. Create new assessment PINNED to this exact version
        new_token = session_token or str(uuid.uuid4())
        assessment = Assessment(
            user_id=user.id if user else None,
            session_token=new_token,
            questionnaire_version_id=active_version.id,
            status=AssessmentStatus.IN_PROGRESS,
            current_domain_index=0,
            total_domains=11
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

        return AssessmentStartResponse(
            assessment_id=assessment.id,
            session_token=assessment.session_token,
            questionnaire_version_id=assessment.questionnaire_version_id,
            version_tag=active_version.version_tag,
            status=assessment.status,
            current_domain_index=0,
            total_domains=11,
            domains_meta=DOMAINS_METADATA
        )

    @classmethod
    def get_domain_questions(
        cls, db: Session, assessment_id: str, domain_index: int
    ) -> DomainQuestionsResponse:
        if domain_index < 0 or domain_index >= len(DOMAINS_METADATA):
            raise HTTPException(status_code=400, detail="Invalid domain index")

        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        domain_meta = DOMAINS_METADATA[domain_index]
        domain_code = domain_meta["code"]

        # Fetch questions for this domain belonging strictly to the pinned version
        questions = db.query(Question).filter(
            Question.version_id == assessment.questionnaire_version_id,
            Question.domain_code == domain_code
        ).order_by(Question.display_order).all()

        # Fetch saved answers for this assessment
        saved_responses = db.query(AssessmentResponse).filter(
            AssessmentResponse.assessment_id == assessment_id
        ).all()
        saved_dict = {}
        for r in saved_responses:
            saved_dict[r.question_key] = {
                "answer_value": r.answer_value,
                "is_unsure": r.is_unsure,
                "is_prefer_not_to_say": r.is_prefer_not_to_say
            }

        # Dynamic Visibility Check: Filter follow-up questions whose parent conditions are not satisfied
        visible_questions = []
        for q in questions:
            if not q.conditional_parent_key:
                visible_questions.append(QuestionResponse.model_validate(q))
            else:
                parent_answer = saved_dict.get(q.conditional_parent_key, {}).get("answer_value")
                trigger_values = q.conditional_trigger_values or []
                
                # Check if parent answer matches any trigger value (case-insensitive string match)
                is_triggered = False
                if parent_answer is not None:
                    parent_str = str(parent_answer).strip().lower()
                    for tv in trigger_values:
                        if str(tv).strip().lower() == parent_str:
                            is_triggered = True
                            break
                        if isinstance(parent_answer, list) and str(tv).strip().lower() in [str(x).strip().lower() for x in parent_answer]:
                            is_triggered = True
                            break

                if is_triggered:
                    visible_questions.append(QuestionResponse.model_validate(q))

        return DomainQuestionsResponse(
            domain_code=domain_code,
            domain_index=domain_index,
            total_domains=11,
            domain_title_en=domain_meta["title_en"],
            domain_title_ar=domain_meta["title_ar"],
            questions=visible_questions,
            saved_answers=saved_dict
        )

    @classmethod
    def save_domain_responses(
        cls, db: Session, assessment_id: str, data: SaveDomainResponsesRequest
    ) -> SaveDomainResponsesResponse:
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        if assessment.status == AssessmentStatus.LOCKED:
            raise HTTPException(status_code=400, detail="Assessment is submitted and locked. Cannot modify answers.")

        urgent_alerts = []

        # Upsert answers
        for ans in data.answers:
            q = db.query(Question).filter(
                Question.id == ans.question_id,
                Question.version_id == assessment.questionnaire_version_id
            ).first()
            if not q:
                continue

            # Deterministic Urgent Red-Flag Check: Immediate safety alert
            if q.is_urgent_red_flag and (ans.answer_value == True or str(ans.answer_value).lower() in ["yes", "true", "urgent"]):
                urgent_alerts.append(q.question_key)

            resp_row = db.query(AssessmentResponse).filter(
                AssessmentResponse.assessment_id == assessment_id,
                AssessmentResponse.question_id == ans.question_id
            ).first()

            if not resp_row:
                resp_row = AssessmentResponse(
                    assessment_id=assessment_id,
                    question_id=ans.question_id,
                    question_key=ans.question_key,
                    answer_value=ans.answer_value,
                    is_unsure=ans.is_unsure,
                    is_prefer_not_to_say=ans.is_prefer_not_to_say,
                    response_timestamp=datetime.now(timezone.utc)
                )
                db.add(resp_row)
            else:
                resp_row.answer_value = ans.answer_value
                resp_row.is_unsure = ans.is_unsure
                resp_row.is_prefer_not_to_say = ans.is_prefer_not_to_say
                resp_row.response_timestamp = datetime.now(timezone.utc)

        # Update assessment navigation state
        if data.next_domain_index is not None and data.next_domain_index <= 11:
            assessment.current_domain_index = data.next_domain_index
            if data.next_domain_index >= 11:
                assessment.status = AssessmentStatus.REVIEW_READY

        assessment.last_saved_at = datetime.now(timezone.utc)
        db.commit()

        # Compute progress percentage (based on completed domains)
        progress = min(100.0, round((assessment.current_domain_index / 11) * 100.0, 1))

        return SaveDomainResponsesResponse(
            assessment_id=assessment.id,
            saved_count=len(data.answers),
            current_domain_index=assessment.current_domain_index,
            progress_percentage=progress,
            urgent_red_flags_detected=urgent_alerts
        )

    @classmethod
    def get_assessment_review(cls, db: Session, assessment_id: str) -> AssessmentReviewResponse:
        assessment = db.query(Assessment).options(
            joinedload(Assessment.questionnaire_version),
            joinedload(Assessment.responses)
        ).filter(Assessment.id == assessment_id).first()

        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        # Fetch all questions in pinned version
        all_questions = db.query(Question).filter(
            Question.version_id == assessment.questionnaire_version_id
        ).order_by(Question.display_order).all()

        saved_by_key = {r.question_key: r for r in assessment.responses}
        domain_groups = []
        total_questions = 0
        answered_count = 0
        unanswered_required = 0
        urgent_flags = []

        for d_meta in DOMAINS_METADATA:
            d_code = d_meta["code"]
            d_questions = [q for q in all_questions if q.domain_code == d_code]
            q_items = []
            domain_is_complete = True

            for q in d_questions:
                resp = saved_by_key.get(q.question_key)
                is_answered = resp is not None and (resp.answer_value is not None or resp.is_unsure or resp.is_prefer_not_to_say)

                # Skip questions whose conditional parent wasn't satisfied
                if q.conditional_parent_key:
                    parent_resp = saved_by_key.get(q.conditional_parent_key)
                    parent_val = parent_resp.answer_value if parent_resp else None
                    triggers = q.conditional_trigger_values or []
                    if parent_val is None or str(parent_val).lower() not in [str(t).lower() for t in triggers]:
                        continue # Don't require or display inactive conditional branch

                total_questions += 1
                if is_answered:
                    answered_count += 1
                elif q.is_required:
                    unanswered_required += 1
                    domain_is_complete = False

                if q.is_urgent_red_flag and resp and (resp.answer_value == True or str(resp.answer_value).lower() in ["yes", "true"]):
                    urgent_flags.append(q.question_key)

                q_items.append(ReviewQuestionAnswerItem(
                    question_id=q.id,
                    question_key=q.question_key,
                    domain_code=q.domain_code,
                    text_en=q.text_en,
                    text_ar=q.text_ar,
                    question_type=q.question_type,
                    answer_value=resp.answer_value if resp else None,
                    is_unsure=resp.is_unsure if resp else False,
                    is_prefer_not_to_say=resp.is_prefer_not_to_say if resp else False,
                    is_answered=is_answered,
                    is_required=q.is_required,
                    is_urgent_red_flag=q.is_urgent_red_flag,
                    options=[
                        {"key": opt.get("key"), "label_en": opt.get("label_en"), "label_ar": opt.get("label_ar"), "order": opt.get("order", 0)}
                        for opt in (q.options_json or [])
                    ]
                ))

            domain_groups.append(ReviewDomainGroup(
                domain_code=d_code,
                domain_index=d_meta["index"],
                domain_title_en=d_meta["title_en"],
                domain_title_ar=d_meta["title_ar"],
                questions=q_items,
                is_complete=domain_is_complete
            ))

        progress = min(100.0, round((answered_count / max(1, total_questions)) * 100.0, 1))

        return AssessmentReviewResponse(
            assessment_id=assessment.id,
            status=assessment.status,
            version_tag=assessment.questionnaire_version.version_tag,
            current_domain_index=assessment.current_domain_index,
            progress_percentage=progress,
            total_questions=total_questions,
            answered_count=answered_count,
            unanswered_required_count=unanswered_required,
            can_submit=unanswered_required == 0,
            domains=domain_groups,
            urgent_red_flags=urgent_flags
        )

    @classmethod
    def submit_assessment(cls, db: Session, assessment_id: str) -> AssessmentSubmitResponse:
        assessment = db.query(Assessment).options(
            joinedload(Assessment.questionnaire_version),
            joinedload(Assessment.responses)
        ).filter(Assessment.id == assessment_id).first()

        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        if assessment.status == AssessmentStatus.LOCKED:
            raise HTTPException(status_code=400, detail="Assessment is already finalized and locked")

        # Check for urgent red-flags deterministically
        urgent_flag_questions = db.query(Question).filter(
            Question.version_id == assessment.questionnaire_version_id,
            Question.is_urgent_red_flag == True
        ).all()
        urgent_keys = {q.question_key for q in urgent_flag_questions}

        has_urgent = False
        for r in assessment.responses:
            if r.question_key in urgent_keys and (r.answer_value == True or str(r.answer_value).lower() in ["yes", "true"]):
                has_urgent = True
                break

        assessment.status = AssessmentStatus.LOCKED
        assessment.submitted_at = datetime.now(timezone.utc)
        db.commit()

        urgent_warning_en = "URGENT CLINICAL ALERT: You reported acute testicular symptoms (e.g. severe sudden pain, acute swelling, or rapid mass). Immediate emergency in-person medical evaluation by a urologist is advised." if has_urgent else None
        urgent_warning_ar = "تنبيه سريري عاجل: لقد ذكرت أعراضاً خصوية حادة (مثل ألم مفاجئ شديد أو تورم حاد). يوصى بالتوجه الفوري للطوارئ أو استشاري المسالك البولية." if has_urgent else None

        return AssessmentSubmitResponse(
            assessment_id=assessment.id,
            status=assessment.status,
            submitted_at=assessment.submitted_at,
            version_tag=assessment.questionnaire_version.version_tag,
            has_urgent_red_flags=has_urgent,
            urgent_warning_en=urgent_warning_en,
            urgent_warning_ar=urgent_warning_ar,
            message_en="Assessment successfully submitted and locked. Ready for deterministic clinical risk evaluation.",
            message_ar="تم إرسال الاستبيان وتأمينه بنجاح. جاهز للتقييم السريري المحدد لعوامل الخطورة."
        )
