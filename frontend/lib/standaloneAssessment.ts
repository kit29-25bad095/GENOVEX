import questionsData from "@/data/questionnaire.json";

export interface QuestionOption {
  value: string;
  label_en: string;
  label_ar: string;
  is_red_flag?: boolean;
}

export interface Question {
  id: number;
  question_code: string;
  question_key: string;
  domain: string;
  domain_index: number;
  question_text_en: string;
  question_text_ar: string;
  help_text_en?: string;
  help_text_ar?: string;
  question_type: "SINGLE_CHOICE" | "MULTIPLE_CHOICE" | "NUMERIC" | "BOOLEAN";
  is_required: boolean;
  options: QuestionOption[];
  conditional_parent_code?: string;
  conditional_parent_key?: string;
  conditional_parent_value?: string;
  conditional_trigger_values?: any[];
  needs_reconfirmation?: boolean;
}

export const DOMAINS_METADATA = [
  { code: "BASIC_HEALTH", index: 0, title_en: "Basic Health Information", title_ar: "المعلومات الصحية الأساسية" },
  { code: "REPRODUCTIVE_HISTORY", index: 1, title_en: "Reproductive History", title_ar: "التاريخ الإنجابي" },
  { code: "TESTICULAR_HISTORY", index: 2, title_en: "Testicular History", title_ar: "التاريخ الخصوي والجراحي" },
  { code: "MEDICAL_HISTORY", index: 3, title_en: "Medical History", title_ar: "التاريخ الطبي العام" },
  { code: "HORMONAL_HEALTH", index: 4, title_en: "Hormonal Health", title_ar: "الصحة الهرمونية والغدد الصماء" },
  { code: "METABOLIC_HEALTH", index: 5, title_en: "Metabolic Health", title_ar: "الصحة الأيضية ونمط الغذاء" },
  { code: "LIFESTYLE_HABITS", index: 6, title_en: "Lifestyle & Habits", title_ar: "العادات ونمط الحياة" },
  { code: "MEDICATION_SUBSTANCE", index: 7, title_en: "Medication & Substance History", title_ar: "الأدوية والمستحضرات الهرمونية" },
  { code: "OCCUPATIONAL_EXPOSURE", index: 8, title_en: "Occupational & Environmental Exposure", title_ar: "التعرض المهني والبيئي" },
  { code: "SEXUAL_EJACULATORY", index: 9, title_en: "Sexual & Ejaculatory Health", title_ar: "الصحة الجنسية والقذف" },
  { code: "FAMILY_GENETIC", index: 10, title_en: "Family & Genetic History", title_ar: "التاريخ العائلي والجيني" },
];

interface AssessmentSession {
  assessment_id: string;
  session_token: string;
  csrf_token: string;
  status: string;
  current_domain_index: number;
  answers: Record<string, any>;
  has_urgent_red_flag: boolean;
  created_at: string;
}

// In-memory store for serverless execution
const assessmentSessions = new Map<string, AssessmentSession>();

function generateId(prefix: string): string {
  const hex = Math.random().toString(16).substring(2, 10);
  const time = Date.now().toString(16);
  return `${prefix}_${hex}${time}`;
}

export function startOrResumeAssessment(sessionToken?: string | null): {
  assessment_id: string;
  session_token: string;
  csrf_token: string;
  version_number: string;
  status: string;
  current_domain_index: number;
  total_domains: number;
  domains_meta: typeof DOMAINS_METADATA;
} {
  // Check for existing session
  if (sessionToken) {
    const sessions = Array.from(assessmentSessions.values());
    for (const session of sessions) {
      if (session.session_token === sessionToken) {
        return {
          assessment_id: session.assessment_id,
          session_token: session.session_token,
          csrf_token: session.csrf_token,
          version_number: "v1.0.0",
          status: session.status,
          current_domain_index: session.current_domain_index,
          total_domains: DOMAINS_METADATA.length,
          domains_meta: DOMAINS_METADATA,
        };
      }
    }
  }

  const assessment_id = generateId("asmt");
  const token = sessionToken || generateId("sess");
  const csrf_token = generateId("csrf");

  const session: AssessmentSession = {
    assessment_id,
    session_token: token,
    csrf_token,
    status: "IN_PROGRESS",
    current_domain_index: 0,
    answers: {},
    has_urgent_red_flag: false,
    created_at: new Date().toISOString(),
  };

  assessmentSessions.set(assessment_id, session);

  return {
    assessment_id,
    session_token: token,
    csrf_token,
    version_number: "v1.0.0",
    status: "IN_PROGRESS",
    current_domain_index: 0,
    total_domains: DOMAINS_METADATA.length,
    domains_meta: DOMAINS_METADATA,
  };
}

export function getDomainQuestions(assessmentId: string, domainIndex: number) {
  const safeIndex = Math.max(0, Math.min(domainIndex, DOMAINS_METADATA.length - 1));
  const domainMeta = DOMAINS_METADATA[safeIndex];
  const session = assessmentSessions.get(assessmentId);
  const savedAnswers = session?.answers || {};

  const domainQuestionsRaw = (questionsData as any[]).filter(
    (q) => q.domain_code === domainMeta.code
  );

  const questions: Question[] = domainQuestionsRaw.map((q, idx) => ({
    id: idx + 1,
    question_code: q.question_key,
    question_key: q.question_key,
    domain: q.domain_code,
    domain_index: safeIndex,
    question_text_en: q.text_en,
    question_text_ar: q.text_ar,
    help_text_en: q.help_text_en || undefined,
    help_text_ar: q.help_text_ar || undefined,
    question_type: q.question_type,
    is_required: q.is_required !== false,
    options: (q.options_json || []).map((opt: any) => ({
      value: opt.key || opt.value,
      label_en: opt.label_en,
      label_ar: opt.label_ar,
      is_red_flag: opt.is_red_flag || false,
    })),
    conditional_parent_code: q.conditional_parent_key || undefined,
    conditional_parent_key: q.conditional_parent_key || undefined,
    conditional_trigger_values: q.conditional_trigger_values || undefined,
  }));

  const saved_responses: Record<string, any> = {};
  for (const q of questions) {
    const val = savedAnswers[q.question_key];
    saved_responses[q.question_key] = {
      answer_value: val !== undefined ? val : null,
      is_unsure: val === "not_sure",
      is_prefer_not_to_say: val === "prefer_not_to_say",
      conditional_pathway_active: true,
      needs_reconfirmation: false,
    };
  }

  return {
    assessment_id: assessmentId,
    domain_name: domainMeta.title_en,
    domain_index: safeIndex,
    total_domains: DOMAINS_METADATA.length,
    questions,
    saved_responses,
    has_urgent_red_flag: session?.has_urgent_red_flag || false,
  };
}

export function saveDomainResponses(
  assessmentId: string,
  domainIndex: number,
  responses: Record<string, any>
) {
  let session = assessmentSessions.get(assessmentId);
  if (!session) {
    session = {
      assessment_id: assessmentId,
      session_token: generateId("sess"),
      csrf_token: generateId("csrf"),
      status: "IN_PROGRESS",
      current_domain_index: domainIndex,
      answers: {},
      has_urgent_red_flag: false,
      created_at: new Date().toISOString(),
    };
    assessmentSessions.set(assessmentId, session);
  }

  // Merge responses
  Object.assign(session.answers, responses);

  // Check red flags
  if (
    responses["Q_ACUTE_SCROTAL_PAIN"] === "yes_severe" ||
    responses["Q_PAINLESS_TESTIS_LUMP"] === "yes_confirmed"
  ) {
    session.has_urgent_red_flag = true;
  }

  const nextIndex = Math.min(domainIndex + 1, DOMAINS_METADATA.length - 1);
  session.current_domain_index = nextIndex;

  return {
    assessment_id: assessmentId,
    domain_index: domainIndex,
    saved_count: Object.keys(responses).length,
    next_domain_index: nextIndex,
    has_urgent_red_flag: session.has_urgent_red_flag,
  };
}

export function getAssessmentReview(assessmentId: string) {
  const session = assessmentSessions.get(assessmentId);
  const answers = session?.answers || {};

  const allQuestions = questionsData as any[];
  let unansweredRequiredCount = 0;

  const domains = DOMAINS_METADATA.map((dom) => {
    const domQuestions = allQuestions.filter((q) => q.domain_code === dom.code);
    const mappedQuestions = domQuestions.map((q) => {
      const ans = answers[q.question_key];
      const isAnswered = ans !== undefined && ans !== null && ans !== "";
      if (q.is_required && !isAnswered) {
        unansweredRequiredCount++;
      }
      return {
        question_id: 1,
        question_key: q.question_key,
        question_code: q.question_key,
        text_en: q.text_en,
        text_ar: q.text_ar,
        is_required: q.is_required !== false,
        is_answered: isAnswered,
        user_answer: ans,
        answer_display_en: String(ans || "Unanswered"),
        answer_display_ar: String(ans || "غير مجاب"),
        is_unsure: ans === "not_sure",
        is_prefer_not_to_say: ans === "prefer_not_to_say",
        needs_reconfirmation: false,
      };
    });

    const isComplete = mappedQuestions.every((q) => !q.is_required || q.is_answered);

    return {
      domain_code: dom.code,
      domain_index: dom.index,
      domain_title_en: dom.title_en,
      domain_title_ar: dom.title_ar,
      is_complete: isComplete,
      questions: mappedQuestions,
    };
  });

  return {
    assessment_id: assessmentId,
    status: session?.status || "IN_PROGRESS",
    can_submit: unansweredRequiredCount === 0,
    unanswered_required_count: unansweredRequiredCount,
    has_urgent_red_flag: session?.has_urgent_red_flag || false,
    domains,
  };
}

export function submitAssessment(assessmentId: string) {
  let session = assessmentSessions.get(assessmentId);
  if (!session) {
    session = {
      assessment_id: assessmentId,
      session_token: generateId("sess"),
      csrf_token: generateId("csrf"),
      status: "COMPLETED",
      current_domain_index: 10,
      answers: {},
      has_urgent_red_flag: false,
      created_at: new Date().toISOString(),
    };
    assessmentSessions.set(assessmentId, session);
  }
  session.status = "COMPLETED";

  const ref = `GNX-${new Date().getFullYear()}-${Math.random().toString(36).substring(2, 8).toUpperCase()}`;

  let outcomeTier = "TIER_1_LOW_RISK";
  let titleEn = "Optimal Reproductive Health & Wellness Profile";
  let titleAr = "ملف صحي إنجابي متوازن وإرشادات عامة";

  if (session.has_urgent_red_flag) {
    outcomeTier = "TIER_4_URGENT";
    titleEn = "URGENT Medical Assessment Required";
    titleAr = "تقييم طبي عاجل مطلوب فورا";
  } else if (
    session.answers["Q_ATTEMPT_DURATION"] === "over_12m" ||
    session.answers["Q_ANABOLIC_STEROIDS"] === "current_use" ||
    session.answers["Q_HEMATOSPERMIA"] === "yes_visible"
  ) {
    outcomeTier = "TIER_3_SPECIALIST";
    titleEn = "Specialist Andrology Evaluation Recommended";
    titleAr = "يوصى بمراجعة استشاري طب الذكورة والعقم";
  } else if (
    session.answers["Q_TOBACCO_USE"] ||
    session.answers["Q_SCROTAL_HEAT"] ||
    session.answers["Q_BMI_CATEGORY"] === "obese"
  ) {
    outcomeTier = "TIER_2_MODIFIABLE";
    titleEn = "Modifiable Lifestyle & Environmental Risk Factors Identified";
    titleAr = "تم رصد عوامل خطر قابلة للتعديل في نمط الحياة";
  }

  return {
    assessment_id: assessmentId,
    status: "COMPLETED",
    submitted_at: new Date().toISOString(),
    report_reference: ref,
    outcome_tier: outcomeTier,
    outcome_title_en: titleEn,
    outcome_title_ar: titleAr,
    is_urgent_red_flag: session.has_urgent_red_flag,
    verification_hash: "sha256_" + Math.random().toString(36).substring(2, 14),
    pdf_available: true,
  };
}
