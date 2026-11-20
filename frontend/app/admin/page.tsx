"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { useLanguage } from "@/context/LanguageContext";
import { useAuth } from "@/context/AuthContext";
import {
  ApiClient,
  AdminOverviewResponse,
  AdminUserListItem,
  AdminUserDetailResponse,
  AdminAssessmentStatsResponse,
  AdminClinicianOperationsResponse,
  AdminAuditEventListResponse,
  AdminHealthResponse,
  AdminConfigResponse,
} from "@/lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Shield,
  Sliders,
  FileEdit,
  Activity,
  Users,
  Lock,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Search,
  RefreshCw,
  Eye,
  UserCheck,
  UserX,
  UserCog,
  Database,
  Cpu,
  Server,
  Settings,
  ChevronLeft,
  ChevronRight,
  HelpCircle,
  XCircle,
} from "lucide-react";

export default function AdminDashboardPage() {
  const { t, language } = useLanguage();
  const { user } = useAuth();
  const isAr = language === "ar";

  // Tab State
  const [activeTab, setActiveTab] = useState<"overview" | "users" | "assessments" | "clinicians" | "audit" | "health">("overview");

  // Data States
  const [overview, setOverview] = useState<AdminOverviewResponse | null>(null);
  const [usersList, setUsersList] = useState<AdminUserListItem[]>([]);
  const [usersTotal, setUsersTotal] = useState(0);
  const [usersPage, setUsersPage] = useState(1);
  const [usersTotalPages, setUsersTotalPages] = useState(1);
  const [userSearch, setUserSearch] = useState("");
  const [userRoleFilter, setUserRoleFilter] = useState("");
  const [userStatusFilter, setUserStatusFilter] = useState("");

  const [assessmentStats, setAssessmentStats] = useState<AdminAssessmentStatsResponse | null>(null);
  const [clinicianOps, setClinicianOps] = useState<AdminClinicianOperationsResponse | null>(null);
  const [auditEvents, setAuditEvents] = useState<any[]>([]);
  const [auditPage, setAuditPage] = useState(1);
  const [auditTotalPages, setAuditTotalPages] = useState(1);
  const [auditActionFilter, setAuditActionFilter] = useState("");

  const [health, setHealth] = useState<AdminHealthResponse | null>(null);
  const [configData, setConfigData] = useState<AdminConfigResponse | null>(null);

  // Modal States
  const [selectedUserDetail, setSelectedUserDetail] = useState<AdminUserDetailResponse | null>(null);
  const [statusConfirmUser, setStatusConfirmUser] = useState<AdminUserListItem | null>(null);
  const [roleChangeUser, setRoleChangeUser] = useState<AdminUserListItem | null>(null);
  const [targetNewRole, setTargetNewRole] = useState<string>("PATIENT");
  const [actionReason, setActionReason] = useState("");

  // Loading & Error States
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const isSuperAdmin = user?.role === "SUPERADMIN";
  const isAdminOrSuper = user?.role === "ADMIN" || isSuperAdmin;

  // 1. Initial Load
  useEffect(() => {
    if (!isAdminOrSuper) {
      setLoading(false);
      return;
    }
    loadAllData();
  }, [isAdminOrSuper, activeTab]);

  const loadAllData = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      if (activeTab === "overview") {
        const ov = await ApiClient.getAdminOverview();
        setOverview(ov);
      } else if (activeTab === "users") {
        await loadUsers(usersPage);
      } else if (activeTab === "assessments") {
        const stats = await ApiClient.getAdminAssessmentStats();
        setAssessmentStats(stats);
      } else if (activeTab === "clinicians") {
        const cops = await ApiClient.getAdminClinicianOperations();
        setClinicianOps(cops);
      } else if (activeTab === "audit") {
        await loadAudit(auditPage);
      } else if (activeTab === "health") {
        const [h, cfg] = await Promise.all([
          ApiClient.getAdminHealth(),
          ApiClient.getAdminConfig(),
        ]);
        setHealth(h);
        setConfigData(cfg);
      }
    } catch (err: any) {
      setErrorMsg(err.message || (isAr ? "فشل تحميل البيانات الإدارية" : "Failed to load administrative telemetry"));
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async (page: number) => {
    try {
      const res = await ApiClient.getAdminUsers({
        search: userSearch || undefined,
        role: userRoleFilter || undefined,
        is_active: userStatusFilter ? userStatusFilter === "true" : undefined,
        page,
        page_size: 15,
      });
      setUsersList(res.items);
      setUsersTotal(res.total);
      setUsersPage(res.page);
      setUsersTotalPages(res.total_pages);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load users");
    }
  };

  const loadAudit = async (page: number) => {
    try {
      const res = await ApiClient.getAdminAuditEvents({
        action: auditActionFilter || undefined,
        page,
        page_size: 15,
      });
      setAuditEvents(res.items);
      setAuditPage(res.page);
      setAuditTotalPages(res.total_pages);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load audit events");
    }
  };

  // User Actions
  const handleToggleStatus = async () => {
    if (!statusConfirmUser) return;
    setActionLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const updated = await ApiClient.updateAdminUserStatus(
        statusConfirmUser.id,
        !statusConfirmUser.is_active,
        actionReason
      );
      setSuccessMsg(
        isAr
          ? `تم تحديث حالة المستخدم ${updated.email} بنجاح`
          : `User ${updated.email} status updated successfully.`
      );
      setStatusConfirmUser(null);
      setActionReason("");
      await loadUsers(usersPage);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to update user status");
    } finally {
      setActionLoading(false);
    }
  };

  const handleChangeRole = async () => {
    if (!roleChangeUser) return;
    setActionLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const updated = await ApiClient.updateAdminUserRole(
        roleChangeUser.id,
        targetNewRole,
        actionReason
      );
      setSuccessMsg(
        isAr
          ? `تم ترقية/تعديل دور المستخدم ${updated.email} إلى ${updated.role}`
          : `User ${updated.email} role updated to ${updated.role}.`
      );
      setRoleChangeUser(null);
      setActionReason("");
      await loadUsers(usersPage);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to update user role");
    } finally {
      setActionLoading(false);
    }
  };

  const viewUserDetail = async (userId: number) => {
    setErrorMsg(null);
    try {
      const d = await ApiClient.getAdminUserDetail(userId);
      setSelectedUserDetail(d);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to fetch user details");
    }
  };

  // Non-admin Access Denied View
  if (!isAdminOrSuper) {
    return (
      <div className="container mx-auto px-4 py-20 max-w-lg text-center space-y-4">
        <div className="h-16 w-16 mx-auto rounded-full bg-rose-100 dark:bg-rose-950 flex items-center justify-center text-rose-600">
          <Lock className="h-8 w-8" />
        </div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          {isAr ? "غير مصرح بالدخول" : "Administrative Access Restricted"}
        </h1>
        <p className="text-sm text-muted-foreground">
          {isAr
            ? "تتطلب لوحة الإدارة صلاحيات ADMIN أو SUPERADMIN معتمدة. لا تملك صلاحية الوصول إلى هذه الصفحة."
            : "The Admin Dashboard requires authorized ADMIN or SUPERADMIN credentials. Your account is not permitted."}
        </p>
        <Link href="/">
          <Button variant="outline">{isAr ? "العودة للرئيسية" : "Return to Home"}</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 sm:px-6 py-8 max-w-7xl space-y-6">
      {/* 1. Header & Operational Context */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-teal-700 border-teal-300 dark:text-teal-400">
              <Shield className="h-3.5 w-3.5 mr-1 rtl:mr-0 rtl:ml-1" />
              {isSuperAdmin ? "SUPERADMIN CONSOLE" : "ADMIN CONSOLE"}
            </Badge>
            <span className="text-xs text-muted-foreground font-mono">GENOVEX Operations v1.0</span>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            {isAr ? "لوحة التحكم والعمليات الإدارية" : "Platform Administration & Operations"}
          </h1>
          <p className="text-xs text-muted-foreground">
            {isAr
              ? "مراقبة العمليات الحتمية، إدارة المستخدمين، حوكمة القواعد الإكلينيكية، وسجل التدقيق والامتثال."
              : "System operations, user role governance, aggregate assessment telemetry, and audit monitoring."}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => loadAllData()} disabled={loading}>
            <RefreshCw className={`h-3.5 w-3.5 mr-1 rtl:mr-0 rtl:ml-1 ${loading ? "animate-spin" : ""}`} />
            {isAr ? "تحديث" : "Refresh"}
          </Button>
          <Link href="/admin/rules">
            <Button variant="outline" size="sm">
              <Sliders className="h-3.5 w-3.5 mr-1 rtl:mr-0 rtl:ml-1" />
              {isAr ? "القواعد الإكلينيكية" : "Clinical Rules"}
            </Button>
          </Link>
          <Link href="/admin/content">
            <Button variant="outline" size="sm">
              <FileEdit className="h-3.5 w-3.5 mr-1 rtl:mr-0 rtl:ml-1" />
              {isAr ? "المحتوى الطبي" : "CMS Content"}
            </Button>
          </Link>
        </div>
      </div>

      {/* 2. Mandatory Clinical Governance Notice Banner */}
      <div className="p-4 rounded-lg border border-amber-300 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-800 text-amber-900 dark:text-amber-200 space-y-1.5">
        <div className="flex items-center gap-2 font-semibold text-xs">
          <AlertTriangle className="h-4 w-4 text-amber-600 flex-shrink-0" />
          <span>
            {isAr
              ? "تنبيه الحوكمة السريرية: مخرجات التقييم محجوبة للمرضى (HTTP 422 Withheld)"
              : "Clinical Governance Notice: Patient Release Withheld (HTTP 422 Fail-Closed Active)"}
          </span>
        </div>
        <p className="text-[11px] leading-relaxed text-amber-800/90 dark:text-amber-300/80">
          {isAr
            ? "جميع القواعد الإكلينيكية الـ 22 مصنفة كغير معتمدة لعدم وجود سجل تدقيق اعتماد سريري حقيقي. تقارير التقييم محجوبة بالكامل عن المرضى عبر جميع المستويات الأربعة. هذه اللوحة هي للمراقبة التشغيلية وإدارة المنصة ولا تخول اعتماد القواعد السريرية أو نشرها."
            : "All 22 deterministic clinical rules remain classified as UNAPPROVED pending formal clinical board review. Patient-facing clinical assessment outputs are 100% WITHHELD across all 4 outcome tiers. This dashboard is an operational interface, NOT a clinical decision-making or release tool."}
        </p>
      </div>

      {/* Alerts */}
      {errorMsg && (
        <div className="p-3 rounded-md bg-rose-50 border border-rose-200 text-rose-800 dark:bg-rose-950/30 dark:border-rose-900 dark:text-rose-300 text-xs flex items-center justify-between">
          <span>{errorMsg}</span>
          <Button variant="ghost" size="sm" onClick={() => setErrorMsg(null)} className="h-6 w-6 p-0">
            <XCircle className="h-4 w-4" />
          </Button>
        </div>
      )}
      {successMsg && (
        <div className="p-3 rounded-md bg-emerald-50 border border-emerald-200 text-emerald-800 dark:bg-emerald-950/30 dark:border-emerald-900 dark:text-emerald-300 text-xs flex items-center justify-between">
          <span>{successMsg}</span>
          <Button variant="ghost" size="sm" onClick={() => setSuccessMsg(null)} className="h-6 w-6 p-0">
            <CheckCircle2 className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* 3. Navigation Tabs */}
      <div className="flex border-b border-border space-x-1 rtl:space-x-reverse overflow-x-auto text-xs font-medium">
        <button
          onClick={() => setActiveTab("overview")}
          className={`px-4 py-2.5 border-b-2 transition-colors flex items-center gap-1.5 whitespace-nowrap ${
            activeTab === "overview"
              ? "border-teal-700 text-teal-800 dark:text-teal-400 font-bold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Activity className="h-4 w-4" />
          {isAr ? "نظرة عامة والعمليات" : "Platform Overview"}
        </button>

        <button
          onClick={() => setActiveTab("users")}
          className={`px-4 py-2.5 border-b-2 transition-colors flex items-center gap-1.5 whitespace-nowrap ${
            activeTab === "users"
              ? "border-teal-700 text-teal-800 dark:text-teal-400 font-bold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Users className="h-4 w-4" />
          {isAr ? "إدارة المستخدمين والأدوار" : "User Management"}
        </button>

        <button
          onClick={() => setActiveTab("assessments")}
          className={`px-4 py-2.5 border-b-2 transition-colors flex items-center gap-1.5 whitespace-nowrap ${
            activeTab === "assessments"
              ? "border-teal-700 text-teal-800 dark:text-teal-400 font-bold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Sliders className="h-4 w-4" />
          {isAr ? "مراقبة التقييمات" : "Assessment Telemetry"}
        </button>

        <button
          onClick={() => setActiveTab("clinicians")}
          className={`px-4 py-2.5 border-b-2 transition-colors flex items-center gap-1.5 whitespace-nowrap ${
            activeTab === "clinicians"
              ? "border-teal-700 text-teal-800 dark:text-teal-400 font-bold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <UserCog className="h-4 w-4" />
          {isAr ? "عمليات الأطباء والمراجعة" : "Clinician Operations"}
        </button>

        <button
          onClick={() => setActiveTab("audit")}
          className={`px-4 py-2.5 border-b-2 transition-colors flex items-center gap-1.5 whitespace-nowrap ${
            activeTab === "audit"
              ? "border-teal-700 text-teal-800 dark:text-teal-400 font-bold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Clock className="h-4 w-4" />
          {isAr ? "سجل التدقيق والأمان" : "Audit & Security"}
        </button>

        <button
          onClick={() => setActiveTab("health")}
          className={`px-4 py-2.5 border-b-2 transition-colors flex items-center gap-1.5 whitespace-nowrap ${
            activeTab === "health"
              ? "border-teal-700 text-teal-800 dark:text-teal-400 font-bold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Server className="h-4 w-4" />
          {isAr ? "صحة النظام والتهيئة" : "Health & Config"}
        </button>
      </div>

      {/* 4. Tab 1: Overview Tab */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Operational Metrics Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardDescription className="text-xs flex items-center justify-between">
                  <span>{isAr ? "المستخدمون المسجلون" : "Total Users"}</span>
                  <Users className="h-4 w-4 text-muted-foreground" />
                </CardDescription>
                <CardTitle className="text-2xl font-bold">
                  {overview?.users_total ?? "..."}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-[11px] text-muted-foreground space-y-0.5">
                <div className="flex justify-between">
                  <span>{isAr ? "نشط:" : "Active:"}</span>
                  <span className="font-semibold text-emerald-600">{overview?.users_active ?? 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>{isAr ? "غير نشط:" : "Inactive:"}</span>
                  <span className="font-semibold text-rose-600">{overview?.users_inactive ?? 0}</span>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardDescription className="text-xs flex items-center justify-between">
                  <span>{isAr ? "إجمالي التقييمات" : "Total Assessments"}</span>
                  <Sliders className="h-4 w-4 text-muted-foreground" />
                </CardDescription>
                <CardTitle className="text-2xl font-bold">
                  {overview?.assessments_total ?? "..."}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-[11px] text-muted-foreground space-y-0.5">
                <div className="flex justify-between">
                  <span>{isAr ? "مكتملة ومقفلة:" : "Locked / Submitted:"}</span>
                  <span className="font-semibold text-slate-800 dark:text-slate-200">
                    {(overview?.assessments_by_status?.["LOCKED"] ?? 0) + (overview?.assessments_by_status?.["SUBMITTED"] ?? 0)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>{isAr ? "قيد الإجراء:" : "In Progress:"}</span>
                  <span className="font-semibold">{overview?.assessments_by_status?.["IN_PROGRESS"] ?? 0}</span>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardDescription className="text-xs flex items-center justify-between">
                  <span>{isAr ? "التقارير المحجوبة" : "Reports Generated"}</span>
                  <Lock className="h-4 w-4 text-amber-600" />
                </CardDescription>
                <CardTitle className="text-2xl font-bold text-amber-600">
                  {overview?.reports_total ?? "..."}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-[11px] text-muted-foreground space-y-0.5">
                <div className="flex justify-between">
                  <span>{isAr ? "محجوبة للحوكمة:" : "Governance Withheld:"}</span>
                  <span className="font-bold text-amber-700 dark:text-amber-400">100% (HTTP 422)</span>
                </div>
                <div className="flex justify-between">
                  <span>{isAr ? "المفرج عنها للمرضى:" : "Released to Patients:"}</span>
                  <span className="font-bold text-rose-600">0</span>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardDescription className="text-xs flex items-center justify-between">
                  <span>{isAr ? "طابور مراجعة الأطباء" : "Clinician Reviews"}</span>
                  <UserCog className="h-4 w-4 text-teal-700" />
                </CardDescription>
                <CardTitle className="text-2xl font-bold">
                  {(overview?.clinician_reviews_pending ?? 0) + (overview?.clinician_reviews_in_progress ?? 0)}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-[11px] text-muted-foreground space-y-0.5">
                <div className="flex justify-between">
                  <span>{isAr ? "بانتظار المراجعة:" : "Pending Review:"}</span>
                  <span className="font-semibold text-amber-600">{overview?.clinician_reviews_pending ?? 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>{isAr ? "مكتملة المراجعة:" : "Completed:"}</span>
                  <span className="font-semibold text-emerald-600">{overview?.clinician_reviews_completed ?? 0}</span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Quick Operations Links */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="border-border hover:shadow-sm transition-shadow">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-bold flex items-center gap-2">
                  <Sliders className="h-4 w-4 text-teal-700" />
                  {isAr ? "حوكمة القواعد الإكلينيكية" : "Clinical Rules Engine"}
                </CardTitle>
                <CardDescription className="text-xs">
                  {isAr
                    ? "فحص الـ 22 قاعدة إكلينيكية، شروط التفعيل والأولوية، وتتبع حالة الاعتماد السريري."
                    : "Inspect all 22 rules, deterministic predicates, and governance audit trails."}
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-2">
                <Link href="/admin/rules">
                  <Button variant="outline" size="sm" className="w-full text-xs">
                    {isAr ? "عرض القواعد الإكلينيكية" : "Open Rules Dashboard"}
                    <ArrowRight className="h-3.5 w-3.5 ml-1 rtl:ml-0 rtl:mr-1" />
                  </Button>
                </Link>
              </CardContent>
            </Card>

            <Card className="border-border hover:shadow-sm transition-shadow">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-bold flex items-center gap-2">
                  <FileEdit className="h-4 w-4 text-emerald-700" />
                  {isAr ? "إدارة المحتوى الطبي CMS" : "Medical Content CMS"}
                </CardTitle>
                <CardDescription className="text-xs">
                  {isAr
                    ? "إدارة الحالات الطبية المعتمدة، مستويات الأدلة السريرية، ومكتبة الصحة العامة."
                    : "Manage verified conditions, evidence classifications, and bilingual clinical descriptions."}
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-2">
                <Link href="/admin/content">
                  <Button variant="outline" size="sm" className="w-full text-xs">
                    {isAr ? "عرض نظام المحتوى" : "Open CMS Dashboard"}
                    <ArrowRight className="h-3.5 w-3.5 ml-1 rtl:ml-0 rtl:mr-1" />
                  </Button>
                </Link>
              </CardContent>
            </Card>

            <Card className="border-border hover:shadow-sm transition-shadow">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-bold flex items-center gap-2">
                  <Users className="h-4 w-4 text-indigo-700" />
                  {isAr ? "إدارة المستخدمين والأدوار" : "User & Role Management"}
                </CardTitle>
                <CardDescription className="text-xs">
                  {isAr
                    ? "تعديل الصلاحيات وتفعيل/تعطيل الحسابات مع حماية الصلاحيات وسجل التدقيق."
                    : "Manage accounts, role assignments, and status changes with strict safety boundaries."}
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-2">
                <Button variant="outline" size="sm" className="w-full text-xs" onClick={() => setActiveTab("users")}>
                  {isAr ? "الانتقال للمستخدمين" : "Manage Platform Users"}
                  <ArrowRight className="h-3.5 w-3.5 ml-1 rtl:ml-0 rtl:mr-1" />
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* Recent Administrative Activity Log */}
          <Card className="border-border">
            <CardHeader className="pb-3 border-b border-border">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-sm font-bold flex items-center gap-2">
                    <Clock className="h-4 w-4 text-teal-700" />
                    {isAr ? "أحدث النشاطات والعمليات الإدارية" : "Recent Administrative Operations"}
                  </CardTitle>
                  <CardDescription className="text-[11px]">
                    {isAr ? "سجل الأحداث والعمليات الإدارية الحديثة." : "Immutable record of administrative actions."}
                  </CardDescription>
                </div>
                <Badge variant="outline" className="text-[10px]">
                  Append-Only Ledger
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-border text-xs">
                {overview?.recent_admin_activity && overview.recent_admin_activity.length > 0 ? (
                  overview.recent_admin_activity.map((item) => (
                    <div key={item.id} className="p-3.5 flex items-center justify-between gap-4">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-900 dark:text-slate-100">{item.action}</span>
                          <Badge variant="secondary" className="text-[10px]">
                            {item.resource_type}
                          </Badge>
                          <span className="font-mono text-[11px] text-muted-foreground">{item.resource_id}</span>
                        </div>
                        <div className="text-[11px] text-muted-foreground">
                          Actor: {item.user_email || "System"} ({item.user_role || "SYSTEM"})
                        </div>
                      </div>
                      <div className="text-[10px] text-muted-foreground whitespace-nowrap">
                        {new Date(item.timestamp).toLocaleString()}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-6 text-center text-xs text-muted-foreground">
                    {isAr ? "لا توجد نشاطات إدارية مسجلة حالياً." : "No administrative activity recorded."}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 5. Tab 2: User Management Tab */}
      {activeTab === "users" && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="p-4 rounded-lg border border-border bg-card flex flex-col md:flex-row gap-3 items-center justify-between text-xs">
            <div className="flex flex-1 items-center gap-2 w-full md:w-auto">
              <div className="relative flex-1 max-w-sm">
                <Search className="h-3.5 w-3.5 absolute left-2.5 rtl:left-auto rtl:right-2.5 top-2.5 text-muted-foreground" />
                <Input
                  placeholder={isAr ? "بحث بالاسم أو البريد الإلكتروني..." : "Search by name or email..."}
                  className="pl-8 rtl:pl-3 rtl:pr-8 h-8 text-xs"
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && loadUsers(1)}
                />
              </div>

              <select
                className="h-8 rounded-md border border-input bg-background px-2 text-xs"
                value={userRoleFilter}
                onChange={(e) => {
                  setUserRoleFilter(e.target.value);
                  loadUsers(1);
                }}
              >
                <option value="">{isAr ? "جميع الأدوار" : "All Roles"}</option>
                <option value="PATIENT">PATIENT</option>
                <option value="CLINICIAN">CLINICIAN</option>
                <option value="ADMIN">ADMIN</option>
                <option value="SUPERADMIN">SUPERADMIN</option>
              </select>

              <select
                className="h-8 rounded-md border border-input bg-background px-2 text-xs"
                value={userStatusFilter}
                onChange={(e) => {
                  setUserStatusFilter(e.target.value);
                  loadUsers(1);
                }}
              >
                <option value="">{isAr ? "جميع الحالات" : "All Statuses"}</option>
                <option value="true">{isAr ? "نشط" : "Active"}</option>
                <option value="false">{isAr ? "غير نشط" : "Inactive"}</option>
              </select>

              <Button variant="secondary" size="sm" className="h-8 text-xs" onClick={() => loadUsers(1)}>
                {isAr ? "تصفية" : "Filter"}
              </Button>
            </div>

            <div className="text-[11px] text-muted-foreground whitespace-nowrap">
              {isAr ? `إجمالي المستخدمين: ${usersTotal}` : `Total Accounts: ${usersTotal}`}
            </div>
          </div>

          {/* User Table */}
          <Card className="border-border">
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left rtl:text-right">
                <thead className="border-b border-border bg-muted/40 font-semibold text-muted-foreground">
                  <tr>
                    <th className="p-3">{isAr ? "المستخدم" : "User Profile"}</th>
                    <th className="p-3">{isAr ? "الدور" : "Role"}</th>
                    <th className="p-3">{isAr ? "الحالة" : "Status"}</th>
                    <th className="p-3">{isAr ? "تاريخ التسجيل" : "Registered"}</th>
                    <th className="p-3 text-right rtl:text-left">{isAr ? "الإجراءات" : "Actions"}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {usersList.length > 0 ? (
                    usersList.map((u) => {
                      const isSelf = user?.email === u.email;
                      const isTargetSuper = u.role === "SUPERADMIN";
                      const canModify = isSuperAdmin || (user?.role === "ADMIN" && !isTargetSuper);

                      return (
                        <tr key={u.id} className="hover:bg-muted/30 transition-colors">
                          <td className="p-3">
                            <div className="font-semibold text-slate-900 dark:text-slate-100">{u.full_name}</div>
                            <div className="text-[11px] text-muted-foreground font-mono">{u.email}</div>
                          </td>
                          <td className="p-3">
                            <Badge
                              variant={
                                u.role === "SUPERADMIN"
                                  ? "destructive"
                                  : u.role === "ADMIN"
                                  ? "default"
                                  : u.role === "CLINICIAN"
                                  ? "secondary"
                                  : "outline"
                              }
                              className="text-[10px]"
                            >
                              {u.role}
                            </Badge>
                          </td>
                          <td className="p-3">
                            <Badge
                              variant={u.is_active ? "success" : "secondary"}
                              className="text-[10px]"
                            >
                              {u.is_active ? (isAr ? "نشط" : "Active") : (isAr ? "معطل" : "Inactive")}
                            </Badge>
                          </td>
                          <td className="p-3 text-[11px] text-muted-foreground whitespace-nowrap">
                            {new Date(u.created_at).toLocaleDateString()}
                          </td>
                          <td className="p-3 text-right rtl:text-left whitespace-nowrap space-x-1.5 rtl:space-x-reverse">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 text-xs px-2"
                              onClick={() => viewUserDetail(u.id)}
                            >
                              <Eye className="h-3.5 w-3.5 mr-1 rtl:mr-0 rtl:ml-1" />
                              {isAr ? "تفاصيل" : "Details"}
                            </Button>

                            {/* Status toggle */}
                            <Button
                              variant="outline"
                              size="sm"
                              className={`h-7 text-xs px-2 ${
                                u.is_active ? "text-rose-600 hover:text-rose-700" : "text-emerald-600 hover:text-emerald-700"
                              }`}
                              disabled={!canModify || isSelf}
                              onClick={() => setStatusConfirmUser(u)}
                            >
                              {u.is_active ? (
                                <>
                                  <UserX className="h-3.5 w-3.5 mr-1 rtl:mr-0 rtl:ml-1" />
                                  {isAr ? "تعطيل" : "Deactivate"}
                                </>
                              ) : (
                                <>
                                  <UserCheck className="h-3.5 w-3.5 mr-1 rtl:mr-0 rtl:ml-1" />
                                  {isAr ? "تفعيل" : "Activate"}
                                </>
                              )}
                            </Button>

                            {/* Role management */}
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-7 text-xs px-2"
                              disabled={!canModify || isSelf}
                              onClick={() => {
                                setRoleChangeUser(u);
                                setTargetNewRole(u.role);
                              }}
                            >
                              <UserCog className="h-3.5 w-3.5 mr-1 rtl:mr-0 rtl:ml-1" />
                              {isAr ? "تعديل الدور" : "Role"}
                            </Button>
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan={5} className="p-8 text-center text-xs text-muted-foreground">
                        {isAr ? "لم يتم العثور على أي مستخدمين يطابقون معايير البحث." : "No users found matching search criteria."}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            {usersTotalPages > 1 && (
              <div className="p-3 border-t border-border flex items-center justify-between text-xs">
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  disabled={usersPage <= 1}
                  onClick={() => loadUsers(usersPage - 1)}
                >
                  <ChevronLeft className="h-3.5 w-3.5 mr-1 rtl:mr-0 rtl:ml-1" />
                  {isAr ? "السابق" : "Previous"}
                </Button>
                <span className="text-muted-foreground">
                  {isAr ? `صفحة ${usersPage} من ${usersTotalPages}` : `Page ${usersPage} of ${usersTotalPages}`}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  disabled={usersPage >= usersTotalPages}
                  onClick={() => loadUsers(usersPage + 1)}
                >
                  {isAr ? "التالي" : "Next"}
                  <ChevronRight className="h-3.5 w-3.5 ml-1 rtl:ml-0 rtl:mr-1" />
                </Button>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* 6. Tab 3: Assessment Telemetry Tab */}
      {activeTab === "assessments" && (
        <div className="space-y-6">
          <div className="p-4 rounded-lg border border-border bg-card space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-teal-800 dark:text-teal-300">
              <Shield className="h-4 w-4" />
              <span>{isAr ? "مراقبة التقييمات الإكلينيكية (خصوصية كاملة - بدون بيانات تعريفية PII)" : "Assessment Operational Telemetry (Zero PII Guarantee)"}</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {isAr
                ? "تعرض هذه اللوحة إحصاءات تشغيلية مجمعة لحالات سير عمل التقييمات. يتم حجب جميع إجابات المرضى والنصوص الطبية الحساسة بشكل كامل وتلقائي للحفاظ على سرية وخصوصية المستخدمين."
                : "Aggregated workflow analytics across all assessments. Raw patient answers and narrative reports are strictly omitted to protect confidentiality."}
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardDescription className="text-xs">{isAr ? "إجمالي التقييمات المسجلة" : "Total Assessments"}</CardDescription>
                <CardTitle className="text-2xl font-bold">{assessmentStats?.total_assessments ?? 0}</CardTitle>
              </CardHeader>
              <CardContent className="text-[11px] text-muted-foreground">
                {isAr ? "مسجلة في قاعدة البيانات" : "Recorded in database engine"}
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardDescription className="text-xs">{isAr ? "تقييمات قيد الإجراء" : "In Progress"}</CardDescription>
                <CardTitle className="text-2xl font-bold text-slate-700 dark:text-slate-300">
                  {assessmentStats?.incomplete_assessments ?? 0}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-[11px] text-muted-foreground">
                {isAr ? "استبيانات لم يتم قفلها بعد" : "Unsubmitted or incomplete questionnaires"}
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardDescription className="text-xs">{isAr ? "التقارير المولدة" : "Reports Compiled"}</CardDescription>
                <CardTitle className="text-2xl font-bold text-teal-700 dark:text-teal-400">
                  {assessmentStats?.reports_generated ?? 0}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-[11px] text-muted-foreground">
                {isAr ? "لقطات حتمية غير قابلة للتغيير" : "Evidence-linked snapshots stored"}
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardDescription className="text-xs">{isAr ? "نسبة الحجب للحوكمة" : "Governance Withholding"}</CardDescription>
                <CardTitle className="text-2xl font-bold text-amber-600">
                  {assessmentStats?.governance_withheld_percent ?? 100}%
                </CardTitle>
              </CardHeader>
              <CardContent className="text-[11px] text-muted-foreground">
                {isAr ? "محجوبة 100% لحين اعتماد القواعد" : "100% withheld until clinical approval"}
              </CardContent>
            </Card>
          </div>

          {/* Outcome Tier Distribution */}
          <Card className="border-border">
            <CardHeader className="pb-3 border-b border-border">
              <CardTitle className="text-sm font-bold flex items-center gap-2">
                <Activity className="h-4 w-4 text-teal-700" />
                {isAr ? "توزيع مستويات النتائج السريرية الأربعة (محجوبة عن المرضى)" : "Four Clinical Outcome Tiers Distribution (All Withheld)"}
              </CardTitle>
              <CardDescription className="text-xs">
                {isAr
                  ? "توزيع مخرجات المحرك الحتمي للتقارير المولدة. جميع المخرجات محجوبة بخاصية Fail-Closed."
                  : "Deterministic classification results across historical reports. Strictly blocked from patient view."}
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                {Object.entries(assessmentStats?.outcome_tier_counts || {}).map(([tier, count]) => (
                  <div key={tier} className="p-3 rounded-lg border border-border bg-muted/20 space-y-1">
                    <Badge variant="outline" className="text-[10px] truncate max-w-full">
                      {tier}
                    </Badge>
                    <div className="text-xl font-extrabold text-slate-900 dark:text-slate-100">{count}</div>
                    <div className="text-[10px] text-amber-700 dark:text-amber-400 font-semibold">
                      {isAr ? "محجوب (HTTP 422)" : "Withheld (HTTP 422)"}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 7. Tab 4: Clinician Operations Tab */}
      {activeTab === "clinicians" && (
        <div className="space-y-6">
          {/* Shared Review Pool Architecture Notice */}
          <div className="p-4 rounded-lg border border-teal-200 bg-teal-50/50 dark:bg-teal-950/20 dark:border-teal-900 text-teal-950 dark:text-teal-200 space-y-1">
            <div className="flex items-center gap-2 font-bold text-xs">
              <CheckCircle2 className="h-4 w-4 text-teal-700 flex-shrink-0" />
              <span>{isAr ? "هيكل طابور المراجعة المشترك (Shared Review Pool)" : "Shared Review Pool Architecture (No Exclusive Claim Locking)"}</span>
            </div>
            <p className="text-xs leading-relaxed text-teal-900/80 dark:text-teal-300/80">
              {isAr
                ? "يعمل طابور الأطباء كحوض مراجعة مشترك بدون قفل استئثاري (exclusive claim locking). يتم تسجيل جميع مراجعات وملاحظات الأطباء بشكل تراكمي في سجل التدقيق AuditLog."
                : "Assessments operate in a shared clinician pool. Multiple qualified clinicians may inspect cases. Individual status transitions and private notes are recorded in application-level audit logs."}
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardDescription className="text-xs">{isAr ? "الأطباء المسجلون" : "Registered Clinicians"}</CardDescription>
                <CardTitle className="text-2xl font-bold">{clinicianOps?.registered_clinicians ?? 0}</CardTitle>
              </CardHeader>
              <CardContent className="text-[11px] text-muted-foreground">
                {isAr ? `النشطون: ${clinicianOps?.active_clinicians ?? 0}` : `Active accounts: ${clinicianOps?.active_clinicians ?? 0}`}
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardDescription className="text-xs">{isAr ? "قيد المراجعة الإكلينيكية" : "In Clinical Review"}</CardDescription>
                <CardTitle className="text-2xl font-bold text-amber-600">{clinicianOps?.in_review_count ?? 0}</CardTitle>
              </CardHeader>
              <CardContent className="text-[11px] text-muted-foreground">
                {isAr ? `بانتظار البدء: ${clinicianOps?.pending_reviews ?? 0}` : `Pending initiation: ${clinicianOps?.pending_reviews ?? 0}`}
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardDescription className="text-xs">{isAr ? "المراجعات المكتملة" : "Completed Reviews"}</CardDescription>
                <CardTitle className="text-2xl font-bold text-emerald-600">{clinicianOps?.completed_reviews ?? 0}</CardTitle>
              </CardHeader>
              <CardContent className="text-[11px] text-muted-foreground">
                {isAr ? "مكتملة وموثقة في السجل" : "Reviewed and recorded in audit trail"}
              </CardContent>
            </Card>
          </div>

          {/* Recent Clinician Actions Table */}
          <Card className="border-border">
            <CardHeader className="pb-3 border-b border-border">
              <CardTitle className="text-sm font-bold flex items-center gap-2">
                <Clock className="h-4 w-4 text-teal-700" />
                {isAr ? "أحدث نشاطات طاقم الأطباء" : "Recent Clinician Review Activity"}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-border text-xs">
                {clinicianOps?.recent_reviews && clinicianOps.recent_reviews.length > 0 ? (
                  clinicianOps.recent_reviews.map((rev) => (
                    <div key={rev.id} className="p-3.5 flex items-center justify-between gap-4">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-900 dark:text-slate-100">{rev.action}</span>
                          <Badge variant="outline" className="text-[10px]">
                            {rev.assessment_reference}
                          </Badge>
                          <span className="text-muted-foreground font-mono text-[11px]">{rev.status}</span>
                        </div>
                        <div className="text-[11px] text-muted-foreground">
                          Clinician: {rev.actor_email}
                        </div>
                      </div>
                      <div className="text-[10px] text-muted-foreground whitespace-nowrap">
                        {new Date(rev.timestamp).toLocaleString()}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-6 text-center text-xs text-muted-foreground">
                    {isAr ? "لا توجد نشاطات مراجعة أطباء مسجلة حالياً." : "No clinician activity recorded."}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 8. Tab 5: Audit & Security Tab */}
      {activeTab === "audit" && (
        <div className="space-y-4">
          <div className="p-4 rounded-lg border border-border bg-card flex flex-col md:flex-row gap-3 items-center justify-between text-xs">
            <div className="flex flex-1 items-center gap-2 w-full md:w-auto">
              <Input
                placeholder={isAr ? "تصفية بنوع الإجراء (مثل: ADMIN_USER_STATUS_UPDATE)..." : "Filter by action code..."}
                className="max-w-xs h-8 text-xs font-mono"
                value={auditActionFilter}
                onChange={(e) => setAuditActionFilter(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && loadAudit(1)}
              />
              <Button variant="secondary" size="sm" className="h-8 text-xs" onClick={() => loadAudit(1)}>
                {isAr ? "تصفية" : "Filter"}
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-[10px]">
                Application-Level Append-Only
              </Badge>
            </div>
          </div>

          <Card className="border-border">
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left rtl:text-right">
                <thead className="border-b border-border bg-muted/40 font-semibold text-muted-foreground">
                  <tr>
                    <th className="p-3">ID</th>
                    <th className="p-3">{isAr ? "نوع الإجراء" : "Action"}</th>
                    <th className="p-3">{isAr ? "المسؤول" : "Actor"}</th>
                    <th className="p-3">{isAr ? "المورد المستهدف" : "Target Resource"}</th>
                    <th className="p-3">{isAr ? "التفاصيل" : "Details"}</th>
                    <th className="p-3 text-right rtl:text-left">{isAr ? "الوقت" : "Timestamp"}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {auditEvents.length > 0 ? (
                    auditEvents.map((evt) => (
                      <tr key={evt.id} className="hover:bg-muted/30 transition-colors">
                        <td className="p-3 font-mono text-[11px] text-muted-foreground">#{evt.id}</td>
                        <td className="p-3 font-semibold text-slate-900 dark:text-slate-100">{evt.action}</td>
                        <td className="p-3">
                          <div className="text-[11px]">{evt.user_email || "System"}</div>
                          <Badge variant="secondary" className="text-[9px]">
                            {evt.user_role || "SYSTEM"}
                          </Badge>
                        </td>
                        <td className="p-3 font-mono text-[11px]">
                          {evt.resource_type}: {evt.resource_id}
                        </td>
                        <td className="p-3 text-[11px] max-w-xs truncate text-muted-foreground">
                          {evt.details ? JSON.stringify(evt.details) : "-"}
                        </td>
                        <td className="p-3 text-right rtl:text-left text-[11px] text-muted-foreground whitespace-nowrap">
                          {new Date(evt.timestamp).toLocaleString()}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-xs text-muted-foreground">
                        {isAr ? "لا توجد سجلات مطابقة." : "No audit events found."}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {auditTotalPages > 1 && (
              <div className="p-3 border-t border-border flex items-center justify-between text-xs">
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  disabled={auditPage <= 1}
                  onClick={() => loadAudit(auditPage - 1)}
                >
                  <ChevronLeft className="h-3.5 w-3.5 mr-1 rtl:mr-0 rtl:ml-1" />
                  {isAr ? "السابق" : "Previous"}
                </Button>
                <span className="text-muted-foreground">
                  {isAr ? `صفحة ${auditPage} من ${auditTotalPages}` : `Page ${auditPage} of ${auditTotalPages}`}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  disabled={auditPage >= auditTotalPages}
                  onClick={() => loadAudit(auditPage + 1)}
                >
                  {isAr ? "التالي" : "Next"}
                  <ChevronRight className="h-3.5 w-3.5 ml-1 rtl:ml-0 rtl:mr-1" />
                </Button>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* 9. Tab 6: Platform Health & Configuration Tab */}
      {activeTab === "health" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardDescription className="text-xs flex items-center justify-between">
                  <span>{isAr ? "قاعدة البيانات" : "Database Engine"}</span>
                  <Database className="h-4 w-4 text-emerald-600" />
                </CardDescription>
                <CardTitle className="text-lg font-bold text-emerald-600 flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4" />
                  {health?.database.connected ? "CONNECTED" : "OFFLINE"}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-[11px] text-muted-foreground">
                Engine: SQLite (Foreign Keys & Isolation Active)
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardDescription className="text-xs flex items-center justify-between">
                  <span>{isAr ? "مزود الذكاء الاصطناعي" : "AI Provider Mode"}</span>
                  <Cpu className="h-4 w-4 text-teal-600" />
                </CardDescription>
                <CardTitle className="text-lg font-bold">
                  {health?.ai_provider_mode || "MOCK"}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-[11px] text-muted-foreground">
                Live Egress Active: {health?.gemini_live_egress_active ? "TRUE" : "FALSE (Sandboxed)"}
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardDescription className="text-xs flex items-center justify-between">
                  <span>{isAr ? "بوابة الحوكمة السريرية" : "Clinical Governance Gate"}</span>
                  <Shield className="h-4 w-4 text-amber-600" />
                </CardDescription>
                <CardTitle className="text-lg font-bold text-amber-600">
                  {health?.clinical_governance_gate || "FAIL_CLOSED"}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-[11px] text-muted-foreground">
                Release Status: 100% Withheld (HTTP 422)
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardDescription className="text-xs flex items-center justify-between">
                  <span>{isAr ? "إصدار المنصة والـ API" : "Platform API Version"}</span>
                  <Server className="h-4 w-4 text-indigo-600" />
                </CardDescription>
                <CardTitle className="text-lg font-bold">
                  v{health?.api_version || "1.0.0"}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-[11px] text-muted-foreground">
                Environment: {configData?.environment || "development"}
              </CardContent>
            </Card>
          </div>

          {/* Configuration Inspector */}
          <Card className="border-border">
            <CardHeader className="pb-3 border-b border-border">
              <CardTitle className="text-sm font-bold flex items-center gap-2">
                <Settings className="h-4 w-4 text-teal-700" />
                {isAr ? "معايير تهيئة النظام (جميع المفاتيح الحساسة محجوبة)" : "Safe System Configuration (Zero Secret Exposure)"}
              </CardTitle>
              <CardDescription className="text-xs">
                {isAr
                  ? "معاينة آمنة لقيم التكوين المصرح بها. يتم حجب جميع المفاتيح السرية وبيانات الاعتماد تلقائياً."
                  : "Verified runtime configuration parameters. Security keys and database connection passwords strictly redacted."}
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-4 space-y-3 text-xs">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-3 rounded-lg border border-border bg-muted/20 space-y-1">
                  <span className="font-semibold text-muted-foreground">Project Name</span>
                  <div className="font-mono">{configData?.project_name || "GENOVEX"}</div>
                </div>

                <div className="p-3 rounded-lg border border-border bg-muted/20 space-y-1">
                  <span className="font-semibold text-muted-foreground">Environment</span>
                  <div className="font-mono">{configData?.environment || "development"}</div>
                </div>

                <div className="p-3 rounded-lg border border-border bg-muted/20 space-y-1">
                  <span className="font-semibold text-muted-foreground">Rate Limit Policy</span>
                  <div className="font-mono">{configData?.rate_limit_per_minute || 60} requests / minute</div>
                </div>

                <div className="p-3 rounded-lg border border-border bg-muted/20 space-y-1">
                  <span className="font-semibold text-muted-foreground">JWT Authentication Algorithm</span>
                  <div className="font-mono">{configData?.auth_jwt_algorithm || "HS256"}</div>
                </div>
              </div>

              <div className="p-3 rounded-lg border border-border bg-muted/20 space-y-1">
                <span className="font-semibold text-muted-foreground">Allowed CORS Origins</span>
                <div className="font-mono text-[11px] break-all">
                  {configData?.allowed_cors_origins?.join(", ") || "*"}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* =========================================================================
          MODALS / DIALOGS
      ========================================================================== */}

      {/* 1. User Detail Modal */}
      {selectedUserDetail && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-lg max-w-lg w-full p-6 space-y-4 shadow-xl text-xs">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="font-bold text-sm flex items-center gap-2">
                <Users className="h-4 w-4 text-teal-700" />
                {isAr ? "تفاصيل المستخدم" : "User Profile & Audit Record"}
              </h3>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
                onClick={() => setSelectedUserDetail(null)}
              >
                <XCircle className="h-4 w-4" />
              </Button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-muted-foreground">{isAr ? "الاسم الكامل:" : "Full Name:"}</span>
                <div className="font-semibold text-slate-900 dark:text-slate-100">{selectedUserDetail.full_name}</div>
              </div>
              <div>
                <span className="text-muted-foreground">{isAr ? "البريد الإلكتروني:" : "Email:"}</span>
                <div className="font-mono text-[11px]">{selectedUserDetail.email}</div>
              </div>
              <div>
                <span className="text-muted-foreground">{isAr ? "الدور الحالي:" : "Current Role:"}</span>
                <div>
                  <Badge variant="outline" className="text-[10px]">
                    {selectedUserDetail.role}
                  </Badge>
                </div>
              </div>
              <div>
                <span className="text-muted-foreground">{isAr ? "حالة الحساب:" : "Account Status:"}</span>
                <div>
                  <Badge variant={selectedUserDetail.is_active ? "success" : "secondary"} className="text-[10px]">
                    {selectedUserDetail.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
              </div>
              <div>
                <span className="text-muted-foreground">{isAr ? "التقييمات المرتبطة:" : "Assessments Count:"}</span>
                <div className="font-semibold">{selectedUserDetail.assessments_count}</div>
              </div>
              <div>
                <span className="text-muted-foreground">{isAr ? "تاريخ الإنشاء:" : "Created At:"}</span>
                <div className="text-[11px]">{new Date(selectedUserDetail.created_at).toLocaleString()}</div>
              </div>
            </div>

            {/* User Audit Logs */}
            <div className="space-y-1.5 pt-2 border-t border-border">
              <span className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                {isAr ? "أحدث سجلات تدقيق المستخدم" : "Recent Audit Events"}
              </span>
              <div className="max-h-40 overflow-y-auto divide-y divide-border border border-border rounded-md text-[11px]">
                {selectedUserDetail.recent_audit_logs.length > 0 ? (
                  selectedUserDetail.recent_audit_logs.map((log) => (
                    <div key={log.id} className="p-2 space-y-0.5">
                      <div className="flex justify-between font-semibold">
                        <span>{log.action}</span>
                        <span className="text-[10px] text-muted-foreground font-mono">
                          {new Date(log.timestamp).toLocaleDateString()}
                        </span>
                      </div>
                      <div className="text-muted-foreground text-[10px]">
                        Actor: {log.user_email || "System"} | Target: {log.resource_type}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-3 text-center text-muted-foreground">
                    {isAr ? "لا توجد سجلات تدقيق لهذا المستخدم." : "No audit records for this account."}
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button variant="outline" size="sm" onClick={() => setSelectedUserDetail(null)}>
                {isAr ? "إغلاق" : "Close"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 2. Status Confirm Modal */}
      {statusConfirmUser && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-lg max-w-md w-full p-6 space-y-4 shadow-xl text-xs">
            <h3 className="font-bold text-sm text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-600" />
              {isAr ? "تأكيد تعديل حالة الحساب" : "Confirm Account Status Change"}
            </h3>

            <p className="text-muted-foreground leading-relaxed">
              {isAr
                ? `هل أنت متأكد من رغبتك في ${statusConfirmUser.is_active ? "تعطيل" : "تفعيل"} حساب المستخدم "${statusConfirmUser.email}"؟`
                : `Are you sure you want to ${statusConfirmUser.is_active ? "deactivate" : "activate"} user "${statusConfirmUser.email}"?`}
            </p>

            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-muted-foreground">
                {isAr ? "سبب الإجراء (لأغراض التدقيق):" : "Reason for Action (Recorded in AuditLog):"}
              </label>
              <Input
                placeholder={isAr ? "أدخل سبب التعديل..." : "Enter reason for audit record..."}
                value={actionReason}
                onChange={(e) => setActionReason(e.target.value)}
                className="h-8 text-xs"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-border">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setStatusConfirmUser(null);
                  setActionReason("");
                }}
                disabled={actionLoading}
              >
                {isAr ? "إلغاء" : "Cancel"}
              </Button>
              <Button
                variant={statusConfirmUser.is_active ? "destructive" : "default"}
                size="sm"
                onClick={handleToggleStatus}
                disabled={actionLoading}
              >
                {actionLoading ? (
                  <RefreshCw className="h-3.5 w-3.5 animate-spin mr-1 rtl:mr-0 rtl:ml-1" />
                ) : null}
                {statusConfirmUser.is_active ? (isAr ? "تأكيد التعطيل" : "Confirm Deactivation") : (isAr ? "تأكيد التفعيل" : "Confirm Activation")}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 3. Role Change Modal */}
      {roleChangeUser && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-lg max-w-md w-full p-6 space-y-4 shadow-xl text-xs">
            <h3 className="font-bold text-sm text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <UserCog className="h-4 w-4 text-teal-700" />
              {isAr ? "تعديل دور وصلاحيات المستخدم" : "Update User Role Assignment"}
            </h3>

            <p className="text-muted-foreground leading-relaxed">
              {isAr
                ? `تعديل الدور المعين للمستخدم "${roleChangeUser.email}". الدور الحالي: ${roleChangeUser.role}`
                : `Update role assignment for user "${roleChangeUser.email}". Current role: ${roleChangeUser.role}.`}
            </p>

            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-muted-foreground">
                {isAr ? "الدور الجديد:" : "New Role:"}
              </label>
              <select
                className="w-full h-8 rounded-md border border-input bg-background px-2 text-xs"
                value={targetNewRole}
                onChange={(e) => setTargetNewRole(e.target.value)}
              >
                <option value="PATIENT">PATIENT</option>
                <option value="CLINICIAN">CLINICIAN</option>
                <option value="ADMIN">ADMIN</option>
                {isSuperAdmin && <option value="SUPERADMIN">SUPERADMIN</option>}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-muted-foreground">
                {isAr ? "سبب التعديل (لأغراض التدقيق):" : "Reason (Recorded in AuditLog):"}
              </label>
              <Input
                placeholder={isAr ? "سبب الترقية أو تغيير الصلاحيات..." : "Reason for role change..."}
                value={actionReason}
                onChange={(e) => setActionReason(e.target.value)}
                className="h-8 text-xs"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-border">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setRoleChangeUser(null);
                  setActionReason("");
                }}
                disabled={actionLoading}
              >
                {isAr ? "إلغاء" : "Cancel"}
              </Button>
              <Button
                variant="default"
                size="sm"
                onClick={handleChangeRole}
                disabled={actionLoading || targetNewRole === roleChangeUser.role}
              >
                {actionLoading ? (
                  <RefreshCw className="h-3.5 w-3.5 animate-spin mr-1 rtl:mr-0 rtl:ml-1" />
                ) : null}
                {isAr ? "حفظ التغييرات" : "Save Changes"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
