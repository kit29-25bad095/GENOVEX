"use client";

import React from "react";
import Link from "next/link";
import { useLanguage } from "@/context/LanguageContext";
import { IntellectualPropertyLicensing } from "@/components/intellectual-property-licensing";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, ShieldCheck, Scale, FileText, CheckCircle2 } from "lucide-react";

export default function LicensingPage() {
  const { language } = useLanguage();
  const isAr = language === "ar";

  return (
    <div className="container mx-auto px-4 sm:px-6 py-10 max-w-5xl space-y-10">
      {/* Navigation Header */}
      <div className="space-y-2">
        <Link
          href="/"
          className="text-xs text-muted-foreground hover:text-teal-700 flex items-center space-x-1.5 rtl:space-x-reverse"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>{isAr ? "العودة للرئيسية" : "Back to Home"}</span>
        </Link>
        <Badge variant="outline" className="text-teal-700 border-teal-300">
          <Scale className="h-3.5 w-3.5 mr-1 rtl:mr-0 rtl:ml-1 inline" />
          Open Source &amp; IP Governance
        </Badge>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          {isAr ? "الملكية الفكرية والتراخيص البرمجية" : "Intellectual Property & Software Licensing"}
        </h1>
        <p className="text-xs sm:text-sm text-muted-foreground max-w-2xl">
          {isAr
            ? "توثيق شامل لتراخيص البرمجيات مفتوحة المصدر والخدمات السحابية المستخدمة في منصة GENOVEX الصحية."
            : "Comprehensive disclosure of open-source libraries, runtimes, frameworks, and third-party AI service terms powering the GENOVEX healthcare platform."}
        </p>
      </div>

      {/* The Visual Licensing Component */}
      <IntellectualPropertyLicensing />

      {/* Additional Details & Disclosures */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="border-border shadow-sm">
          <CardHeader className="pb-3 border-b border-border/60">
            <div className="flex items-center space-x-2 rtl:space-x-reverse">
              <ShieldCheck className="h-5 w-5 text-teal-700" />
              <CardTitle className="text-base font-bold">
                {isAr ? "حقوق الملكية الفكرية لمنصة GENOVEX" : "GENOVEX Proprietary Intellectual Property"}
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="pt-4 text-xs text-muted-foreground leading-relaxed space-y-2.5">
            <p>
              {isAr
                ? "تعتبر شجرة القواعد السريرية الحتمية (Deterministic Clinical Rules)، واستبيان التقييم التكيفي المكون من 11 مجالاً، ومنهجية الفرز الطبي رايات حمراء حقوق ملكية فكرية محمية لمنصة GENOVEX."
                : "The proprietary deterministic clinical rule DAG, 11-domain adaptive questionnaire branching logic, and urgent red-flag clinical triage matrices are proprietary intellectual property of GENOVEX."}
            </p>
            <p>
              {isAr
                ? "جميع الحقوق محفوظة لصالح منصة جينوفيكس للرعاية الصحية © 2026."
                : "All rights reserved. Unauthorized reproduction, clinical rule scraping, or reverse engineering of the deterministic compiler is strictly prohibited."}
            </p>
          </CardContent>
        </Card>

        <Card className="border-border shadow-sm">
          <CardHeader className="pb-3 border-b border-border/60">
            <div className="flex items-center space-x-2 rtl:space-x-reverse">
              <FileText className="h-5 w-5 text-indigo-600" />
              <CardTitle className="text-base font-bold">
                {isAr ? "الامتثال لتراخيص البرمجيات الحرة" : "Open-Source License Compliance"}
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="pt-4 text-xs text-muted-foreground leading-relaxed space-y-2.5">
            <p>
              {isAr
                ? "تلتزم GENOVEX بكافة الشروط والحقوق المقررة في تراخيص MIT و Apache 2.0 و PSF و PostgreSQL، وتتيح الإسناد القانوني اللازم لكافة المطورين والمؤسسات المساهمة."
                : "GENOVEX complies with all notice, attribution, and redistribution requirements stipulated under the MIT License, Apache License 2.0, Python Software Foundation License, and PostgreSQL License."}
            </p>
            <div className="flex items-center space-x-1.5 text-emerald-600 dark:text-emerald-400 font-medium">
              <CheckCircle2 className="h-4 w-4" />
              <span>Full compliance with third-party service terms and software notices.</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
