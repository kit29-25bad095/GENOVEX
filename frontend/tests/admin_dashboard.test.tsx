import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import AdminDashboardPage from "@/app/admin/page";
import { LanguageProvider } from "@/context/LanguageContext";
import { AuthProvider } from "@/context/AuthContext";
import { ApiClient } from "@/lib/api";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useParams: () => ({}),
  useRouter: () => ({ push: vi.fn() }),
}));

// Mock AuthContext to return ADMIN user
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    user: {
      id: 2,
      email: "admin@genovex.ae",
      full_name: "Admin User",
      role: "ADMIN",
    },
    token: "mock-admin-token",
    login: vi.fn(),
    logout: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

describe("Phase 11: Admin Dashboard Frontend Suite", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const mockOverview = {
    users_total: 25,
    users_active: 22,
    users_inactive: 3,
    users_by_role: {
      PATIENT: 18,
      CLINICIAN: 4,
      ADMIN: 2,
      SUPERADMIN: 1,
    },
    assessments_total: 90,
    assessments_by_status: {
      IN_PROGRESS: 10,
      LOCKED: 75,
      SUBMITTED: 5,
    },
    reports_total: 80,
    reports_withheld_count: 80,
    clinician_reviews_pending: 12,
    clinician_reviews_in_progress: 3,
    clinician_reviews_completed: 65,
    recent_admin_activity: [
      {
        id: 101,
        user_email: "superadmin@genovex.ae",
        user_role: "SUPERADMIN",
        action: "ADMIN_USER_ROLE_UPDATE",
        resource_type: "User",
        resource_id: "5",
        timestamp: new Date().toISOString(),
      },
    ],
    platform_health_status: "HEALTHY",
    clinical_governance_status: "WITHHELD - PENDING CLINICAL BOARD REVIEW",
    governance_warning: "All 22 deterministic clinical rules are classified as UNAPPROVED.",
  };

  it("renders Admin Dashboard with real overview metrics and governance banner", async () => {
    vi.spyOn(ApiClient, "getAdminOverview").mockResolvedValue(mockOverview);

    render(
      <LanguageProvider>
        <AdminDashboardPage />
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Platform Administration & Operations")).toBeDefined();
    });

    // Overview cards
    expect(screen.getByText("25")).toBeDefined(); // Users total
    expect(screen.getByText("90")).toBeDefined(); // Assessments total

    // Governance notice banner
    expect(
      screen.getByText(/Clinical Governance Notice: Patient Release Withheld/i)
    ).toBeDefined();
    expect(screen.getByText(/100% \(HTTP 422\)/i)).toBeDefined();
  });

  it("navigates to User Management tab and displays user list with filters", async () => {
    vi.spyOn(ApiClient, "getAdminOverview").mockResolvedValue(mockOverview);
    vi.spyOn(ApiClient, "getAdminUsers").mockResolvedValue({
      items: [
        {
          id: 5,
          email: "target_clinician@genovex.ae",
          full_name: "Dr. Targeted Clinician",
          role: "CLINICIAN",
          credentials_summary: "Consultant",
          is_active: true,
          created_at: new Date().toISOString(),
        },
      ],
      total: 1,
      page: 1,
      page_size: 15,
      total_pages: 1,
    });

    render(
      <LanguageProvider>
        <AdminDashboardPage />
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("User Management")).toBeDefined();
    });

    // Click User Management tab
    const userTabBtn = screen.getByRole("button", { name: /User Management/i });
    fireEvent.click(userTabBtn);

    await waitFor(() => {
      expect(screen.getByText("Dr. Targeted Clinician")).toBeDefined();
    });

    expect(screen.getByText("target_clinician@genovex.ae")).toBeDefined();
    expect(screen.getByText("Deactivate")).toBeDefined();
    expect(screen.getAllByText(/Role/i).length).toBeGreaterThan(0);
  });

  it("navigates to Assessment Telemetry tab and displays aggregate stats without patient PII", async () => {
    vi.spyOn(ApiClient, "getAdminOverview").mockResolvedValue(mockOverview);
    vi.spyOn(ApiClient, "getAdminAssessmentStats").mockResolvedValue({
      total_assessments: 90,
      status_counts: { LOCKED: 80, IN_PROGRESS: 10 },
      reports_generated: 80,
      incomplete_assessments: 10,
      withheld_clinical_results: 80,
      outcome_tier_counts: {
        ROUTINE_PREVENTIVE_CARE: 30,
        LIFESTYLE_MODIFIABLE_FACTORS: 25,
        SPECIALIST_EVALUATION_RECOMMENDED: 20,
        URGENT_MEDICAL_ASSESSMENT: 5,
      },
      governance_withheld_percent: 100.0,
    });

    render(
      <LanguageProvider>
        <AdminDashboardPage />
      </LanguageProvider>
    );

    const assessmentTabBtn = screen.getByRole("button", { name: /Assessment Telemetry/i });
    fireEvent.click(assessmentTabBtn);

    await waitFor(() => {
      expect(screen.getByText("Assessment Operational Telemetry (Zero PII Guarantee)")).toBeDefined();
    });

    expect(screen.getByText("Reports Compiled")).toBeDefined();
    expect(screen.getByText("Governance Withholding")).toBeDefined();
    expect(screen.getByText("ROUTINE_PREVENTIVE_CARE")).toBeDefined();
    expect(screen.getByText("URGENT_MEDICAL_ASSESSMENT")).toBeDefined();
  });

  it("navigates to Clinician Operations tab and displays shared review pool notice", async () => {
    vi.spyOn(ApiClient, "getAdminOverview").mockResolvedValue(mockOverview);
    vi.spyOn(ApiClient, "getAdminClinicianOperations").mockResolvedValue({
      registered_clinicians: 4,
      active_clinicians: 4,
      shared_review_pool: true,
      exclusive_locking_implemented: false,
      pending_reviews: 5,
      in_review_count: 2,
      completed_reviews: 40,
      recent_reviews: [
        {
          id: 1,
          action: "CLINICIAN_REVIEW_WORKFLOW_UPDATE",
          actor_email: "dr.tarek@genovex.ae",
          assessment_reference: "PT-ABC12345",
          status: "REVIEW_COMPLETED",
          timestamp: new Date().toISOString(),
        },
      ],
    });

    render(
      <LanguageProvider>
        <AdminDashboardPage />
      </LanguageProvider>
    );

    const clinicianTabBtn = screen.getByRole("button", { name: /Clinician Operations/i });
    fireEvent.click(clinicianTabBtn);

    await waitFor(() => {
      expect(screen.getByText("Shared Review Pool Architecture (No Exclusive Claim Locking)")).toBeDefined();
    });

    expect(screen.getByText("Registered Clinicians")).toBeDefined();
    expect(screen.getByText("Completed Reviews")).toBeDefined();
    expect(screen.getByText("PT-ABC12345")).toBeDefined();
  });

  it("navigates to Platform Health & Config tab and confirms safe configuration without secrets", async () => {
    vi.spyOn(ApiClient, "getAdminOverview").mockResolvedValue(mockOverview);
    vi.spyOn(ApiClient, "getAdminHealth").mockResolvedValue({
      status: "HEALTHY",
      database: { connected: true, engine: "sqlite", read_only: false, sandbox_mode: true },
      api_version: "1.0.0",
      ai_provider_mode: "MOCK",
      ai_provider_configured: true,
      gemini_live_egress_active: false,
      clinical_governance_gate: "FAIL_CLOSED_ACTIVE",
      timestamp: new Date().toISOString(),
    });
    vi.spyOn(ApiClient, "getAdminConfig").mockResolvedValue({
      environment: "development",
      project_name: "GENOVEX",
      api_v1_str: "/api/v1",
      allowed_cors_origins: ["http://localhost:3000"],
      rate_limit_per_minute: 60,
      auth_jwt_algorithm: "HS256",
      ai_provider_mode: "MOCK",
      shared_review_queue: true,
    });

    render(
      <LanguageProvider>
        <AdminDashboardPage />
      </LanguageProvider>
    );

    const healthTabBtn = screen.getByRole("button", { name: /Health & Config/i });
    fireEvent.click(healthTabBtn);

    await waitFor(() => {
      expect(screen.getByText("Safe System Configuration (Zero Secret Exposure)")).toBeDefined();
    });

    expect(screen.getByText("CONNECTED")).toBeDefined();
    expect(screen.getByText("FAIL_CLOSED_ACTIVE")).toBeDefined();
    expect(screen.getByText(/FALSE \(Sandboxed\)/i)).toBeDefined();
    expect(screen.getByText("HS256")).toBeDefined();
  });
});
