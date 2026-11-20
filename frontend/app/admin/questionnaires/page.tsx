"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useLanguage } from "@/context/LanguageContext";
import { useAuth } from "@/context/AuthContext";
import { ApiClient } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  FileCheck2,
  ArrowLeft,
  CheckCircle2,
  Layers,
  Activity,
  Shield,
  HelpCircle,
  GitBranch,
  Lock,
} from "lucide-react";

export default function QuestionnaireAdminPage() {
  const { t, language } = useLanguage();
  const { user } = useAuth();

  const [versions, setVersions] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any>({
    total_assessments: 0,
    submitted_locked: 0,
    in_progress: 0,
    completion_rate: 0,
  });
  const [isLoading, setIsLoading] = useState(true);

  // 11 Clinical Domains Reference
  const domains = [
    { code: "BASIC_HEALTH", nameEn: "Basic Health & Demographics", nameAr: "الصحة العامة والبيانات الديموغرافية", questions: 3 },
    { code: "REPRODUCTIVE_HISTORY", nameEn: "Reproductive & Fertility History", nameAr: "التاريخ الإنجابي والخصوبة", questions: 3 },
    { code: "TESTICULAR_HISTORY", nameEn: "Testicular & Scrotal History", nameAr: "تاريخ الخصية وكيس الصفن", questions: 3 },
    { code: "MEDICAL_HISTORY", nameEn: "Systemic Medical History", nameAr: "التاريخ الطبي العام", questions: 2 },
    { code: "HORMONAL_HEALTH", nameEn: "Hormonal & Endocrine Indicators", nameAr: "المؤشرات الهرمونية والغدد الصماء", questions: 2 },
    { code: "METABOLIC_HEALTH", nameEn: "Metabolic Health & Weight", nameAr: "الصحة الأيضية والوزن", questions: 1 },
    { code: "LIFESTYLE_HABITS", nameEn: "Lifestyle & Thermal Exposures", nameAr: "أنماط الحياة والتعرض الحراري", questions: 3 },
    { code: "MEDICATIONS_SUBSTANCES", nameEn: "Medications & Anabolic Steroids", nameAr: "الأدوية والستيرويدات البنائية", questions: 2 },
    { code: "OCCUPATIONAL_ENVIRONMENTAL", nameEn: "Occupational & Environmental Toxins", nameAr: "التعرض المهني والبيئي للسموم", questions: 1 },
    { code: "SEXUAL_HEALTH", nameEn: "Sexual & Ejaculatory Function", nameAr: "الصحة الجنسية والقذف", questions: 2 },
    { code: "FAMILY_GENETIC_HISTORY", nameEn: "Family & Genetic Infertility History", nameAr: "التاريخ العائلي والوراثي", questions: 1 },
  ];

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const [vData, mData] = await Promise.all([
          ApiClient.getQuestionnaireVersions(),
          ApiClient.getAssessmentsOverview(),
        ]);
        setVersions(vData);
        setMetrics(mData);
      } catch (err) {
        console.error("Error loading questionnaire governance:", err);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="container mx-auto px-4 sm:px-6 py-10 max-w-5xl space-y-6">
      {/* Back button & badge */}
      <div className="flex items-center justify-between">
        <Link
          href="/admin"
          className="text-xs text-muted-foreground hover:text-teal-700 flex items-center space-x-1.5 rtl:space-x-reverse"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>{language === "ar" ? "العودة للوحة الإدارة" : "Back to Admin"}</span>
        </Link>
        <Badge variant="outline" className="text-teal-700 border-teal-300">
          <GitBranch className="h-3 w-3 mr-1 rtl:mr-0 rtl:ml-1 inline" />
          DAG Branching & Versions
        </Badge>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white flex items-center space-x-2.5 rtl:space-x-reverse">
            <FileCheck2 className="h-7 w-7 text-teal-700" />
            <span>{language === "ar" ? "حوكمة محرك الاستبيانات" : "Questionnaire Engine Governance"}</span>
          </h1>
          <p className="text-xs text-muted-foreground">
            {language === "ar"
              ? "مراقبة المجالات السريرية الـ 11، إصدارات الأسئلة المعتمدة، وإحصائيات إتمام التقييمات."
              : "Governance of the 11 clinical domains, version immutability, and completion metrics."}
          </p>
        </div>
      </div>

      {/* Overview Metrics Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card className="border-border shadow-sm">
          <CardContent className="p-4 space-y-1">
            <span className="text-[11px] font-medium text-muted-foreground">
              {language === "ar" ? "إجمالي التقييمات" : "Total Assessments"}
            </span>
            <div className="text-2xl font-extrabold text-slate-900 dark:text-white">
              {metrics.total_assessments}
            </div>
            <p className="text-[10px] text-teal-700 font-medium">Session Initializations</p>
          </CardContent>
        </Card>

        <Card className="border-border shadow-sm">
          <CardContent className="p-4 space-y-1">
            <span className="text-[11px] font-medium text-muted-foreground">
              {language === "ar" ? "مكتملة ومقفلة" : "Submitted & Locked"}
            </span>
            <div className="text-2xl font-extrabold text-slate-900 dark:text-white">
              {metrics.submitted_locked}
            </div>
            <p className="text-[10px] text-emerald-700 font-medium">Immutable Status</p>
          </CardContent>
        </Card>

        <Card className="border-border shadow-sm">
          <CardContent className="p-4 space-y-1">
            <span className="text-[11px] font-medium text-muted-foreground">
              {language === "ar" ? "قيد الإجراء" : "In Progress"}
            </span>
            <div className="text-2xl font-extrabold text-slate-900 dark:text-white">
              {metrics.in_progress}
            </div>
            <p className="text-[10px] text-amber-700 font-medium">Active Drafts</p>
          </CardContent>
        </Card>

        <Card className="border-border shadow-sm">
          <CardContent className="p-4 space-y-1">
            <span className="text-[11px] font-medium text-muted-foreground">
              {language === "ar" ? "نسبة الإتمام" : "Completion Rate"}
            </span>
            <div className="text-2xl font-extrabold text-slate-900 dark:text-white">
              {metrics.completion_rate}%
            </div>
            <p className="text-[10px] text-purple-700 font-medium">Completion Ratio</p>
          </CardContent>
        </Card>
      </div>

      {/* Published Versions */}
      <Card className="border-border shadow-sm">
        <CardHeader className="pb-3 border-b border-border/60">
          <CardTitle className="text-base font-bold flex items-center space-x-2 rtl:space-x-reverse">
            <Lock className="h-4 w-4 text-teal-700" />
            <span>{language === "ar" ? "نسخ الاستبيان المعتمدة" : "Published Questionnaire Versions"}</span>
          </CardTitle>
          <CardDescription className="text-xs">
            {language === "ar"
              ? "النسخ المعتمدة تخضع لتجميد غير قابل للتعديل لضمان تطابق تاريخ التقييمات."
              : "Questionnaire versions are pinned to assessment sessions to ensure absolute reproducibility."}
          </CardDescription>
        </CardHeader>

        <CardContent className="p-0">
          <div className="divide-y divide-border text-xs">
            {versions.length === 0 ? (
              <div className="p-4 flex items-center justify-between">
                <div>
                  <div className="font-bold text-sm">Version 1.0.0 (Production Master)</div>
                  <div className="text-muted-foreground text-xs">Authoritative baseline pinned to all active assessments.</div>
                </div>
                <Badge variant="success">PUBLISHED</Badge>
              </div>
            ) : (
              versions.map((v) => (
                <div key={v.id} className="p-4 flex items-center justify-between">
                  <div className="space-y-0.5">
                    <div className="flex items-center space-x-2 rtl:space-x-reverse">
                      <span className="font-bold text-sm">Version {v.version_number}</span>
                      <Badge variant={v.is_published ? "success" : "outline"} className="text-[10px]">
                        {v.is_published ? "PUBLISHED" : "DRAFT"}
                      </Badge>
                    </div>
                    <div className="text-muted-foreground text-xs">
                      {v.clinical_notes || "Clinical sign-off completed."}
                    </div>
                  </div>
                  <div className="text-[10px] text-muted-foreground">
                    {v.published_at ? new Date(v.published_at).toLocaleDateString() : "Active"}
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* 11 Clinical Domains Architecture */}
      <Card className="border-border shadow-sm">
        <CardHeader className="pb-3 border-b border-border/60">
          <CardTitle className="text-base font-bold flex items-center space-x-2 rtl:space-x-reverse">
            <Layers className="h-4 w-4 text-teal-700" />
            <span>{language === "ar" ? "المجالات السريرية الـ 11 وهيكل التفرع" : "11 Clinical Domains Architecture"}</span>
          </CardTitle>
          <CardDescription className="text-xs">
            Structured according to EAU 2024 and AUA/ASRM clinical guidelines for male reproductive evaluation.
          </CardDescription>
        </CardHeader>

        <CardContent className="p-0">
          <div className="divide-y divide-border text-xs">
            {domains.map((d, index) => (
              <div key={d.code} className="p-3.5 flex items-center justify-between hover:bg-slate-50/50 dark:hover:bg-slate-900/50">
                <div className="space-y-0.5">
                  <div className="flex items-center space-x-2 rtl:space-x-reverse">
                    <span className="font-mono text-teal-700 font-bold text-xs">{index + 1}.</span>
                    <span className="font-semibold text-slate-900 dark:text-white">
                      {language === "ar" ? d.nameAr : d.nameEn}
                    </span>
                    <span className="font-mono text-[10px] text-muted-foreground">({d.code})</span>
                  </div>
                </div>

                <Badge variant="secondary" className="text-[10px]">
                  {d.questions} {language === "ar" ? "أسئلة معتمدة" : "Questions"}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
