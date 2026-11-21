"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useLanguage } from "@/context/LanguageContext";
import { ApiClient, AssessmentReport, NavigationRecommendationResponse } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { UrgentAlertBanner } from "@/components/urgent-alert-banner";
import {
  FileText,
  Printer,
  ShieldCheck,
  AlertTriangle,
  CheckCircle,
  ExternalLink,
  ArrowLeft,
  Calendar,
  Lock,
  Stethoscope,
  Info,
  Download,
  MapPin,
  Building2,
  Phone,
  CheckCircle2,
} from "lucide-react";

export default function AssessmentReportPage() {
  const { token } = useParams<{ token: string }>();
  const { t, language } = useLanguage();
  const router = useRouter();

  const [report, setReport] = useState<AssessmentReport | null>(null);
  const [navigationRecs, setNavigationRecs] = useState<NavigationRecommendationResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);

  useEffect(() => {
    async function loadReport() {
      if (!token) return;
      setIsLoading(true);
      setError(null);
      setErrorCode(null);
      try {
        const res = await ApiClient.getReport(token);
        setReport(res);
        if (typeof window !== "undefined" && window.location.search.includes("print=true")) {
          setTimeout(() => window.print(), 800);
        }
        // Load clinical navigation facilities matching report
        try {
          const navRes = await ApiClient.getNavigationRecommendations(token);
          setNavigationRecs(navRes);
        } catch {
          // Navigation recommendation failure is non-fatal to report display
        }
      } catch (err: any) {
        // If report not finalized yet, attempt evaluate
        try {
          const evalRes = await ApiClient.evaluateAssessment(token);
          setReport(evalRes);
          try {
            const navRes = await ApiClient.getNavigationRecommendations(token);
            setNavigationRecs(navRes);
          } catch {
            // Ignore non-fatal
          }
        } catch (evalErr: any) {
          const code = evalErr.code || err.code || null;
          setErrorCode(code);
          setError(evalErr.message || err.message || "Assessment report could not be located");
        }
      } finally {
        setIsLoading(false);
      }
    }
    loadReport();
  }, [token]);

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-20 text-center space-y-3">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-teal-700 border-r-transparent" />
        <p className="text-sm text-muted-foreground">
          {language === "ar" ? "جاري تجميع تقرير الأدلة الإكلينيكية الموثقة..." : "Compiling evidence-linked clinical assessment report..."}
        </p>
      </div>
    );
  }

  // Stage 6 & Stage 7: Governance Withholding Display
  if (errorCode === "CLINICAL_RELEASE_WITHHELD") {
    return (
      <div className="container mx-auto px-4 py-16 max-w-lg text-center space-y-4">
        <div className="p-3 bg-amber-100 dark:bg-amber-950/40 rounded-full w-14 h-14 mx-auto flex items-center justify-center">
          <Lock className="h-7 w-7 text-amber-600 dark:text-amber-400" />
        </div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          {language === "ar" ? "تم حجب التقرير السريري" : "Clinical Report Release Withheld"}
        </h2>
        <div className="text-xs text-muted-foreground leading-relaxed p-4 bg-slate-50 dark:bg-slate-900 rounded-lg border border-border text-left rtl:text-right space-y-2">
          <p className="font-semibold text-slate-800 dark:text-slate-200">
            {language === "ar"
              ? "إشعار الحوكمة السريرية وسلامة المرضى:"
              : "Clinical Governance & Safety Notice:"}
          </p>
          <p>
            {language === "ar"
              ? "يتم حجب نتائج هذا التقييم مؤقتاً عن العرض للمرضى نظراً لأن القواعد الإكلينيكية المستخدمة في التقييم لا تزال قيد المراجعة والاعتماد الطبي من قبل استشاريين مرخصين. في إطار معايير السلامة السريرية، يقتصر الاطلاع على هذه النتائج على الأطباء المصرح لهم في وضع التدقيق السريري."
              : "This assessment was processed using clinical rules that are currently undergoing formal medical review by licensed clinicians. In accordance with clinical governance standards, patient-facing report presentation is withheld pending qualified clinician sign-off. Access is restricted to authorized clinicians and administrators in clinical audit mode."}
          </p>
        </div>
        <Link href="/assessment">
          <Button variant="outline" size="sm">
            {language === "ar" ? "العودة للرئيسية" : "Return to Home"}
          </Button>
        </Link>
      </div>
    );
  }

  if (errorCode === "INCOMPLETE_EVALUATION_WITHHELD") {
    return (
      <div className="container mx-auto px-4 py-16 max-w-lg text-center space-y-4">
        <div className="p-3 bg-amber-100 dark:bg-amber-950/40 rounded-full w-14 h-14 mx-auto flex items-center justify-center">
          <AlertTriangle className="h-7 w-7 text-amber-600 dark:text-amber-400" />
        </div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          {language === "ar" ? "تقييم غير مكتمل محجوب" : "Incomplete Evaluation Withheld"}
        </h2>
        <div className="text-xs text-muted-foreground leading-relaxed p-4 bg-amber-50/50 dark:bg-amber-950/20 rounded-lg border border-amber-200 dark:border-amber-900 text-left rtl:text-right space-y-2">
          <p className="font-semibold text-amber-900 dark:text-amber-200">
            {language === "ar"
              ? "تنبيه الحوكمة السريرية للاستبيانات غير المكتملة:"
              : "Clinical Notice: Incomplete Assessment Evidence:"}
          </p>
          <p>
            {language === "ar"
              ? "التقييم غير مكتمل بسبب وجود أسئلة تم تسجيلها كـ 'غير متأكد' أو تم تفضيل عدم الإجابة عليها أو تركت دون إجابة. يتم حجب تقرير النتيجة لمنع إعطاء طمأنينة خاطئة بالخصوبة الطبيعية. يوصى بمراجعة طبيب مختص مباشرة."
              : "Assessment evaluation is incomplete due to unsure, declined, or unanswered questions. Report release is withheld to prevent misleading reassurance of confirmed absence of risk or normal fertility. An in-person physician consultation is recommended."}
          </p>
        </div>
        <Link href="/assessment">
          <Button variant="clinical" size="sm">
            {language === "ar" ? "إعادة التقييم" : "Start New Assessment"}
          </Button>
        </Link>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="container mx-auto px-4 py-16 max-w-lg text-center space-y-4">
        <AlertTriangle className="h-10 w-10 text-amber-500 mx-auto" />
        <h2 className="text-xl font-bold">Report Not Found</h2>
        <p className="text-xs text-muted-foreground">{error || "Could not retrieve assessment record."}</p>
        <Link href="/assessment">
          <Button variant="clinical" size="sm">Start New Assessment</Button>
        </Link>
      </div>
    );
  }

  const isTier4 = report.overall_tier === "URGENT_MEDICAL_ASSESSMENT";
  const isTier3 = report.overall_tier === "SPECIALIST_EVALUATION_RECOMMENDED";
  const isTier2 = report.overall_tier === "LIFESTYLE_MODIFIABLE_FACTORS";
  const isTier1 = report.overall_tier === "ROUTINE_PREVENTIVE_CARE";
  const isIncomplete = report.is_evaluation_incomplete || report.evaluation_completeness === "INDETERMINATE";

  const tierBadgeVariant = isTier4 ? "urgent" : isTier3 ? "warning" : isTier2 ? "success" : "default";

  return (
    <div className="container mx-auto px-4 sm:px-6 py-10 max-w-4xl space-y-8 print:py-0 print:px-0">
      {/* Action Header */}
      <div className="flex items-center justify-between print:hidden">
        <Link href="/dashboard" className="text-xs text-muted-foreground hover:text-teal-700 flex items-center space-x-1.5 rtl:space-x-reverse">
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>{language === "ar" ? "العودة للوحة التحكم" : "Back to Dashboard"}</span>
        </Link>
        <div className="flex items-center space-x-2 rtl:space-x-reverse">
          <a
            href={ApiClient.getReportPdfDownloadUrl(token)}
            download
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button
              variant="outline"
              size="sm"
              className="flex items-center space-x-1.5 rtl:space-x-reverse text-xs"
            >
              <Download className="h-3.5 w-3.5" />
              <span>{language === "ar" ? "تحميل التقرير (PDF)" : "Download PDF"}</span>
            </Button>
          </a>
          <Button
            variant="outline"
            size="sm"
            onClick={() => window.print()}
            className="flex items-center space-x-1.5 rtl:space-x-reverse text-xs"
          >
            <Printer className="h-3.5 w-3.5" />
            <span>{t("report.print")}</span>
          </Button>
          <Link href="/navigation">
            <Button variant="outline" size="sm" className="text-xs font-semibold">
              {language === "ar" ? "دليل العيادات" : "Clinics Directory"}
            </Button>
          </Link>
          <Link href="/assessment">
            <Button variant="clinical" size="sm" className="text-xs font-semibold">
              {language === "ar" ? "تقييم جديد" : "New Assessment"}
            </Button>
          </Link>
        </div>
      </div>

      {/* Urgent Safety Banner if Tier 4 */}
      {isTier4 && (
        <UrgentAlertBanner
          type={report.urgent_guidance?.includes("pain") ? "acute_pain" : "testis_lump"}
          referralGuidance={report.urgent_guidance}
        />
      )}

      {/* Main Report Card */}
      <Card className="border-border shadow-md print:shadow-none print:border-none">
        <CardHeader className="border-b border-border/60 pb-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center space-x-2 rtl:space-x-reverse">
                <FileText className="h-5 w-5 text-teal-700" />
                <CardTitle className="text-2xl text-slate-900 dark:text-white">
                  {t("report.title")}
                </CardTitle>
              </div>
              <p className="text-xs text-muted-foreground flex items-center space-x-3 rtl:space-x-reverse">
                <span className="flex items-center space-x-1 rtl:space-x-reverse">
                  <Calendar className="h-3 w-3 text-slate-400" />
                  <span>{new Date(report.created_at || Date.now()).toLocaleDateString()}</span>
                </span>
                <span className="font-mono text-[11px] text-slate-500">
                  Ref: {report.report_reference || "GNX-RPT-CONFIDENTIAL"}
                </span>
              </p>
            </div>

            {/* Overall Tier Pill */}
            <div className="sm:text-right rtl:sm:text-left">
              <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider block mb-1">
                {t("report.overall_tier")}
              </span>
              <Badge variant={tierBadgeVariant} className="text-xs px-3 py-1 font-bold">
                {isTier4 && t("report.tier.4")}
                {isTier3 && t("report.tier.3")}
                {isTier2 && t("report.tier.2")}
                {isTier1 && t("report.tier.1")}
              </Badge>
            </div>
          </div>
        </CardHeader>

        <CardContent className="pt-6 space-y-8">
          {/* Clinical Non-Diagnostic Summary */}
          <div className="p-4 rounded-xl border border-teal-200 dark:border-teal-900 bg-teal-50/50 dark:bg-teal-950/20 space-y-2">
            <h4 className="text-sm font-bold text-teal-900 dark:text-teal-200 flex items-center space-x-1.5 rtl:space-x-reverse">
              <Stethoscope className="h-4 w-4 text-teal-700" />
              <span>{language === "ar" ? "الملخص السريري والتوجيه الطبي" : "Clinical Summary & Specialist Referral Direction"}</span>
            </h4>
            <p className="text-xs text-teal-950 dark:text-teal-100 leading-relaxed font-medium">
              {language === "ar" ? report.non_diagnostic_summary_ar : report.non_diagnostic_summary_en}
            </p>
          </div>

          {/* Identified Risk Factors Breakdown */}
          <div className="space-y-4">
            <h4 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider text-xs border-b border-border pb-2">
              {t("report.risk_factors")} ({report.identified_risk_factors?.length || 0})
            </h4>

            {report.identified_risk_factors && report.identified_risk_factors.length > 0 ? (
              <div className="space-y-3">
                {report.identified_risk_factors.map((rf, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col sm:flex-row sm:items-start justify-between gap-3"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2 rtl:space-x-reverse">
                        <span className="font-semibold text-xs text-slate-900 dark:text-slate-100">
                          {rf.rule_name}
                        </span>
                        <span className="text-[10px] font-mono text-slate-400 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">
                          {rf.rule_code}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {rf.referral_guidance}
                      </p>
                    </div>

                    <div className="sm:text-right rtl:sm:text-left flex-shrink-0">
                      <Badge variant="outline" className="text-[10px]">
                        Priority {rf.priority}
                      </Badge>
                      <div className="text-[10px] text-teal-700 dark:text-teal-400 font-medium mt-1">
                        {rf.evidence_source}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : isIncomplete ? (
              /* STAGE 7: Incomplete Evaluation Amber Warning Contract */
              <div className="p-4 rounded-lg border border-amber-300 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 text-amber-950 dark:text-amber-100 text-xs space-y-2">
                <div className="flex items-center space-x-2 rtl:space-x-reverse font-bold text-amber-900 dark:text-amber-200">
                  <AlertTriangle className="h-4 w-4 text-amber-600 flex-shrink-0" />
                  <span>{language === "ar" ? "تنبيه تحذيري: تقييم مخاطر غير مكتمل" : "Amber Advisory: Incomplete Risk Evaluation"}</span>
                </div>
                <p className="leading-relaxed">
                  {language === "ar"
                    ? "لم يتم تسجيل عوامل خطورة واضحة من بين الأسئلة التي تم الجواب عليها. ومع ذلك، تم تسجيل إجابة واحدة أو أكثر كـ 'غير متأكد'، أو تفضيل عدم الإجابة، أو تركت دون إجابة. نظراً لعدم اكتمال الإجابات، فإن هذا التقييم لا يمكنه تأكيد غياب عوامل الخطورة أو الخصوبة الطبيعية. يوصى بمراجعة طبيب مختص واستكمال الفحص السريري المخبري."
                    : "No affirmative risk factors were identified among the questions answered. However, one or more questions were marked as Unsure, declined, or unanswered. Because these factors could not be evaluated, this assessment is INCOMPLETE and CANNOT confirm the absence of risk factors or normal fertility. An in-person clinical consultation and laboratory semen analysis are recommended."}
                </p>
              </div>
            ) : (
              /* Standard Determinate Tier 1 Card */
              <div className="p-4 rounded-lg border border-emerald-200 bg-emerald-50/50 text-emerald-900 text-xs flex items-center space-x-2 rtl:space-x-reverse">
                <CheckCircle className="h-4 w-4 text-emerald-600 flex-shrink-0" />
                <span>
                  {language === "ar"
                    ? "لم يتم تحديد أي عوامل خطر سريرية في الاستبيان. يوصى بمتابعة الرعاية الوقائية الدورية (الاستبيان لا يغني عن الفحص الطبي المخبري عند التخطيط للإنجاب)."
                    : "No high-risk clinical factors identified. Routine preventive health optimization is recommended. Note: An absence of reported risk factors does not guarantee normal fertility or substitute for physician evaluation."}
                </span>
              </div>
            )}
          </div>

          {/* Evidence Guideline Citations */}
          {report.evidence_citations && report.evidence_citations.length > 0 && (
            <div className="space-y-3 pt-4 border-t border-border">
              <h4 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                {t("report.citations")}
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                {report.evidence_citations.map((cite, idx) => (
                  <div key={idx} className="p-3 bg-slate-50 dark:bg-slate-900/60 rounded-md border border-border space-y-1">
                    <div className="font-semibold text-teal-800 dark:text-teal-300">
                      {cite.guideline} ({cite.year}) - {cite.section}
                    </div>
                    <p className="text-[11px] text-muted-foreground leading-relaxed">
                      {cite.recommendation}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Clinical Navigation & Recommended Healthcare Facilities (Phase 12) */}
          {navigationRecs && (navigationRecs.recommended_facilities.length > 0 || navigationRecs.emergency_facilities.length > 0) && (
            <div className="space-y-4 pt-6 border-t border-border">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="space-y-1">
                  <h4 className="text-sm font-bold text-slate-900 dark:text-white flex items-center space-x-2 rtl:space-x-reverse">
                    <Building2 className="h-4 w-4 text-teal-700" />
                    <span>
                      {language === "ar" ? "التوجيه الإكلينيكي والمنشآت الصحية الموصى بها في الإمارات" : "Clinical Navigation & Specialized UAE Healthcare Facilities"}
                    </span>
                  </h4>
                  <p className="text-xs text-muted-foreground">
                    {language === "ar"
                      ? "مراكز طبية ومستشفيات مرخصة تضم استشاريين في طب الذكورة والإنجاب بناءً على نتائج التقييم."
                      : "Licensed centers and tertiary hospitals offering relevant andrology and reproductive specialties."}
                  </p>
                </div>
                <Link href="/navigation">
                  <Button variant="outline" size="sm" className="text-xs">
                    {language === "ar" ? "عرض كامل الدليل" : "Browse All Facilities"}
                  </Button>
                </Link>
              </div>

              {/* Navigation Notice Box */}
              <div className="p-3 bg-teal-50/60 dark:bg-teal-950/20 border border-teal-200 dark:border-teal-900/40 rounded-lg text-xs text-teal-950 dark:text-teal-200">
                <p className="leading-relaxed">
                  {language === "ar" ? navigationRecs.navigation_notice_ar : navigationRecs.navigation_notice_en}
                </p>
              </div>

              {/* Facilities Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {(isTier4 ? navigationRecs.emergency_facilities : navigationRecs.recommended_facilities).slice(0, 4).map((f) => (
                  <div key={f.id} className="p-4 bg-white dark:bg-slate-900 rounded-lg border border-border space-y-2.5 hover:border-teal-600 transition-colors">
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-1">
                        <h5 className="font-semibold text-xs text-slate-900 dark:text-white">
                          {language === "ar" ? f.name_ar : f.name_en}
                        </h5>
                        <p className="text-[11px] text-muted-foreground flex items-center space-x-1 rtl:space-x-reverse">
                          <MapPin className="h-3 w-3 text-slate-400" />
                          <span>{language === "ar" ? f.city_ar : f.city_en}, {f.emirate.replace(/_/g, " ")}</span>
                        </p>
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        {f.has_24_7_emergency && (
                          <Badge variant="destructive" className="text-[10px] font-bold">
                            24/7 ER
                          </Badge>
                        )}
                        {f.is_verified && (
                          <span className="text-[10px] text-teal-700 dark:text-teal-400 flex items-center space-x-0.5 font-medium">
                            <CheckCircle2 className="h-3 w-3" />
                            <span>Verified</span>
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-1 text-[10px]">
                      {(f.offered_specialties || []).slice(0, 3).map((spec, i) => (
                        <span key={i} className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded">
                          {spec}
                        </span>
                      ))}
                    </div>

                    <div className="pt-2 border-t border-border/60 flex items-center justify-between text-xs">
                      <a href={`tel:${f.phone_number}`} className="text-teal-700 hover:underline flex items-center space-x-1 rtl:space-x-reverse">
                        <Phone className="h-3 w-3" />
                        <span>{f.phone_number}</span>
                      </a>
                      {f.booking_url && (
                        <a href={f.booking_url} target="_blank" rel="noopener noreferrer" className="text-xs text-teal-700 font-semibold hover:underline flex items-center space-x-1 rtl:space-x-reverse">
                          <span>{language === "ar" ? "حجز موعد" : "Book Appointment"}</span>
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Mandatory Safety & Disclaimers */}
          <div className="p-4 bg-slate-100 dark:bg-slate-900 rounded-lg text-[11px] text-muted-foreground leading-relaxed space-y-1 border border-border">
            <div className="font-semibold text-slate-800 dark:text-slate-200 flex items-center space-x-1.5 rtl:space-x-reverse">
              <Info className="h-3.5 w-3.5 text-teal-700" />
              <span>Clinical Decision Support Disclaimer</span>
            </div>
            <p>
              This report is compiled deterministically based on patient-provided assessment responses and codified clinical guidelines (EAU, AUA/ASRM, WHO 6th ed). It is not a definitive diagnosis and does not substitute for an in-person physical examination, scrotal ultrasound, or laboratory semen analysis performed by a qualified urologist or andrologist.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
