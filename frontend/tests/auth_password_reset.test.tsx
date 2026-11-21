import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import LoginPage from "@/app/auth/login/page";
import ForgotPasswordPage from "@/app/auth/forgot-password/page";
import ResetPasswordPage from "@/app/auth/reset-password/page";
import { LanguageProvider } from "@/context/LanguageContext";
import { AuthProvider } from "@/context/AuthContext";
import { ApiClient } from "@/lib/api";

let mockSearchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
  usePathname: () => "/auth/forgot-password",
  useSearchParams: () => mockSearchParams,
}));

describe("Password Reset User Journey", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams = new URLSearchParams();
  });

  it("login page renders a link to the forgot password flow", () => {
    render(
      <LanguageProvider>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </LanguageProvider>
    );

    const forgotLink = screen.getByText("Forgot password?");
    expect(forgotLink).toBeDefined();
    expect(forgotLink.getAttribute("href")).toBe("/auth/forgot-password");
  });

  it("renders forgot password page with email input, dispatch button, and back link", () => {
    render(
      <LanguageProvider>
        <ForgotPasswordPage />
      </LanguageProvider>
    );

    expect(screen.getByText("Reset Your Password")).toBeDefined();
    expect(screen.getByLabelText("Email Address")).toBeDefined();
    expect(screen.getByText("Send Password Reset Link")).toBeDefined();
    expect(screen.getByText("Back to Sign In")).toBeDefined();
  });

  it("submits forgot password request and displays confirmation", async () => {
    const requestSpy = vi.spyOn(ApiClient, "requestPasswordReset").mockResolvedValueOnce({
      message: "If an account with this email exists, a password reset link has been dispatched.",
    });

    render(
      <LanguageProvider>
        <ForgotPasswordPage />
      </LanguageProvider>
    );

    const emailInput = screen.getByLabelText("Email Address");
    fireEvent.change(emailInput, { target: { value: "testpatient@genovex.health" } });

    const submitBtn = screen.getByText("Send Password Reset Link");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(requestSpy).toHaveBeenCalledWith("testpatient@genovex.health");
      expect(screen.getByText("Check Your Inbox")).toBeDefined();
    });
  });

  it("renders reset password page with missing token error when no token provided", () => {
    mockSearchParams = new URLSearchParams("");

    render(
      <LanguageProvider>
        <ResetPasswordPage />
      </LanguageProvider>
    );

    expect(
      screen.getByText("The password reset link is invalid or has expired. Please request a new link.")
    ).toBeDefined();
  });

  it("renders reset password form when token is present and validates matching passwords", async () => {
    mockSearchParams = new URLSearchParams("token=valid-secret-token-123");

    render(
      <LanguageProvider>
        <ResetPasswordPage />
      </LanguageProvider>
    );

    expect(screen.getByText("Create New Password")).toBeDefined();
    const newPassInput = screen.getByLabelText("New Password");
    const confirmPassInput = screen.getByLabelText("Confirm New Password");

    // Test mismatched passwords
    fireEvent.change(newPassInput, { target: { value: "NewPass1234!" } });
    fireEvent.change(confirmPassInput, { target: { value: "DifferentPass123!" } });

    const submitBtn = screen.getByText("Update Password");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("The password confirmation does not match.")).toBeDefined();
    });
  });

  it("submits password reset and displays success card when input is valid", async () => {
    mockSearchParams = new URLSearchParams("token=valid-secret-token-123");
    const resetSpy = vi.spyOn(ApiClient, "resetPassword").mockResolvedValueOnce({
      message: "Password has been successfully reset. You may now log in with your new credentials.",
      email: "patient@genovex.health",
    });

    render(
      <LanguageProvider>
        <ResetPasswordPage />
      </LanguageProvider>
    );

    const newPassInput = screen.getByLabelText("New Password");
    const confirmPassInput = screen.getByLabelText("Confirm New Password");

    fireEvent.change(newPassInput, { target: { value: "NewSecurePassword@2026" } });
    fireEvent.change(confirmPassInput, { target: { value: "NewSecurePassword@2026" } });

    const submitBtn = screen.getByText("Update Password");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(resetSpy).toHaveBeenCalledWith({
        token: "valid-secret-token-123",
        new_password: "NewSecurePassword@2026",
        confirm_password: "NewSecurePassword@2026",
      });
      expect(screen.getByText("Password Successfully Updated")).toBeDefined();
    });
  });
});
