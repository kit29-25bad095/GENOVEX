"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useLanguage } from "@/context/LanguageContext";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  FileEdit,
  ArrowLeft,
  CheckCircle2,
  FileCheck,
  PlusCircle,
  Archive,
  Eye,
  History,
} from "lucide-react";

export default function MedicalContentAdminPage() {
  const { t, language } = useLanguage();
  const [activeTab, setActiveTab] = useState<"conditions" | "categories">("conditions");

  const sampleConditions = [
    {
      id: 1,
      slug: "varicocele",
      name_en: "Clinical Varicocele (Scrotal Vein Dilation)",
      name_ar: "دوالي الخصية السريرية (توسع الأوردة المنوية)",
      status: "PUBLISHED",
      version: "v2.1",
      last_reviewed_by: "Dr. Tarek Al-Mansoor (DHA-P-00129)",
      updated_at: "2026-11-18",
    },
    {
      id: 2,
      slug: "non-obstructive-azoospermia",
      name_en: "Non-Obstructive Azoospermia (NOA)",
      name_ar: "فقد النطاف غير الانسدادي (NOA)",
      status: "PUBLISHED",
      version: "v1.4",
      last_reviewed_by: "Dr. Mansoor Al-Ketbi",
      updated_at: "2026-11-18",
    },
    {
      id: 3,
      slug: "acute-scrotal-pain-torsion",
      name_en: "Acute Scrotal Pain Emergency Pathway",
      name_ar: "مسار طوارئ ألم الصفن الحاد",
      status: "PUBLISHED",
      version: "v1.0",
      last_reviewed_by: "Dr. Tarek Al-Mansoor",
      updated_at: "2026-11-19",
    },
  ];

  return (
    <div className="container mx-auto px-4 sm:px-6 py-10 max-w-5xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Link href="/admin" className="text-xs text-muted-foreground hover:text-teal-700 flex items-center space-x-1.5 rtl:space-x-reverse">
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>{language === "ar" ? "العودة للوحة الإدارة" : "Back to Admin"}</span>
        </Link>
        <Badge variant="outline" className="text-teal-700 border-teal-300">
          Medical CMS & Versioning
        </Badge>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white flex items-center space-x-2.5 rtl:space-x-reverse">
            <FileEdit className="h-7 w-7 text-teal-700" />
            <span>{t("admin.content.title")}</span>
          </h1>
          <p className="text-xs text-muted-foreground">
            {language === "ar"
              ? "إدارة المحتوى الطبي ثنائي اللغة المعتمد والمقيد بمراجعات سريرية غير قابلة للتغيير."
              : "Authoring, translation, and clinician review governance for public health conditions."}
          </p>
        </div>
      </div>

      {/* Conditions Table */}
      <Card className="border-border shadow-sm">
        <CardHeader className="pb-3 border-b border-border/60">
          <CardTitle className="text-base font-bold">
            {language === "ar" ? "الحالات الطبية المنشورة" : "Published Medical Conditions"}
          </CardTitle>
          <CardDescription className="text-xs">
            {language === "ar"
              ? "كل حالة تخضع للمراجعة والاعتماد الطبي قبل ظهورها في المكتبة الصحية العامة."
              : "Every condition requires formal clinician review before public health library visibility."}
          </CardDescription>
        </CardHeader>

        <CardContent className="p-0">
          <div className="divide-y divide-border text-xs">
            {sampleConditions.map((cond) => (
              <div key={cond.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50/50 dark:hover:bg-slate-900/50 transition-colors">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2 rtl:space-x-reverse">
                    <span className="font-bold text-sm text-slate-900 dark:text-white">{cond.name_en}</span>
                    <Badge variant="success" className="text-[10px]">
                      {cond.status}
                    </Badge>
                    <span className="text-[10px] font-mono bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">
                      {cond.version}
                    </span>
                  </div>
                  <div className="text-slate-600 dark:text-slate-400 font-arabic text-xs">
                    {cond.name_ar}
                  </div>
                  <div className="text-[11px] text-muted-foreground flex items-center space-x-2 rtl:space-x-reverse pt-0.5">
                    <CheckCircle2 className="h-3 w-3 text-teal-600" />
                    <span>Reviewed by: {cond.last_reviewed_by}</span>
                    <span>•</span>
                    <span>Updated: {cond.updated_at}</span>
                  </div>
                </div>

                <div className="flex items-center space-x-2 rtl:space-x-reverse">
                  <Link href={`/library`}>
                    <Button variant="outline" size="sm" className="text-xs h-8">
                      <Eye className="h-3.5 w-3.5 mr-1 rtl:mr-0 rtl:ml-1" />
                      Preview
                    </Button>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
