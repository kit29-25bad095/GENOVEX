import type { Metadata } from "next";
import { cookies, headers } from "next/headers";
import "./globals.css";
import { LanguageProvider } from "@/context/LanguageContext";
import { AuthProvider } from "@/context/AuthContext";
import { Navbar } from "@/components/navbar";
import { Footer } from "@/components/footer";

export const metadata: Metadata = {
  title: "GENOVEX | Male Reproductive Health & Clinical Triage Platform",
  description:
    "Evidence-linked male fertility assessment, reproductive symptom triage, and clinical decision support system grounded in EAU, AUA/ASRM, and WHO guidelines.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  let initialLanguage: "en" | "ar" = "en";
  try {
    const cookieStore = cookies();
    const langCookie = cookieStore.get("genovex_lang")?.value;
    if (langCookie === "ar" || langCookie === "en") {
      initialLanguage = langCookie;
    } else {
      const headerStore = headers();
      const acceptLang = headerStore.get("accept-language") || "";
      if (acceptLang.toLowerCase().startsWith("ar")) {
        initialLanguage = "ar";
      }
    }
  } catch {
    // Graceful fallback during static optimization or test environments
    initialLanguage = "en";
  }

  const initialDirection = initialLanguage === "ar" ? "rtl" : "ltr";

  return (
    <html lang={initialLanguage} dir={initialDirection} suppressHydrationWarning>
      <head>
        {/*
          Synchronous pre-hydration direction script:
          Executes inline before the body is painted by the browser.
          Guarantees that html.dir and html.lang immediately match stored preferences,
          eliminating any flash of wrong direction (FOUC) or Cumulative Layout Shift (CLS).
        */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var m = document.cookie.match(/(?:^|; )genovex_lang=([^;]+)/);
                  var lang = m ? decodeURIComponent(m[1]) : null;
                  if (!lang) {
                    lang = localStorage.getItem('genovex_lang');
                  }
                  if (lang === 'ar' || lang === 'en') {
                    document.documentElement.lang = lang;
                    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
                  }
                } catch (e) {}
              })();
            `,
          }}
        />
      </head>
      <body className="min-h-screen flex flex-col bg-slate-50/50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 antialiased font-sans">
        <LanguageProvider initialLanguage={initialLanguage}>
          <AuthProvider>
            <Navbar />
            <main className="flex-1">{children}</main>
            <Footer />
          </AuthProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
