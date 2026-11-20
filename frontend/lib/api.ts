/**
 * GENOVEX API Client
 * Interfaces with the FastAPI 0.115+ backend endpoints.
 * Includes token injection, guest session storage, and deterministic response typing.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

let storedCsrfToken: string | null = null;

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: "PATIENT" | "CLINICIAN" | "ADMIN" | "SUPERADMIN";
  credentials_summary?: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  email: string;
  full_name: string;
  role: "PATIENT" | "CLINICIAN" | "ADMIN" | "SUPERADMIN";
  credentials_summary?: string;
}

export interface QuestionOption {
  value: string;
  label_en: string;
  label_ar: string;
  is_red_flag?: boolean;
}

export interface Question {
  id: number;
  question_code: string;
  question_key?: string;
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

export interface AssessmentStartResponse {
  assessment_id: string;
  session_token: string;
  csrf_token?: string;
  version_number: string;
  status: string;
  current_domain_index: number;
  total_domains: number;
}

export interface DomainQuestionsResponse {
  assessment_id: string;
  domain_name: string;
  domain_index: number;
  total_domains: number;
  questions: Question[];
  saved_responses: Record<string, any>;
  has_urgent_red_flag: boolean;
}

export interface ReviewQuestionItem {
  question_id: number;
  question_key: string;
  question_code: string;
  text_en: string;
  text_ar: string;
  answer_value?: any;
  is_unsure: boolean;
  is_prefer_not_to_say: boolean;
  conditional_pathway_active: boolean;
  needs_reconfirmation: boolean;
  is_answered: boolean;
  is_required: boolean;
  is_urgent_red_flag: boolean;
  domain_code: string;
}

export interface ReviewDomainGroup {
  domain_code: string;
  domain_index: number;
  domain_title_en: string;
  domain_title_ar: string;
  is_complete: boolean;
  questions: ReviewQuestionItem[];
}

export interface AssessmentReviewResponse {
  assessment_id: string;
  status: string;
  version_tag: string;
  current_domain_index: number;
  progress_percentage: number;
  total_questions: number;
  answered_count: number;
  unanswered_required_count: number;
  can_submit: boolean;
  domains: ReviewDomainGroup[];
  urgent_red_flags: string[];
}

export interface AssessmentReport {
  id: number;
  report_reference?: string;
  assessment_id: string | number;
  session_token?: string;
  evaluation_completeness?: "DETERMINATE" | "INDETERMINATE";
  is_evaluation_incomplete?: boolean;
  is_amber_warning?: boolean;
  outcome_title_en?: string;
  outcome_title_ar?: string;
  overall_tier: "ROUTINE_PREVENTIVE_CARE" | "LIFESTYLE_MODIFIABLE_FACTORS" | "SPECIALIST_EVALUATION_RECOMMENDED" | "URGENT_MEDICAL_ASSESSMENT";
  has_urgent_flags: boolean;
  urgent_guidance?: string;
  identified_risk_factors: Array<{
    rule_code: string;
    rule_name: string;
    priority: number;
    tier: string;
    referral_guidance: string;
    evidence_source: string;
  }>;
  evidence_citations: Array<{
    guideline: string;
    year: number;
    section: string;
    recommendation: string;
  }>;
  non_diagnostic_summary_en: string;
  non_diagnostic_summary_ar: string;
  created_at: string;
}

// AI Integration Interfaces (Phase 9)
export interface AIMetadata {
  provider: string;
  model: string;
  prompt_version: string;
  request_id: string;
  timestamp: string;
  is_educational: boolean;
  disclaimer: string;
}

export interface HealthEducationResponse {
  topic: string;
  title: string;
  explanation: string;
  key_points: string[];
  guideline_sources: string[];
  metadata: AIMetadata;
}

export interface TerminologyExplanationResponse {
  term: string;
  plain_language_definition: string;
  clinical_context: string;
  common_misconceptions?: string;
  metadata: AIMetadata;
}

export interface ResultExplanationResponse {
  report_reference: string;
  outcome_tier: string;
  plain_language_summary: string;
  identified_factors_explained: Array<{ factor: string; explanation: string }>;
  next_steps_explained: string[];
  non_diagnostic_notice: string;
  metadata: AIMetadata;
}

export interface PreparationQuestionsResponse {
  report_reference: string;
  questions_for_clinician: string[];
  suggested_specialties: string[];
  recommended_documents_to_bring: string[];
  metadata: AIMetadata;
}

// Clinician Portal Interfaces (Phase 10)
export interface ClinicianAssessmentQueueItem {
  assessment_id: string;
  patient_reference: string;
  status: string;
  outcome_tier?: string;
  is_urgent_red_flag: boolean;
  review_workflow_status: "PENDING_REVIEW" | "IN_REVIEW" | "REVIEW_COMPLETED" | "FURTHER_INFO_REQUIRED";
  submitted_at?: string;
  last_activity_at: string;
}

export interface ClinicianDashboardSummary {
  clinician_id: number;
  clinician_name: string;
  credentials_summary?: string;
  assigned_assessments_count: number;
  pending_review_count: number;
  in_review_count: number;
  review_completed_count: number;
  assessments_queue: ClinicianAssessmentQueueItem[];
}

export interface ClinicianAssessmentDetail {
  assessment_id: string;
  patient_reference: string;
  status: string;
  questionnaire_version_tag: string;
  current_review_status: string;
  submitted_at?: string;
  responses: Array<{
    question_key: string;
    domain_code: string;
    prompt_en: string;
    prompt_ar: string;
    answer_value?: any;
    is_unsure: boolean;
    is_prefer_not_to_say: boolean;
    conditional_pathway_active: boolean;
    needs_reconfirmation: boolean;
    is_urgent_red_flag: boolean;
  }>;
  deterministic_report?: any;
  review_history: Array<{
    action: string;
    user_id?: number;
    details?: any;
    timestamp: string;
  }>;
  has_unapproved_rules: boolean;
  is_evaluation_incomplete: boolean;
}

export interface ClinicianNoteItem {
  note_id: number;
  author_name: string;
  author_role: string;
  note_text: string;
  created_at: string;
}

export interface ClinicianAISummaryResponse {
  assessment_id: string;
  patient_reference: string;
  clinical_triage_tier: string;
  is_urgent_red_flag: boolean;
  response_overview: {
    total_answered: number;
    unsure_count: number;
    prefer_not_to_say_count: number;
    active_responses_count?: number;
  };
  synthesized_risk_narrative: string;
  suggested_diagnostic_workup: string[];
  is_ai_generated: boolean;
  metadata: AIMetadata;
}

export class ApiClient {
  static setCsrfToken(token: string | null) {
    storedCsrfToken = token;
    if (typeof sessionStorage !== "undefined" && token) {
      sessionStorage.setItem("genovex_csrf", token);
    }
  }

  private static getHeaders(): HeadersInit {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("genovex_token");
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      const csrf = storedCsrfToken || (typeof sessionStorage !== "undefined" ? sessionStorage.getItem("genovex_csrf") : null);
      if (csrf) {
        headers["X-CSRF-Token"] = csrf;
      }
    }
    return headers;
  }

  // Auth Endpoints
  static async login(email: string, password: string): Promise<AuthResponse> {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Invalid email or password");
    }
    return res.json();
  }

  static async register(data: { email: string; password: string; full_name: string }): Promise<User> {
    const res = await fetch(`${API_BASE_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Registration failed");
    }
    return res.json();
  }

  static async getCurrentUser(): Promise<User> {
    const res = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) throw new Error("Failed to load user profile");
    return res.json();
  }

  // Health Library
  static async getCategories(): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/content/categories`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) return [];
    return res.json();
  }

  static async getConditions(search?: string): Promise<any[]> {
    const url = search 
      ? `${API_BASE_URL}/content/conditions?search=${encodeURIComponent(search)}`
      : `${API_BASE_URL}/content/conditions`;
    const res = await fetch(url, { headers: this.getHeaders(), credentials: "include" });
    if (!res.ok) return [];
    return res.json();
  }

  // Adaptive Questionnaire
  static async startAssessment(sessionToken?: string): Promise<AssessmentStartResponse> {
    const res = await fetch(`${API_BASE_URL}/questionnaire/assessments/start`, {
      method: "POST",
      headers: this.getHeaders(),
      credentials: "include",
      body: JSON.stringify({ session_token: sessionToken || null }),
    });
    if (!res.ok) throw new Error("Could not initialize assessment");
    const data: AssessmentStartResponse = await res.json();
    if (data.csrf_token) {
      this.setCsrfToken(data.csrf_token);
    }
    return data;
  }

  static async getDomainQuestions(assessmentId: string, domainIndex: number): Promise<DomainQuestionsResponse> {
    const res = await fetch(
      `${API_BASE_URL}/questionnaire/assessments/${assessmentId}/domain/${domainIndex}`,
      { headers: this.getHeaders(), credentials: "include" }
    );
    if (!res.ok) throw new Error("Failed to load domain questions");
    return res.json();
  }

  static async saveDomainResponses(
    assessmentId: string,
    domainIndex: number,
    responses: Record<string, any>,
    clientLastSavedAt?: string
  ): Promise<any> {
    const res = await fetch(
      `${API_BASE_URL}/questionnaire/assessments/${assessmentId}/save-domain`,
      {
        method: "POST",
        headers: this.getHeaders(),
        credentials: "include",
        body: JSON.stringify({
          domain_index: domainIndex,
          responses,
          client_last_saved_at: clientLastSavedAt || null
        }),
      }
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to save responses");
    }
    return res.json();
  }

  static async getAssessmentReview(assessmentId: string): Promise<AssessmentReviewResponse> {
    const res = await fetch(
      `${API_BASE_URL}/questionnaire/assessments/${assessmentId}/review`,
      {
        headers: this.getHeaders(),
        credentials: "include",
      }
    );
    if (!res.ok) throw new Error("Failed to load assessment review");
    return res.json();
  }

  static async submitAssessment(assessmentId: string): Promise<any> {
    const res = await fetch(
      `${API_BASE_URL}/questionnaire/assessments/${assessmentId}/submit`,
      {
        method: "POST",
        headers: this.getHeaders(),
        credentials: "include",
      }
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to submit assessment");
    }
    return res.json();
  }

  // Assessment Report
  static async evaluateAssessment(idOrToken: string): Promise<AssessmentReport> {
    let res = await fetch(
      `${API_BASE_URL}/questionnaire/assessments/${idOrToken}/evaluate`,
      {
        method: "POST",
        headers: this.getHeaders(),
        credentials: "include",
      }
    );
    if (!res.ok && res.status !== 422 && res.status !== 403 && res.status !== 409) {
      res = await fetch(
        `${API_BASE_URL}/assessment/${idOrToken}/evaluate`,
        {
          method: "POST",
          headers: this.getHeaders(),
          credentials: "include",
        }
      );
    }
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      const detail = errData.detail;
      const err = new Error(typeof detail === "object" ? detail.message : (detail || "Failed to evaluate assessment"));
      (err as any).code = typeof detail === "object" ? detail.code : "PROCESSING_ERROR";
      (err as any).status = res.status;
      (err as any).detail = detail;
      throw err;
    }
    return res.json();
  }

  static async getReport(idOrToken: string): Promise<AssessmentReport> {
    let res = await fetch(
      `${API_BASE_URL}/questionnaire/assessments/${idOrToken}/report`,
      { headers: this.getHeaders(), credentials: "include" }
    );
    if (!res.ok && res.status !== 422 && res.status !== 403) {
      res = await fetch(
        `${API_BASE_URL}/assessment/${idOrToken}/report`,
        { headers: this.getHeaders(), credentials: "include" }
      );
    }
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      const detail = errData.detail;
      const err = new Error(typeof detail === "object" ? detail.message : (detail || "Report not found"));
      (err as any).code = typeof detail === "object" ? detail.code : "REPORT_ERROR";
      (err as any).status = res.status;
      (err as any).detail = detail;
      throw err;
    }
    return res.json();
  }

  // Clinical Rules & Admin
  static async getClinicalRules(): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/rules/`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) return [];
    return res.json();
  }

  static async approveRule(ruleId: number): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/rules/${ruleId}/approve`, {
      method: "POST",
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) throw new Error("Failed to approve rule");
    return res.json();
  }

  static async getAuditLogs(limit = 100): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/admin/audit-logs?limit=${limit}`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) return [];
    return res.json();
  }

  // Phase 9: AI Educational & Decision Support
  static async explainHealthTopic(topic: string, context?: string, language = "en"): Promise<HealthEducationResponse> {
    const res = await fetch(`${API_BASE_URL}/ai/explain-topic`, {
      method: "POST",
      headers: this.getHeaders(),
      credentials: "include",
      body: JSON.stringify({ topic, context, language }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.message || err.detail || "Failed to generate health topic explanation");
    }
    return res.json();
  }

  static async explainTerminology(term: string, language = "en"): Promise<TerminologyExplanationResponse> {
    const res = await fetch(`${API_BASE_URL}/ai/explain-terminology`, {
      method: "POST",
      headers: this.getHeaders(),
      credentials: "include",
      body: JSON.stringify({ term, language }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.message || err.detail || "Failed to explain terminology");
    }
    return res.json();
  }

  static async explainAssessmentResult(reportReference: string, sessionToken?: string, language = "en"): Promise<ResultExplanationResponse> {
    const res = await fetch(`${API_BASE_URL}/ai/explain-result`, {
      method: "POST",
      headers: this.getHeaders(),
      credentials: "include",
      body: JSON.stringify({ report_reference: reportReference, session_token: sessionToken, language }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.message || err.detail || "Failed to explain assessment result");
    }
    return res.json();
  }

  static async getPreparationQuestions(reportReference: string, sessionToken?: string, language = "en"): Promise<PreparationQuestionsResponse> {
    const res = await fetch(`${API_BASE_URL}/ai/preparation-questions`, {
      method: "POST",
      headers: this.getHeaders(),
      credentials: "include",
      body: JSON.stringify({ report_reference: reportReference, session_token: sessionToken, language }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.message || err.detail || "Failed to generate doctor preparation questions");
    }
    return res.json();
  }

  // Phase 10: Clinician Decision Support Portal
  static async getClinicianDashboard(): Promise<ClinicianDashboardSummary> {
    const res = await fetch(`${API_BASE_URL}/clinician/dashboard`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to retrieve clinician dashboard");
    }
    return res.json();
  }

  static async getClinicianAssessmentReview(assessmentId: string): Promise<ClinicianAssessmentDetail> {
    const res = await fetch(`${API_BASE_URL}/clinician/assessments/${assessmentId}/review`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to retrieve assessment for review");
    }
    return res.json();
  }

  static async updateClinicianReviewStatus(assessmentId: string, reviewStatus: string, notes?: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/clinician/assessments/${assessmentId}/review-status`, {
      method: "POST",
      headers: this.getHeaders(),
      credentials: "include",
      body: JSON.stringify({ review_status: reviewStatus, notes }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to update review workflow status");
    }
    return res.json();
  }

  static async addClinicianNote(assessmentId: string, noteText: string): Promise<ClinicianNoteItem> {
    const res = await fetch(`${API_BASE_URL}/clinician/assessments/${assessmentId}/notes`, {
      method: "POST",
      headers: this.getHeaders(),
      credentials: "include",
      body: JSON.stringify({ note_text: noteText }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to record clinician note");
    }
    return res.json();
  }

  static async getClinicianNotes(assessmentId: string): Promise<ClinicianNoteItem[]> {
    const res = await fetch(`${API_BASE_URL}/clinician/assessments/${assessmentId}/notes`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) return [];
    return res.json();
  }

  static async getClinicianAISummary(assessmentId: string, focusAreas?: string[]): Promise<ClinicianAISummaryResponse> {
    const res = await fetch(`${API_BASE_URL}/clinician/assessments/${assessmentId}/ai-summary`, {
      method: "POST",
      headers: this.getHeaders(),
      credentials: "include",
      body: JSON.stringify({ focus_areas: focusAreas || [] }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.message || err.detail || "Failed to generate AI clinician summary");
    }
    return res.json();
  }
}
