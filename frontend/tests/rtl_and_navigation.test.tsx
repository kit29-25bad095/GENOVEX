import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { Navbar } from "@/components/navbar";
import { LanguageProvider, useLanguage } from "@/context/LanguageContext";
import { AuthProvider } from "@/context/AuthContext";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

describe("Bilingual Arabic RTL & Navigation", () => {
  it("renders Navbar and toggles language to Arabic with RTL direction", () => {
    const TestComponent = () => {
      const { language, direction } = useLanguage();
      return (
        <div>
          <Navbar />
          <div data-testid="current-lang">{language}</div>
          <div data-testid="current-dir">{direction}</div>
        </div>
      );
    };

    render(
      <LanguageProvider>
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      </LanguageProvider>
    );

    // Initial language is English
    expect(screen.getByTestId("current-lang").textContent).toBe("en");
    expect(screen.getByTestId("current-dir").textContent).toBe("ltr");

    // Click language switch button (العربية)
    const langBtn = screen.getByText("العربية");
    fireEvent.click(langBtn);

    // Language should switch to Arabic with RTL direction
    expect(screen.getByTestId("current-lang").textContent).toBe("ar");
    expect(screen.getByTestId("current-dir").textContent).toBe("rtl");
    expect(document.documentElement.dir).toBe("rtl");
    expect(document.documentElement.lang).toBe("ar");
  });
});
