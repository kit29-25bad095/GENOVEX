"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { useLanguage } from "@/context/LanguageContext";
import { ApiClient, ReportVerificationResponse } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  ShieldCheck,
  ShieldAlert,
  Search,
  CheckCircle2,
  Calendar,
  Layers,
  FileText,
  AlertTriangle,
  ArrowLeft,
  Lock,
} from "lucide-react";

function VerifyContent() {
  const { language } = useLanguage();
  const searchParams = useSearchParams();
  const initialRef = searchParams.get("ref") || "";

  const [referenceInput, setReferenceInput] = useState<string>(initialRef);
  const [verificationResult, setVerificationResult] = useState<ReportVerificationResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleVerify = async (refToVerify: string) => {
    const trimmed = refToVerify.trim();
    if (!trimmed) return;

    setIsLoading(true);
    setError(null);
    try {
      const res = await ApiClient.verifyReport(trimmed);
      setVerificationResult(res);
    } catch (err: any) {
      setError(err.message || "Failed to verify report reference");
      setVerificationResult(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (initialRef) {
      handleVerify(initialRef);
    }
  }, [initialRef]);

  return (
    <div className="container mx-auto px-4 sm:px-6 py-10 max-w-2xl space-y-6">
      {/* Navigation */}
      <div className="flex items-center justify-between">
        <Link
          href="/"
          className="text-xs text-muted-foreground hover:text-teal-700 flex items-center space-x-1.5 rtl:space-x-reverse"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>{language === "ar" ? "العودة للرئيسية" : "Back to Home"}</span>
        </Link>
        <span className="text-xs text-muted-foreground flex items-center space-x-1 rtl:space-x-reverse">
          <Lock className="h-3 w-3 text-teal-600" />
          <span>{language === "ar" ? "التحقق الموثوق" : "Cryptographic Verification"}</span>
        </span>
      </div>

      {/* Header */}
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center space-x-2 rtl:space-x-reverse">
          <ShieldCheck className="h-6 w-6 text-teal-700" />
          <span>{language === "ar" ? "التحقق من صحة تقرير جينوفيكس" : "Verify Report Authenticity"}</span>
        </h1>
        <p className="text-xs text-muted-foreground">
          {language === "ar"
            ? "تأكيد صحة المرجع الإكلينيكي وتطابق التوقيع الرقمي دون الكشف عن أي بيانات شخصية للمريض."
            : "Cryptographically verify report integrity and rule versions without exposing any patient PHI."}
        </p>
      </div>

      {/* Search Input Box */}
      <Card className="border-border">
        <CardContent className="p-4 space-y-3">
          <label className="text-xs font-semibold text-slate-800 dark:text-slate-200">
            {language === "ar" ? "الرقم المرجعي للتقرير (Reference Code)" : "Report Reference Code"}
          </label>
          <div className="flex gap-2">
            <Input
              placeholder="e.g. GNX-RPT-2026-F98B2A"
              value={referenceInput}
              onChange={(e) => setReferenceInput(e.target.value)}
              className="text-xs font-mono"
            />
            <Button
              variant="clinical"
              size="sm"
              onClick={() => handleVerify(referenceInput)}
              disabled={isLoading || !referenceInput.trim()}
              className="text-xs shrink-0"
            >
              <Search className="h-3.5 w-3.5 mr-1 rtl:mr-0 rtl:ml-1" />
              <span>{language === "ar" ? "تحقق" : "Verify"}</span>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Loading */}
      {isLoading && (
        <div className="py-12 text-center space-y-3">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-teal-700 border-r-transparent" />
          <p className="text-xs text-muted-foreground">
            {language === "ar" ? "جاري التحقق من السجل الرقمي..." : "Verifying cryptographic registry..."}
          </p>
        </div>
      )}

      {/* Error */}
      {error && !isLoading && (
        <Card className="border-red-200 bg-red-50/40 dark:bg-red-950/20">
          <CardContent className="p-4 flex items-center space-x-3 rtl:space-x-reverse text-red-700 dark:text-red-400 text-xs">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </CardContent>
        </Card>
      )}

      {/* Result Display */}
      {verificationResult && !isLoading && (
        <Card
          className={`border ${
            verificationResult.is_valid
              ? "border-teal-200 bg-teal-50/20 dark:bg-teal-950/10"
              : "border-red-200 bg-red-50/20 dark:bg-red-950/10"
          }`}
        >
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 rtl:space-x-reverse">
                {verificationResult.is_valid ? (
                  <CheckCircle2 className="h-5 w-5 text-teal-600" />
                ) : (
                  <ShieldAlert className="h-5 w-5 text-red-600" />
                )}
                <CardTitle className="text-base font-bold">
                  {verificationResult.is_valid
                    ? language === "ar"
                      ? "تقرير أصلي موثق"
                      : "Authentic & Verified Report"
                    : language === "ar"
                    ? "تقرير غير معتمد أو ملغى"
                    : "Invalid or Revoked Report"}
                </CardTitle>
              </div>
              <Badge
                variant={verificationResult.is_valid ? "success" : "destructive"}
                className="text-xs font-semibold"
              >
                {verificationResult.status}
              </Badge>
            </div>
            <CardDescription className="text-xs">
              {language === "ar" ? verificationResult.message_ar : verificationResult.message_en}
            </CardDescription>
          </CardHeader>

          {verificationResult.is_valid && (
            <CardContent className="space-y-4 pt-0">
              <div className="border-t border-border pt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-muted-foreground block text-[11px]">
                    {language === "ar" ? "الرقم المرجعي:" : "Report Reference:"}
                  </span>
                  <span className="font-mono font-medium text-slate-800 dark:text-slate-200">
                    {verificationResult.report_reference}
                  </span>
                </div>

                <div>
                  <span className="text-muted-foreground block text-[11px]">
                    {language === "ar" ? "تاريخ الإصدار:" : "Generated At:"}
                  </span>
                  <span className="font-medium text-slate-800 dark:text-slate-200 flex items-center space-x-1 rtl:space-x-reverse">
                    <Calendar className="h-3 w-3 text-slate-400" />
                    <span>
                      {verificationResult.generated_at
                        ? new Date(verificationResult.generated_at).toLocaleString()
                        : "N/A"}
                    </span>
                  </span>
                </div>

                <div>
                  <span className="text-muted-foreground block text-[11px]">
                    {language === "ar" ? "إصدار الاستبيان:" : "Questionnaire Version:"}
                  </span>
                  <span className="font-medium text-slate-800 dark:text-slate-200">
                    {verificationResult.questionnaire_version_tag}
                  </span>
                </div>

                <div>
                  <span className="text-muted-foreground block text-[11px]">
                    {language === "ar" ? "إصدار محرك القواعد:" : "Rule Engine Version:"}
                  </span>
                  <span className="font-medium text-slate-800 dark:text-slate-200">
                    {verificationResult.rule_engine_version}
                  </span>
                </div>

                <div className="sm:col-span-2">
                  <span className="text-muted-foreground block text-[11px]">
                    {language === "ar" ? "تصنيف النتيجة الإكلينيكية:" : "Outcome Tier:"}
                  </span>
                  <span className="font-semibold text-teal-800 dark:text-teal-300">
                    {language === "ar" && verificationResult.outcome_title_ar
                      ? verificationResult.outcome_title_ar
                      : verificationResult.outcome_title_en || verificationResult.outcome_tier}
                  </span>
                </div>

                {verificationResult.integrity_hash && (
                  <div className="sm:col-span-2">
                    <span className="text-muted-foreground block text-[11px]">
                      {language === "ar" ? "البصمة الرقمية للتقرير (SHA-256):" : "Cryptographic Integrity Hash (SHA-256):"}
                    </span>
                    <span className="font-mono text-[10px] break-all text-slate-600 dark:text-slate-400">
                      {verificationResult.integrity_hash}
                    </span>
                  </div>
                )}
              </div>

              {/* Strict Non-Diagnostic Notice */}
              <div className="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded p-3 text-[11px] text-amber-800 dark:text-amber-300 space-y-1">
                <span className="font-semibold block">
                  {language === "ar"
                    ? "إشعار الخصوصية والطبيعة غير التشخيصية:"
                    : "Privacy & Non-Diagnostic Notice:"}
                </span>
                <p>
                  {language === "ar"
                    ? "منصة جينوفيكس تقدم إرشادات استرشادية غير تشخيصية. هذا التحقق يؤكد أصالة المستند الصادر دون الكشف عن إجابات المريض أو هويته. لا يحل هذا التقرير محل الفحص الطبي لدى طبيب معتمد أو تحليل السائل المنوي المخبري."
                    : "GENOVEX is a non-diagnostic risk identification platform. This verification confirms document authenticity without exposing patient answers or identifiers. It does not replace in-person physical clinical examination or laboratory semen analysis."}
                </p>
              </div>
            </CardContent>
          )}
        </Card>
      )}
    </div>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={<div className="py-16 text-center text-xs text-muted-foreground">Loading verification...</div>}>
      <VerifyContent />
    </Suspense>
  );
}
