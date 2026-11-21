import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { Navbar } from "@/components/navbar";
import { LanguageProvider, useLanguage } from "@/context/LanguageContext";
import { AuthProvider } from "@/context/AuthContext";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

describe("Phase 3: Bilingual RTL & Layout Shift Resolution", () => {
  beforeEach(() => {
    // Clear storage and cookies before each test
    localStorage.clear();
    document.cookie = "genovex_lang=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    document.documentElement.dir = "ltr";
    document.documentElement.lang = "en";
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const TestConsumer = () => {
    const { language, direction, toggleLanguage, t } = useLanguage();
    return (
      <div>
        <Navbar />
        <div data-testid="current-lang">{language}</div>
        <div data-testid="current-dir">{direction}</div>
        <div data-testid="hero-title">{t("hero.title")}</div>
        <div data-testid="doc-dir">{document.documentElement.dir}</div>
        <div data-testid="doc-lang">{document.documentElement.lang}</div>
        <button data-testid="toggle-btn" onClick={toggleLanguage}>
          Toggle
        </button>
      </div>
    );
  };

  it("1. renders initial English LTR by default with zero layout shift", () => {
    render(
      <LanguageProvider initialLanguage="en">
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      </LanguageProvider>
    );

    expect(screen.getByTestId("current-lang").textContent).toBe("en");
    expect(screen.getByTestId("current-dir").textContent).toBe("ltr");
    expect(screen.getByTestId("hero-title").textContent).toBe("Precision Male Fertility & Reproductive Triage");
    expect(document.documentElement.dir).toBe("ltr");
    expect(document.documentElement.lang).toBe("en");
  });

  it("2. renders initial Arabic RTL immediately when initialLanguage is 'ar' (Server-Rendered SSR Parity)", () => {
    // When RootLayout reads genovex_lang=ar from cookies, it renders dir='rtl' and initialLanguage='ar'
    document.documentElement.dir = "rtl";
    document.documentElement.lang = "ar";

    render(
      <LanguageProvider initialLanguage="ar">
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      </LanguageProvider>
    );

    // Initial render must ALREADY be Arabic with RTL direction from frame 0 (no hydration layout shift)
    expect(screen.getByTestId("current-lang").textContent).toBe("ar");
    expect(screen.getByTestId("current-dir").textContent).toBe("rtl");
    expect(screen.getByTestId("hero-title").textContent).toBe("الفرز والتقييم الإكلينيكي الدقيق لخصوبة الرجال");
    expect(document.documentElement.dir).toBe("rtl");
    expect(document.documentElement.lang).toBe("ar");
  });

  it("3. persists language preference to both cookie and localStorage on switch", () => {
    render(
      <LanguageProvider initialLanguage="en">
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      </LanguageProvider>
    );

    // Toggle to Arabic
    const toggleBtn = screen.getByTestId("toggle-btn");
    fireEvent.click(toggleBtn);

    expect(screen.getByTestId("current-lang").textContent).toBe("ar");
    expect(screen.getByTestId("current-dir").textContent).toBe("rtl");
    expect(document.documentElement.dir).toBe("rtl");
    expect(document.documentElement.lang).toBe("ar");

    // Dual-persistence verification
    expect(localStorage.getItem("genovex_lang")).toBe("ar");
    expect(document.cookie).toContain("genovex_lang=ar");
  });

  it("4. synchronizes from cookie/localStorage if already saved on direct refresh", () => {
    // Simulate user who previously selected Arabic refreshing the page
    localStorage.setItem("genovex_lang", "ar");
    document.cookie = "genovex_lang=ar; path=/";

    render(
      <LanguageProvider initialLanguage="ar">
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      </LanguageProvider>
    );

    expect(screen.getByTestId("current-lang").textContent).toBe("ar");
    expect(screen.getByTestId("current-dir").textContent).toBe("rtl");
    expect(document.documentElement.dir).toBe("rtl");
    expect(document.documentElement.lang).toBe("ar");
  });

  it("5. toggles back and forth smoothly between English and Arabic", () => {
    render(
      <LanguageProvider initialLanguage="en">
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      </LanguageProvider>
    );

    const toggleBtn = screen.getByTestId("toggle-btn");

    // First switch: EN -> AR
    fireEvent.click(toggleBtn);
    expect(screen.getByTestId("current-lang").textContent).toBe("ar");
    expect(screen.getByTestId("current-dir").textContent).toBe("rtl");
    expect(localStorage.getItem("genovex_lang")).toBe("ar");
    expect(document.cookie).toContain("genovex_lang=ar");

    // Second switch: AR -> EN
    fireEvent.click(toggleBtn);
    expect(screen.getByTestId("current-lang").textContent).toBe("en");
    expect(screen.getByTestId("current-dir").textContent).toBe("ltr");
    expect(localStorage.getItem("genovex_lang")).toBe("en");
    expect(document.cookie).toContain("genovex_lang=en");
  });

  it("6. renders Navbar links and buttons with correct localized labels in both languages", () => {
    const { unmount } = render(
      <LanguageProvider initialLanguage="en">
        <AuthProvider>
          <Navbar />
        </AuthProvider>
      </LanguageProvider>
    );

    // English labels
    expect(screen.getByText("Home")).toBeDefined();
    expect(screen.getByText("Health Library")).toBeDefined();
    expect(screen.getByText("Health Assessment")).toBeDefined();
    expect(screen.getByText("Sign In")).toBeDefined();
    expect(screen.getByText("العربية")).toBeDefined();

    unmount();

    // Arabic labels
    render(
      <LanguageProvider initialLanguage="ar">
        <AuthProvider>
          <Navbar />
        </AuthProvider>
      </LanguageProvider>
    );

    expect(screen.getByText("الرئيسية")).toBeDefined();
    expect(screen.getByText("المكتبة الصحية")).toBeDefined();
    expect(screen.getByText("التقييم الصحي")).toBeDefined();
    expect(screen.getByText("تسجيل الدخول")).toBeDefined();
    expect(screen.getByText("English")).toBeDefined();
  });
});
