"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useLanguage } from "@/context/LanguageContext";
import { useAuth } from "@/context/AuthContext";
import {
  ApiClient,
  AssessmentHistoryItem,
  AssessmentComparisonResponse,
  ReportShareResponse,
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  History,
  FileText,
  ArrowLeft,
  ExternalLink,
  Calendar,
  Download,
  AlertTriangle,
  Clock,
  ShieldCheck,
  CheckCircle2,
  Printer,
  Share2,
  GitCompare,
  X,
  Copy,
  Info,
  Lock,
} from "lucide-react";

export default function AssessmentHistoryPage() {
  const { language } = useLanguage();
  const { guestSessionToken, user } = useAuth();
  const [historyItems, setHistoryItems] = useState<AssessmentHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Comparison State
  const [compareBaseItem, setCompareBaseItem] = useState<AssessmentHistoryItem | null>(null);
  const [compareTargetItem, setCompareTargetItem] = useState<AssessmentHistoryItem | null>(null);
  const [comparisonResult, setComparisonResult] = useState<AssessmentComparisonResponse | null>(null);
  const [isComparing, setIsComparing] = useState<boolean>(false);
  const [compareError, setCompareError] = useState<string | null>(null);

  // Share Dialog State
  const [shareItem, setShareItem] = useState<AssessmentHistoryItem | null>(null);
  const [clinicianEmail, setClinicianEmail] = useState<string>("");
  const [expiresInDays, setExpiresInDays] = useState<number>(7);
  const [shareResult, setShareResult] = useState<ReportShareResponse | null>(null);
  const [isSharing, setIsSharing] = useState<boolean>(false);
  const [copiedLink, setCopiedLink] = useState<boolean>(false);
  const [shareError, setShareError] = useState<string | null>(null);

  // Details Modal State
  const [selectedDetailsItem, setSelectedDetailsItem] = useState<AssessmentHistoryItem | null>(null);

  useEffect(() => {
    async function loadHistory() {
      setIsLoading(true);
      setError(null);
      try {
        if (user) {
          const res = await ApiClient.getAssessmentHistory(50, 0);
          setHistoryItems(res.items);
        } else if (guestSessionToken) {
          setHistoryItems([
            {
              assessment_id: "guest-current",
              session_token: guestSessionToken,
              status: "REVIEW_READY",
              started_at: new Date().toISOString(),
              questionnaire_version_tag: "v1.0.0-published",
              rule_engine_version: "v1.0.0",
              is_urgent_red_flag: false,
            },
          ]);
        } else {
          setHistoryItems([]);
        }
      } catch (err: any) {
        setError(err.message || "Failed to load clinical assessment history");
      } finally {
        setIsLoading(false);
      }
    }
    loadHistory();
  }, [user, guestSessionToken]);

  // Handle Trigger Comparison
  const handleRunComparison = async (baseId: string, targetId: string) => {
    setIsComparing(true);
    setCompareError(null);
    try {
      const res = await ApiClient.compareAssessments(baseId, targetId);
      setComparisonResult(res);
    } catch (err: any) {
      setCompareError(err.message || "Failed to compare historical assessments");
    } finally {
      setIsComparing(false);
    }
  };

  // Handle Share Submission
  const handleGenerateShareToken = async () => {
    if (!shareItem || !shareItem.report_reference) return;
    setIsSharing(true);
    setShareError(null);
    try {
      const res = await ApiClient.shareReport(shareItem.report_reference, {
        clinician_email: clinicianEmail || undefined,
        expires_in_days: expiresInDays,
      });
      setShareResult(res);
    } catch (err: any) {
      setShareError(err.message || "Failed to generate secure share link");
    } finally {
      setIsSharing(false);
    }
  };

  const handleRevokeShare = async (reportRef: string, shareToken?: string) => {
    try {
      await ApiClient.revokeReportShare(reportRef, shareToken);
      setShareResult(null);
      alert(language === "ar" ? "تم إلغاء صلاحية الرابط بنجاح" : "Share access revoked successfully");
    } catch (err: any) {
      alert(err.message || "Failed to revoke share token");
    }
  };

  const handleCopyShareLink = (url: string) => {
    const fullUrl = window.location.origin + url;
    navigator.clipboard.writeText(fullUrl);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 3000);
  };

  const handlePrint = (sessionToken: string) => {
    window.open(`/assessment/report/${sessionToken}?print=true`, "_blank");
  };

  return (
    <div className="container mx-auto px-4 sm:px-6 py-10 max-w-4xl space-y-6">
      {/* Header Navigation */}
      <div className="flex items-center justify-between">
        <Link
          href="/dashboard"
          className="text-xs text-muted-foreground hover:text-teal-700 flex items-center space-x-1.5 rtl:space-x-reverse"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>{language === "ar" ? "العودة للوحة التحكم" : "Back to Dashboard"}</span>
        </Link>
        <div className="flex items-center space-x-2 rtl:space-x-reverse">
          <Link href="/verify">
            <Button variant="outline" size="sm" className="text-xs font-medium">
              <ShieldCheck className="h-3.5 w-3.5 mr-1 rtl:mr-0 rtl:ml-1 text-teal-600" />
              <span>{language === "ar" ? "التحقق من تقرير" : "Verify Report"}</span>
            </Button>
          </Link>
          <Link href="/assessment">
            <Button variant="clinical" size="sm" className="text-xs font-semibold">
              {language === "ar" ? "بدء تقييم جديد" : "New Assessment"}
            </Button>
          </Link>
        </div>
      </div>

      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center space-x-2 rtl:space-x-reverse">
          <History className="h-6 w-6 text-teal-700" />
          <span>{language === "ar" ? "سجل التقييمات الإكلينيكية" : "Clinical Assessment History"}</span>
        </h1>
        <p className="text-xs text-muted-foreground">
          {language === "ar"
            ? "جميع التقييمات مؤمنة بلقطات غير قابلة للتغيير ومقيدة بإصدارات القواعد المعتمدة."
            : "Immutable, reproducible clinical snapshots pinned to exact guideline rule versions."}
        </p>
      </div>

      {/* Comparison Drawer / Active Compare Selection */}
      {compareBaseItem && (
        <Card className="border-teal-300 bg-teal-50/40 dark:bg-teal-950/20">
          <CardContent className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 rtl:space-x-reverse text-xs font-semibold text-teal-900 dark:text-teal-200">
                <GitCompare className="h-4 w-4 text-teal-700" />
                <span>
                  {language === "ar" ? "مقارنة التقييمات التاريخية" : "Compare Historical Assessments"}
                </span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
                onClick={() => {
                  setCompareBaseItem(null);
                  setCompareTargetItem(null);
                  setComparisonResult(null);
                }}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>

            <p className="text-xs text-muted-foreground">
              {language === "ar"
                ? `التقييم الأساسي: ${compareBaseItem.report_reference || compareBaseItem.assessment_id.substring(0, 10)}. حدد تقييماً آخر للمقارنة:`
                : `Base: ${compareBaseItem.report_reference || compareBaseItem.assessment_id.substring(0, 10)}. Select a second assessment below to compare:`}
            </p>

            <div className="flex flex-wrap gap-2">
              {historyItems
                .filter((item) => item.assessment_id !== compareBaseItem.assessment_id)
                .map((item) => (
                  <Button
                    key={item.assessment_id}
                    variant={compareTargetItem?.assessment_id === item.assessment_id ? "clinical" : "outline"}
                    size="sm"
                    className="text-xs"
                    onClick={() => {
                      setCompareTargetItem(item);
                      handleRunComparison(compareBaseItem.assessment_id, item.assessment_id);
                    }}
                  >
                    <span>
                      {item.submitted_at ? new Date(item.submitted_at).toLocaleDateString() : "Recent"} (
                      {item.outcome_title_en || item.outcome_tier || "Assessment"})
                    </span>
                  </Button>
                ))}
            </div>

            {isComparing && (
              <div className="py-4 text-center text-xs text-muted-foreground">
                <div className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-teal-700 border-r-transparent mr-2" />
                <span>{language === "ar" ? "جاري إجراء المقارنة الإكلينيكية..." : "Computing clinical comparison..."}</span>
              </div>
            )}

            {compareError && (
              <div className="text-xs text-red-600 bg-red-50 p-2 rounded">{compareError}</div>
            )}

            {comparisonResult && (
              <div className="mt-4 pt-3 border-t border-teal-200 dark:border-teal-800 space-y-3 text-xs">
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-2.5 bg-white dark:bg-slate-900 rounded border border-border">
                    <span className="font-semibold block text-slate-700 dark:text-slate-300 mb-1">
                      {language === "ar" ? "التقييم الأساسي" : "Base Assessment"}
                    </span>
                    <div>{comparisonResult.base_report_reference}</div>
                    <Badge variant="outline" className="mt-1 text-[10px]">
                      {comparisonResult.base_outcome_tier}
                    </Badge>
                  </div>
                  <div className="p-2.5 bg-white dark:bg-slate-900 rounded border border-border">
                    <span className="font-semibold block text-slate-700 dark:text-slate-300 mb-1">
                      {language === "ar" ? "التقييم المقارن" : "Target Assessment"}
                    </span>
                    <div>{comparisonResult.target_report_reference}</div>
                    <Badge variant="outline" className="mt-1 text-[10px]">
                      {comparisonResult.target_outcome_tier}
                    </Badge>
                  </div>
                </div>

                {/* Risk Factors Differential */}
                <div className="space-y-1.5">
                  <span className="font-semibold text-slate-800 dark:text-slate-200 block">
                    {language === "ar" ? "الفروقات في عوامل الخطر المسجلة:" : "Risk Factors Differential:"}
                  </span>
                  {comparisonResult.new_risk_factors.length > 0 && (
                    <div className="text-amber-700 dark:text-amber-400">
                      • {language === "ar" ? "عوامل خطر جديدة تم الإبلاغ عنها:" : "Newly Reported Risk Factors:"}{" "}
                      {comparisonResult.new_risk_factors.map((f: any) => f.title_en || f.factor_code).join(", ")}
                    </div>
                  )}
                  {comparisonResult.resolved_risk_factors.length > 0 && (
                    <div className="text-teal-700 dark:text-teal-400">
                      • {language === "ar" ? "عوامل خطر لم تعد مسجلة:" : "Factors No Longer Reported:"}{" "}
                      {comparisonResult.resolved_risk_factors.map((f: any) => f.title_en || f.factor_code).join(", ")}
                    </div>
                  )}
                  {comparisonResult.persisting_risk_factors.length > 0 && (
                    <div className="text-slate-600 dark:text-slate-400">
                      • {language === "ar" ? "عوامل خطر مستمرة:" : "Persisting Factors:"}{" "}
                      {comparisonResult.persisting_risk_factors.map((f: any) => f.title_en || f.factor_code).join(", ")}
                    </div>
                  )}
                  {comparisonResult.new_risk_factors.length === 0 &&
                    comparisonResult.resolved_risk_factors.length === 0 && (
                      <div className="text-muted-foreground text-[11px]">
                        {language === "ar" ? "لا توجد فروقات في عوامل الخطر المبلغ عنها." : "No changes in reported risk factors."}
                      </div>
                    )}
                </div>

                {/* Mandatory Non-Diagnostic Comparison Notice */}
                <div className="bg-amber-100/60 dark:bg-amber-950/40 p-2.5 rounded text-[11px] text-amber-900 dark:text-amber-300">
                  <span className="font-bold block mb-0.5">
                    {language === "ar" ? "تنبيه إكلينيكي غير تشخيصي:" : "Non-Diagnostic Comparison Notice:"}
                  </span>
                  {language === "ar" ? comparisonResult.disclaimer_ar : comparisonResult.disclaimer_en}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Share Dialog / Modal */}
      {shareItem && (
        <Card className="border-border shadow-md">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-bold flex items-center space-x-2 rtl:space-x-reverse">
                <Share2 className="h-4 w-4 text-teal-700" />
                <span>{language === "ar" ? "مشاركة التقرير مع الطبيب" : "Share Report with Clinician"}</span>
              </CardTitle>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
                onClick={() => {
                  setShareItem(null);
                  setShareResult(null);
                  setClinicianEmail("");
                }}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
            <CardDescription className="text-xs">
              {language === "ar"
                ? `إنشاء رابط مؤقت ومشفّر لمشاركة التقرير المرجعي (${shareItem.report_reference}) مع طبيبك المعالج.`
                : `Generate a secure, expiring link to share report (${shareItem.report_reference}) with your authorized clinician.`}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-0 text-xs">
            {!shareResult ? (
              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="font-semibold text-slate-800 dark:text-slate-200">
                    {language === "ar" ? "البريد الإلكتروني للطبيب (اختياري)" : "Clinician Email (Optional)"}
                  </label>
                  <Input
                    placeholder="doctor@clinic.ae"
                    type="email"
                    value={clinicianEmail}
                    onChange={(e) => setClinicianEmail(e.target.value)}
                    className="text-xs"
                  />
                </div>

                <div className="space-y-1">
                  <label className="font-semibold text-slate-800 dark:text-slate-200">
                    {language === "ar" ? "مدة صلاحية الرابط" : "Link Expiration"}
                  </label>
                  <select
                    value={expiresInDays}
                    onChange={(e) => setExpiresInDays(Number(e.target.value))}
                    className="w-full text-xs rounded border border-border bg-background p-2"
                  >
                    <option value={1}>{language === "ar" ? "يوم واحد (24 ساعة)" : "1 Day (24 Hours)"}</option>
                    <option value={7}>{language === "ar" ? "7 أيام (موصى به)" : "7 Days (Recommended)"}</option>
                    <option value={14}>{language === "ar" ? "14 يوماً" : "14 Days"}</option>
                    <option value={30}>{language === "ar" ? "30 يوماً" : "30 Days"}</option>
                  </select>
                </div>

                <div className="p-2.5 bg-slate-50 dark:bg-slate-900 border border-border rounded text-[11px] text-muted-foreground flex items-start space-x-2 rtl:space-x-reverse">
                  <Info className="h-4 w-4 shrink-0 text-teal-700 mt-0.5" />
                  <span>
                    {language === "ar"
                      ? "إقرار المريض: بالضغط على إنشاء الرابط، أوافق صراحة على مشاركة هذا التقرير الاسترشادي مع الطبيب المحدد. يمكنني إلغاء الصلاحية في أي وقت."
                      : "Patient Consent: By generating this link, you explicitly consent to sharing this informational report with your designated clinician. You can revoke access at any time."}
                  </span>
                </div>

                {shareError && <div className="text-red-600">{shareError}</div>}

                <Button
                  variant="clinical"
                  size="sm"
                  onClick={handleGenerateShareToken}
                  disabled={isSharing}
                  className="w-full text-xs font-semibold"
                >
                  {isSharing
                    ? language === "ar"
                      ? "جاري التشفير وإنشاء الرابط..."
                      : "Generating Secure Link..."
                    : language === "ar"
                    ? "إنشاء رابط المشاركة المؤقت"
                    : "Generate Secure Share Link"}
                </Button>
              </div>
            ) : (
              <div className="space-y-3 bg-teal-50/50 dark:bg-teal-950/20 p-3 rounded border border-teal-200">
                <div className="flex items-center space-x-1.5 rtl:space-x-reverse text-teal-800 dark:text-teal-300 font-semibold">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>{shareResult.message_en}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Input
                    readOnly
                    value={window.location.origin + shareResult.share_url}
                    className="text-xs font-mono bg-white dark:bg-slate-900"
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleCopyShareLink(shareResult.share_url)}
                    className="shrink-0 text-xs"
                  >
                    <Copy className="h-3.5 w-3.5 mr-1 rtl:mr-0 rtl:ml-1" />
                    <span>{copiedLink ? (language === "ar" ? "تم النسخ!" : "Copied!") : language === "ar" ? "نسخ" : "Copy"}</span>
                  </Button>
                </div>
                <div className="flex justify-between items-center text-[11px] text-muted-foreground pt-1">
                  <span>
                    {language === "ar" ? "ينتهي في:" : "Expires at:"}{" "}
                    {new Date(shareResult.expires_at).toLocaleDateString()}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-red-600 hover:text-red-700 h-6 text-xs p-0"
                    onClick={() => handleRevokeShare(shareItem.report_reference!, shareResult.share_token)}
                  >
                    {language === "ar" ? "إلغاء الصلاحية فوراً" : "Revoke Access Now"}
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="py-16 text-center space-y-3">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-teal-700 border-r-transparent" />
          <p className="text-xs text-muted-foreground">
            {language === "ar" ? "جاري تحميل سجل التقييمات..." : "Loading assessment history..."}
          </p>
        </div>
      )}

      {/* Error State */}
      {error && !isLoading && (
        <Card className="border-red-200 bg-red-50/40 dark:bg-red-950/20">
          <CardContent className="p-4 flex items-center space-x-3 rtl:space-x-reverse text-red-700 dark:text-red-400 text-xs">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </CardContent>
        </Card>
      )}

      {/* Empty State */}
      {!isLoading && !error && historyItems.length === 0 && (
        <Card className="border-dashed border-border py-16 text-center space-y-4">
          <History className="h-10 w-10 text-muted-foreground mx-auto" />
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
              {language === "ar" ? "لا توجد تقييمات مسجلة حتى الآن" : "No Assessments Found"}
            </h3>
            <p className="text-xs text-muted-foreground max-w-sm mx-auto">
              {language === "ar"
                ? "ابدأ تقييمك الأول لتحديد مؤشرات الخصوبة وصحة الإنجاب بصورة سرية وموثقة."
                : "Complete your first digital reproductive health risk assessment to generate a reproducible clinical snapshot."}
            </p>
          </div>
          <Link href="/assessment">
            <Button variant="clinical" size="sm" className="text-xs">
              {language === "ar" ? "بدء التقييم الآن" : "Start First Assessment"}
            </Button>
          </Link>
        </Card>
      )}

      {/* History Items List */}
      {!isLoading && historyItems.length > 0 && (
        <div className="space-y-4">
          {historyItems.map((item) => {
            const isUrgent = item.is_urgent_red_flag;
            const tierBadge = isUrgent
              ? "destructive"
              : item.outcome_tier?.includes("SPECIALIST") || item.outcome_tier?.includes("CLINICAL")
              ? "warning"
              : item.outcome_tier?.includes("LIFESTYLE")
              ? "success"
              : "outline";

            const downloadUrl = item.report_reference
              ? ApiClient.getReportPdfDownloadByRefUrl(item.report_reference)
              : ApiClient.getReportPdfDownloadUrl(item.session_token);

            return (
              <Card key={item.assessment_id} className="border-border hover:shadow-sm transition-shadow">
                <CardContent className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      {item.outcome_tier ? (
                        <Badge variant={tierBadge as any} className="text-xs font-semibold">
                          {language === "ar" && item.outcome_title_ar
                            ? item.outcome_title_ar
                            : item.outcome_title_en || item.outcome_tier.replace(/_/g, " ")}
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-xs font-semibold">
                          {item.status}
                        </Badge>
                      )}

                      {isUrgent && (
                        <Badge variant="destructive" className="text-[11px] font-bold">
                          {language === "ar" ? "أولوية عاجلة" : "Urgent Red Flag"}
                        </Badge>
                      )}

                      <span className="text-[11px] text-muted-foreground flex items-center space-x-1 rtl:space-x-reverse">
                        <Calendar className="h-3 w-3 text-slate-400" />
                        <span>
                          {item.submitted_at || item.started_at
                            ? new Date(item.submitted_at || item.started_at!).toLocaleDateString()
                            : "Recent"}
                        </span>
                      </span>
                    </div>

                    <div className="text-xs text-muted-foreground font-mono">
                      Ref: {item.report_reference || item.session_token.substring(0, 20) + "..."}
                    </div>

                    <div className="flex items-center space-x-3 rtl:space-x-reverse text-[11px] text-teal-800 dark:text-teal-300">
                      <span>Questionnaire: {item.questionnaire_version_tag || "v1.0.0"}</span>
                      <span>•</span>
                      <span>Rules: {item.rule_engine_version || "v1.0.0"}</span>
                    </div>
                  </div>

                  {/* Actions Bar */}
                  <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
                    {/* View Report */}
                    <Link href={`/assessment/report/${item.session_token}`}>
                      <Button variant="outline" size="sm" className="text-xs flex items-center space-x-1 rtl:space-x-reverse">
                        <FileText className="h-3.5 w-3.5" />
                        <span>{language === "ar" ? "عرض التقرير" : "View Report"}</span>
                        <ExternalLink className="h-3 w-3 ml-0.5 rtl:ml-0 rtl:mr-0.5" />
                      </Button>
                    </Link>

                    {/* Download PDF */}
                    <a href={downloadUrl} download target="_blank" rel="noopener noreferrer">
                      <Button variant="outline" size="sm" className="text-xs flex items-center space-x-1 rtl:space-x-reverse">
                        <Download className="h-3.5 w-3.5" />
                        <span>{language === "ar" ? "PDF" : "PDF"}</span>
                      </Button>
                    </a>

                    {/* Print Report */}
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-xs flex items-center space-x-1 rtl:space-x-reverse"
                      onClick={() => handlePrint(item.session_token)}
                    >
                      <Printer className="h-3.5 w-3.5" />
                      <span>{language === "ar" ? "طباعة" : "Print"}</span>
                    </Button>

                    {/* Share with Clinician */}
                    {item.report_reference && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-xs flex items-center space-x-1 rtl:space-x-reverse text-teal-700 dark:text-teal-400"
                        onClick={() => {
                          setShareItem(item);
                          setShareResult(null);
                        }}
                      >
                        <Share2 className="h-3.5 w-3.5" />
                        <span>{language === "ar" ? "مشاركة" : "Share"}</span>
                      </Button>
                    )}

                    {/* Compare */}
                    {historyItems.length > 1 && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-xs flex items-center space-x-1 rtl:space-x-reverse text-slate-600 hover:text-teal-700"
                        onClick={() => {
                          setCompareBaseItem(item);
                          setCompareTargetItem(null);
                          setComparisonResult(null);
                        }}
                      >
                        <GitCompare className="h-3.5 w-3.5" />
                        <span>{language === "ar" ? "مقارنة" : "Compare"}</span>
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
