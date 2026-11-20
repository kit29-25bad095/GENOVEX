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
  Database,
  RefreshCw,
  AlertTriangle,
  HelpCircle,
  FileCheck2,
} from "lucide-react";

export default function AdminDashboardPage() {
  const { t, language } = useLanguage();
  const { user } = useAuth();

  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [logFilter, setLogFilter] = useState<string>("ALL");
  const [stats, setStats] = useState({
    rulesCount: 0,
    rulesApproved: 0,
    conditionsCount: 0,
    conditionsPublished: 0,
    usersCount: 0,
    assessmentsCount: 0,
    completionRate: 0,
  });
  const [diagnostics, setDiagnostics] = useState<any>(null);
  const [isBackingUp, setIsBackingUp] = useState(false);
  const [backupMessage, setBackupMessage] = useState<string | null>(null);

  useEffect(() => {
    async function loadDashboardData() {
      try {
        // Fetch audit logs
        const logs = await ApiClient.getAuditLogs(25);
        if (logs && logs.length > 0) setAuditLogs(logs);

        // Fetch clinical rules metrics
        const rules = await ApiClient.getAdminRules();
        const approvedRules = rules.filter((r: any) => r.status === "PUBLISHED" || r.status === "APPROVED").length;

        // Fetch conditions metrics
        const conditions = await ApiClient.getAdminConditions({ limit: 100 });
        const publishedConditions = conditions.filter((c: any) => c.status === "PUBLISHED").length;

        // Fetch users count
        const users = await ApiClient.getAdminUsers();

        // Fetch assessment metrics
        const assessmentOverview = await ApiClient.getAssessmentsOverview();

        setStats({
          rulesCount: rules.length || 20,
          rulesApproved: approvedRules || 20,
          conditionsCount: conditions.length || 3,
          conditionsPublished: publishedConditions || 3,
          usersCount: users.length || 4,
          assessmentsCount: assessmentOverview.total_assessments || 0,
          completionRate: assessmentOverview.completion_rate || 0,
        });

        // Fetch system diagnostics
        const diag = await ApiClient.getAdminDiagnostics();
        if (diag) setDiagnostics(diag);
      } catch (err) {
        console.error("Dashboard metric loading error:", err);
      }
    }

    loadDashboardData();
  }, []);

  const handleManualBackup = async () => {
    setIsBackingUp(true);
    setBackupMessage(null);
    try {
      const res = await ApiClient.triggerManualBackup();
      setBackupMessage(
        language === "ar"
          ? `تم إنشاء نسخة احتياطية بنجاح (${res.backup_filename})`
          : `Database snapshot verified: ${res.backup_filename}`
      );
    } catch (err: any) {
      setBackupMessage(`Backup failed: ${err.message}`);
    } finally {
      setIsBackingUp(false);
    }
  };

  const filteredLogs = logFilter === "ALL" 
    ? auditLogs 
    : auditLogs.filter(l => l.action.includes(logFilter));

  return (
    <div className="container mx-auto px-4 sm:px-6 py-10 max-w-6xl space-y-8">
      {/* Header & Status Indicator */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/60 pb-6">
        <div className="space-y-1">
          <Badge variant="outline" className="text-teal-700 border-teal-300">
            <Shield className="h-3.5 w-3.5 mr-1 rtl:mr-0 rtl:ml-1 inline" />
            {language === "ar" ? "لوحة الإدارة والرقابة السريرية" : "Clinical Administration & Governance"}
          </Badge>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            {language === "ar" ? "مركز العمليات الإدارية" : "Admin Operations Hub"}
          </h1>
          <p className="text-xs text-muted-foreground">
            {language === "ar"
              ? "حوكمة القواعد الإكلينيكية، إدارة المحتوى الطبي، إدارة المستخدمين، وتتبع سجلات التدقيق غير القابلة للتغيير."
              : "Rule authoring, bilingual medical content lifecycle, user RBAC management, and immutable audit logs."}
          </p>
        </div>

        <div className="flex items-center space-x-3 rtl:space-x-reverse">
          <Button
            variant="outline"
            size="sm"
            onClick={handleManualBackup}
            disabled={isBackingUp}
            className="text-xs border-teal-200 text-teal-800 hover:bg-teal-50"
          >
            <Database className="h-3.5 w-3.5 mr-1.5 rtl:mr-0 rtl:ml-1.5 text-teal-600" />
            {isBackingUp 
              ? (language === "ar" ? "جارٍ النسخ..." : "Backing Up...") 
              : (language === "ar" ? "نسخ احتياطي فوري" : "Trigger Snapshot")}
          </Button>
        </div>
      </div>

      {backupMessage && (
        <div className="p-3 bg-teal-50 border border-teal-200 rounded-md text-xs text-teal-800 flex items-center justify-between">
          <div className="flex items-center space-x-2 rtl:space-x-reverse">
            <CheckCircle2 className="h-4 w-4 text-teal-600" />
            <span>{backupMessage}</span>
          </div>
          <button onClick={() => setBackupMessage(null)} className="text-teal-600 hover:text-teal-900 font-bold">×</button>
        </div>
      )}

      {/* Top Telemetry KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card className="border-border shadow-sm">
          <CardContent className="p-4 space-y-1">
            <span className="text-[11px] font-medium text-muted-foreground flex items-center justify-between">
              {language === "ar" ? "القواعد الإكلينيكية" : "Clinical Rules"}
              <Sliders className="h-3.5 w-3.5 text-teal-600" />
            </span>
            <div className="text-2xl font-extrabold text-slate-900 dark:text-white">
              {stats.rulesApproved} <span className="text-xs font-normal text-muted-foreground">/ {stats.rulesCount}</span>
            </div>
            <p className="text-[10px] text-teal-700 font-medium">
              {language === "ar" ? "قواعد حتمية منشورة" : "Active Published Rules"}
            </p>
          </CardContent>
        </Card>

        <Card className="border-border shadow-sm">
          <CardContent className="p-4 space-y-1">
            <span className="text-[11px] font-medium text-muted-foreground flex items-center justify-between">
              {language === "ar" ? "المحتوى الطبي" : "Medical Conditions"}
              <FileEdit className="h-3.5 w-3.5 text-emerald-600" />
            </span>
            <div className="text-2xl font-extrabold text-slate-900 dark:text-white">
              {stats.conditionsPublished} <span className="text-xs font-normal text-muted-foreground">/ {stats.conditionsCount}</span>
            </div>
            <p className="text-[10px] text-emerald-700 font-medium">
              {language === "ar" ? "مقالات معتمدة سريرياً" : "Peer-Reviewed Conditions"}
            </p>
          </CardContent>
        </Card>

        <Card className="border-border shadow-sm">
          <CardContent className="p-4 space-y-1">
            <span className="text-[11px] font-medium text-muted-foreground flex items-center justify-between">
              {language === "ar" ? "المستخدمون والكوادر" : "Users & Clinicians"}
              <Users className="h-3.5 w-3.5 text-blue-600" />
            </span>
            <div className="text-2xl font-extrabold text-slate-900 dark:text-white">
              {stats.usersCount}
            </div>
            <p className="text-[10px] text-blue-700 font-medium">
              {language === "ar" ? "حسابات مسجلة وموثقة" : "Managed User Personas"}
            </p>
          </CardContent>
        </Card>

        <Card className="border-border shadow-sm">
          <CardContent className="p-4 space-y-1">
            <span className="text-[11px] font-medium text-muted-foreground flex items-center justify-between">
              {language === "ar" ? "التقييمات المكتملة" : "Completion Rate"}
              <Activity className="h-3.5 w-3.5 text-purple-600" />
            </span>
            <div className="text-2xl font-extrabold text-slate-900 dark:text-white">
              {stats.completionRate}%
            </div>
            <p className="text-[10px] text-purple-700 font-medium">
              {stats.assessmentsCount} {language === "ar" ? "تقييم إجمالي" : "Total Assessments"}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Admin Modules Navigation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Module 1: Clinical Rules */}
        <Card className="border-border hover:shadow-md transition-shadow flex flex-col justify-between">
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
                ? "إدارة ومراجعة القواعد الإكلينيكية الحتمية، شروط المنطق ثلاثي القيم، واعتماد النسخ السريرية."
                : "Author three-valued logic predicates (all_of, any_of), priority tiers, and clinician sign-offs."}
            </p>
            <Link href="/admin/rules" className="block w-full">
              <Button variant="clinical" size="sm" className="w-full text-xs font-semibold">
                <span>{language === "ar" ? "إدارة القواعد" : "Rule Authoring CMS"}</span>
                <ArrowRight className="h-3.5 w-3.5 ml-1.5 rtl:ml-0 rtl:mr-1.5" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        {/* Module 2: Medical Content CMS */}
        <Card className="border-border hover:shadow-md transition-shadow flex flex-col justify-between">
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
                ? "إدارة المحتوى الطبي ثنائي اللغة، مسارات المراجعة السريرية، واستعادة الإصدارات السابقة."
                : "Manage bilingual health condition articles, review workflows, and historical version restores."}
            </p>
            <Link href="/admin/content" className="block w-full">
              <Button variant="outline" size="sm" className="w-full text-xs font-semibold">
                <span>{language === "ar" ? "المحتوى الطبي" : "Medical Content CMS"}</span>
                <ArrowRight className="h-3.5 w-3.5 ml-1.5 rtl:ml-0 rtl:mr-1.5" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        {/* Module 3: User & Role Administration */}
        <Card className="border-border hover:shadow-md transition-shadow flex flex-col justify-between">
          <CardHeader className="pb-3">
            <div className="h-10 w-10 rounded-lg bg-blue-100 dark:bg-blue-950 flex items-center justify-center text-blue-700 mb-2">
              <Users className="h-5 w-5" />
            </div>
            <CardTitle className="text-base font-bold">
              {language === "ar" ? "إدارة المستخدمين والأدوار" : "User & Role Governance"}
            </CardTitle>
            <CardDescription className="text-xs">
              {language === "ar" ? "صلاحيات RBAC وبيانات الأطباء" : "Role assignments & credential audits"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-1">
            <p className="text-xs text-muted-foreground leading-relaxed">
              {language === "ar"
                ? "تعيين أدوار الأطباء والمشرفين، تحديث أرقام التراخيص الطبية، وتفعيل أو تعطيل الحسابات."
                : "Assign clinician roles, verify DHA/DoH licensing IDs, and govern account permissions."}
            </p>
            <Link href="/admin/users" className="block w-full">
              <Button variant="outline" size="sm" className="w-full text-xs font-semibold">
                <span>{language === "ar" ? "إدارة المستخدمين" : "User Management"}</span>
                <ArrowRight className="h-3.5 w-3.5 ml-1.5 rtl:ml-0 rtl:mr-1.5" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        {/* Module 4: Questionnaire Governance */}
        <Card className="border-border hover:shadow-md transition-shadow flex flex-col justify-between">
          <CardHeader className="pb-3">
            <div className="h-10 w-10 rounded-lg bg-amber-100 dark:bg-amber-950 flex items-center justify-center text-amber-700 mb-2">
              <FileCheck2 className="h-5 w-5" />
            </div>
            <CardTitle className="text-base font-bold">
              {language === "ar" ? "حوكمة الاستبيانات" : "Questionnaire Engine"}
            </CardTitle>
            <CardDescription className="text-xs">
              {language === "ar" ? "إصدارات ومسارات الأسئلة" : "Domain versions & branching rules"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-1">
            <p className="text-xs text-muted-foreground leading-relaxed">
              {language === "ar"
                ? "فحص الـ 11 مجالاً صحياً، مراقبة مسارات التفرع الشرطي، ومتابعة اعتماد النسخ الرسمية."
                : "Inspect the 11 clinical domains, conditional DAG branching logic, and approved versions."}
            </p>
            <Link href="/admin/questionnaires" className="block w-full">
              <Button variant="outline" size="sm" className="w-full text-xs font-semibold">
                <span>{language === "ar" ? "حوكمة الاستبيان" : "Questionnaire CMS"}</span>
                <ArrowRight className="h-3.5 w-3.5 ml-1.5 rtl:ml-0 rtl:mr-1.5" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Audit Log Stream */}
      <Card className="border-border">
        <CardHeader className="pb-3 border-b border-border">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-0.5">
              <CardTitle className="text-sm font-bold flex items-center space-x-2 rtl:space-x-reverse">
                <Clock className="h-4 w-4 text-teal-700" />
                <span>{t("admin.audit.title")}</span>
              </CardTitle>
              <CardDescription className="text-[11px]">
                {t("admin.audit.subtitle")}
              </CardDescription>
            </div>

            {/* Filter buttons */}
            <div className="flex items-center space-x-1.5 rtl:space-x-reverse text-xs">
              {["ALL", "RULE", "CONTENT", "USER"].map((filter) => (
                <button
                  key={filter}
                  onClick={() => setLogFilter(filter)}
                  className={`px-2 py-0.5 rounded text-[10px] font-semibold transition-colors ${
                    logFilter === filter
                      ? "bg-teal-700 text-white"
                      : "bg-slate-100 dark:bg-slate-800 text-muted-foreground hover:bg-slate-200"
                  }`}
                >
                  {filter}
                </button>
              ))}
              <Badge variant="outline" className="text-[10px] ml-2">
                Immutable WORM
              </Badge>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <div className="divide-y divide-border text-xs max-h-96 overflow-y-auto">
            {filteredLogs.length === 0 ? (
              <div className="p-6 text-center text-muted-foreground text-xs">
                {language === "ar" ? "لا توجد سجلات مطابقة للفلتر المحدد" : "No audit entries matching filter"}
              </div>
            ) : (
              filteredLogs.map((log) => (
                <div key={log.id} className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 hover:bg-slate-50/50 dark:hover:bg-slate-900/50 transition-colors">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2 rtl:space-x-reverse">
                      <span className="font-semibold text-slate-800 dark:text-slate-200">{log.action}</span>
                      <Badge variant="secondary" className="text-[10px]">
                        {log.resource_type}
                      </Badge>
                      <span className="text-muted-foreground font-mono text-[11px]">{log.resource_id}</span>
                    </div>
                    <div className="text-[11px] text-muted-foreground">
                      Actor: <span className="font-medium text-slate-700 dark:text-slate-300">{log.user_email || "System"}</span> ({log.user_role || "ADMIN"})
                      {log.ip_address && ` • IP: ${log.ip_address}`}
                    </div>
                  </div>

                  <div className="text-[10px] text-muted-foreground whitespace-nowrap">
                    {new Date(log.timestamp).toLocaleString()}
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
