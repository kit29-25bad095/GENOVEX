"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

type Language = "en" | "ar";
type Direction = "ltr" | "rtl";

interface LanguageContextType {
  language: Language;
  direction: Direction;
  setLanguage: (lang: Language) => void;
  toggleLanguage: () => void;
  t: (key: string) => string;
}

const translations: Record<Language, Record<string, string>> = {
  en: {
    // Brand & Navigation
    "app.title": "GENOVEX Male Reproductive Health",
    "nav.home": "Home",
    "nav.library": "Health Library",
    "nav.assessment": "Health Assessment",
    "nav.dashboard": "Dashboard",
    "nav.clinician": "Clinician Portal",
    "nav.admin": "Admin",
    "nav.login": "Sign In",
    "nav.register": "Register",
    "nav.logout": "Sign Out",
    "nav.language": "العربية",

    // Hero & Landing
    "hero.badge": "Evidence-Based Male Reproductive Health Platform",
    "hero.title": "Precision Male Fertility & Reproductive Triage",
    "hero.subtitle": "A deterministic clinical engine adhering to EAU, AUA/ASRM, and WHO 6th edition guidelines. Designed for early detection, confidential risk assessment, and rapid clinical referral.",
    "hero.cta.start": "Start Free Confidential Assessment",
    "hero.cta.library": "Browse Health Library",
    "hero.stats.rules": "14 Seeded Clinical Rules",
    "hero.stats.domains": "11 Clinical Domains",
    "hero.stats.guidelines": "EAU & AUA Validated",
    "hero.stats.confidential": "100% Confidential & Secure",

    // Urgent Safety Circuit
    "alert.urgent.title": "URGENT MEDICAL SAFETY NOTICE",
    "alert.urgent.pain": "Sudden, severe testicular pain is a medical emergency requiring immediate in-person evaluation at the nearest emergency department within 6 hours to preserve testicular viability.",
    "alert.urgent.lump": "A painless testicular lump or firm swelling warrants prompt evaluation by a urologist within 48-72 hours, including a physical examination and scrotal ultrasound.",
    "alert.urgent.disclaimer": "GENOVEX provides clinical risk stratification and education, not a definitive diagnosis. If you are experiencing acute pain, seek immediate emergency medical care.",

    // Questionnaire
    "quest.title": "Adaptive Reproductive Health Assessment",
    "quest.subtitle": "Answer each question accurately. Your responses remain completely confidential and are evaluated deterministically.",
    "quest.progress": "Domain Progress",
    "quest.next": "Next Question",
    "quest.prev": "Previous",
    "quest.submit": "Submit Assessment",
    "quest.review": "Review Responses",
    "quest.safe_unsure": "Not Sure",
    "quest.safe_decline": "Prefer Not to Say",
    "quest.required": "This question is required to complete the assessment.",

    // Report
    "report.title": "Clinical Assessment & Evidence-Linked Report",
    "report.session": "Session Token",
    "report.date": "Date of Assessment",
    "report.overall_tier": "Assessed Clinical Outcome Tier",
    "report.tier.1": "Tier 1: Routine Preventive Care",
    "report.tier.2": "Tier 2: Modifiable Lifestyle Risk Factors",
    "report.tier.3": "Tier 3: Specialist Evaluation Recommended",
    "report.tier.4": "Tier 4: URGENT Medical Assessment",
    "report.recommendations": "Evidence-Linked Clinical Recommendations",
    "report.risk_factors": "Identified Risk Factors",
    "report.citations": "Clinical Evidence Citations",
    "report.print": "Print Clinical Summary",

    // Auth
    "auth.login.title": "Sign In to GENOVEX",
    "auth.login.subtitle": "Access your assessments, consultation history, and personalized health guidance.",
    "auth.email": "Email Address",
    "auth.password": "Password",
    "auth.fullname": "Full Name",
    "auth.role": "Account Role",
    "auth.signin": "Sign In",
    "auth.signup": "Create Free Account",
    "auth.no_account": "Don't have an account?",
    "auth.has_account": "Already have an account?",
    "auth.demo_credentials": "Demo System Personas available for testing below.",

    // Dashboard
    "dash.welcome": "Welcome back",
    "dash.active_assessments": "Your Assessments",
    "dash.new_assessment": "Start New Assessment",
    "dash.health_overview": "Reproductive Health Overview",
    "dash.recent_activity": "Recent Activity",

    // Admin & Clinician
    "admin.rules.title": "Clinical Rule Governance",
    "admin.rules.subtitle": "Deterministic rule engine triggers, priorities, and version-locked approvals.",
    "admin.content.title": "Medical Content Management",
    "admin.content.subtitle": "Bilingual condition definitions, evidence references, and clinical review status.",
    "admin.audit.title": "Security & Audit Trail",
    "admin.audit.subtitle": "Immutable audit records of all clinical and administrative actions.",

    // Footer
    "footer.disclaimer": "GENOVEX is an informational health platform and clinical decision support system. It is not an alternative to professional in-person medical diagnosis.",
    "footer.privacy": "Privacy Policy",
    "footer.terms": "Terms of Service",
    "footer.copyright": "© 2026 GENOVEX Healthcare Platform. All rights reserved.",
  },
  ar: {
    // Brand & Navigation
    "app.title": "جينوفيكس لصحة الجهاز التناسلي للذكور",
    "nav.home": "الرئيسية",
    "nav.library": "المكتبة الصحية",
    "nav.assessment": "التقييم الصحي",
    "nav.dashboard": "لوحة التحكم",
    "nav.clinician": "بوابة الأطباء",
    "nav.admin": "الإدارة",
    "nav.login": "تسجيل الدخول",
    "nav.register": "إنشاء حساب",
    "nav.logout": "تسجيل الخروج",
    "nav.language": "English",

    // Hero & Landing
    "hero.badge": "منصة صحة الرجل التناسلية القائمة على الأدلة الإكلينيكية",
    "hero.title": "الفرز والتقييم الإكلينيكي الدقيق لخصوبة الرجال",
    "hero.subtitle": "محرك سريري حتمي معتمد على إرشادات الجمعية الأوروبية والجمعية الأمريكية لجراحة المسالك ومنظمة الصحة العالمية (الإصدار السادس). مصمم للكشف المبكر والتقييم السري والإحالة السريعة.",
    "hero.cta.start": "ابدأ التقييم السري المجاني",
    "hero.cta.library": "تصفح المكتبة الصحية",
    "hero.stats.rules": "14 قاعدة إكلينيكية معتمدة",
    "hero.stats.domains": "11 مجالاً طبياً",
    "hero.stats.guidelines": "إرشادات EAU و AUA المعتمدة",
    "hero.stats.confidential": "سري وآمن بنسبة 100٪",

    // Urgent Safety Circuit
    "alert.urgent.title": "تنبيه طبي عاجل للسلامة",
    "alert.urgent.pain": "يُعد ألم الخصية المفاجئ والحاد حالة طبية طارئة تتطلب فحصاً فورياً في أقرب قسم طوارئ خلال 6 ساعات للحفاظ على حيوية الخصية.",
    "alert.urgent.lump": "أي كتلة أو تورم غير مؤلم في الخصية يتطلب تقييماً عاجلاً لدى طبيب المسالك البولية خلال 48 إلى 72 ساعة متضمناً الفحص السريري والتصوير بالموجات فوق الصوتية.",
    "alert.urgent.disclaimer": "جينوفيكس يوفر تصنيفاً للمخاطر وتثقيفاً صحياً وليس تشخيصاً نهائياً. في حال الألم الحاد، توجه فوراً إلى الطوارئ.",

    // Questionnaire
    "quest.title": "التقييم التكيفي للصحة الإنجابية",
    "quest.subtitle": "يرجى الإجابة بدقة. جميع إجاباتك مشفرة وسرية تماماً وتخضع لقواعد سريرية حتمية.",
    "quest.progress": "تقدم المجالات السريرية",
    "quest.next": "السؤال التالي",
    "quest.prev": "السابق",
    "quest.submit": "إرسال التقييم",
    "quest.review": "مراجعة الإجابات",
    "quest.safe_unsure": "غير متأكد",
    "quest.safe_decline": "أفضل عدم الإجابة",
    "quest.required": "هذا السؤال مطلوب لإتمام التقييم.",

    // Report
    "report.title": "تقرير التقييم الإكلينيكي الموثق بالأدلة",
    "report.session": "رمز الجلسة",
    "report.date": "تاريخ التقييم",
    "report.overall_tier": "مستوى النتيجة الإكلينيكية المعتمد",
    "report.tier.1": "المستوى 1: رعاية وقائية روتينية",
    "report.tier.2": "المستوى 2: عوامل خطر متعلقة بنمط الحياة قابلة للتعديل",
    "report.tier.3": "المستوى 3: يُنصح بمراجعة طبيب مختص",
    "report.tier.4": "المستوى 4: تقييم طبي عاجل",
    "report.recommendations": "التوصيات الإكلينيكية المرتبطة بالأدلة",
    "report.risk_factors": "عوامل الخطر المحددة",
    "report.citations": "مراجع الأدلة الإكلينيكية",
    "report.print": "طباعة الملخص الطبي",

    // Auth
    "auth.login.title": "تسجيل الدخول إلى جينوفيكس",
    "auth.login.subtitle": "ادخل إلى تقييماتك وتاريخ استشاراتك وتوجيهاتك الصحية الشخصية.",
    "auth.email": "البريد الإلكتروني",
    "auth.password": "كلمة المرور",
    "auth.fullname": "الاسم الكامل",
    "auth.role": "نوع الحساب",
    "auth.signin": "تسجيل الدخول",
    "auth.signup": "إنشاء حساب جديد مجاناً",
    "auth.no_account": "ليس لديك حساب؟",
    "auth.has_account": "هل لديك حساب بالفعل؟",
    "auth.demo_credentials": "الحسابات التجريبية للمنظومة متوفرة للاختبار أدناه.",

    // Dashboard
    "dash.welcome": "مرحباً بك",
    "dash.active_assessments": "تقييماتك السريرية",
    "dash.new_assessment": "بدء تقييم جديد",
    "dash.health_overview": "نظرة عامة على صحة الإنجاب",
    "dash.recent_activity": "النشاط الأخير",

    // Admin & Clinician
    "admin.rules.title": "حوكمة القواعد الإكلينيكية",
    "admin.rules.subtitle": "محفزات وأولويات محرك القواعد الحتمي والاعتمادات المقفلة بالإصدار.",
    "admin.content.title": "إدارة المحتوى الطبي",
    "admin.content.subtitle": "تعريفات الحالات باللغتين ومراجع الأدلة وحالة المراجعة السريرية.",
    "admin.audit.title": "سجل الأمان والتدقيق",
    "admin.audit.subtitle": "سجلات تدقيق غير قابلة للتغيير لجميع العمليات السريرية والإدارية.",

    // Footer
    "footer.disclaimer": "جينوفيكس هي منصة صحية معلوماتية ونظام دعم القرار السريري وليست بديلاً عن التشخيص الطبي السريري المباشر.",
    "footer.privacy": "سياسة الخصوصية",
    "footer.terms": "شروط الخدمة",
    "footer.copyright": "© 2026 منصة جينوفيكس للرعاية الصحية. جميع الحقوق محفوظة.",
  },
};

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>("en");

  useEffect(() => {
    const saved = localStorage.getItem("genovex_lang") as Language;
    if (saved === "ar" || saved === "en") {
      setLanguageState(saved);
      document.documentElement.dir = saved === "ar" ? "rtl" : "ltr";
      document.documentElement.lang = saved;
    }
  }, []);

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem("genovex_lang", lang);
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.documentElement.lang = lang;
  };

  const toggleLanguage = () => {
    const nextLang = language === "en" ? "ar" : "en";
    setLanguage(nextLang);
  };

  const direction: Direction = language === "ar" ? "rtl" : "ltr";

  const t = (key: string): string => {
    return translations[language][key] || translations["en"][key] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, direction, setLanguage, toggleLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
};
