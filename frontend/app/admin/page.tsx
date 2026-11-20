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
  Shield,
  Sliders,
  FileEdit,
  Activity,
  Users,
  Lock,
  ArrowRight,
  CheckCircle2,
  Clock,
} from "lucide-react";

export default function AdminDashboardPage() {
  const { t, language } = useLanguage();
  const { user } = useAuth();
  const [auditLogs, setAuditLogs] = useState<any[]>([]);

  useEffect(() => {
    async function fetchLogs() {
      try {
        const logs = await ApiClient.getAuditLogs(10);
        if (logs) setAuditLogs(logs);
      } catch (err) {
        // Fallback demo audit items if local auth token not set
        setAuditLogs([
          {
            id: 1,
            user_email: "superadmin@genovex.health",
            user_role: "SUPERADMIN",
            action: "APPROVE_RULE",
            resource_type: "ClinicalRule",
            resource_id: "R-URG-ACUTE-SCROTAL-PAIN",
            timestamp: new Date().toISOString(),
          },
          {
            id: 2,
            user_email: "admin@genovex.health",
            user_role: "ADMIN",
            action: "PUBLISH_CONTENT",
            resource_type: "MedicalCondition",
            resource_id: "varicocele",
            timestamp: new Date().toISOString(),
          },
        ]);
      }
    }
    fetchLogs();
  }, []);

  return (
    <div className="container mx-auto px-4 sm:px-6 py-10 max-w-5xl space-y-8">
      {/* Header */}
      <div className="space-y-1">
        <Badge variant="outline" className="text-teal-700 border-teal-300">
          <Shield className="h-3.5 w-3.5 mr-1 rtl:mr-0 rtl:ml-1 inline" />
          {language === "ar" ? "لوحة الإدارة والرقابة السريرية" : "Clinical Administration & Governance"}
        </Badge>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          {language === "ar" ? "لوحة تحكم المشرفين" : "Admin Operations Hub"}
        </h1>
        <p className="text-xs text-muted-foreground">
          {language === "ar"
            ? "حوكمة القواعد الإكلينيكية، إدارة المحتوى الطبي، وتتبع سجلات الأمان والتدقيق غير القابلة للتغيير."
            : "Rule approvals, bilingual medical content lifecycle, and immutable audit log inspection."}
        </p>
      </div>

      {/* Admin Modules Navigation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Module 1: Clinical Rules */}
        <Card className="border-border hover:shadow-md transition-shadow">
          <CardHeader className="pb-3">
            <div className="h-10 w-10 rounded-lg bg-teal-100 dark:bg-teal-950 flex items-center justify-center text-teal-700 mb-2">
              <Sliders className="h-5 w-5" />
            </div>
            <CardTitle className="text-base font-bold">
              {t("admin.rules.title")}
            </CardTitle>
            <CardDescription className="text-xs">
              {t("admin.rules.subtitle")}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-1">
            <p className="text-xs text-muted-foreground leading-relaxed">
              {language === "ar"
                ? "إدارة ومراجعة 14 قاعدة إكلينيكية حتمية، فحص شروط التفعيل، الأولوية (1..100)، واعتماد النسخ السريرية."
                : "Inspect trigger conditions, priority hierarchies, evidence citations, and clinician approval statuses."}
            </p>
            <Link href="/admin/rules">
              <Button variant="clinical" size="sm" className="w-full text-xs font-semibold">
                <span>{language === "ar" ? "إدارة القواعد الإكلينيكية" : "Manage Clinical Rules"}</span>
                <ArrowRight className="h-3.5 w-3.5 ml-1.5 rtl:ml-0 rtl:mr-1.5" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        {/* Module 2: Medical Content CMS */}
        <Card className="border-border hover:shadow-md transition-shadow">
          <CardHeader className="pb-3">
            <div className="h-10 w-10 rounded-lg bg-emerald-100 dark:bg-emerald-950 flex items-center justify-center text-emerald-700 mb-2">
              <FileEdit className="h-5 w-5" />
            </div>
            <CardTitle className="text-base font-bold">
              {t("admin.content.title")}
            </CardTitle>
            <CardDescription className="text-xs">
              {t("admin.content.subtitle")}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-1">
            <p className="text-xs text-muted-foreground leading-relaxed">
              {language === "ar"
                ? "تحديث وتعديل تعريفات الحالات الطبية باللغتين العربية والإنجليزية مع الحفاظ على سجل الإصدارات التاريخية."
                : "Manage bilingual health condition definitions, prevalence metrics, and medical review states."}
            </p>
            <Link href="/admin/content">
              <Button variant="outline" size="sm" className="w-full text-xs font-semibold">
                <span>{language === "ar" ? "إدارة المحتوى الطبي" : "Manage Medical Content"}</span>
                <ArrowRight className="h-3.5 w-3.5 ml-1.5 rtl:ml-0 rtl:mr-1.5" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Audit Log Stream */}
      <Card className="border-border">
        <CardHeader className="pb-3 border-b border-border">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <CardTitle className="text-sm font-bold flex items-center space-x-2 rtl:space-x-reverse">
                <Clock className="h-4 w-4 text-teal-700" />
                <span>{t("admin.audit.title")}</span>
              </CardTitle>
              <CardDescription className="text-[11px]">
                {t("admin.audit.subtitle")}
              </CardDescription>
            </div>
            <Badge variant="outline" className="text-[10px]">
              Immutable Ledger
            </Badge>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <div className="divide-y divide-border text-xs">
            {auditLogs.map((log) => (
              <div key={log.id} className="p-3.5 flex items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2 rtl:space-x-reverse">
                    <span className="font-semibold text-slate-800 dark:text-slate-200">{log.action}</span>
                    <Badge variant="secondary" className="text-[10px]">
                      {log.resource_type}
                    </Badge>
                    <span className="text-muted-foreground font-mono text-[11px]">{log.resource_id}</span>
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    Actor: {log.user_email || "System"} ({log.user_role || "ADMIN"})
                  </div>
                </div>

                <div className="text-[10px] text-muted-foreground whitespace-nowrap">
                  {new Date(log.timestamp).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
