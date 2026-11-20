"use client";

import React from "react";
import Link from "next/link";
import { useLanguage } from "@/context/LanguageContext";
import { useAuth } from "@/context/AuthContext";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Activity,
  History,
  BookOpen,
  ArrowRight,
  ShieldCheck,
  User,
  HeartPulse,
  PlusCircle,
  FileText,
} from "lucide-react";

export default function UserDashboardPage() {
  const { t, language } = useLanguage();
  const { user, isAuthenticated, guestSessionToken } = useAuth();

  return (
    <div className="container mx-auto px-4 sm:px-6 py-10 max-w-5xl space-y-8">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-teal-800 to-slate-900 text-white rounded-2xl p-6 sm:p-8 shadow-md flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center space-x-2 rtl:space-x-reverse">
            <Badge variant="secondary" className="bg-teal-600 text-white">
              {user?.role || "GUEST HEALTH SEEKER"}
            </Badge>
            <span className="text-xs text-teal-200">
              {language === "ar" ? "ملف صحي سري" : "Confidential Health Profile"}
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            {t("dash.welcome")}, {user?.full_name || (language === "ar" ? "ضيف جينوفيكس" : "Guest Health Seeker")}
          </h1>
          <p className="text-xs sm:text-sm text-teal-100/90 max-w-xl">
            {language === "ar"
              ? "تابع تقييماتك السريرية وتاريخ استشاراتك ومكتبتك الطبية المعتمدة في منصة واحدة آمنة."
              : "Access your evidence-linked triage reports, assessment history, and clinical guidelines."}
          </p>
        </div>

        <Link href="/assessment">
          <Button size="lg" className="bg-white text-teal-900 hover:bg-teal-50 font-bold text-xs sm:text-sm whitespace-nowrap shadow">
            <PlusCircle className="h-4 w-4 mr-2 rtl:mr-0 rtl:ml-2" />
            {t("dash.new_assessment")}
          </Button>
        </Link>
      </div>

      {/* Grid of Dashboard Panels */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card 1: Active Assessment Quick Access */}
        <Card className="border-border hover:shadow-sm transition-shadow">
          <CardHeader className="pb-3">
            <div className="h-9 w-9 rounded-lg bg-teal-100 dark:bg-teal-950 flex items-center justify-center text-teal-700 mb-2">
              <Activity className="h-5 w-5" />
            </div>
            <CardTitle className="text-base font-bold">
              {language === "ar" ? "التقييم السريري النشط" : "Clinical Assessment"}
            </CardTitle>
            <CardDescription className="text-xs">
              {language === "ar" ? "19 سؤالاً تكيفياً لفرز عوامل الخطر" : "19 adaptive questions across 11 domains"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-1">
            <p className="text-xs text-muted-foreground leading-relaxed">
              {language === "ar"
                ? "ابدأ أو استأنف تقييمك الصحي للكشف عن الأعراض الحادة وتأخر الإنجاب ونمط الحياة."
                : "Complete your multi-domain assessment to generate an immutable evidence-linked clinical report."}
            </p>
            <Link href="/assessment">
              <Button variant="clinical" size="sm" className="w-full text-xs font-semibold">
                <span>{language === "ar" ? "بدء التقييم الآن" : "Launch Assessment"}</span>
                <ArrowRight className="h-3.5 w-3.5 ml-1.5 rtl:ml-0 rtl:mr-1.5" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        {/* Card 2: Assessment History */}
        <Card className="border-border hover:shadow-sm transition-shadow">
          <CardHeader className="pb-3">
            <div className="h-9 w-9 rounded-lg bg-blue-100 dark:bg-blue-950 flex items-center justify-center text-blue-700 mb-2">
              <History className="h-5 w-5" />
            </div>
            <CardTitle className="text-base font-bold">
              {language === "ar" ? "سجل التقييمات السابقة" : "Assessment History"}
            </CardTitle>
            <CardDescription className="text-xs">
              {language === "ar" ? "لقطات تاريخية غير قابلة للتغيير" : "Immutable historical snapshots & reports"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-1">
            <p className="text-xs text-muted-foreground leading-relaxed">
              {language === "ar"
                ? "استعرض جميع التقارير السابقة الموثقة بالأدلة والرموز المرجعية لجلساتك."
                : "View and reprint your verified clinical reports locked to exact guideline versions."}
            </p>
            <Link href="/dashboard/history">
              <Button variant="outline" size="sm" className="w-full text-xs font-semibold">
                <span>{language === "ar" ? "استعراض السجل" : "View History"}</span>
                <ArrowRight className="h-3.5 w-3.5 ml-1.5 rtl:ml-0 rtl:mr-1.5" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        {/* Card 3: Clinical Health Library */}
        <Card className="border-border hover:shadow-sm transition-shadow">
          <CardHeader className="pb-3">
            <div className="h-9 w-9 rounded-lg bg-emerald-100 dark:bg-emerald-950 flex items-center justify-center text-emerald-700 mb-2">
              <BookOpen className="h-5 w-5" />
            </div>
            <CardTitle className="text-base font-bold">
              {language === "ar" ? "المكتبة التثقيفية الطبية" : "Health Library"}
            </CardTitle>
            <CardDescription className="text-xs">
              {language === "ar" ? "إرشادات EAU و AUA/ASRM و WHO" : "Evidence-based condition overviews"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-1">
            <p className="text-xs text-muted-foreground leading-relaxed">
              {language === "ar"
                ? "تصفح المقالات الطبية المراجعة من قبل استشاريي المسالك البولية والذكورة."
                : "Explore clinician-reviewed guides on varicoceles, azoospermia, hormonal health, and fertility."}
            </p>
            <Link href="/library">
              <Button variant="outline" size="sm" className="w-full text-xs font-semibold">
                <span>{language === "ar" ? "تصفح المكتبة" : "Browse Library"}</span>
                <ArrowRight className="h-3.5 w-3.5 ml-1.5 rtl:ml-0 rtl:mr-1.5" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Clinical Safety Protocol Notice */}
      <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs text-muted-foreground space-y-1">
        <div className="font-semibold text-slate-800 dark:text-slate-200 flex items-center space-x-1.5 rtl:space-x-reverse">
          <ShieldCheck className="h-4 w-4 text-teal-700" />
          <span>{language === "ar" ? "ضمان الخصوصية والسرية الطبية" : "Medical Privacy & Confidentiality Guarantee"}</span>
        </div>
        <p className="leading-relaxed">
          {language === "ar"
            ? "تخضع جميع استجاباتك لتشفير تام وفق أعلى المعايير الصحية العالمية. تقاريرك مشفرة ولا يتم مشاركتها إلا مع طبيبك المعالج حسب اختيارك."
            : "All responses are encrypted under strict healthcare data governance. Your reports remain strictly confidential and can only be accessed by you or shared with your consulting clinician."}
        </p>
      </div>
    </div>
  );
}
