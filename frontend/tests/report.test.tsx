import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import AssessmentReportPage from "@/app/assessment/report/[token]/page";
import { LanguageProvider } from "@/context/LanguageContext";
import { AuthProvider } from "@/context/AuthContext";
import { ApiClient } from "@/lib/api";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useParams: () => ({ token: "test_token_urgent_123" }),
  useRouter: () => ({ push: vi.fn() }),
}));

describe("Assessment Results & Evidence-Linked Report", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders Tier 4 Urgent Medical Assessment with emergency safety banner", async () => {
    vi.spyOn(ApiClient, "getReport").mockResolvedValue({
      id: 99,
      assessment_id: 123,
      report_reference: "GNX-RPT-2026-URG001",
      overall_tier: "URGENT_MEDICAL_ASSESSMENT",
      has_urgent_flags: true,
      urgent_guidance: "Sudden onset acute scrotal pain requires immediate emergency department attendance within 6 hours.",
      identified_risk_factors: [
        {
          rule_code: "R-URG-ACUTE-SCROTAL-PAIN",
          rule_name: "Acute Scrotal Pain Emergency Pathway",
          priority: 1,
          tier: "URGENT_MEDICAL_ASSESSMENT",
          referral_guidance: "Emergency Department immediately within 6-hour surgical window.",
          evidence_source: "EAU Guidelines on Urological Emergencies (2024)",
        },
      ],
      evidence_citations: [
        {
          guideline: "EAU Guidelines on Urological Emergencies",
          year: 2024,
          section: "Sec 3.1",
          recommendation: "Testicular torsion requires emergent exploration within 6 hours to preserve fertility and testicular salvage.",
        },
      ],
      non_diagnostic_summary_en: "Urgent urological safety protocol triggered due to reported acute severe scrotal pain.",
      non_diagnostic_summary_ar: "تم تفعيل بروتوكول السلامة الطبية العاجل بسبب الإبلاغ عن ألم حاد ومفاجئ في الصفن.",
      created_at: new Date().toISOString(),
    });

    render(
      <LanguageProvider>
        <AuthProvider>
          <AssessmentReportPage />
        </AuthProvider>
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Clinical Assessment & Evidence-Linked Report")).toBeDefined();
    });

    expect(screen.getByText("Tier 4: URGENT Medical Assessment")).toBeDefined();
    expect(screen.getByText("URGENT MEDICAL SAFETY NOTICE")).toBeDefined();
    expect(screen.getByText(/Acute Scrotal Pain Emergency Pathway/i)).toBeDefined();
    expect(screen.getAllByText(/EAU Guidelines on Urological Emergencies/i).length).toBeGreaterThan(0);
  });

  it("renders Incomplete Tier 1 with amber advisory warning and no reassuring green card", async () => {
    vi.spyOn(ApiClient, "getReport").mockResolvedValue({
      id: 101,
      assessment_id: 456,
      report_reference: "GNX-RPT-2026-INDET1",
      overall_tier: "ROUTINE_PREVENTIVE_CARE",
      has_urgent_flags: false,
      evaluation_completeness: "INDETERMINATE",
      is_evaluation_incomplete: true,
      is_amber_warning: true,
      outcome_title_en: "NO REPORTED RISK FACTORS IDENTIFIED — INCOMPLETE EVALUATION",
      outcome_title_ar: "لم يتم تسجيل عوامل خطورة واضحة — تقييم غير مكتمل",
      identified_risk_factors: [],
      evidence_citations: [],
      non_diagnostic_summary_en: "No affirmative risk factors identified. Assessment is incomplete.",
      non_diagnostic_summary_ar: "لم يتم تسجيل عوامل خطورة. التقييم غير مكتمل.",
      created_at: new Date().toISOString(),
    });

    render(
      <LanguageProvider>
        <AuthProvider>
          <AssessmentReportPage />
        </AuthProvider>
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Clinical Assessment & Evidence-Linked Report")).toBeDefined();
    });

    // Amber warning banner is displayed
    expect(screen.getByText(/Amber Advisory: Incomplete Risk Evaluation/i)).toBeDefined();
    expect(screen.getByText(/assessment is INCOMPLETE and CANNOT confirm the absence of risk factors or normal fertility/i)).toBeDefined();
    // Reassuring green text must NOT be present
    expect(screen.queryByText(/Routine preventive health optimization is recommended/i)).toBeNull();
  });

  it("renders governance withholding notice when clinical rules are unapproved", async () => {
    const withheldError = new Error("Assessment evaluation outputs are withheld from patient-facing release");
    (withheldError as any).code = "CLINICAL_RELEASE_WITHHELD";
    (withheldError as any).status = 422;

    vi.spyOn(ApiClient, "getReport").mockRejectedValue(withheldError);
    vi.spyOn(ApiClient, "evaluateAssessment").mockRejectedValue(withheldError);

    render(
      <LanguageProvider>
        <AuthProvider>
          <AssessmentReportPage />
        </AuthProvider>
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Clinical Report Release Withheld/i)).toBeDefined();
    });

    expect(screen.getByText(/Clinical Governance & Safety Notice:/i)).toBeDefined();
    expect(screen.getByText(/patient-facing report presentation is withheld pending qualified clinician sign-off/i)).toBeDefined();
  });

  it("renders incomplete evaluation withheld notice when Tier 1 evaluation is indeterminate", async () => {
    const incompleteError = new Error("Assessment evaluation is incomplete");
    (incompleteError as any).code = "INCOMPLETE_EVALUATION_WITHHELD";
    (incompleteError as any).status = 422;

    vi.spyOn(ApiClient, "getReport").mockRejectedValue(incompleteError);
    vi.spyOn(ApiClient, "evaluateAssessment").mockRejectedValue(incompleteError);

    render(
      <LanguageProvider>
        <AuthProvider>
          <AssessmentReportPage />
        </AuthProvider>
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Incomplete Evaluation Withheld/i)).toBeDefined();
    });

    expect(screen.getByText(/Clinical Notice: Incomplete Assessment Evidence:/i)).toBeDefined();
  });
});
