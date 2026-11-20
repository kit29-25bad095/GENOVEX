"use client";

import React from "react";
import Link from "next/link";
import { useLanguage } from "@/context/LanguageContext";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ShieldCheck, Lock, FileText, ArrowLeft, AlertCircle, Info, HeartHandshake, Scale } from "lucide-react";
import { IntellectualPropertyLicensing } from "@/components/intellectual-property-licensing";

export default function PrivacyPolicyPage() {
  const { t, language } = useLanguage();

  return (
    <div className="container mx-auto px-4 sm:px-6 py-10 max-w-4xl space-y-8">
      {/* Header */}
      <div className="space-y-2">
        <Link href="/" className="text-xs text-muted-foreground hover:text-teal-700 flex items-center space-x-1.5 rtl:space-x-reverse">
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>{language === "ar" ? "العودة للرئيسية" : "Back to Home"}</span>
        </Link>
        <Badge variant="outline" className="text-teal-700 border-teal-300">
          <ShieldCheck className="h-3.5 w-3.5 mr-1 rtl:mr-0 rtl:ml-1 inline" />
          Governance & Health Data Protection
        </Badge>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          {language === "ar" ? "الخصوصية وإدارة الموافقة الطبية" : "Privacy Policy & Clinical Consent Management"}
        </h1>
        <p className="text-xs text-muted-foreground">
          {language === "ar"
            ? "التزامنا الصارم بالسرية الطبية التامة وحماية البيانات الصحية وفق المعايير الإقليمية والدولية."
            : "Our adherence to healthcare data ethics, confidentiality, and deterministic decision boundaries."}
        </p>
      </div>

      {/* Section 1: Non-Diagnostic Medical Disclaimer */}
      <Card className="border-border shadow-sm">
        <CardHeader className="pb-3 border-b border-border/60">
          <div className="flex items-center space-x-2 rtl:space-x-reverse">
            <Info className="h-5 w-5 text-teal-700" />
            <CardTitle className="text-base font-bold">
              {language === "ar" ? "1. إخلاء المسؤولية الطبية ونطاق المنصة" : "1. Clinical Decision Support Scope & Medical Disclaimer"}
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="pt-4 text-xs text-muted-foreground leading-relaxed space-y-3">
          <p>
            GENOVEX is a digital health triage and clinical decision support system designed to facilitate pre-consultation risk stratification and patient education regarding male reproductive, sexual, and fertility health.
          </p>
          <div className="p-3 bg-amber-50 dark:bg-amber-950/30 text-amber-950 dark:text-amber-200 border border-amber-200 dark:border-amber-900 rounded-md font-medium">
            <strong>CRITICAL NOTICE:</strong> GENOVEX does NOT provide a definitive medical diagnosis, nor does it prescribe pharmaceutical therapies. It does not replace an in-person physical clinical examination, scrotal Doppler ultrasound, endocrine lab testing, or standard semen analysis performed by an accredited laboratory.
          </div>
          <p>
            In the event of acute, severe testicular pain, immediate emergency hospital attendance within the 6-hour surgical golden window is mandatory to exclude testicular torsion.
          </p>
        </CardContent>
      </Card>

      {/* Section 2: Data Protection & Anonymization */}
      <Card className="border-border shadow-sm">
        <CardHeader className="pb-3 border-b border-border/60">
          <div className="flex items-center space-x-2 rtl:space-x-reverse">
            <Lock className="h-5 w-5 text-teal-700" />
            <CardTitle className="text-base font-bold">
              {language === "ar" ? "2. سرية وتشفير البيانات الصحية" : "2. Health Data Protection & Anonymous Sessions"}
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="pt-4 text-xs text-muted-foreground leading-relaxed space-y-3">
          <p>
            We recognize the highly sensitive nature of male reproductive health. You are permitted to undertake full assessments anonymously using pseudonymous session tokens without disclosing your legal identity.
          </p>
          <ul className="list-disc pl-5 rtl:pl-0 rtl:pr-5 space-y-1 text-slate-700 dark:text-slate-300">
            <li>All transmissions are secured via TLS 1.3 encryption.</li>
            <li>No reproductive health answers or risk factors are ever logged in plaintext server stdout/stderr.</li>
            <li>No patient health data is sold, monetized, or shared with third-party advertisers.</li>
          </ul>
        </CardContent>
      </Card>

      {/* Section 3: Consent Withdrawal */}
      <Card className="border-border shadow-sm">
        <CardHeader className="pb-3 border-b border-border/60">
          <div className="flex items-center space-x-2 rtl:space-x-reverse">
            <HeartHandshake className="h-5 w-5 text-teal-700" />
            <CardTitle className="text-base font-bold">
              {language === "ar" ? "3. حقوق المريض وإلغاء الموافقة" : "3. Patient Rights & Consent Revocation"}
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="pt-4 text-xs text-muted-foreground leading-relaxed space-y-3">
          <p>
            Under international health privacy standards and local healthcare data governance, you retain full ownership of your health records. You may request deletion of your account and associated assessment snapshots at any time by contacting compliance@genovex.health.
          </p>
          <div className="pt-2">
            <Link href="/assessment">
              <Button variant="clinical" size="sm" className="text-xs font-semibold">
                {language === "ar" ? "الموافقة وبدء التقييم" : "Acknowledge & Proceed to Assessment"}
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>

      {/* Section 4: Intellectual Property & Third-Party Licensing */}
      <div className="space-y-4 pt-4">
        <IntellectualPropertyLicensing />
      </div>
    </div>
  );
}
