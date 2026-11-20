import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AdaptiveAssessmentPage from "@/app/assessment/page";
import { LanguageProvider } from "@/context/LanguageContext";
import { AuthProvider } from "@/context/AuthContext";
import { ApiClient } from "@/lib/api";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

describe("Adaptive Questionnaire Engine & Safe Answers", () => {
  it("renders questionnaire wizard and handles safe answers", async () => {
    // Mock ApiClient responses
    vi.spyOn(ApiClient, "startAssessment").mockResolvedValue({
      assessment_id: "test-assessment-id-12345",
      session_token: "test-session-token-67890",
      version_number: "v1.0.0",
      status: "IN_PROGRESS",
      current_domain_index: 0,
      total_domains: 11,
    });

    vi.spyOn(ApiClient, "getDomainQuestions").mockResolvedValue({
      assessment_id: "test-assessment-id-12345",
      domain_name: "Baselines & Demographics",
      domain_index: 0,
      total_domains: 11,
      questions: [
        {
          id: 1,
          question_code: "Q_AGE",
          domain: "Baselines",
          domain_index: 0,
          question_text_en: "What is your current age in years?",
          question_text_ar: "ما هو عمرك الحالي بالسنوات؟",
          question_type: "NUMERIC",
          is_required: true,
          options: [],
        },
        {
          id: 2,
          question_code: "Q_ATTEMPT_DURATION",
          domain: "Reproductive Goals",
          domain_index: 0,
          question_text_en: "How long have you been actively attempting conception?",
          question_text_ar: "كم المدة التي تحاول فيها الإنجاب بنشاط؟",
          question_type: "SINGLE_CHOICE",
          is_required: true,
          options: [
            { value: "less_than_6m", label_en: "Less than 6 months", label_ar: "أقل من 6 أشهر" },
            { value: "12_to_24m", label_en: "12 to 24 months", label_ar: "من 12 إلى 24 شهراً" },
          ],
        },
      ],
      saved_responses: {},
      has_urgent_red_flag: false,
    });

    render(
      <LanguageProvider>
        <AuthProvider>
          <AdaptiveAssessmentPage />
        </AuthProvider>
      </LanguageProvider>
    );

    // Verify questions render
    await waitFor(() => {
      expect(screen.getByText(/What is your current age in years/i)).toBeDefined();
    });

    // Verify safe choice buttons exist
    const notSureButtons = screen.getAllByText("Not Sure");
    expect(notSureButtons.length).toBeGreaterThan(0);

    const preferNotToSayButtons = screen.getAllByText("Prefer Not to Say");
    expect(preferNotToSayButtons.length).toBeGreaterThan(0);

    // Clicking "Not Sure" records safe response without crashing
    fireEvent.click(notSureButtons[0]);
    expect(notSureButtons[0].className).toContain("font-semibold");
  });

  it("dynamically shows conditional follow-up question only when parent answer matches", async () => {
    vi.spyOn(ApiClient, "startAssessment").mockResolvedValue({
      assessment_id: "test-assessment-id-12345",
      session_token: "test-session-token-67890",
      version_number: "v1.0.0",
      status: "IN_PROGRESS",
      current_domain_index: 3,
      total_domains: 11,
    });

    vi.spyOn(ApiClient, "getDomainQuestions").mockResolvedValue({
      assessment_id: "test-assessment-id-12345",
      domain_name: "Surgical & Anatomic History",
      domain_index: 3,
      total_domains: 11,
      questions: [
        {
          id: 10,
          question_code: "Q_TESTIS_SURGERY_HISTORY",
          domain: "Surgical",
          domain_index: 3,
          question_text_en: "Have you ever undergone scrotal or groin surgery?",
          question_text_ar: "هل سبق لك الخضوع لجراحة في كيس الصفن أو الإربية؟",
          question_type: "SINGLE_CHOICE",
          is_required: true,
          options: [
            { value: "yes", label_en: "Yes", label_ar: "نعم" },
            { value: "no", label_en: "No", label_ar: "لا" },
          ],
        },
        {
          id: 11,
          question_code: "Q_TESTIS_SURGERY_TYPE",
          domain: "Surgical",
          domain_index: 3,
          question_text_en: "What type of surgery was performed?",
          question_text_ar: "ما نوع العملية الجراحية التي خضعت لها؟",
          question_type: "SINGLE_CHOICE",
          is_required: false,
          conditional_parent_code: "Q_TESTIS_SURGERY_HISTORY",
          conditional_parent_value: "yes",
          options: [
            { value: "undescended_testis", label_en: "Orchiopexy (Undescended Testis)", label_ar: "تثبيت الخصية الهاجرة" },
            { value: "varicocele_repair", label_en: "Varicocele Repair", label_ar: "إصلاح دوالي الخصية" },
          ],
        },
      ],
      saved_responses: {},
      has_urgent_red_flag: false,
    });

    render(
      <LanguageProvider>
        <AuthProvider>
          <AdaptiveAssessmentPage />
        </AuthProvider>
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Have you ever undergone scrotal or groin surgery/i)).toBeDefined();
    });

    // Conditional question should NOT be visible initially
    expect(screen.queryByText(/What type of surgery was performed/i)).toBeNull();

    // Select "Yes" to surgery
    const yesButton = screen.getByText("Yes");
    fireEvent.click(yesButton);

    // Conditional question should now appear
    await waitFor(() => {
      expect(screen.getByText(/What type of surgery was performed/i)).toBeDefined();
    });
  });

  // Acceptance Criteria 6: Invalidation Confirmation UX
  it("shows confirmation modal when changing answer with answered dependents and cancel retains selection", async () => {
    vi.spyOn(ApiClient, "startAssessment").mockResolvedValue({
      assessment_id: "test-assessment-id-12345",
      session_token: "test-session-token-67890",
      version_number: "v1.0.0",
      status: "IN_PROGRESS",
      current_domain_index: 3,
      total_domains: 11,
    });

    vi.spyOn(ApiClient, "getDomainQuestions").mockResolvedValue({
      assessment_id: "test-assessment-id-12345",
      domain_name: "Surgical & Anatomic History",
      domain_index: 3,
      total_domains: 11,
      questions: [
        {
          id: 10,
          question_code: "Q_TESTIS_SURGERY_HISTORY",
          domain: "Surgical",
          domain_index: 3,
          question_text_en: "Have you ever undergone scrotal or groin surgery?",
          question_text_ar: "هل سبق لك الخضوع لجراحة في كيس الصفن أو الإربية؟",
          question_type: "SINGLE_CHOICE",
          is_required: true,
          options: [
            { value: "yes", label_en: "Yes", label_ar: "نعم" },
            { value: "no", label_en: "No", label_ar: "لا" },
          ],
        },
        {
          id: 11,
          question_code: "Q_TESTIS_SURGERY_TYPE",
          domain: "Surgical",
          domain_index: 3,
          question_text_en: "What type of surgery was performed?",
          question_text_ar: "ما نوع العملية الجراحية التي خضعت لها؟",
          question_type: "SINGLE_CHOICE",
          is_required: false,
          conditional_parent_code: "Q_TESTIS_SURGERY_HISTORY",
          conditional_parent_value: "yes",
          options: [
            { value: "undescended_testis", label_en: "Orchiopexy (Undescended Testis)", label_ar: "تثبيت الخصية الهاجرة" },
            { value: "varicocele_repair", label_en: "Varicocele Repair", label_ar: "إصلاح دوالي الخصية" },
          ],
        },
      ],
      saved_responses: {
        Q_TESTIS_SURGERY_HISTORY: { answer_value: "yes", conditional_pathway_active: true },
        Q_TESTIS_SURGERY_TYPE: { answer_value: "varicocele_repair", conditional_pathway_active: true }
      },
      has_urgent_red_flag: false,
    });

    render(
      <LanguageProvider>
        <AuthProvider>
          <AdaptiveAssessmentPage />
        </AuthProvider>
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/What type of surgery was performed/i)).toBeDefined();
    });

    // Attempt to change parent answer from "Yes" to "No"
    const noButton = screen.getByText("No");
    fireEvent.click(noButton);

    // Verify confirmation modal appears with warning
    await waitFor(() => {
      expect(screen.getByText("Confirm Answer Change")).toBeDefined();
      expect(screen.getByText(/Changing this answer will deactivate \(1\) previously answered follow-up response/i)).toBeDefined();
    });

    // Click "Cancel & Keep Current"
    const cancelButton = screen.getByText("Cancel & Keep Current");
    fireEvent.click(cancelButton);

    // Verify modal dismissed and dependent question still visible
    expect(screen.queryByText("Confirm Answer Change")).toBeNull();
    expect(screen.getByText(/What type of surgery was performed/i)).toBeDefined();

    // Now click "No" again and confirm
    fireEvent.click(noButton);
    await waitFor(() => {
      expect(screen.getByText("Confirm & Deactivate")).toBeDefined();
    });
    const confirmButton = screen.getByText("Confirm & Deactivate");
    fireEvent.click(confirmButton);

    // Dependent question is now hidden
    await waitFor(() => {
      expect(screen.queryByText(/What type of surgery was performed/i)).toBeNull();
    });
  });

  // Acceptance Criteria 17: Pre-Submission Review UI
  it("pre-submission review UI displays complete summary and disables submit when required questions unanswered", async () => {
    vi.spyOn(ApiClient, "startAssessment").mockResolvedValue({
      assessment_id: "test-assessment-id-review",
      session_token: "test-token-review",
      version_number: "v1.0.0",
      status: "IN_PROGRESS",
      current_domain_index: 10,
      total_domains: 11,
    });

    vi.spyOn(ApiClient, "getDomainQuestions").mockResolvedValue({
      assessment_id: "test-assessment-id-review",
      domain_name: "Prior Clinical Investigations",
      domain_index: 10,
      total_domains: 11,
      questions: [
        {
          id: 19,
          question_code: "Q_PRIOR_SEMEN_ANALYSIS",
          domain: "Prior Investigations",
          domain_index: 10,
          question_text_en: "Have you previously had a semen analysis performed?",
          question_text_ar: "هل سبق لك إجراء تحليل للسائل المنوي؟",
          question_type: "SINGLE_CHOICE",
          is_required: true,
          options: [
            { value: "yes", label_en: "Yes", label_ar: "نعم" },
            { value: "no", label_en: "No", label_ar: "لا" },
          ],
        },
      ],
      saved_responses: {},
      has_urgent_red_flag: false,
    });

    vi.spyOn(ApiClient, "saveDomainResponses").mockResolvedValue({
      saved_count: 1,
      invalidated_question_keys: []
    });

    vi.spyOn(ApiClient, "getAssessmentReview").mockResolvedValue({
      assessment_id: "test-assessment-id-review",
      status: "IN_PROGRESS",
      version_tag: "v1.0.0",
      current_domain_index: 10,
      progress_percentage: 85.0,
      total_questions: 19,
      answered_count: 16,
      unanswered_required_count: 3,
      can_submit: false,
      domains: [
        {
          domain_code: "BASELINES_DEMOGRAPHICS",
          domain_index: 0,
          domain_title_en: "Baselines & Demographics",
          domain_title_ar: "البيانات الأساسية والديموغرافية",
          is_complete: true,
          questions: []
        },
        {
          domain_code: "TESTICULAR_HISTORY",
          domain_index: 1,
          domain_title_en: "Testicular & Scrotal History",
          domain_title_ar: "تاريخ الخصية وكيس الصفن",
          is_complete: false,
          questions: []
        }
      ],
      urgent_red_flags: []
    });

    render(
      <LanguageProvider>
        <AuthProvider>
          <AdaptiveAssessmentPage />
        </AuthProvider>
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Review Answers/i)).toBeDefined();
    });

    // Click "Review Answers" on Domain 10
    const reviewBtn = screen.getByText("Review Answers");
    fireEvent.click(reviewBtn);

    // Verify Review screen loads
    await waitFor(() => {
      expect(screen.getByText("Comprehensive Pre-Submission Review")).toBeDefined();
      expect(screen.getByText("Required Pending")).toBeDefined();
      expect(screen.getByText("3")).toBeDefined(); // 3 required questions pending
    });

    // Verify submit button is disabled because can_submit = false
    const submitBtn = screen.getByRole("button", { name: /Submit Assessment & View Report/i });
    expect(submitBtn.hasAttribute("disabled")).toBe(true);
  });
});
