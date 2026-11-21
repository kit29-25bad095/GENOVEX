"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/context/LanguageContext";
import { useAuth } from "@/context/AuthContext";
import { ApiClient, Question, DomainQuestionsResponse, AssessmentReviewResponse } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { UrgentAlertBanner } from "@/components/urgent-alert-banner";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Shield,
  Activity,
  FileCheck,
  AlertTriangle,
  RotateCcw,
} from "lucide-react";

interface PendingChangeState {
  questionCode: string;
  newValue: any;
  affectedCount: number;
  affectedQuestions: string[];
}

export default function AdaptiveAssessmentPage() {
  const { t, language } = useLanguage();
  const { guestSessionToken } = useAuth();
  const router = useRouter();

  const [assessmentId, setAssessmentId] = useState<string>("");
  const [sessionToken, setSessionToken] = useState<string>("");
  const [currentDomainIndex, setCurrentDomainIndex] = useState<number>(0);
  const [domainData, setDomainData] = useState<DomainQuestionsResponse | null>(null);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [reconfirmationNeeded, setReconfirmationNeeded] = useState<Record<string, boolean>>({});
  const [pendingChange, setPendingChange] = useState<PendingChangeState | null>(null);
  const [isReviewMode, setIsReviewMode] = useState<boolean>(false);
  const [reviewData, setReviewData] = useState<AssessmentReviewResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize or resume assessment session
  useEffect(() => {
    async function init() {
      setIsLoading(true);
      setError(null);
      try {
        const res = await ApiClient.startAssessment(guestSessionToken);
        setAssessmentId(res.assessment_id);
        setSessionToken(res.session_token);
        setCurrentDomainIndex(res.current_domain_index || 0);

        const domainRes = await ApiClient.getDomainQuestions(res.assessment_id, res.current_domain_index || 0);
        setDomainData(domainRes);
        
        // Extract saved responses and reconfirmation flags
        const initialAnswers: Record<string, any> = {};
        const reconfirmFlags: Record<string, boolean> = {};
        if (domainRes.saved_responses) {
          for (const [k, v] of Object.entries(domainRes.saved_responses)) {
            if (v && typeof v === "object") {
              if (v.is_unsure) initialAnswers[k] = "not_sure";
              else if (v.is_prefer_not_to_say) initialAnswers[k] = "prefer_not_to_say";
              else initialAnswers[k] = v.answer_value;

              if (v.needs_reconfirmation || v.conditional_pathway_active === false) {
                reconfirmFlags[k] = true;
              }
            } else {
              initialAnswers[k] = v;
            }
          }
        }
        setAnswers(initialAnswers);
        setReconfirmationNeeded(reconfirmFlags);
      } catch (err: any) {
        setError(err.message || "Failed to initialize assessment engine");
      } finally {
        setIsLoading(false);
      }
    }
    init();
  }, [guestSessionToken]);

  // Load specific domain questions
  const loadDomain = async (index: number) => {
    setIsLoading(true);
    setError(null);
    setIsReviewMode(false);
    try {
      const res = await ApiClient.getDomainQuestions(assessmentId, index);
      setDomainData(res);
      setCurrentDomainIndex(index);

      const updatedAnswers: Record<string, any> = { ...answers };
      const reconfirmFlags: Record<string, boolean> = { ...reconfirmationNeeded };
      if (res.saved_responses) {
        for (const [k, v] of Object.entries(res.saved_responses)) {
          if (v && typeof v === "object") {
            if (v.is_unsure) updatedAnswers[k] = "not_sure";
            else if (v.is_prefer_not_to_say) updatedAnswers[k] = "prefer_not_to_say";
            else if (v.answer_value !== undefined) updatedAnswers[k] = v.answer_value;

            if (v.needs_reconfirmation || v.conditional_pathway_active === false) {
              reconfirmFlags[k] = true;
            } else {
              reconfirmFlags[k] = false;
            }
          } else if (v !== undefined) {
            updatedAnswers[k] = v;
          }
        }
      }
      setAnswers(updatedAnswers);
      setReconfirmationNeeded(reconfirmFlags);
    } catch (err: any) {
      setError(err.message || "Failed to load domain questions");
    } finally {
      setIsLoading(false);
    }
  };

  // Load Pre-Submission Review breakdown
  const loadReview = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Save current domain first
      if (currentDomainIndex < 11) {
        await ApiClient.saveDomainResponses(assessmentId, currentDomainIndex, answers);
      }
      const review = await ApiClient.getAssessmentReview(assessmentId);
      setReviewData(review);
      setIsReviewMode(true);
    } catch (err: any) {
      setError(err.message || "Failed to load assessment review");
    } finally {
      setIsLoading(false);
    }
  };

  // Check if a conditional question should be displayed
  const isQuestionVisible = (q: Question) => {
    const parentCode = q.conditional_parent_code || q.conditional_parent_key;
    if (!parentCode) return true;

    const parentAnswer = answers[parentCode];
    if (parentAnswer === undefined || parentAnswer === null) return false;
    if (parentAnswer === "not_sure" || parentAnswer === "prefer_not_to_say") return false;

    const triggers = q.conditional_trigger_values || (q.conditional_parent_value ? [q.conditional_parent_value] : []);
    if (triggers.length === 0) return !!parentAnswer;

    const parentStr = String(parentAnswer).toLowerCase().trim();
    if (Array.isArray(parentAnswer)) {
      const lowerArr = parentAnswer.map((x) => String(x).toLowerCase().trim());
      return triggers.some((t) => lowerArr.includes(String(t).toLowerCase().trim()));
    }
    return triggers.some((t) => String(t).toLowerCase().trim() === parentStr);
  };

  // Check if changing this answer would invalidate dependent answered questions
  const checkInvalidationImpact = (questionCode: string, newValue: any): PendingChangeState | null => {
    if (!domainData) return null;
    const currentVal = answers[questionCode];
    if (currentVal === newValue) return null;

    // Find direct dependents in domain
    const dependents = domainData.questions.filter(
      (q) => (q.conditional_parent_code === questionCode || q.conditional_parent_key === questionCode)
    );

    const affected: string[] = [];
    for (const dep of dependents) {
      const depCode = dep.question_code || (dep as any).question_key;
      const depAns = answers[depCode];
      if (depAns !== undefined && depAns !== null && depAns !== "") {
        // Check if newValue would hide this dependent
        const triggers = dep.conditional_trigger_values || (dep.conditional_parent_value ? [dep.conditional_parent_value] : []);
        const newStr = String(newValue).toLowerCase().trim();
        const wouldTrigger = triggers.some((t) => String(t).toLowerCase().trim() === newStr);
        if (!wouldTrigger) {
          affected.push(dep.question_text_en || depCode);
        }
      }
    }

    if (affected.length > 0) {
      return {
        questionCode,
        newValue,
        affectedCount: affected.length,
        affectedQuestions: affected,
      };
    }
    return null;
  };

  // Handle single response update with confirmation check
  const handleAnswerChange = (questionCode: string, value: any) => {
    const impact = checkInvalidationImpact(questionCode, value);
    if (impact) {
      setPendingChange(impact);
      return;
    }
    applyAnswer(questionCode, value);
  };

  const applyAnswer = (questionCode: string, value: any) => {
    setAnswers((prev) => ({
      ...prev,
      [questionCode]: value,
    }));
    // If this question needed reconfirmation, clearing the flag
    if (reconfirmationNeeded[questionCode]) {
      setReconfirmationNeeded((prev) => ({
        ...prev,
        [questionCode]: false,
      }));
    }
    setPendingChange(null);
  };

  const cancelPendingChange = () => {
    setPendingChange(null);
  };

  // Handle multi-select options
  const handleMultiChoiceToggle = (questionCode: string, optionValue: string) => {
    const currentValues: string[] = Array.isArray(answers[questionCode]) ? answers[questionCode] : [];
    let updated: string[];
    if (currentValues.includes(optionValue)) {
      updated = currentValues.filter((v) => v !== optionValue);
    } else {
      updated = [...currentValues, optionValue];
    }
    handleAnswerChange(questionCode, updated);
  };

  // Advance to next domain or review step
  const handleNext = async () => {
    setError(null);
    setIsLoading(true);

    try {
      // 1. Save current domain responses to backend
      await ApiClient.saveDomainResponses(assessmentId, currentDomainIndex, answers);

      // 2. Advance to next domain or enter Pre-Submission Review step
      const total = domainData?.total_domains || 11;
      if (currentDomainIndex < total - 1) {
        await loadDomain(currentDomainIndex + 1);
      } else {
        await loadReview();
      }
    } catch (err: any) {
      setError(err.message || "Failed to process answers");
      setIsLoading(false);
    }
  };

  const handlePrevious = async () => {
    if (isReviewMode) {
      // Return to last domain from review mode
      const total = domainData?.total_domains || 11;
      await loadDomain(total - 1);
      return;
    }
    if (currentDomainIndex > 0) {
      setIsLoading(true);
      try {
        // Auto-save on Previous
        await ApiClient.saveDomainResponses(assessmentId, currentDomainIndex, answers);
      } catch (e) {
        // Continue even if background auto-save fails
      }
      await loadDomain(currentDomainIndex - 1);
    }
  };

  const handleFinalSubmit = async () => {
    setError(null);
    setIsSubmitting(true);
    try {
      await ApiClient.submitAssessment(assessmentId);
      await ApiClient.evaluateAssessment(sessionToken || assessmentId);
      router.push(`/assessment/report/${sessionToken || assessmentId}`);
    } catch (err: any) {
      setError(err.message || "Failed to submit assessment");
      setIsSubmitting(false);
    }
  };

  // Detect live urgent red-flag responses in current answers
  const hasAcutePain = answers["Q_ACUTE_SCROTAL_PAIN"] === "yes";
  const hasTestisLump = answers["Q_PAINLESS_TESTIS_LUMP"] === "yes";

  const totalDomains = domainData?.total_domains || 11;
  const progressPercent = isReviewMode
    ? reviewData?.progress_percentage || 100
    : Math.round(((currentDomainIndex + 1) / (totalDomains + 1)) * 100);

  return (
    <div className="container mx-auto px-4 sm:px-6 py-8 max-w-4xl space-y-6">
      {/* Real-time Emergency Banner */}
      {hasAcutePain && (
        <UrgentAlertBanner
          type="acute_pain"
          referralGuidance="Emergency warning: You reported sudden severe testicular pain. Seek an immediate emergency department within 6 hours."
        />
      )}
      {!hasAcutePain && hasTestisLump && (
        <UrgentAlertBanner
          type="testis_lump"
          referralGuidance="Urgent warning: You reported a painless testicular lump. Schedule a urologist evaluation with scrotal ultrasound within 48-72 hours."
        />
      )}

      {/* Confirmation Modal for Downstream Invalidation */}
      {pendingChange && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <Card className="max-w-md w-full border-amber-300 dark:border-amber-700 bg-white dark:bg-slate-900 shadow-xl">
            <CardHeader className="pb-3 border-b border-border/60">
              <div className="flex items-center space-x-2 rtl:space-x-reverse text-amber-800 dark:text-amber-400">
                <AlertTriangle className="h-5 w-5 flex-shrink-0" />
                <CardTitle className="text-base font-bold">
                  {language === "ar" ? "تأكيد تعديل الإجابة" : "Confirm Answer Change"}
                </CardTitle>
              </div>
            </CardHeader>
            <CardContent className="pt-4 space-y-3 text-xs leading-relaxed text-slate-700 dark:text-slate-300">
              <p>
                {language === "ar"
                  ? `تعديل هذه الإجابة سيؤدي إلى إلغاء تفعيل (${pendingChange.affectedCount}) من الإجابات التابعة التالية:`
                  : `Changing this answer will deactivate (${pendingChange.affectedCount}) previously answered follow-up response(s):`}
              </p>
              <ul className="list-disc list-inside space-y-1 bg-amber-50/60 dark:bg-amber-950/30 p-2.5 rounded border border-amber-200 dark:border-amber-800 text-[11px] font-medium text-amber-900 dark:text-amber-200">
                {pendingChange.affectedQuestions.map((qText, i) => (
                  <li key={i}>{qText}</li>
                ))}
              </ul>
              <p className="text-[11px] text-muted-foreground">
                {language === "ar"
                  ? "لن تشارك هذه الإجابات في التقييم الإكلينيكي الحالي ما لم تتم إعادة تفعيلها وتأكيدها لاحقاً."
                  : "These follow-up responses will no longer participate in your current clinical assessment."}
              </p>
            </CardContent>
            <CardFooter className="flex items-center justify-end space-x-2 rtl:space-x-reverse pt-2 border-t border-border">
              <Button
                variant="outline"
                size="sm"
                onClick={cancelPendingChange}
                className="text-xs"
              >
                {language === "ar" ? "إلغاء والاحتفاظ بالإجابة" : "Cancel & Keep Current"}
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => applyAnswer(pendingChange.questionCode, pendingChange.newValue)}
                className="text-xs font-semibold"
              >
                {language === "ar" ? "تأكيد التعديل" : "Confirm & Deactivate"}
              </Button>
            </CardFooter>
          </Card>
        </div>
      )}

      {/* Progress & Header */}
      <div className="space-y-3">
        <div className="flex items-center justify-between text-xs text-muted-foreground font-medium">
          <span className="flex items-center space-x-1.5 rtl:space-x-reverse text-teal-800 dark:text-teal-400 font-semibold">
            <Activity className="h-4 w-4" />
            <span>
              {isReviewMode
                ? language === "ar" ? "مراجعة الاستبيان قبل الاعتماد" : "Pre-Submission Review"
                : language === "ar"
                  ? `المجال ${currentDomainIndex + 1} من ${totalDomains}: ${domainData?.domain_name || ""}`
                  : `Domain ${currentDomainIndex + 1} of ${totalDomains}: ${domainData?.domain_name || ""}`}
            </span>
          </span>
          <span>{progressPercent}% {language === "ar" ? "مكتمل" : "Complete"}</span>
        </div>
        <Progress value={progressPercent} className="h-2.5" />
      </div>

      {/* REVIEW MODE SCREEN */}
      {isReviewMode ? (
        <Card className="border-border shadow-sm">
          <CardHeader className="pb-4 border-b border-border/60">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-xl text-slate-900 dark:text-white flex items-center space-x-2 rtl:space-x-reverse">
                  <FileCheck className="h-5 w-5 text-teal-700" />
                  <span>{language === "ar" ? "مراجعة الاستبيان الطبي الشامل" : "Comprehensive Pre-Submission Review"}</span>
                </CardTitle>
                <CardDescription className="text-xs mt-1">
                  {language === "ar"
                    ? "يرجى مراجعة إجاباتك عبر جميع المجالات الـ 11 قبل تقديم التقييم النهائي والحصول على التقرير السريري."
                    : "Please review your completed answers across all 11 clinical domains before locking and evaluating your report."}
                </CardDescription>
              </div>
              <Badge variant="outline" className="text-xs font-semibold px-2.5 py-1">
                {reviewData?.version_tag || "v1.0.0"}
              </Badge>
            </div>
          </CardHeader>

          <CardContent className="pt-6 space-y-6">
            {error && (
              <div className="p-3 bg-red-50 text-red-900 border border-red-200 rounded-md text-xs flex items-center space-x-2 rtl:space-x-reverse">
                <AlertCircle className="h-4 w-4 text-red-600 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Review Metrics */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 text-center">
                <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
                  {language === "ar" ? "إجمالي الأسئلة" : "Total Questions"}
                </span>
                <p className="text-lg font-bold text-slate-900 dark:text-slate-100">{reviewData?.total_questions || 0}</p>
              </div>
              <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 text-center">
                <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
                  {language === "ar" ? "المجاب عنها" : "Answered"}
                </span>
                <p className="text-lg font-bold text-teal-700 dark:text-teal-400">{reviewData?.answered_count || 0}</p>
              </div>
              <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 text-center">
                <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
                  {language === "ar" ? "إلزامية متبقية" : "Required Pending"}
                </span>
                <p className={`text-lg font-bold ${(reviewData?.unanswered_required_count || 0) > 0 ? "text-amber-600" : "text-slate-900 dark:text-slate-100"}`}>
                  {reviewData?.unanswered_required_count || 0}
                </p>
              </div>
              <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 text-center">
                <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
                  {language === "ar" ? "حالة الاعتماد" : "Submission Status"}
                </span>
                <p className={`text-xs font-bold mt-1 ${reviewData?.can_submit ? "text-teal-700" : "text-amber-600"}`}>
                  {reviewData?.can_submit
                    ? language === "ar" ? "جاهز للتقديم" : "Ready to Submit"
                    : language === "ar" ? "مطلوب استكمال" : "Action Required"}
                </p>
              </div>
            </div>

            {/* Incomplete Required Warning */}
            {reviewData && !reviewData.can_submit && (
              <div className="p-3.5 bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800 rounded-lg text-xs flex items-start space-x-2.5 rtl:space-x-reverse text-amber-900 dark:text-amber-200">
                <AlertCircle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold">
                    {language === "ar"
                      ? `يوجد (${reviewData.unanswered_required_count}) أسئلة إلزامية غير مجاب عنها أو بانتظار التأكيد.`
                      : `There are (${reviewData.unanswered_required_count}) required questions unanswered or awaiting reconfirmation.`}
                  </p>
                  <p className="text-[11px] text-amber-800 dark:text-amber-300 mt-0.5">
                    {language === "ar"
                      ? "يرجى الرجوع إلى المجالات غير المكتملة وإكمال الإجابات المطلوبة لتمكين الاعتماد السريري."
                      : "Please return to incomplete domains to answer or reconfirm required questions before final submission."}
                  </p>
                </div>
              </div>
            )}

            {/* Domains Breakdown List */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                {language === "ar" ? "تفاصيل المجالات الإكلينيكية الـ 11" : "11 Clinical Domains Breakdown"}
              </h4>
              <div className="grid grid-cols-1 gap-2">
                {reviewData?.domains.map((dom) => (
                  <div
                    key={dom.domain_code}
                    className="flex items-center justify-between p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 hover:bg-slate-50 transition-colors"
                  >
                    <div className="flex items-center space-x-3 rtl:space-x-reverse">
                      <div className={`h-2.5 w-2.5 rounded-full ${dom.is_complete ? "bg-teal-600" : "bg-amber-500"}`} />
                      <div>
                        <p className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                          {language === "ar" ? dom.domain_title_ar : dom.domain_title_en}
                        </p>
                        <p className="text-[10px] text-muted-foreground">
                          {dom.questions.filter((q) => q.is_answered).length} / {dom.questions.length} {language === "ar" ? "أسئلة مكتملة" : "completed"}
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => loadDomain(dom.domain_index)}
                      className="text-xs text-teal-800 hover:text-teal-900"
                    >
                      {language === "ar" ? "تعديل" : "Edit"}
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>

          <CardFooter className="flex items-center justify-between border-t border-border pt-4">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePrevious}
              className="flex items-center space-x-1.5 rtl:space-x-reverse text-xs"
            >
              <ArrowLeft className="h-3.5 w-3.5 rtl:rotate-180" />
              <span>{language === "ar" ? "العودة للمجالات" : "Back to Questions"}</span>
            </Button>

            <Button
              variant="clinical"
              size="sm"
              onClick={handleFinalSubmit}
              disabled={!reviewData?.can_submit || isSubmitting}
              className="flex items-center space-x-1.5 rtl:space-x-reverse text-xs font-semibold px-6"
            >
              <span>
                {isSubmitting
                  ? (language === "ar" ? "جاري تقييم التقرير..." : "Evaluating Clinical Report...")
                  : (language === "ar" ? "اعتماد التقييم وعرض التقرير" : "Submit Assessment & View Report")}
              </span>
              <ArrowRight className="h-3.5 w-3.5 rtl:rotate-180" />
            </Button>
          </CardFooter>
        </Card>
      ) : (
        /* NORMAL DOMAIN QUESTIONS CARD */
        <Card className="border-border shadow-sm">
          <CardHeader className="pb-4 border-b border-border/60">
            <CardTitle className="text-xl text-slate-900 dark:text-white">
              {domainData?.domain_name || t("quest.title")}
            </CardTitle>
            <CardDescription className="text-xs">
              {t("quest.subtitle")}
            </CardDescription>
          </CardHeader>

          <CardContent className="pt-6 space-y-8">
            {error && (
              <div className="p-3 bg-red-50 text-red-900 border border-red-200 rounded-md text-xs flex items-center space-x-2 rtl:space-x-reverse">
                <AlertCircle className="h-4 w-4 text-red-600 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {isLoading ? (
              <div className="py-16 text-center space-y-3">
                <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-teal-700 border-r-transparent" />
                <p className="text-xs text-muted-foreground">
                  {language === "ar" ? "جاري تحميل الأسئلة الإكلينيكية..." : "Loading clinical domain questions..."}
                </p>
              </div>
            ) : (
              <div className="space-y-8">
                {domainData?.questions.filter(isQuestionVisible).map((q, qIndex) => {
                  const questionCode = q.question_code || (q as any).question_key;
                  const questionText = language === "ar" ? q.question_text_ar : q.question_text_en;
                  const helpText = language === "ar" ? q.help_text_ar : q.help_text_en;
                  const currentValue = answers[questionCode];
                  const needsReconfirm = reconfirmationNeeded[questionCode];

                  return (
                    <div
                      key={q.id}
                      className={`space-y-3 p-4 rounded-xl border ${
                        needsReconfirm
                          ? "border-amber-300 bg-amber-50/30 dark:bg-amber-950/20"
                          : "border-slate-200 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-900/30"
                      }`}
                    >
                      <div className="space-y-1">
                        <div className="flex items-start justify-between gap-2">
                          <Label className="text-sm font-semibold text-slate-900 dark:text-slate-100 leading-snug">
                            {qIndex + 1}. {questionText}
                            {q.is_required && <span className="text-red-500 ml-1 rtl:ml-0 rtl:mr-1">*</span>}
                          </Label>
                          <div className="flex items-center space-x-1.5 rtl:space-x-reverse">
                            {needsReconfirm && (
                              <Badge variant="outline" className="text-[10px] text-amber-700 border-amber-400 bg-amber-50">
                                <RotateCcw className="h-2.5 w-2.5 mr-1" />
                                Reconfirmation Required
                              </Badge>
                            )}
                            {(q.conditional_parent_code || q.conditional_parent_key) && (
                              <Badge variant="outline" className="text-[10px] text-teal-700 border-teal-300">
                                Follow-up
                              </Badge>
                            )}
                          </div>
                        </div>
                        {helpText && (
                          <p className="text-xs text-muted-foreground flex items-center space-x-1 rtl:space-x-reverse">
                            <HelpCircle className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
                            <span>{helpText}</span>
                          </p>
                        )}
                        {needsReconfirm && (
                          <p className="text-[11px] text-amber-800 dark:text-amber-300 flex items-center space-x-1 font-medium pt-1">
                            <AlertCircle className="h-3 w-3" />
                            <span>
                              {language === "ar"
                                ? `إجابة سابقة: (${String(currentValue)}) — يرجى إعادة التأكيد أو تحديد خيار جديد للمتابعة.`
                                : `Previously answered: (${String(currentValue)}) — Please reconfirm or select a new option to proceed.`}
                            </span>
                          </p>
                        )}
                      </div>

                      {/* Numeric Input */}
                      {q.question_type === "NUMERIC" && (
                        <div className="max-w-xs">
                          <Input
                            type="number"
                            placeholder="e.g., 34"
                            value={currentValue !== undefined && currentValue !== null ? currentValue : ""}
                            onChange={(e) => handleAnswerChange(questionCode, e.target.value ? parseInt(e.target.value) : "")}
                            className="bg-white dark:bg-slate-950"
                          />
                        </div>
                      )}

                      {/* Single Choice Options */}
                      {q.question_type === "SINGLE_CHOICE" && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                          {q.options.map((opt) => {
                            const isSelected = currentValue === opt.value;
                            const optLabel = language === "ar" ? opt.label_ar : opt.label_en;
                            return (
                              <button
                                key={opt.value}
                                type="button"
                                onClick={() => handleAnswerChange(questionCode, opt.value)}
                                className={`flex items-center justify-between p-3 rounded-lg border text-xs font-medium text-left rtl:text-right transition-all ${
                                  isSelected
                                    ? "border-teal-600 bg-teal-50 dark:bg-teal-950/60 text-teal-950 dark:text-teal-200 ring-1 ring-teal-600 shadow-sm"
                                    : "border-border bg-white dark:bg-slate-950 hover:bg-slate-100 dark:hover:bg-slate-900"
                                } ${opt.is_red_flag && isSelected ? "border-red-600 bg-red-50 text-red-950 ring-red-600" : ""}`}
                              >
                                <span>{optLabel}</span>
                                {isSelected && <CheckCircle2 className="h-4 w-4 text-teal-600 flex-shrink-0 ml-2 rtl:ml-0 rtl:mr-2" />}
                              </button>
                            );
                          })}
                        </div>
                      )}

                      {/* Multiple Choice Options */}
                      {q.question_type === "MULTIPLE_CHOICE" && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                          {q.options.map((opt) => {
                            const currentArr: string[] = Array.isArray(currentValue) ? currentValue : [];
                            const isSelected = currentArr.includes(opt.value);
                            const optLabel = language === "ar" ? opt.label_ar : opt.label_en;
                            return (
                              <button
                                key={opt.value}
                                type="button"
                                onClick={() => handleMultiChoiceToggle(questionCode, opt.value)}
                                className={`flex items-center justify-between p-3 rounded-lg border text-xs font-medium text-left rtl:text-right transition-all ${
                                  isSelected
                                    ? "border-teal-600 bg-teal-50 dark:bg-teal-950/60 text-teal-950 dark:text-teal-200 ring-1 ring-teal-600 shadow-sm"
                                    : "border-border bg-white dark:bg-slate-950 hover:bg-slate-100 dark:hover:bg-slate-900"
                                }`}
                              >
                                <span>{optLabel}</span>
                                <div
                                  className={`h-4 w-4 rounded border flex items-center justify-center ${
                                    isSelected ? "bg-teal-700 border-teal-700 text-white" : "border-slate-300"
                                  }`}
                                >
                                  {isSelected && <CheckCircle2 className="h-3 w-3" />}
                                </div>
                              </button>
                            );
                          })}
                        </div>
                      )}

                      {/* Safe Choice Shortcuts (Not Sure / Prefer Not To Say) */}
                      <div className="flex items-center space-x-2 rtl:space-x-reverse pt-2 text-[11px] text-muted-foreground">
                        <span>{language === "ar" ? "خيارات آمنة:" : "Safe options:"}</span>
                        <button
                          type="button"
                          onClick={() => handleAnswerChange(questionCode, "not_sure")}
                          className={`px-2 py-0.5 rounded border ${
                            currentValue === "not_sure"
                              ? "bg-slate-200 dark:bg-slate-800 border-slate-400 font-semibold text-foreground"
                              : "border-slate-200 dark:border-slate-800 hover:bg-slate-100"
                          }`}
                        >
                          {t("quest.safe_unsure")}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleAnswerChange(questionCode, "prefer_not_to_say")}
                          className={`px-2 py-0.5 rounded border ${
                            currentValue === "prefer_not_to_say"
                              ? "bg-slate-200 dark:bg-slate-800 border-slate-400 font-semibold text-foreground"
                              : "border-slate-200 dark:border-slate-800 hover:bg-slate-100"
                          }`}
                        >
                          {t("quest.safe_decline")}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>

          <CardFooter className="flex items-center justify-between border-t border-border pt-4">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePrevious}
              disabled={currentDomainIndex === 0 || isLoading}
              className="flex items-center space-x-1.5 rtl:space-x-reverse text-xs"
            >
              <ArrowLeft className="h-3.5 w-3.5 rtl:rotate-180" />
              <span>{t("quest.prev")}</span>
            </Button>

            <Button
              variant="clinical"
              size="sm"
              onClick={handleNext}
              disabled={isLoading || isSubmitting}
              className="flex items-center space-x-1.5 rtl:space-x-reverse text-xs font-semibold px-5"
            >
              <span>
                {currentDomainIndex === totalDomains - 1
                  ? language === "ar" ? "مراجعة الاستبيان" : "Review Answers"
                  : t("quest.next")}
              </span>
              <ArrowRight className="h-3.5 w-3.5 rtl:rotate-180" />
            </Button>
          </CardFooter>
        </Card>
      )}
    </div>
  );
}
