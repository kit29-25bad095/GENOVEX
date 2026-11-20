"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useLanguage } from "@/context/LanguageContext";
import { useAuth } from "@/context/AuthContext";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { History, FileText, ArrowLeft, ExternalLink, Calendar, ShieldCheck } from "lucide-react";

interface AssessmentHistoryItem {
  id: string;
  session_token: string;
  created_at: string;
  overall_tier: string;
  questionnaire_version: string;
  rule_version: string;
  status: string;
}

export default function AssessmentHistoryPage() {
  const { t, language } = useLanguage();
  const { guestSessionToken, user } = useAuth();
  const [historyItems, setHistoryItems] = useState<AssessmentHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Collect local and demo assessment snapshots
    const items: AssessmentHistoryItem[] = [
      {
        id: "1",
        session_token: guestSessionToken || "gst_sample_token_2026",
        created_at: new Date().toISOString(),
        overall_tier: "LIFESTYLE_MODIFIABLE_FACTORS",
        questionnaire_version: "v1.0.0-published",
        rule_version: "v1.0-clinical-approved",
        status: "COMPLETED",
      },
    ];
    setHistoryItems(items);
  }, [guestSessionToken]);

  return (
    <div className="container mx-auto px-4 sm:px-6 py-10 max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Link href="/dashboard" className="text-xs text-muted-foreground hover:text-teal-700 flex items-center space-x-1.5 rtl:space-x-reverse">
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

      {/* History Items List */}
      <div className="space-y-4">
        {historyItems.map((item) => (
          <Card key={item.id} className="border-border hover:shadow-sm transition-shadow">
            <CardContent className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="space-y-1.5">
                <div className="flex items-center space-x-2 rtl:space-x-reverse">
                  <Badge variant="outline" className="text-xs font-semibold">
                    {item.overall_tier.replace(/_/g, " ")}
                  </Badge>
                  <span className="text-[11px] text-muted-foreground flex items-center space-x-1 rtl:space-x-reverse">
                    <Calendar className="h-3 w-3 text-slate-400" />
                    <span>{new Date(item.created_at).toLocaleDateString()}</span>
                  </span>
                </div>

                <div className="text-xs text-muted-foreground font-mono">
                  Token: {item.session_token.substring(0, 20)}...
                </div>

                <div className="flex items-center space-x-3 rtl:space-x-reverse text-[11px] text-teal-800 dark:text-teal-300">
                  <span>Questionnaire: {item.questionnaire_version}</span>
                  <span>•</span>
                  <span>Rules: {item.rule_version}</span>
                </div>
              </div>

              <div className="flex items-center space-x-2 rtl:space-x-reverse">
                <Link href={`/assessment/report/${item.session_token}`}>
                  <Button variant="outline" size="sm" className="text-xs flex items-center space-x-1.5 rtl:space-x-reverse">
                    <FileText className="h-3.5 w-3.5" />
                    <span>{language === "ar" ? "عرض التقرير الموثق" : "View Report"}</span>
                    <ExternalLink className="h-3 w-3 ml-1 rtl:ml-0 rtl:mr-1" />
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
