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

  // ==========================================
  // Admin Dashboard API Endpoints (Phase 11)
  // ==========================================
  static async getAdminOverview(): Promise<AdminOverviewResponse> {
    const res = await fetch(`${API_BASE_URL}/admin/overview`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to fetch admin overview");
    }
    return res.json();
  }

  static async getAdminUsers(params?: {
    search?: string;
    role?: string;
    is_active?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<AdminUserListResponse> {
    const q = new URLSearchParams();
    if (params?.search) q.append("search", params.search);
    if (params?.role) q.append("role", params.role);
    if (params?.is_active !== undefined) q.append("is_active", String(params.is_active));
    if (params?.page) q.append("page", String(params.page));
    if (params?.page_size) q.append("page_size", String(params.page_size));

    const res = await fetch(`${API_BASE_URL}/admin/users?${q.toString()}`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to fetch user list");
    }
    return res.json();
  }

  static async getAdminUserDetail(userId: number): Promise<AdminUserDetailResponse> {
    const res = await fetch(`${API_BASE_URL}/admin/users/${userId}`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to fetch user details");
    }
    return res.json();
  }

  static async updateAdminUserStatus(userId: number, isActive: boolean, reason?: string): Promise<AdminUserListItem> {
    const res = await fetch(`${API_BASE_URL}/admin/users/${userId}/status`, {
      method: "PATCH",
      headers: this.getHeaders(),
      credentials: "include",
      body: JSON.stringify({ is_active: isActive, reason }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to update user status");
    }
    return res.json();
  }

  static async updateAdminUserRole(userId: number, role: string, reason?: string): Promise<AdminUserListItem> {
    const res = await fetch(`${API_BASE_URL}/admin/users/${userId}/role`, {
      method: "PATCH",
      headers: this.getHeaders(),
      credentials: "include",
      body: JSON.stringify({ role, reason }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to update user role");
    }
    return res.json();
  }

  static async getAdminAssessmentStats(): Promise<AdminAssessmentStatsResponse> {
    const res = await fetch(`${API_BASE_URL}/admin/assessments/stats`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to fetch assessment statistics");
    }
    return res.json();
  }

  static async getAdminClinicianOperations(): Promise<AdminClinicianOperationsResponse> {
    const res = await fetch(`${API_BASE_URL}/admin/clinician-operations`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to fetch clinician operations data");
    }
    return res.json();
  }

  static async getAdminAuditEvents(params?: {
    action?: string;
    resource_type?: string;
    user_id?: number;
    page?: number;
    page_size?: number;
  }): Promise<AdminAuditEventListResponse> {
    const q = new URLSearchParams();
    if (params?.action) q.append("action", params.action);
    if (params?.resource_type) q.append("resource_type", params.resource_type);
    if (params?.user_id) q.append("user_id", String(params.user_id));
    if (params?.page) q.append("page", String(params.page));
    if (params?.page_size) q.append("page_size", String(params.page_size));

    const res = await fetch(`${API_BASE_URL}/admin/audit-events?${q.toString()}`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to fetch audit events");
    }
    return res.json();
  }

  static async getAdminHealth(): Promise<AdminHealthResponse> {
    const res = await fetch(`${API_BASE_URL}/admin/health`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to fetch platform health");
    }
    return res.json();
  }

  static async getAdminConfig(): Promise<AdminConfigResponse> {
    const res = await fetch(`${API_BASE_URL}/admin/config`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to fetch platform configuration");
    }
    return res.json();
  }

  static async updateAdminUser(userId: number, data: { role?: string; credentials_summary?: string; is_active?: boolean; full_name?: string }): Promise<User> {
    const res = await fetch(`${API_BASE_URL}/admin/users/${userId}`, {
      method: "PUT",
      headers: this.getHeaders(),
      credentials: "include",
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to update user profile");
    }
    return res.json();
  }



  // Clinical Rules Management
  static async getAdminRules(params?: { domain_code?: string; outcome_tier?: string; status?: string; is_urgent?: boolean }): Promise<any[]> {
    const query = new URLSearchParams();
    if (params?.domain_code) query.set("domain_code", params.domain_code);
    if (params?.outcome_tier) query.set("outcome_tier", params.outcome_tier);
    if (params?.status) query.set("status", params.status);
    if (params?.is_urgent !== undefined) query.set("is_urgent", String(params.is_urgent));
    const qs = query.toString() ? `?${query.toString()}` : "";
    const res = await fetch(`${API_BASE_URL}/admin/clinical-rules${qs}`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) return [];
    return res.json();
  }

  static async createAdminRule(data: any): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/admin/clinical-rules`, {
      method: "POST",
      headers: this.getHeaders(),
      credentials: "include",
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to create clinical rule");
    }
    return res.json();
  }

  static async updateAdminRule(ruleId: number, data: any): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/admin/clinical-rules/${ruleId}`, {
      method: "PUT",
      headers: this.getHeaders(),
      credentials: "include",
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to update clinical rule");
    }
    return res.json();
  }

  static async submitAdminRuleForReview(ruleId: number): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/admin/clinical-rules/${ruleId}/submit-review`, {
      method: "POST",
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to submit rule for clinical review");
    }
    return res.json();
  }

  static async reviewAdminRule(ruleId: number, action: "APPROVE" | "REJECT", notes?: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/admin/clinical-rules/${ruleId}/review`, {
      method: "POST",
      headers: this.getHeaders(),
      credentials: "include",
      body: JSON.stringify({ action, notes }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to complete clinician review action");
    }
    return res.json();
  }

  static async publishAdminRule(ruleId: number): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/admin/clinical-rules/${ruleId}/publish`, {
      method: "POST",
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to publish rule to production engine");
    }
    return res.json();
  }

  static async getAdminRuleVersions(ruleId: number): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/admin/clinical-rules/${ruleId}/versions`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) return [];
    return res.json();
  }

  // Medical Content CMS
  static async getAdminConditions(params?: { search?: string; category_id?: number; status?: string; skip?: number; limit?: number }): Promise<any[]> {
    const query = new URLSearchParams();
    if (params?.search) query.set("search", params.search);
    if (params?.category_id) query.set("category_id", String(params.category_id));
    if (params?.status) query.set("status", params.status);
    if (params?.skip) query.set("skip", String(params.skip));
    if (params?.limit) query.set("limit", String(params.limit));
    const qs = query.toString() ? `?${query.toString()}` : "";
    const res = await fetch(`${API_BASE_URL}/admin/medical-content/conditions${qs}`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) return [];
    return res.json();
  }

  static async getAdminConditionDetail(conditionId: number): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/admin/medical-content/conditions/${conditionId}`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) throw new Error("Failed to load medical condition details");
    return res.json();
  }

  static async createAdminCondition(data: any): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/admin/medical-content/conditions`, {
      method: "POST",
      headers: this.getHeaders(),
      credentials: "include",
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to create medical condition");
    }
    return res.json();
  }

  static async updateAdminCondition(conditionId: number, data: any): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/admin/medical-content/conditions/${conditionId}`, {
      method: "PUT",
      headers: this.getHeaders(),
      credentials: "include",
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to update medical condition");
    }
    return res.json();
  }

  static async reviewActionCondition(conditionId: number, action: string, notes?: string, reviewerName = "Clinical Reviewer", reviewerRole = "CLINICIAN"): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/admin/medical-content/conditions/${conditionId}/review-action`, {
      method: "POST",
      headers: this.getHeaders(),
      credentials: "include",
      body: JSON.stringify({ action, notes, reviewer_name: reviewerName, reviewer_role: reviewerRole }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to execute clinical review action on condition");
    }
    return res.json();
  }

  static async getConditionVersions(conditionId: number): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/admin/medical-content/conditions/${conditionId}/versions`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) return [];
    return res.json();
  }

  static async restoreConditionVersion(conditionId: number, versionNumber: number | string, reason: string, restoredBy = "Administrator"): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/admin/medical-content/conditions/${conditionId}/restore`, {
      method: "POST",
      headers: this.getHeaders(),
      credentials: "include",
      body: JSON.stringify({ version_number: Number(versionNumber), reason, restored_by: restoredBy }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to restore earlier condition version");
    }
    return res.json();
  }

  static async getAdminCategories(): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/admin/medical-content/categories`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) return [];
    return res.json();
  }

  // Questionnaire Version Governance
  static async getQuestionnaireVersions(): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/admin/questionnaire/versions`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) return [];
    return res.json();
  }

  static async getAssessmentsOverview(): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/admin/questionnaire/assessments-overview`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) return { total_assessments: 0, submitted_locked: 0, in_progress: 0, completion_rate: 0 };
    return res.json();
  }

  // Phase 18 Maintenance Telemetry & Backups
  static async getAdminDiagnostics(): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/admin/maintenance/diagnostics`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) return null;
    return res.json();
  }

  static async triggerManualBackup(): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/admin/maintenance/backup`, {
      method: "POST",
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to trigger database backup");
    }
    return res.json();
  }

  static async getBackupHistory(): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/admin/maintenance/backups`, {
      headers: this.getHeaders(),
      credentials: "include",
    });
    if (!res.ok) return [];
    return res.json();
  }

  private static async fetchWithAuth<T>(path: string, options?: RequestInit): Promise<T> {
    const url = `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
    const res = await fetch(url, {
      ...options,
      headers: {
        ...this.getHeaders(),
        ...(options?.headers || {}),
      },
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.message || err.detail || "API request failed");
    }
    return res.json();
  }


  // =========================================================================
  // Phase 12: Clinical Navigation & Provider Directory
  // =========================================================================
  static async getFacilities(params?: {
    specialty?: string;
    emirate?: string;
    facility_type?: string;
    has_emergency?: boolean;
    is_verified?: boolean;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<FacilityListResponse> {
    const query = new URLSearchParams();
    if (params?.specialty) query.set("specialty", params.specialty);
    if (params?.emirate) query.set("emirate", params.emirate);
    if (params?.facility_type) query.set("facility_type", params.facility_type);
    if (params?.has_emergency !== undefined) query.set("has_emergency", String(params.has_emergency));
    if (params?.is_verified !== undefined) query.set("is_verified", String(params.is_verified));
    if (params?.search) query.set("search", params.search);
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));

    const qs = query.toString();
    return this.fetchWithAuth<FacilityListResponse>(`/navigation/facilities${qs ? `?${qs}` : ""}`);
  }

  static async getFacilityDetail(identifier: string): Promise<FacilityItem> {
    return this.fetchWithAuth<FacilityItem>(`/navigation/facilities/${identifier}`);
  }

  static async getNavigationRecommendations(sessionTokenOrRef: string): Promise<NavigationRecommendationResponse> {
    return this.fetchWithAuth<NavigationRecommendationResponse>(`/navigation/recommendations/${sessionTokenOrRef}`);
  }

  // =========================================================================
  // Phase 13: Reports & Assessment History
  // =========================================================================
  static async getAssessmentHistory(limit = 50, offset = 0): Promise<AssessmentHistoryResponse> {
    return this.fetchWithAuth<AssessmentHistoryResponse>(`/assessment/history?limit=${limit}&offset=${offset}`);
  }

  static async claimAssessment(sessionToken: string): Promise<any> {
    return this.fetchWithAuth(`/assessment/${sessionToken}/claim`, {
      method: "POST",
    });
  }

  static getReportPdfDownloadUrl(sessionToken: string): string {
    return `${API_BASE_URL}/assessment/${sessionToken}/report/pdf`;
  }

  // =========================================================================
  // Phase 14 & 15: Security, Privacy & User Account APIs
  // =========================================================================
  static async updateProfile(data: { full_name?: string; credentials_summary?: string }): Promise<User> {
    return this.fetchWithAuth<User>("/auth/me", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  static async changePassword(data: { old_password: string; new_password: string }): Promise<any> {
    return this.fetchWithAuth("/auth/change-password", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  static async exportUserData(): Promise<any> {
    return this.fetchWithAuth("/auth/privacy/export-data");
  }

  static async deleteAccount(confirm = true): Promise<any> {
    return this.fetchWithAuth(`/auth/privacy/delete-account?confirm=${confirm}`, {
      method: "POST",
    });
  }

}

export interface AdminAuditLogItem {
  id: number;
  user_id?: number | null;
  user_email?: string | null;
  user_role?: string | null;
  action: string;
  resource_type: string;
  resource_id: string;
  details?: Record<string, any> | null;
  ip_address?: string | null;
  timestamp: string;
}

export interface AdminOverviewResponse {
  users_total: number;
  users_active: number;
  users_inactive: number;
  users_by_role: Record<string, number>;
  assessments_total: number;
  assessments_by_status: Record<string, number>;
  reports_total: number;
  reports_withheld_count: number;
  clinician_reviews_pending: number;
  clinician_reviews_in_progress: number;
  clinician_reviews_completed: number;
  recent_admin_activity: AdminAuditLogItem[];
  platform_health_status: string;
  clinical_governance_status: string;
  governance_warning: string;
}

export interface AdminUserListItem {
  id: number;
  email: string;
  full_name: string;
  role: "PATIENT" | "CLINICIAN" | "ADMIN" | "SUPERADMIN";
  credentials_summary?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AdminUserListResponse {
  items: AdminUserListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AdminUserDetailResponse {
  id: number;
  email: string;
  full_name: string;
  role: "PATIENT" | "CLINICIAN" | "ADMIN" | "SUPERADMIN";
  credentials_summary?: string | null;
  is_active: boolean;
  created_at: string;
  assessments_count: number;
  recent_audit_logs: AdminAuditLogItem[];
}

export interface AdminAssessmentStatsResponse {
  total_assessments: number;
  status_counts: Record<string, number>;
  reports_generated: number;
  incomplete_assessments: number;
  withheld_clinical_results: number;
  outcome_tier_counts: Record<string, number>;
  governance_withheld_percent: number;
}

export interface AdminClinicianOperationsResponse {
  registered_clinicians: number;
  active_clinicians: number;
  shared_review_pool: boolean;
  exclusive_locking_implemented: boolean;
  pending_reviews: number;
  in_review_count: number;
  completed_reviews: number;
  recent_reviews: Array<{
    id: number;
    action: string;
    actor_email: string;
    assessment_reference: string;
    status: string;
    timestamp: string;
  }>;
}

export interface AdminAuditEventListResponse {
  items: AdminAuditLogItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  storage_type: string;
  immutable_hardware_enforced: boolean;
}

export interface AdminHealthResponse {
  status: string;
  database: {
    connected: boolean;
    engine: string;
    read_only: boolean;
    sandbox_mode: boolean;
  };
  api_version: string;
  ai_provider_mode: string;
  ai_provider_configured: boolean;
  gemini_live_egress_active: boolean;
  clinical_governance_gate: string;
  timestamp: string;
}

export interface AdminConfigResponse {
  environment: string;
  project_name: string;
  api_v1_str: string;
  allowed_cors_origins: string[];
  rate_limit_per_minute: number;
  auth_jwt_algorithm: string;
  ai_provider_mode: string;
  shared_review_queue: boolean;
}


export interface FacilityItem {
  id: number;
  slug: string;
  name_en: string;
  name_ar: string;
  emirate: string;
  regulatory_authority: string;
  facility_type: string;
  address_en: string;
  address_ar: string;
  city_en: string;
  city_ar: string;
  phone_number: string;
  emergency_phone?: string;
  website_url?: string;
  booking_url?: string;
  has_24_7_emergency: boolean;
  has_andrology_specialist: boolean;
  has_who_semen_analysis_lab: boolean;
  has_micro_tese_capability: boolean;
  offered_specialties: string[];
  insurance_networks: string[];
  is_verified: boolean;
  is_active: boolean;
  notes_en?: string;
  notes_ar?: string;
  created_at?: string;
  updated_at?: string;
}

export interface FacilityListResponse {
  items: FacilityItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages?: number;
  emirates: string[];
  specialties: string[];
}

export interface NavigationRecommendationResponse {
  assessment_id?: string;
  report_reference?: string;
  outcome_tier?: string;
  is_urgent_red_flag: boolean;
  recommended_specialties: string[];
  recommended_facilities: FacilityItem[];
  emergency_facilities: FacilityItem[];
  is_formal_referral: boolean;
  navigation_notice_en: string;
  navigation_notice_ar: string;
}

export interface AssessmentHistoryItem {
  assessment_id: string;
  session_token: string;
  status: string;
  started_at?: string;
  submitted_at?: string;
  report_reference?: string;
  outcome_tier?: string;
  outcome_title_en?: string;
  outcome_title_ar?: string;
  is_urgent_red_flag: boolean;
  questionnaire_version_tag?: string;
  rule_engine_version?: string;
}

export interface AssessmentHistoryResponse {
  items: AssessmentHistoryItem[];
  total: number;
  limit?: number;
  offset?: number;
}
