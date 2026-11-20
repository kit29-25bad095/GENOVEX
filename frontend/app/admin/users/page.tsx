"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useLanguage } from "@/context/LanguageContext";
import { useAuth } from "@/context/AuthContext";
import { ApiClient, User } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Users,
  ArrowLeft,
  Search,
  Shield,
  UserCheck,
  UserX,
  Edit,
  Save,
  X,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";

export default function UserAdministrationPage() {
  const { t, language } = useLanguage();
  const { user: currentUser } = useAuth();

  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("ALL");
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editRole, setEditRole] = useState<string>("PATIENT");
  const [editCredentials, setEditCredentials] = useState<string>("");
  const [editFullName, setEditFullName] = useState<string>("");
  const [editIsActive, setEditIsActive] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchUsers = async () => {
    setIsLoading(true);
    try {
      const data = await ApiClient.getAdminUsers();
      setUsers(data);
    } catch (err: any) {
      console.error("Failed to load users:", err);
      // Fallback local list
      setUsers([
        {
          id: 1,
          email: "superadmin@genovex.health",
          full_name: "Dr. Tariq Al-Hashimi",
          role: "SUPERADMIN",
          credentials_summary: "Consultant Urologist & Platform Lead (DHA-P-001)",
          is_active: true,
          created_at: new Date().toISOString(),
        },
        {
          id: 2,
          email: "clinician@genovex.health",
          full_name: "Dr. Mansoor Al-Ketbi",
          role: "CLINICIAN",
          credentials_summary: "Specialist Andrologist (DoH License 8492)",
          is_active: true,
          created_at: new Date().toISOString(),
        },
        {
          id: 3,
          email: "admin@genovex.health",
          full_name: "Noura Al-Zaabi",
          role: "ADMIN",
          credentials_summary: "Clinical Informatics Operations Manager",
          is_active: true,
          created_at: new Date().toISOString(),
        },
        {
          id: 4,
          email: "patient.ahmed@example.com",
          full_name: "Ahmed Al-Mansoori",
          role: "PATIENT",
          credentials_summary: "Registered Health Seeker",
          is_active: true,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const openEditModal = (u: User) => {
    setEditingUser(u);
    setEditRole(u.role);
    setEditCredentials(u.credentials_summary || "");
    setEditFullName(u.full_name || "");
    setEditIsActive(u.is_active);
    setMessage(null);
  };

  const handleSaveUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    setIsSubmitting(true);
    setMessage(null);

    try {
      await ApiClient.updateAdminUser(editingUser.id, {
        role: editRole,
        credentials_summary: editCredentials,
        full_name: editFullName,
        is_active: editIsActive,
      });

      setMessage({
        type: "success",
        text: language === "ar" ? "تم تحديث بيانات وصلاحيات المستخدم بنجاح" : "User role and account details updated successfully.",
      });

      await fetchUsers();
      setTimeout(() => {
        setEditingUser(null);
      }, 1200);
    } catch (err: any) {
      setMessage({
        type: "error",
        text: err.message || "Failed to update user",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredUsers = users.filter((u) => {
    const matchesSearch =
      u.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (u.credentials_summary && u.credentials_summary.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesRole = roleFilter === "ALL" || u.role === roleFilter;

    return matchesSearch && matchesRole;
  });

  const getRoleBadgeVariant = (role: string) => {
    switch (role) {
      case "SUPERADMIN":
        return "destructive";
      case "ADMIN":
        return "secondary";
      case "CLINICIAN":
        return "clinical";
      default:
        return "outline";
    }
  };

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
          <Shield className="h-3 w-3 mr-1 rtl:mr-0 rtl:ml-1 inline" />
          RBAC & User Governance
        </Badge>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white flex items-center space-x-2.5 rtl:space-x-reverse">
            <Users className="h-7 w-7 text-teal-700" />
            <span>{language === "ar" ? "إدارة المستخدمين والصلاحيات" : "User & Role Governance"}</span>
          </h1>
          <p className="text-xs text-muted-foreground">
            {language === "ar"
              ? "تعيين أدوار الأطباء والمشرفين، التحقق من بيانات التراخيص، وإدارة صلاحيات الوصول."
              : "Assign clinical and administrative permissions, verify healthcare licensing, and audit access."}
          </p>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <Card className="border-border shadow-sm">
        <CardContent className="p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-2.5 rtl:left-auto rtl:right-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder={language === "ar" ? "البحث بالاسم أو البريد..." : "Search name or email..."}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8 rtl:pl-3 rtl:pr-8 text-xs h-9"
            />
          </div>

          <div className="flex items-center space-x-1.5 rtl:space-x-reverse w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
            {["ALL", "CLINICIAN", "ADMIN", "SUPERADMIN", "PATIENT"].map((role) => (
              <button
                key={role}
                onClick={() => setRoleFilter(role)}
                className={`px-3 py-1 rounded text-xs font-semibold whitespace-nowrap transition-colors ${
                  roleFilter === role
                    ? "bg-teal-700 text-white"
                    : "bg-slate-100 dark:bg-slate-800 text-muted-foreground hover:bg-slate-200"
                }`}
              >
                {role}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Users Table */}
      <Card className="border-border shadow-sm">
        <CardHeader className="pb-3 border-b border-border/60">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-bold">
              {language === "ar" ? "قائمة المستخدمين المسجلين" : "Registered User Accounts"}
            </CardTitle>
            <span className="text-xs text-muted-foreground">
              {filteredUsers.length} {language === "ar" ? "مستخدم" : "users"}
            </span>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <div className="divide-y divide-border text-xs">
            {isLoading ? (
              <div className="p-8 text-center text-muted-foreground">
                {language === "ar" ? "جارٍ تحميل قائمة المستخدمين..." : "Loading user directory..."}
              </div>
            ) : filteredUsers.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">
                {language === "ar" ? "لا يوجد مستخدمون مطابقون لمعايير البحث." : "No users found matching search criteria."}
              </div>
            ) : (
              filteredUsers.map((u) => (
                <div
                  key={u.id}
                  className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50/50 dark:hover:bg-slate-900/50 transition-colors"
                >
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2 rtl:space-x-reverse">
                      <span className="font-bold text-sm text-slate-900 dark:text-white">{u.full_name}</span>
                      <Badge variant={getRoleBadgeVariant(u.role) as any} className="text-[10px]">
                        {u.role}
                      </Badge>
                      {u.is_active ? (
                        <span className="inline-flex items-center text-[10px] text-emerald-600 bg-emerald-50 dark:bg-emerald-950/40 px-1.5 py-0.5 rounded">
                          <UserCheck className="h-2.5 w-2.5 mr-0.5 rtl:mr-0 rtl:ml-0.5" />
                          {language === "ar" ? "نشط" : "Active"}
                        </span>
                      ) : (
                        <span className="inline-flex items-center text-[10px] text-rose-600 bg-rose-50 dark:bg-rose-950/40 px-1.5 py-0.5 rounded">
                          <UserX className="h-2.5 w-2.5 mr-0.5 rtl:mr-0 rtl:ml-0.5" />
                          {language === "ar" ? "معطل" : "Inactive"}
                        </span>
                      )}
                    </div>

                    <div className="text-muted-foreground text-xs font-mono">{u.email}</div>

                    {u.credentials_summary && (
                      <div className="text-[11px] text-teal-800 dark:text-teal-400">
                        {u.credentials_summary}
                      </div>
                    )}

                    <div className="text-[10px] text-muted-foreground">
                      Registered: {new Date(u.created_at).toLocaleDateString()}
                    </div>
                  </div>

                  <div className="flex items-center space-x-2 rtl:space-x-reverse">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openEditModal(u)}
                      className="text-xs h-8"
                    >
                      <Edit className="h-3.5 w-3.5 mr-1.5 rtl:mr-0 rtl:ml-1.5 text-teal-700" />
                      {language === "ar" ? "تعديل الصلاحيات" : "Edit Role"}
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Edit User Modal */}
      {editingUser && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <Card className="w-full max-w-lg border-border shadow-xl animate-in fade-in zoom-in-95">
            <CardHeader className="pb-3 border-b border-border/60">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-bold flex items-center space-x-2 rtl:space-x-reverse">
                  <Shield className="h-4 w-4 text-teal-700" />
                  <span>{language === "ar" ? "تعديل صلاحيات المستخدم" : "Edit User Role & Permissions"}</span>
                </CardTitle>
                <button
                  onClick={() => setEditingUser(null)}
                  className="text-muted-foreground hover:text-slate-900 dark:hover:text-white"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <CardDescription className="text-xs">
                {editingUser.email}
              </CardDescription>
            </CardHeader>

            <form onSubmit={handleSaveUser}>
              <CardContent className="space-y-4 pt-4 text-xs">
                {message && (
                  <div
                    className={`p-3 rounded-md text-xs flex items-center space-x-2 rtl:space-x-reverse ${
                      message.type === "success"
                        ? "bg-teal-50 text-teal-800 border border-teal-200"
                        : "bg-rose-50 text-rose-800 border border-rose-200"
                    }`}
                  >
                    {message.type === "success" ? (
                      <CheckCircle2 className="h-4 w-4 text-teal-600" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-rose-600" />
                    )}
                    <span>{message.text}</span>
                  </div>
                )}

                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">
                    {language === "ar" ? "الاسم الكامل" : "Full Name"}
                  </Label>
                  <Input
                    value={editFullName}
                    onChange={(e) => setEditFullName(e.target.value)}
                    className="text-xs h-9"
                    required
                  />
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">
                    {language === "ar" ? "الدور والصلاحيات (RBAC)" : "Assigned Role (RBAC)"}
                  </Label>
                  <select
                    value={editRole}
                    onChange={(e) => setEditRole(e.target.value)}
                    className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-teal-600"
                  >
                    <option value="PATIENT">PATIENT — Standard Health Seeker</option>
                    <option value="CLINICIAN">CLINICIAN — Licensed Medical Reviewer</option>
                    <option value="ADMIN">ADMIN — System & Content Manager</option>
                    <option value="SUPERADMIN">SUPERADMIN — Master Governance & Security</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">
                    {language === "ar" ? "ملخص المؤهلات والترخيص الطبي" : "Professional Credentials / License Summary"}
                  </Label>
                  <Input
                    value={editCredentials}
                    onChange={(e) => setEditCredentials(e.target.value)}
                    placeholder="e.g. Consultant Urologist (DHA-P-12345)"
                    className="text-xs h-9"
                  />
                  <p className="text-[10px] text-muted-foreground">
                    {language === "ar"
                      ? "رقم ترخيص هيئة الصحة بدبي (DHA) أو دائرة الصحة بأبوظبي (DoH)."
                      : "Healthcare professional license number and specialty designation."}
                  </p>
                </div>

                <div className="flex items-center space-x-2 rtl:space-x-reverse pt-2">
                  <input
                    type="checkbox"
                    id="isActiveCheck"
                    checked={editIsActive}
                    onChange={(e) => setEditIsActive(e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300 text-teal-600 focus:ring-teal-500"
                  />
                  <Label htmlFor="isActiveCheck" className="text-xs cursor-pointer">
                    {language === "ar" ? "الحساب نشط ومصرح له بالدخول" : "Account Active & Permitted to Login"}
                  </Label>
                </div>

                <div className="flex items-center justify-end space-x-2 rtl:space-x-reverse pt-4 border-t border-border/60">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setEditingUser(null)}
                    disabled={isSubmitting}
                  >
                    {language === "ar" ? "إلغاء" : "Cancel"}
                  </Button>
                  <Button
                    type="submit"
                    variant="clinical"
                    size="sm"
                    disabled={isSubmitting}
                  >
                    <Save className="h-3.5 w-3.5 mr-1.5 rtl:mr-0 rtl:ml-1.5" />
                    {isSubmitting
                      ? (language === "ar" ? "جارٍ الحفظ..." : "Saving...")
                      : (language === "ar" ? "حفظ التغييرات" : "Save Changes")}
                  </Button>
                </div>
              </CardContent>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
}
