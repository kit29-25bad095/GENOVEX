"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useLanguage } from "@/context/LanguageContext";
import { useAuth } from "@/context/AuthContext";
import { ApiClient, AssessmentHistoryItem } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
} from "lucide-react";

export default function AssessmentHistoryPage() {
  const { language } = useLanguage();
  const { guestSessionToken, user } = useAuth();
  const [historyItems, setHistoryItems] = useState<AssessmentHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadHistory() {
      setIsLoading(true);
      setError(null);
      try {
        if (user) {
          const res = await ApiClient.getAssessmentHistory(50, 0);
          setHistoryItems(res.items);
        } else if (guestSessionToken) {
          // Fallback to guest assessment session representation
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
        <Link href="/assessment">
          <Button variant="clinical" size="sm" className="text-xs font-semibold">
            {language === "ar" ? "بدء تقييم جديد" : "New Assessment"}
          </Button>
        </Link>
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

            const downloadUrl = ApiClient.getReportPdfDownloadUrl(item.session_token);

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

                  <div className="flex items-center space-x-2 rtl:space-x-reverse">
                    <Link href={`/assessment/report/${item.session_token}`}>
                      <Button variant="outline" size="sm" className="text-xs flex items-center space-x-1.5 rtl:space-x-reverse">
                        <FileText className="h-3.5 w-3.5" />
                        <span>{language === "ar" ? "عرض التقرير" : "View Report"}</span>
                        <ExternalLink className="h-3 w-3 ml-1 rtl:ml-0 rtl:mr-1" />
                      </Button>
                    </Link>

                    <a href={downloadUrl} download target="_blank" rel="noopener noreferrer">
                      <Button variant="outline" size="sm" className="text-xs flex items-center space-x-1.5 rtl:space-x-reverse">
                        <Download className="h-3.5 w-3.5" />
                        <span>{language === "ar" ? "تحميل PDF" : "PDF"}</span>
                      </Button>
                    </a>
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
