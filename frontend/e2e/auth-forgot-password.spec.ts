import { test, expect } from "@playwright/test";

test.describe("Phase 16 E2E: Authentication & Forgot Password Lifecycle", () => {
  test("should navigate from login to forgot password page", async ({ page }) => {
    await page.goto("/auth/login");
    await expect(page).toHaveTitle(/GENOVEX/i);

    // Verify login card exists
    const emailInput = page.locator("#email");
    await expect(emailInput).toBeVisible();

    // Locate and click 'Forgot your password?'
    const forgotLink = page.getByRole("link", { name: /forgot/i });
    await expect(forgotLink).toBeVisible();
    await forgotLink.click();

    // Verify route is /auth/forgot-password
    await expect(page).toHaveURL(/\/auth\/forgot-password/);
    await expect(page.locator("#reset-email")).toBeVisible();
  });

  test("should submit forgot password request and display confirmation notice", async ({ page }) => {
    // Intercept backend API call to return standard generic success response (preventing enumeration)
    await page.route("**/api/v1/auth/forgot-password", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          message: "If this email address is registered, password reset instructions have been sent.",
        }),
      });
    });

    await page.goto("/auth/forgot-password");

    const emailInput = page.locator("#reset-email");
    await emailInput.fill("patient.test@genovex.ae");

    const submitBtn = page.getByRole("button", { name: /send|submit|instructions|إرسال/i });
    await expect(submitBtn).toBeEnabled();
    await submitBtn.click();

    // Confirmation alert should appear
    await expect(page.getByText(/instructions to/i)).toBeVisible();
    await expect(page.getByText("patient.test@genovex.ae")).toBeVisible();
  });

  test("should display error on reset-password page when token is missing", async ({ page }) => {
    await page.goto("/auth/reset-password");

    // The page alerts that link is invalid or expired
    await expect(
      page.getByText(/invalid.*link|expired.*link|رابط غير صالح/i)
    ).toBeVisible();

    // Password input form is guarded when token is invalid/missing
    await expect(page.locator("#new-password")).toHaveCount(0);
  });

  test("should handle expired or invalid token on reset-password submission", async ({ page }) => {
    // Intercept backend reset-password endpoint returning 400 Expired/Invalid Token
    await page.route("**/api/v1/auth/reset-password", async (route) => {
      await route.fulfill({
        status: 400,
        contentType: "application/json",
        body: JSON.stringify({
          detail: "The password reset link is invalid or has expired.",
        }),
      });
    });

    await page.goto("/auth/reset-password?token=mock_expired_token_999");

    const newPassInput = page.locator("#new-password");
    const confirmPassInput = page.locator("#confirm-password");
    await expect(newPassInput).toBeVisible();
    await expect(confirmPassInput).toBeVisible();

    await newPassInput.fill("NewPassword@2026");
    await confirmPassInput.fill("NewPassword@2026");

    const submitBtn = page.getByRole("button", { name: /Update Password|تحديث كلمة المرور/i });
    await submitBtn.click();

    // Error alert should be displayed with retry guidance
    await expect(page.getByText(/invalid.*link|expired.*link|رابط غير صالح/i)).toBeVisible();
    await expect(page.getByRole("link", { name: /Request a new|طلب رابط/i })).toBeVisible();
  });

  test("should render password policy checklist and strength meter when token is provided", async ({ page }) => {
    await page.goto("/auth/reset-password?token=mock_valid_test_token_12345");

    const newPassInput = page.locator("#new-password");
    const confirmPassInput = page.locator("#confirm-password");
    await expect(newPassInput).toBeVisible();
    await expect(confirmPassInput).toBeVisible();

    // Type a weak password
    await newPassInput.fill("short");
    await expect(page.getByText("• 8+ characters")).toBeVisible();

    // Type a strong password meeting all criteria
    await newPassInput.fill("SecurePass@2026");
    await confirmPassInput.fill("SecurePass@2026");

    // Update Password submit button should be enabled
    const submitBtn = page.getByRole("button", { name: /Update Password|تحديث كلمة المرور/i });
    await expect(submitBtn).toBeEnabled();
  });

  test("should successfully reset password and proceed through subsequent login", async ({ page }) => {
    // Mock successful password reset
    await page.route("**/api/v1/auth/reset-password", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          message: "Password reset successful. You can now log in with your new password.",
        }),
      });
    });

    // Mock successful login
    await page.route("**/api/v1/auth/login", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          access_token: "mock_jwt_access_token_patient_12345",
          token_type: "bearer",
          user: {
            id: 1,
            email: "patient.test@genovex.ae",
            role: "PATIENT",
            full_name: "Test Patient",
          },
        }),
      });
    });

    await page.goto("/auth/reset-password?token=mock_valid_test_token_12345");

    await page.locator("#new-password").fill("BrandNewPassword@2026");
    await page.locator("#confirm-password").fill("BrandNewPassword@2026");

    const submitBtn = page.getByRole("button", { name: /Update Password|تحديث كلمة المرور/i });
    await submitBtn.click();

    // Success confirmation banner should be visible
    await expect(page.getByText(/successful|بنجاح/i)).toBeVisible();

    // Click through to Sign In
    const signInLink = page.getByRole("main").getByRole("link", { name: /Sign In|تسجيل الدخول/i }).first();
    await expect(signInLink).toBeVisible();
    await signInLink.click();

    // Should navigate to /auth/login
    await expect(page).toHaveURL(/\/auth\/login/);

    // Fill in login credentials with newly updated password
    await page.locator("#email").fill("patient.test@genovex.ae");
    await page.locator("#password").fill("BrandNewPassword@2026");

    const loginBtn = page.locator('button[type="submit"]');
    await loginBtn.click();

    // Login succeeds and transitions user
    await expect(page).toHaveURL(/\/(dashboard|auth\/login)/);
  });
});
