"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useLanguage } from "@/context/LanguageContext";
import { useAuth } from "@/context/AuthContext";
import {
  ApiClient,
  ClinicianAssessmentDetail,
  ClinicianAISummaryResponse,
  ClinicianNoteItem,
} from "@/lib/api";
import { AISummaryCard } from "@/components/ai-summary-card";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Stethoscope,
  ArrowLeft,
  ShieldAlert,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Clock,
  FileText,
  User,
  MessageSquare,
  Lock,
} from "lucide-react";

export default function ClinicianReviewPage() {
  const params = useParams<{ id: string }>();
  const assessmentId = params?.id;
  const router = useRouter();
  const { language } = useLanguage();
  const { user } = useAuth();

  const [assessment, setAssessment] = useState<ClinicianAssessmentDetail | null>(null);
  const [aiSummary, setAiSummary] = useState<ClinicianAISummaryResponse | null>(null);
  const [notes, setNotes] = useState<ClinicianNoteItem[]>([]);
  const [newNoteText, setNewNoteText] = useState("");
  const [newStatus, setNewStatus] = useState<string>("IN_REVIEW");
  const [statusNotes, setStatusNotes] = useState("");

  const [isLoading, setIsLoading] = useState(true);
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [isSubmittingStatus, setIsSubmittingStatus] = useState(false);
  const [isSubmittingNote, setIsSubmittingNote] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isAr = language === "ar";

  useEffect(() => {
    async function loadData() {
      if (!assessmentId) return;
      setIsLoading(true);
      setError(null);
      try {
        const detail = await ApiClient.getClinicianAssessmentReview(assessmentId);
        setAssessment(detail);
        setNewStatus(detail.current_review_status || "IN_REVIEW");

        const existingNotes = await ApiClient.getClinicianNotes(assessmentId);
        setNotes(existingNotes);
      } catch (err: any) {
        setError(err.message || "Failed to load assessment review.");
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, [assessmentId]);

  const handleGenerateAiSummary = async () => {
    if (!assessmentId) return;
    setIsAiLoading(true);
    try {
      const summary = await ApiClient.getClinicianAISummary(assessmentId);
      setAiSummary(summary);
    } catch (err: any) {
      alert(err.message || "Failed to generate AI summary.");
    } finally {
      setIsAiLoading(false);
    }
  };

  const handleUpdateStatus = async () => {
    if (!assessmentId) return;
    setIsSubmittingStatus(true);
    try {
      await ApiClient.updateClinicianReviewStatus(assessmentId, newStatus, statusNotes);
      alert("Review status updated successfully.");
      // Refresh
      const detail = await ApiClient.getClinicianAssessmentReview(assessmentId);
      setAssessment(detail);
      setStatusNotes("");
    } catch (err: any) {
      alert(err.message || "Failed to update review status.");
    } finally {
      setIsSubmittingStatus(false);
    }
  };

  const handleAddNote = async () => {
    if (!assessmentId || !newNoteText.trim()) return;
    setIsSubmittingNote(true);
    try {
      const note = await ApiClient.addClinicianNote(assessmentId, newNoteText);
      setNotes([note, ...notes]);
      setNewNoteText("");
    } catch (err: any) {
      alert(err.message || "Failed to add clinician note.");
    } finally {
      setIsSubmittingNote(false);
    }
  };

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-20 text-center space-y-3">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-teal-700 border-r-transparent" />
        <p className="text-xs text-muted-foreground">
          {isAr ? "جاري تحميل بيانات الفحص الإكلينيكي..." : "Loading clinical assessment review..."}
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-20 max-w-md text-center space-y-4">
        <AlertTriangle className="h-10 w-10 text-amber-500 mx-auto" />
        <h2 className="text-xl font-bold">{isAr ? "خطأ في تحميل التقييم" : "Assessment Review Error"}</h2>
        <p className="text-xs text-muted-foreground">{error}</p>
        <Link href="/clinician">
          <Button variant="outline" size="sm">
            {isAr ? "العودة للوحة التحكم" : "Back to Clinician Dashboard"}
          </Button>
        </Link>
      </div>
    );
  }

  if (!assessment) return null;

  return (
    <div className="container mx-auto px-4 sm:px-6 py-10 max-w-5xl space-y-8">
      {/* Action Header */}
      <div className="flex items-center justify-between">
        <Link href="/clinician" className="text-xs text-muted-foreground hover:text-teal-700 flex items-center space-x-1.5 rtl:space-x-reverse">
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>{isAr ? "العودة للوحة تحكم الأطباء" : "Back to Clinician Queue"}</span>
        </Link>
        <Badge variant="outline" className="text-xs font-mono">
          Ref: {assessment.patient_reference}
        </Badge>
      </div>

      {/* Title Card */}
      <Card className="border-border shadow-sm">
        <CardHeader className="pb-4 border-b border-border/60">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center space-x-2 rtl:space-x-reverse">
                <Stethoscope className="h-5 w-5 text-teal-700" />
                <CardTitle className="text-xl font-bold text-slate-900 dark:text-white">
                  {isAr ? "مراجعة التقييم السريري الشامل" : "Specialist Clinical Assessment Review"}
                </CardTitle>
              </div>
              <CardDescription className="text-xs">
                {isAr ? "فحص الإجابات خماسية الحالات، نتائج الفرز الحتمي، والدعم الذكي" : "Inspection of 5-state response breakdown, deterministic findings, and AI assistance"}
              </CardDescription>
            </div>

            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-xs">
                Status: {assessment.status}
              </Badge>
              <Badge
                variant={
                  assessment.current_review_status === "REVIEW_COMPLETED"
                    ? "success"
                    : assessment.current_review_status === "IN_REVIEW"
                    ? "warning"
                    : "default"
                }
                className="text-xs"
              >
                {assessment.current_review_status}
              </Badge>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* SECTION 1: AI-Assisted Clinical Summary */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
            <Sparkles className="h-4 w-4 text-purple-600" />
            <span>{isAr ? "الدعم الإكلينيكي بالذكاء الاصطناعي (Phase 9 Integration)" : "Clinician AI Decision Assistance"}</span>
          </h3>
          {!aiSummary && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleGenerateAiSummary}
              disabled={isAiLoading}
              className="text-xs h-8 border-purple-300 text-purple-700 dark:text-purple-300"
            >
              <Sparkles className="h-3.5 w-3.5 mr-1.5 rtl:mr-0 rtl:ml-1.5" />
              {isAiLoading
                ? (isAr ? "جاري التوليد..." : "Generating AI Summary...")
                : (isAr ? "توليد ملخص سريري ذكي" : "Generate Clinician AI Summary")}
            </Button>
          )}
        </div>

        {aiSummary && <AISummaryCard summary={aiSummary} language={language} />}
      </div>

      {/* SECTION 2: Deterministic Clinical Rule Engine Snapshot */}
      {assessment.deterministic_report && (
        <Card className="border-teal-200 dark:border-teal-900 bg-teal-50/20 dark:bg-teal-950/10">
          <CardHeader className="pb-3 border-b border-teal-100 dark:border-teal-900/50">
            <CardTitle className="text-sm font-bold text-teal-900 dark:text-teal-200 flex items-center justify-between">
              <span>{isAr ? "مخرجات محرك القواعد الإكلينيكية الحتمي" : "Deterministic Clinical Engine Findings"}</span>
              <Badge variant="clinical" className="text-[10px]">
                {assessment.deterministic_report.outcome_tier}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4 space-y-3 text-xs">
            <div className="font-semibold text-slate-900 dark:text-slate-100">
              {assessment.deterministic_report.outcome_title_en}
            </div>
            <p className="text-muted-foreground leading-relaxed">
              {assessment.deterministic_report.outcome_description_en}
            </p>
            {assessment.deterministic_report.is_urgent_red_flag && (
              <div className="p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-md text-red-900 dark:text-red-200 font-medium">
                URGENT MEDICAL RED FLAG: {assessment.deterministic_report.urgent_emergency_guidance_en}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* SECTION 3: Five-State Questionnaire Response Breakdown */}
      <Card className="border-border">
        <CardHeader className="pb-3 border-b border-border/60">
          <CardTitle className="text-sm font-bold text-slate-900 dark:text-white">
            {isAr ? "تفصيل إجابات الاستبيان (خماسية الحالات)" : "Detailed Questionnaire Responses (5-State Model)"}
          </CardTitle>
          <CardDescription className="text-xs">
            {isAr
              ? "استعراض الإجابات وتصنيفها بدقة: إجابة صريحة، غير متأكد، تفضيل عدم الإجابة، أو مسار شرطي معطل."
              : "Responses preserved with explicit unsure, prefer-not-to-say, and conditional DAG activation states."}
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-4 space-y-3 text-xs">
          {assessment.responses.map((r, idx) => (
            <div
              key={idx}
              className={`p-3 rounded-lg border ${
                !r.conditional_pathway_active
                  ? "bg-slate-50/50 dark:bg-slate-900/40 border-slate-200/50 opacity-60"
                  : "bg-white dark:bg-slate-900 border-border"
              } space-y-1.5`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="font-semibold text-slate-900 dark:text-slate-100">
                  {isAr ? r.prompt_ar : r.prompt_en}
                </div>
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="font-mono text-[10px] text-slate-400 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">
                    {r.question_key}
                  </span>
                  {r.is_unsure && (
                    <Badge variant="warning" className="text-[10px]">
                      {isAr ? "غير متأكد" : "Unsure"}
                    </Badge>
                  )}
                  {r.is_prefer_not_to_say && (
                    <Badge variant="outline" className="text-[10px] text-slate-600">
                      {isAr ? "فضل عدم الإجابة" : "Prefer not to say"}
                    </Badge>
                  )}
                  {!r.conditional_pathway_active && (
                    <Badge variant="outline" className="text-[10px] text-slate-400">
                      {isAr ? "مسار شرطي غير مفعّل" : "Conditional Inactive"}
                    </Badge>
                  )}
                  {r.needs_reconfirmation && (
                    <Badge variant="urgent" className="text-[10px]">
                      {isAr ? "يتطلب إعادة تأكيد" : "Needs Reconfirmation"}
                    </Badge>
                  )}
                </div>
              </div>

              <div className="text-slate-700 dark:text-slate-300">
                <span className="font-semibold">{isAr ? "الإجابة المسجلة: " : "Answer: "}</span>
                {r.answer_value !== null && r.answer_value !== undefined ? (
                  <span className="font-mono">{JSON.stringify(r.answer_value)}</span>
                ) : (
                  <span className="italic text-muted-foreground">{isAr ? "لا توجد إجابة صريحة" : "No affirmative value"}</span>
                )}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* SECTION 4: Clinician Review Workflow Controls */}
      <Card className="border-border">
        <CardHeader className="pb-3 border-b border-border/60">
          <CardTitle className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Clock className="h-4 w-4 text-teal-700" />
            <span>{isAr ? "إدارة مسار مراجعة الطبيب" : "Clinician Review Workflow Management"}</span>
          </CardTitle>
          <CardDescription className="text-xs">
            {isAr ? "تحديث حالة المراجعة الطبية للاستبيان وتسجيل الملاحظات" : "Transition review state and record rationale in immutable audit trail"}
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-4 space-y-4 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="font-semibold block mb-1">
                {isAr ? "حالة المراجعة الجديدة:" : "Target Review Workflow Status:"}
              </label>
              <select
                value={newStatus}
                onChange={(e) => setNewStatus(e.target.value)}
                className="w-full text-xs p-2 rounded-md border border-border bg-white dark:bg-slate-900"
              >
                <option value="PENDING_REVIEW">PENDING_REVIEW</option>
                <option value="IN_REVIEW">IN_REVIEW</option>
                <option value="REVIEW_COMPLETED">REVIEW_COMPLETED</option>
                <option value="FURTHER_INFO_REQUIRED">FURTHER_INFO_REQUIRED</option>
              </select>
            </div>

            <div>
              <label className="font-semibold block mb-1">
                {isAr ? "ملاحظات الانتقال (اختياري):" : "Transition Notes (Optional):"}
              </label>
              <input
                type="text"
                value={statusNotes}
                onChange={(e) => setStatusNotes(e.target.value)}
                placeholder="e.g., Reviewed endocrine history; referred to andrology"
                className="w-full text-xs p-2 rounded-md border border-border bg-white dark:bg-slate-900"
              />
            </div>
          </div>

          <Button
            variant="clinical"
            size="sm"
            onClick={handleUpdateStatus}
            disabled={isSubmittingStatus}
            className="text-xs font-semibold"
          >
            {isSubmittingStatus ? (isAr ? "جاري الحفظ..." : "Updating...") : (isAr ? "تحديث حالة المراجعة" : "Update Review Status")}
          </Button>
        </CardContent>
      </Card>

      {/* SECTION 5: Confidential Clinician Notes */}
      <Card className="border-border">
        <CardHeader className="pb-3 border-b border-border/60">
          <CardTitle className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-teal-700" />
            <span>{isAr ? "الملاحظات الإكلينيكية السرية" : "Confidential Clinician Notes"}</span>
          </CardTitle>
          <CardDescription className="text-xs">
            {isAr ? "ملاحظات داخلية مسجلة في سجل التدقيق المحمي ولا تظهر للمريض." : "Internal clinical notes recorded in the immutable audit trail. Strictly isolated from patient view."}
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-4 space-y-4 text-xs">
          <div className="space-y-2">
            <textarea
              value={newNoteText}
              onChange={(e) => setNewNoteText(e.target.value)}
              placeholder="Add confidential clinical consultation note or recommendations..."
              className="w-full text-xs p-2.5 rounded-md border border-border bg-white dark:bg-slate-900 min-h-[80px]"
            ></textarea>
            <Button
              variant="outline"
              size="sm"
              onClick={handleAddNote}
              disabled={isSubmittingNote || !newNoteText.trim()}
              className="text-xs font-semibold"
            >
              {isSubmittingNote ? (isAr ? "جاري الإضافة..." : "Adding Note...") : (isAr ? "إضافة ملاحظة إكلينيكية" : "Add Clinician Note")}
            </Button>
          </div>

          {notes.length > 0 && (
            <div className="space-y-2.5 pt-4 border-t border-border/60">
              <span className="font-semibold text-slate-800 dark:text-slate-200 block text-xs">
                {isAr ? "سجل الملاحظات السابقة:" : "Historical Clinician Notes:"}
              </span>
              {notes.map((n) => (
                <div key={n.note_id} className="p-3 bg-slate-50 dark:bg-slate-900 rounded-md border border-border space-y-1">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-semibold text-slate-900 dark:text-slate-100">
                      {n.author_name} ({n.author_role})
                    </span>
                    <span className="text-slate-400 font-mono text-[10px]">
                      {new Date(n.created_at).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-slate-700 dark:text-slate-300 leading-relaxed font-normal">
                    {n.note_text}
                  </p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
