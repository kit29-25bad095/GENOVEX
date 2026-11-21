import { test, expect } from "@playwright/test";

test.describe("Phase 16 E2E: Bilingual Support & RTL Rendering", () => {
  test("should render in English LTR by default and toggle to Arabic RTL with computed layout verification", async ({ page }) => {
    await page.goto("/");

    // 1. Check default HTML attributes and computed CSS direction
    const html = page.locator("html");
    await expect(html).toHaveAttribute("dir", "ltr");
    await expect(html).toHaveAttribute("lang", "en");

    let computedDir = await page.evaluate(() =>
      window.getComputedStyle(document.querySelector("main") || document.body).direction
    );
    expect(computedDir).toBe("ltr");

    // 2. Locate language switcher button (shows 'العربية')
    const langBtn = page.getByRole("button", { name: "العربية" });
    await expect(langBtn).toBeVisible();

    // 3. Click to toggle to Arabic
    await langBtn.click();

    // 4. Assert HTML updates to RTL and Arabic
    await expect(html).toHaveAttribute("dir", "rtl");
    await expect(html).toHaveAttribute("lang", "ar");

    // 5. Verify actual layout element computed styles in RTL mode
    computedDir = await page.evaluate(() =>
      window.getComputedStyle(document.querySelector("main") || document.body).direction
    );
    expect(computedDir).toBe("rtl");

    const headingDir = await page.evaluate(() => {
      const h1 = document.querySelector("h1");
      return h1 ? window.getComputedStyle(h1).direction : "rtl";
    });
    expect(headingDir).toBe("rtl");

    // 6. Button should now show 'English'
    const englishBtn = page.getByRole("button", { name: "English" });
    await expect(englishBtn).toBeVisible();

    // 7. Switch back to English and confirm computed styles revert
    await englishBtn.click();
    await expect(html).toHaveAttribute("dir", "ltr");
    await expect(html).toHaveAttribute("lang", "en");

    computedDir = await page.evaluate(() =>
      window.getComputedStyle(document.querySelector("main") || document.body).direction
    );
    expect(computedDir).toBe("ltr");
  });

  test("should preserve RTL and Arabic content across navigation with verified layout attributes", async ({ page }) => {
    // Mock the facilities endpoint for all navigation patterns
    const mockFacilities = {
      total: 1,
      page: 1,
      page_size: 50,
      emirates: ["Abu Dhabi", "Dubai"],
      specialties: ["Andrology", "Urology"],
      items: [
        {
          id: 1,
          facility_name_en: "Cleveland Clinic Abu Dhabi",
          facility_name_ar: "كليفلاند كلينك أبوظبي",
          facility_type: "HOSPITAL",
          licensing_authority: "DOH",
          emirate: "Abu Dhabi",
          city: "Al Maryah Island",
          has_emergency_service: true,
          phone_number: "+971 2 659 0200",
          is_active: true,
        },
      ],
    };

    await page.route("**/navigation/facilities*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockFacilities),
      });
    });

    await page.route("**/api/v1/facilities*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockFacilities),
      });
    });

    await page.goto("/");

    // Switch to Arabic
    await page.getByRole("button", { name: "العربية" }).click();
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");

    // Navigate to /navigation (Clinics Directory)
    await page.goto("/navigation");

    // In Arabic, dir must remain rtl
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");

    // Verify layout direction on navigation page
    const navMainDir = await page.evaluate(() =>
      window.getComputedStyle(document.querySelector("main") || document.body).direction
    );
    expect(navMainDir).toBe("rtl");

    // Verify Arabic main heading is visible and rendered in Arabic
    const mainHeading = page.getByRole("main").getByRole("heading", { level: 1 });
    await expect(mainHeading).toBeVisible();
    await expect(page.getByRole("main").getByText(/دليل التوجيه السريري|مراكز الذكورة/i)).toBeVisible();
  });

  test("should display emergency hospital notice on clinical directory in both languages", async ({ page }) => {
    const emptyFacilities = {
      total: 0,
      page: 1,
      page_size: 50,
      emirates: [],
      specialties: [],
      items: [],
    };

    await page.route("**/navigation/facilities*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(emptyFacilities),
      });
    });

    await page.route("**/api/v1/facilities*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(emptyFacilities),
      });
    });

    // Check in English
    await page.goto("/navigation");
    await expect(page.getByRole("main").getByText(/emergency|hospital/i).first()).toBeVisible();

    // Switch to Arabic
    await page.getByRole("button", { name: "العربية" }).click();
    await expect(page.getByRole("main").getByText(/طوارئ|مستشفى/i).first()).toBeVisible();

    // Verify computed layout direction for emergency notice
    const emergencyNoticeDir = await page.evaluate(() => {
      const banner = document.querySelector(".border-destructive") || document.querySelector("main");
      return banner ? window.getComputedStyle(banner).direction : "rtl";
    });
    expect(emergencyNoticeDir).toBe("rtl");
  });
});
