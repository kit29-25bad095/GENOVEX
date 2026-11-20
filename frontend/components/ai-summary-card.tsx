"use client";

import React from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sparkles, ShieldAlert, Info, Stethoscope, CheckCircle2 } from "lucide-react";
import { ClinicianAISummaryResponse, AIMetadata } from "@/lib/api";

interface AISummaryCardProps {
  summary: ClinicianAISummaryResponse;
  language?: "en" | "ar";
}

export function AISummaryCard({ summary, language = "en" }: AISummaryCardProps) {
  const isAr = language === "ar";

  return (
    <Card className="border border-purple-200 dark:border-purple-900 bg-gradient-to-br from-purple-50/40 via-white to-slate-50 dark:from-purple-950/20 dark:via-slate-900 dark:to-slate-900 shadow-sm space-y-4">
      <CardHeader className="pb-3 border-b border-purple-100 dark:border-purple-900/60">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center space-x-2 rtl:space-x-reverse">
            <div className="p-1.5 bg-purple-100 dark:bg-purple-900/60 rounded-md text-purple-700 dark:text-purple-300">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <CardTitle className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <span>{isAr ? "الملخص السريري الذكي المدعوم بالذكاء الاصطناعي" : "AI-Assisted Clinical Synthesis"}</span>
              </CardTitle>
              <CardDescription className="text-[11px] text-muted-foreground">
                {isAr ? "تحليل تلخيصي للبيانات المقدمة من المريض لمساعدة الطبيب" : "Synthesized data overview for attending physician review"}
              </CardDescription>
            </div>
          </div>

          <Badge variant="outline" className="text-[10px] bg-purple-100/60 dark:bg-purple-950/40 text-purple-800 dark:text-purple-200 border-purple-300 w-fit">
            <Sparkles className="h-3 w-3 mr-1 rtl:mr-0 rtl:ml-1 inline" />
            {isAr ? "محتوى مولد بالذكاء الاصطناعي" : "AI-Generated Assistance"}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 text-xs">
        {/* Narrative Box */}
        <div className="p-3.5 bg-white dark:bg-slate-900/80 rounded-lg border border-purple-100 dark:border-purple-900/50 space-y-1.5">
          <div className="font-semibold text-purple-900 dark:text-purple-200 flex items-center space-x-1.5 rtl:space-x-reverse text-xs">
            <Stethoscope className="h-3.5 w-3.5 text-purple-600" />
            <span>{isAr ? "السرد الإكلينيكي التلخيصي" : "Synthesized Clinical Narrative"}</span>
          </div>
          <p className="text-slate-800 dark:text-slate-200 leading-relaxed font-normal">
            {summary.synthesized_risk_narrative}
          </p>
        </div>

        {/* Suggested Diagnostic Workup */}
        {summary.suggested_diagnostic_workup && summary.suggested_diagnostic_workup.length > 0 && (
          <div className="space-y-2">
            <span className="font-semibold text-slate-800 dark:text-slate-200 block text-xs uppercase tracking-wider">
              {isAr ? "الفحوصات المقترحة للاستقصاء السريري (EAU / AUA)" : "Suggested Clinical Diagnostic Workup (EAU / AUA)"}
            </span>
            <div className="grid grid-cols-1 gap-2">
              {summary.suggested_diagnostic_workup.map((item, idx) => (
                <div
                  key={idx}
                  className="p-2.5 bg-slate-50 dark:bg-slate-900 rounded-md border border-border flex items-start space-x-2 rtl:space-x-reverse"
                >
                  <CheckCircle2 className="h-3.5 w-3.5 text-teal-600 dark:text-teal-400 mt-0.5 flex-shrink-0" />
                  <span className="text-slate-700 dark:text-slate-300 leading-snug">{item}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Safety Disclaimer */}
        <div className="p-2.5 bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/60 rounded-md text-[11px] text-amber-950 dark:text-amber-200 flex items-start space-x-2 rtl:space-x-reverse leading-relaxed">
          <Info className="h-4 w-4 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
          <span>
            {summary.metadata?.disclaimer ||
              "AI assistance is provided strictly for educational and data organization purposes. It does not establish a medical diagnosis, override deterministic triage, or replace qualified physician examination."}
          </span>
        </div>

        {/* Traceability Metadata Footer */}
        <div className="flex items-center justify-between text-[10px] text-slate-400 border-t border-border/50 pt-2 font-mono">
          <span>Model: {summary.metadata?.model || "genovex-educational-v1"}</span>
          <span>Req ID: {summary.metadata?.request_id || "N/A"}</span>
        </div>
      </CardContent>
    </Card>
  );
}
