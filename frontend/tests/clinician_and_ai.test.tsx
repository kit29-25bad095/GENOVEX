import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import ClinicianPortalPage from "@/app/clinician/page";
import ClinicianReviewPage from "@/app/clinician/review/[id]/page";
import { AISummaryCard } from "@/components/ai-summary-card";
import { LanguageProvider } from "@/context/LanguageContext";
import { AuthProvider } from "@/context/AuthContext";
import { ApiClient } from "@/lib/api";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "test-assessment-uuid-123" }),
  useRouter: () => ({ push: vi.fn() }),
}));

describe("Unified Phase 9 & Phase 10: Clinician Portal & AI Decision Support", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders Clinician Dashboard with queue counts and sanitized patient references", async () => {
    vi.spyOn(ApiClient, "getClinicianDashboard").mockResolvedValue({
      clinician_id: 10,
      clinician_name: "Dr. Tarek Al-Mansoor",
      credentials_summary: "Consultant Andrologist / UAE MOHAP",
      assigned_assessments_count: 5,
      pending_review_count: 3,
      in_review_count: 1,
      review_completed_count: 1,
      assessments_queue: [
        {
          assessment_id: "test-assessment-uuid-123",
          patient_reference: "PT-TEST1234",
          status: "LOCKED",
          outcome_tier: "CLINICAL_EVALUATION_RECOMMENDED",
          is_urgent_red_flag: false,
          review_workflow_status: "PENDING_REVIEW",
          submitted_at: new Date().toISOString(),
          last_activity_at: new Date().toISOString(),
        },
      ],
    });

    render(
      <LanguageProvider>
        <AuthProvider>
          <ClinicianPortalPage />
        </AuthProvider>
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Clinician Consultation Dashboard")).toBeDefined();
    });

    expect(screen.getByText("Dr. Tarek Al-Mansoor")).toBeDefined();
    expect(screen.getByText("Pending Review")).toBeDefined();
    expect(screen.getByText("PT-TEST1234")).toBeDefined();
    expect(screen.getByText("CLINICAL_EVALUATION_RECOMMENDED")).toBeDefined();
  });

  it("renders Assessment Review page with 5-state response distinctions and deterministic findings", async () => {
    vi.spyOn(ApiClient, "getClinicianAssessmentReview").mockResolvedValue({
      assessment_id: "test-assessment-uuid-123",
      patient_reference: "PT-TEST1234",
      status: "LOCKED",
      questionnaire_version_tag: "v1.0.0",
      current_review_status: "IN_REVIEW",
      submitted_at: new Date().toISOString(),
      responses: [
        {
          question_key: "Q_AGE",
          domain_code: "BASIC_HEALTH",
          prompt_en: "What is your current age?",
          prompt_ar: "ما هو عمرك الحالي؟",
          answer_value: 34,
          is_unsure: false,
          is_prefer_not_to_say: false,
          conditional_pathway_active: true,
          needs_reconfirmation: false,
          is_urgent_red_flag: false,
        },
        {
          question_key: "Q_TOBACCO_USE",
          domain_code: "LIFESTYLE_HABITS",
          prompt_en: "Do you use tobacco or dokha?",
          prompt_ar: "هل تدخن التبغ أو الدوخة؟",
          answer_value: null,
          is_unsure: true,
          is_prefer_not_to_say: false,
          conditional_pathway_active: true,
          needs_reconfirmation: false,
          is_urgent_red_flag: false,
        },
      ],
      deterministic_report: {
        report_reference: "GNX-RPT-TEST001",
        outcome_tier: "SPECIALIST_EVALUATION_RECOMMENDED",
        outcome_title_en: "Clinical Specialist Evaluation Recommended",
        outcome_description_en: "Responses indicate modifiable factors.",
        is_urgent_red_flag: false,
      },
      review_history: [],
      has_unapproved_rules: true,
      is_evaluation_incomplete: false,
    });

    vi.spyOn(ApiClient, "getClinicianNotes").mockResolvedValue([]);

    render(
      <LanguageProvider>
        <AuthProvider>
          <ClinicianReviewPage />
        </AuthProvider>
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Specialist Clinical Assessment Review")).toBeDefined();
    });

    // Asserts 5-state distinction is visible
    expect(screen.getByText("What is your current age?")).toBeDefined();
    expect(screen.getByText("Do you use tobacco or dokha?")).toBeDefined();
    expect(screen.getByText("Unsure")).toBeDefined();
    expect(screen.getByText("Deterministic Clinical Engine Findings")).toBeDefined();
  });

  it("renders AI Summary Card with AI-Generated badge and non-diagnostic disclaimer", () => {
    const mockSummary = {
      assessment_id: "test-assessment-uuid-123",
      patient_reference: "PT-TEST1234",
      clinical_triage_tier: "CLINICAL_EVALUATION_RECOMMENDED",
      is_urgent_red_flag: false,
      response_overview: {
        total_answered: 19,
        unsure_count: 1,
        prefer_not_to_say_count: 0,
      },
      synthesized_risk_narrative:
        "Patient-reported lifestyle risk factors warrant formal endocrine and semen analysis workup.",
      suggested_diagnostic_workup: [
        "Semen analysis in accredited laboratory (WHO 6th ed)",
        "Endocrine profile: Morning Total Testosterone, FSH, LH",
      ],
      is_ai_generated: true,
      metadata: {
        provider: "mock",
        model: "genovex-educational-v1",
        prompt_version: "v1.0.0",
        request_id: "ai-req-test-99",
        timestamp: new Date().toISOString(),
        is_educational: true,
        disclaimer: "AI-Generated Clinician Review Assistance — Not a Medical Diagnosis or Decision.",
      },
    };

    render(<AISummaryCard summary={mockSummary} language="en" />);

    expect(screen.getByText("AI-Assisted Clinical Synthesis")).toBeDefined();
    expect(screen.getByText("AI-Generated Assistance")).toBeDefined();
    expect(screen.getByText(/Patient-reported lifestyle risk factors warrant formal/i)).toBeDefined();
    expect(screen.getByText(/Semen analysis in accredited laboratory/i)).toBeDefined();
    expect(screen.getByText(/AI-Generated Clinician Review Assistance — Not a Medical Diagnosis/i)).toBeDefined();
  });

  it("displays Access Restricted notice when unauthorized user attempts dashboard access", async () => {
    vi.spyOn(ApiClient, "getClinicianDashboard").mockRejectedValue(
      new Error("Access denied: Clinician or Administrator privileges required.")
    );

    render(
      <LanguageProvider>
        <AuthProvider>
          <ClinicianPortalPage />
        </AuthProvider>
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Clinician Access Restricted")).toBeDefined();
    });
    expect(screen.getByText(/This portal is restricted to authorized clinicians/i)).toBeDefined();
  });
});
