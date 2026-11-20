import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import ClinicalNavigationPage from "@/app/navigation/page";
import AssessmentHistoryPage from "@/app/dashboard/history/page";
import { LanguageProvider } from "@/context/LanguageContext";
import { ApiClient } from "@/lib/api";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useParams: () => ({}),
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/navigation",
}));

// Mock AuthContext
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    user: {
      id: 1,
      email: "patient_history@genovex.ae",
      full_name: "History Patient",
      role: "PATIENT",
    },
    guestSessionToken: "mock-guest-token-123",
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

describe("Phase 12 & Phase 13: Clinical Navigation & Assessment History Frontend", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const mockFacilities = {
    items: [
      {
        id: 1,
        slug: "cleveland-clinic-abu-dhabi",
        name_en: "Cleveland Clinic Abu Dhabi — Male Health Center",
        name_ar: "كليفلاند كلينك أبوظبي — مركز صحة الرجل",
        emirate: "ABU_DHABI",
        regulatory_authority: "DOH",
        facility_type: "TERTIARY_HOSPITAL",
        address_en: "Al Maryah Island, Abu Dhabi",
        address_ar: "جزيرة المارية، أبوظبي",
        city_en: "Abu Dhabi",
        city_ar: "أبوظبي",
        phone_number: "+971-2-659-0000",
        emergency_phone: "+971-2-659-9999",
        website_url: "https://www.clevelandclinicabudhabi.ae",
        booking_url: "https://www.clevelandclinicabudhabi.ae/appointments",
        has_24_7_emergency: true,
        has_andrology_specialist: true,
        has_who_semen_analysis_lab: true,
        has_micro_tese_capability: true,
        offered_specialties: ["Male Reproductive Urologist / Andrologist", "General Urology"],
        insurance_networks: ["Daman Thiqa", "AXA"],
        is_verified: true,
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      {
        id: 2,
        slug: "fakeeh-university-hospital-dubai",
        name_en: "Fakeeh University Hospital — Men's Health",
        name_ar: "مستشفى فقيه الجامعي — صحة الرجل",
        emirate: "DUBAI",
        regulatory_authority: "DHA",
        facility_type: "TERTIARY_HOSPITAL",
        address_en: "Dubai Silicon Oasis",
        address_ar: "واحة دبي للسيليكون",
        city_en: "Dubai",
        city_ar: "دبي",
        phone_number: "+971-4-414-4444",
        has_24_7_emergency: true,
        has_andrology_specialist: true,
        has_who_semen_analysis_lab: true,
        has_micro_tese_capability: true,
        offered_specialties: ["Male Reproductive Urologist / Andrologist"],
        insurance_networks: ["NextCare", "MetLife"],
        is_verified: true,
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ],
    total: 2,
    page: 1,
    page_size: 50,
    emirates: ["ABU_DHABI", "DUBAI"],
    specialties: ["General Urology", "Male Reproductive Urologist / Andrologist"],
  };

  const mockHistory = {
    items: [
      {
        assessment_id: "assess-history-01",
        session_token: "token_history_01",
        status: "LOCKED",
        started_at: "2026-11-20T10:00:00Z",
        submitted_at: "2026-11-20T10:25:00Z",
        report_reference: "GNX-RPT-2026-HIST01",
        outcome_tier: "LIFESTYLE_MODIFIABLE_FACTORS",
        outcome_title_en: "Lifestyle & Modifiable Risk Factors",
        outcome_title_ar: "عوامل نمط الحياة القابلة للتعديل",
        is_urgent_red_flag: false,
        questionnaire_version_tag: "v1.0.0-published",
        rule_engine_version: "v1.0.0",
      },
      {
        assessment_id: "assess-history-02",
        session_token: "token_history_02",
        status: "SUBMITTED",
        started_at: "2026-11-19T14:00:00Z",
        submitted_at: "2026-11-19T14:20:00Z",
        report_reference: "GNX-RPT-2026-HIST02",
        outcome_tier: "URGENT_MEDICAL_ASSESSMENT",
        outcome_title_en: "Urgent Medical Assessment Required",
        outcome_title_ar: "تقييم طبي عاجل مطلوب",
        is_urgent_red_flag: true,
        questionnaire_version_tag: "v1.0.0-published",
        rule_engine_version: "v1.0.0",
      },
    ],
    total: 2,
  };

  it("renders Clinical Navigation Directory with safety notice and facilities", async () => {
    vi.spyOn(ApiClient, "getFacilities").mockResolvedValue(mockFacilities);

    render(
      <LanguageProvider>
        <ClinicalNavigationPage />
      </LanguageProvider>
    );

    // Verify title and safety notice
    await waitFor(() => {
      expect(screen.getByText(/UAE Clinical Navigation & Andrology Directory/i)).toBeDefined();
      expect(screen.getByText(/Clinical Navigation & Patient Safety Notice/i)).toBeDefined();
      expect(screen.getByText(/Cleveland Clinic Abu Dhabi/i)).toBeDefined();
      expect(screen.getByText(/Fakeeh University Hospital/i)).toBeDefined();
    }, { timeout: 3000 });

    expect(screen.getAllByText(/24\/7 ER/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Verified/i).length).toBeGreaterThan(0);
  });

  it("renders Clinical Assessment History with real snapshots and action buttons", async () => {
    vi.spyOn(ApiClient, "getAssessmentHistory").mockResolvedValue(mockHistory);

    render(
      <LanguageProvider>
        <AssessmentHistoryPage />
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Clinical Assessment History/i)).toBeDefined();
    });

    // Verify historical items rendered
    expect(screen.getByText(/Lifestyle & Modifiable Risk Factors/i)).toBeDefined();
    expect(screen.getByText(/Urgent Medical Assessment Required/i)).toBeDefined();
    expect(screen.getByText(/Urgent Red Flag/i)).toBeDefined();
    expect(screen.getAllByText(/View Report/i).length).toBe(2);
    expect(screen.getAllByText(/PDF/i).length).toBe(2);
  });
});
