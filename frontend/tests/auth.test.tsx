import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import LoginPage from "@/app/auth/login/page";
import RegisterPage from "@/app/auth/register/page";
import { LanguageProvider } from "@/context/LanguageContext";
import { AuthProvider } from "@/context/AuthContext";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
  usePathname: () => "/auth/login",
}));

describe("Frontend Authentication Interfaces", () => {
  it("renders login form with email, password fields and demo buttons", () => {
    render(
      <LanguageProvider>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </LanguageProvider>
    );

    expect(screen.getByText("Sign In to GENOVEX")).toBeDefined();
    expect(screen.getByLabelText("Email Address")).toBeDefined();
    expect(screen.getByLabelText("Password")).toBeDefined();
    expect(screen.getByText("👤 Patient (Rashid)")).toBeDefined();
    expect(screen.getByText("🩺 Clinician (Dr. Tarek)")).toBeDefined();
  });

  it("populates demo credentials when demo button is clicked", () => {
    render(
      <LanguageProvider>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </LanguageProvider>
    );

    const clinicianBtn = screen.getByText("🩺 Clinician (Dr. Tarek)");
    fireEvent.click(clinicianBtn);

    const emailInput = screen.getByLabelText("Email Address") as HTMLInputElement;
    expect(emailInput.value).toBe("clinician@genovex.health");
  });

  it("renders register form with password confirmation", () => {
    render(
      <LanguageProvider>
        <AuthProvider>
          <RegisterPage />
        </AuthProvider>
      </LanguageProvider>
    );

    expect(screen.getAllByText("Create Free Account").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Full Name")).toBeDefined();
    expect(screen.getByLabelText("Email Address")).toBeDefined();
    expect(screen.getByLabelText("Password")).toBeDefined();
    expect(screen.getByLabelText("Confirm Password")).toBeDefined();
  });
});
