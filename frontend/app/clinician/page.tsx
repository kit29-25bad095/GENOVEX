"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/context/LanguageContext";
import { useAuth } from "@/context/AuthContext";
import { ApiClient, ClinicianDashboardSummary } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Stethoscope,
  Search,
  ShieldAlert,
  Clock,
  CheckCircle2,
  AlertCircle,
  FileText,
  UserCheck,
  ChevronRight,
  ExternalLink,
  Lock,
} from "lucide-react";

export default function ClinicianPortalPage() {
  const { t, language } = useLanguage();
  const { user } = useAuth();
  const router = useRouter();

  const [dashboardData, setDashboardData] = useState<ClinicianDashboardSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lookupToken, setLookupToken] = useState("");

  const isAr = language === "ar";

  useEffect(() => {
    async function fetchDashboard() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await ApiClient.getClinicianDashboard();
        setDashboardData(data);
      } catch (err: any) {
        setError(err.message || "Failed to load clinician dashboard. Clinician credentials required.");
      } finally {
        setIsLoading(false);
      }
    }
    fetchDashboard();
  }, []);

  const clinicalProtocols = [
    {
      title_en: "Acute Scrotal Pain Emergency Protocol",
      title_ar: "بروتوكول طوارئ ألم الصفن الحاد",
      guideline: "EAU Guidelines on Urological Emergencies (2024)",
      target: "Immediate Emergency Department Triage",
      window: "6-Hour Golden Window",
      notes_en: "Urgent surgical exploration if torsion is suspected. Color Doppler ultrasound must not delay operative exploration if clinical suspicion is high.",
      notes_ar: "استكشاف جراحي عاجل في حال الاشتباه في الالتواء. يجب ألا يؤخر تصوير الدوبلر التدخل الجراحي عند الاشتباه السريري المرتفع.",
      tier: "Tier 4 Urgent",
      tierColor: "urgent" as const,
    },
    {
      title_en: "Painless Testicular Mass Protocol",
      title_ar: "بروتوكول كتلة الخصية غير المؤلمة",
      guideline: "EAU Guidelines on Testicular Cancer (2024)",
      target: "Outpatient Urologic Oncology Evaluation",
      window: "48-72 Hours",
      notes_en: "Physical examination, high-frequency (7.5-10 MHz) scrotal ultrasound, and serum tumor markers (AFP, beta-hCG, LDH).",
      notes_ar: "الفحص السريري، التصوير بالموجات فوق الصوتية عالية التردد (7.5-10 ميغاهرتز)، وفحص دلالات الأورام في المصل (AFP, beta-hCG, LDH).",
      tier: "Tier 4 Urgent",
      tierColor: "urgent" as const,
    },
    {
      title_en: "Prolonged Infertility Diagnostic Workup",
      title_ar: "بروتوكول الفحص التشخيصي لتأخر الإنجاب المطول",
      guideline: "AUA/ASRM Male Infertility Guidelines (2021)",
      target: "Andrology / Reproductive Urology",
      window: "Elective Specialist Referral",
      notes_en: "Two semen analyses (WHO 6th ed), endocrine evaluation (morning total testosterone, FSH, LH, prolactin), and physical exam for varicocele.",
      notes_ar: "تحليلان للمني (وفق منظمة الصحة العالمية الإصدار السادس)، تقييم الغدد الصماء (التستوستيرون الصباحي، FSH، LH، البرولاكتين)، وفحص دوالي الخصية.",
      tier: "Tier 3 Specialist",
      tierColor: "warning" as const,
    },
  ];

  if (error && error.includes("Access denied")) {
    return (
      <div className="container mx-auto px-4 py-20 max-w-md text-center space-y-4">
        <div className="p-3 bg-red-100 dark:bg-red-950/40 rounded-full w-14 h-14 mx-auto flex items-center justify-center">
          <Lock className="h-7 w-7 text-red-600 dark:text-red-400" />
        </div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          {isAr ? "غير مصرح بالدخول" : "Clinician Access Restricted"}
        </h2>
        <p className="text-xs text-muted-foreground leading-relaxed">
          {isAr
            ? "هذه البوابة مخصصة للأطباء واستشاريي الذكورة المرخصين فقط. يرجى تسجيل الدخول بحساب كادر طبي معتمد."
            : "This portal is restricted to authorized clinicians, andrologists, and medical administrators. Please log in with valid clinician credentials."}
        </p>
        <Link href="/auth/login">
          <Button variant="clinical" size="sm">
            {isAr ? "تسجيل دخول الأطباء" : "Clinician Sign In"}
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 sm:px-6 py-10 max-w-6xl space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-6">
        <div className="space-y-1">
          <div className="flex items-center space-x-2 rtl:space-x-reverse">
            <Badge variant="outline" className="text-teal-700 border-teal-300">
              <Stethoscope className="h-3.5 w-3.5 mr-1 rtl:mr-0 rtl:ml-1 inline" />
              {isAr ? "بوابة الكادر الطبي المعتمد" : "Clinician Decision Support Portal"}
            </Badge>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            {isAr ? "لوحة تحكم استشارات الذكورة" : "Clinician Consultation Dashboard"}
          </h1>
          <p className="text-xs text-muted-foreground">
            {isAr
              ? "استعراض تقييمات المرضى، فحص تفاصيل الإجابات خماسية الحالات، ومتابعة بروتوكولات الفرز الإكلينيكي المعتمدة."
              : "Review patient assessments, inspect 5-state response breakdowns, and manage specialist review workflows."}
          </p>
        </div>

        <div className="flex items-center space-x-2 rtl:space-x-reverse text-xs bg-slate-100 dark:bg-slate-800 p-2.5 rounded-lg border border-border">
          <UserCheck className="h-4 w-4 text-emerald-600 flex-shrink-0" />
          <div>
            <div className="font-semibold text-slate-900 dark:text-white">
              {dashboardData?.clinician_name || user?.full_name || "Dr. Clinician"}
            </div>
            <div className="text-[10px] text-muted-foreground">
              {dashboardData?.credentials_summary || user?.credentials_summary || "Consultant Andrologist / UAE MOHAP"}
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card className="border-border">
          <CardContent className="pt-4 pb-4">
            <div className="text-xs text-muted-foreground font-medium">
              {isAr ? "إجمالي التقييمات" : "Total Assessments"}
            </div>
            <div className="text-2xl font-extrabold text-slate-900 dark:text-white mt-1">
              {dashboardData?.assigned_assessments_count ?? 0}
            </div>
          </CardContent>
        </Card>

        <Card className="border-amber-200 dark:border-amber-900 bg-amber-50/30 dark:bg-amber-950/20">
          <CardContent className="pt-4 pb-4">
            <div className="text-xs text-amber-900 dark:text-amber-200 font-medium flex items-center gap-1">
              <Clock className="h-3.5 w-3.5 text-amber-600" />
              <span>{isAr ? "قيد الانتظار" : "Pending Review"}</span>
            </div>
            <div className="text-2xl font-extrabold text-amber-700 dark:text-amber-300 mt-1">
              {dashboardData?.pending_review_count ?? 0}
            </div>
          </CardContent>
        </Card>

        <Card className="border-blue-200 dark:border-blue-900 bg-blue-50/30 dark:bg-blue-950/20">
          <CardContent className="pt-4 pb-4">
            <div className="text-xs text-blue-900 dark:text-blue-200 font-medium flex items-center gap-1">
              <AlertCircle className="h-3.5 w-3.5 text-blue-600" />
              <span>{isAr ? "قيد المراجعة" : "In Review"}</span>
            </div>
            <div className="text-2xl font-extrabold text-blue-700 dark:text-blue-300 mt-1">
              {dashboardData?.in_review_count ?? 0}
            </div>
          </CardContent>
        </Card>

        <Card className="border-emerald-200 dark:border-emerald-900 bg-emerald-50/30 dark:bg-emerald-950/20">
          <CardContent className="pt-4 pb-4">
            <div className="text-xs text-emerald-900 dark:text-emerald-200 font-medium flex items-center gap-1">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
              <span>{isAr ? "مكتملة المراجعة" : "Review Completed"}</span>
            </div>
            <div className="text-2xl font-extrabold text-emerald-700 dark:text-emerald-300 mt-1">
              {dashboardData?.review_completed_count ?? 0}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Assessment Queue Table */}
      <Card className="border-border shadow-sm">
        <CardHeader className="pb-3 border-b border-border/60">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <CardTitle className="text-base font-bold text-slate-900 dark:text-white">
                {isAr ? "قائمة انتظار مراجعة التقييمات الإكلينيكية" : "Clinical Assessment Review Queue"}
              </CardTitle>
              <CardDescription className="text-xs">
                {isAr
                  ? "الوصول السريع لتقارير المرضى وتفاصيل الإجابات خماسية الحالات."
                  : "Assessments awaiting clinical review. Click to inspect responses, deterministic triage, and AI summaries."}
              </CardDescription>
            </div>
            <Badge variant="outline" className="text-xs w-fit">
              {dashboardData?.assessments_queue?.length || 0} {isAr ? "تقييم متاح" : "assessments available"}
            </Badge>
          </div>
        </CardHeader>

        <CardContent className="pt-4">
          {isLoading ? (
            <div className="py-12 text-center text-xs text-muted-foreground space-y-2">
              <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-teal-700 border-r-transparent" />
              <p>{isAr ? "جاري تحميل قائمة التقييمات..." : "Loading assessment queue..."}</p>
            </div>
          ) : dashboardData?.assessments_queue && dashboardData.assessments_queue.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left rtl:text-right text-xs">
                <thead>
                  <tr className="border-b border-border text-muted-foreground uppercase text-[10px] tracking-wider font-semibold">
                    <th className="py-2.5 px-3">{isAr ? "رمز المريض" : "Patient Ref"}</th>
                    <th className="py-2.5 px-3">{isAr ? "حالة التقييم" : "Assessment Status"}</th>
                    <th className="py-2.5 px-3">{isAr ? "المستوى التقديري" : "Deterministic Tier"}</th>
                    <th className="py-2.5 px-3">{isAr ? "حالة المراجعة" : "Review Workflow"}</th>
                    <th className="py-2.5 px-3">{isAr ? "تاريخ التقديم" : "Submitted"}</th>
                    <th className="py-2.5 px-3 text-right rtl:text-left">{isAr ? "الإجراء" : "Action"}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {dashboardData.assessments_queue.map((item) => (
                    <tr key={item.assessment_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                      <td className="py-3 px-3 font-mono font-medium text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                        {item.is_urgent_red_flag && <ShieldAlert className="h-3.5 w-3.5 text-red-600 flex-shrink-0" />}
                        <span>{item.patient_reference}</span>
                      </td>
                      <td className="py-3 px-3">
                        <Badge variant="outline" className="text-[10px]">
                          {item.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-3">
                        {item.outcome_tier ? (
                          <span className="font-semibold text-[11px] text-teal-800 dark:text-teal-300">
                            {item.outcome_tier}
                          </span>
                        ) : (
                          <span className="text-muted-foreground italic text-[11px]">Pending Evaluation</span>
                        )}
                      </td>
                      <td className="py-3 px-3">
                        <Badge
                          variant={
                            item.review_workflow_status === "REVIEW_COMPLETED"
                              ? "success"
                              : item.review_workflow_status === "IN_REVIEW"
                              ? "warning"
                              : "default"
                          }
                          className="text-[10px]"
                        >
                          {item.review_workflow_status}
                        </Badge>
                      </td>
                      <td className="py-3 px-3 text-muted-foreground text-[11px]">
                        {item.submitted_at ? new Date(item.submitted_at).toLocaleDateString() : "In Progress"}
                      </td>
                      <td className="py-3 px-3 text-right rtl:text-left">
                        <Link href={`/clinician/review/${item.assessment_id}`}>
                          <Button variant="outline" size="sm" className="text-xs h-7 px-2.5 font-semibold">
                            <span>{isAr ? "مراجعة" : "Review"}</span>
                            <ChevronRight className="h-3 w-3 ml-1 rtl:ml-0 rtl:mr-1" />
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="py-12 text-center text-xs text-muted-foreground space-y-2">
              <FileText className="h-8 w-8 text-slate-300 mx-auto" />
              <p>{isAr ? "لا توجد تقييمات مكتملة بانتظار المراجعة حالياً." : "No submitted assessments currently in review queue."}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Direct Session Token Lookup Card */}
      <Card className="border-border shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-bold">
            {isAr ? "البحث المباشر برمز الجلسة (Session Token)" : "Direct Assessment Session Lookup"}
          </CardTitle>
          <CardDescription className="text-xs">
            {isAr
              ? "أدخل رمز الجلسة السري المقدم من المريض لاستعراض التقرير الإكلينيكي في وضع التدقيق الطبي."
              : "Enter the confidential session token provided by the patient to inspect their immutable report in clinical audit mode."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-3">
            <Input
              type="text"
              placeholder="e.g., gst_xxxx or uuid..."
              value={lookupToken}
              onChange={(e) => setLookupToken(e.target.value)}
              className="font-mono text-xs flex-1"
            />
            <Link href={lookupToken ? `/assessment/report/${lookupToken}` : "#"}>
              <Button variant="clinical" size="sm" disabled={!lookupToken} className="w-full sm:w-auto text-xs font-semibold">
                <Search className="h-3.5 w-3.5 mr-1.5 rtl:mr-0 rtl:ml-1.5" />
                {isAr ? "فتح التقرير الإكلينيكي" : "Inspect Clinical Report"}
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>

      {/* Clinical Protocols Section */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-slate-900 dark:text-white">
          {isAr ? "بروتوكولات الفرز الإكلينيكي السريعة (EAU / AUA)" : "Clinical Triage & Escalation Protocols (EAU / AUA)"}
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {clinicalProtocols.map((proto, idx) => (
            <Card key={idx} className="border-border flex flex-col justify-between">
              <CardHeader className="pb-3 space-y-2">
                <div className="flex items-center justify-between">
                  <Badge variant={proto.tierColor} className="text-[10px]">
                    {proto.tier}
                  </Badge>
                  <span className="text-[10px] font-mono text-slate-500">{proto.window}</span>
                </div>
                <CardTitle className="text-sm font-bold leading-snug">
                  {isAr ? proto.title_ar : proto.title_en}
                </CardTitle>
              </CardHeader>

              <CardContent className="space-y-3 text-xs">
                <p className="text-muted-foreground leading-relaxed">
                  {isAr ? proto.notes_ar : proto.notes_en}
                </p>
                <div className="p-2 bg-slate-50 dark:bg-slate-900 rounded border border-border text-[11px] text-teal-800 dark:text-teal-300 font-medium">
                  {proto.guideline}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
