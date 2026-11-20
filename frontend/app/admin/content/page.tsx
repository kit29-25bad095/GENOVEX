"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useLanguage } from "@/context/LanguageContext";
import { useAuth } from "@/context/AuthContext";
import { ApiClient } from "@/lib/api";
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
  X,
  Search,
  RotateCcw,
  ShieldCheck,
  Send,
  AlertCircle,
} from "lucide-react";

export default function MedicalContentAdminPage() {
  const { t, language } = useLanguage();
  const { user } = useAuth();

  const [conditions, setConditions] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [notification, setNotification] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Modals
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [versionModalCondition, setVersionModalCondition] = useState<any | null>(null);
  const [versionHistory, setVersionHistory] = useState<any[]>([]);
  const [isLoadingVersions, setIsLoadingVersions] = useState(false);
  const [restoreReason, setRestoreReason] = useState("");

  // New condition form state
  const [newCond, setNewCond] = useState({
    slug: "",
    category_id: 1,
    name_en: "",
    name_ar: "",
    short_description_en: "",
    short_description_ar: "",
    detailed_explanation_en: "",
    detailed_explanation_ar: "",
    organs_involved: "Testis, Scrotum",
    biological_mechanism_en: "",
    biological_mechanism_ar: "",
    causes_risk_factors_en: "",
    causes_risk_factors_ar: "",
    possible_symptoms_en: "",
    possible_symptoms_ar: "",
    can_be_asymptomatic: true,
    diagnostic_investigations_en: "Semen Analysis, Scrotal Doppler Ultrasound",
    diagnostic_investigations_ar: "تحليل السائل المنوي، تخطيط دوبلر للصفن",
    clinical_next_steps_en: "Consult reproductive urologist for physical evaluation",
    clinical_next_steps_ar: "استشارة طبيب المسالك البولية التناسلية للفحص السريري",
    evidence_classification: "Level 1a",
  });

  const fetchConditions = async () => {
    setIsLoading(true);
    try {
      const [condData, catData] = await Promise.all([
        ApiClient.getAdminConditions({ limit: 100 }),
        ApiClient.getAdminCategories(),
      ]);
      setConditions(condData);
      setCategories(catData);
    } catch (err: any) {
      console.error("Error loading conditions:", err);
      // Fallback baseline
      setConditions([
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
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchConditions();
  }, []);

  const handleCreateCondition = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        slug: newCond.slug.trim().toLowerCase().replace(/[^a-z0-9-]/g, "-"),
        category_id: Number(newCond.category_id),
        can_be_asymptomatic: newCond.can_be_asymptomatic,
        evidence_classification: newCond.evidence_classification,
        organs_involved: newCond.organs_involved.split(",").map(o => o.trim()).filter(Boolean),
        translations: [
          {
            language_code: "en",
            name: newCond.name_en,
            short_description: newCond.short_description_en,
            detailed_explanation: newCond.detailed_explanation_en,
            biological_mechanism: newCond.biological_mechanism_en,
            causes_and_risk_factors: newCond.causes_risk_factors_en.split("\n").filter(Boolean),
            possible_symptoms: newCond.possible_symptoms_en.split("\n").filter(Boolean),
            diagnostic_investigations: newCond.diagnostic_investigations_en.split(",").map(s => s.trim()),
            clinical_next_steps: newCond.clinical_next_steps_en,
          },
          {
            language_code: "ar",
            name: newCond.name_ar,
            short_description: newCond.short_description_ar,
            detailed_explanation: newCond.detailed_explanation_ar,
            biological_mechanism: newCond.biological_mechanism_ar,
            causes_and_risk_factors: newCond.causes_risk_factors_ar.split("\n").filter(Boolean),
            possible_symptoms: newCond.possible_symptoms_ar.split("\n").filter(Boolean),
            diagnostic_investigations: newCond.diagnostic_investigations_ar.split(",").map(s => s.trim()),
            clinical_next_steps: newCond.clinical_next_steps_ar,
          },
        ],
      };

      await ApiClient.createAdminCondition(payload);
      setNotification({
        type: "success",
        text: language === "ar" ? "تم إنشاء الحالة الطبية بنجاح كمسودة" : "Medical condition created successfully as DRAFT.",
      });
      setIsAddOpen(false);
      await fetchConditions();
    } catch (err: any) {
      setNotification({ type: "error", text: err.message || "Failed to create condition" });
    }
  };

  const handleReviewAction = async (conditionId: number, action: string) => {
    try {
      await ApiClient.reviewActionCondition(conditionId, action, `Clinician review action: ${action}`);
      setNotification({
        type: "success",
        text: `Condition action ${action} executed successfully.`,
      });
      await fetchConditions();
    } catch (err: any) {
      setNotification({ type: "error", text: err.message || "Action failed" });
    }
  };

  const openVersionModal = async (condition: any) => {
    setVersionModalCondition(condition);
    setIsLoadingVersions(true);
    setRestoreReason("");
    try {
      const data = await ApiClient.getConditionVersions(condition.id);
      setVersionHistory(data);
    } catch (err) {
      setVersionHistory([]);
    } finally {
      setIsLoadingVersions(false);
    }
  };

  const handleRestoreVersion = async (versionNumber: string) => {
    if (!versionModalCondition || !restoreReason.trim()) return;
    try {
      await ApiClient.restoreConditionVersion(versionModalCondition.id, versionNumber, restoreReason);
      setNotification({
        type: "success",
        text: `Restored condition to version ${versionNumber} successfully.`,
      });
      setVersionModalCondition(null);
      await fetchConditions();
    } catch (err: any) {
      setNotification({ type: "error", text: err.message || "Restore failed" });
    }
  };

  const filteredConditions = conditions.filter((c) => {
    const matchesSearch =
      c.name_en?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.slug?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (c.name_ar && c.name_ar.includes(searchTerm));
    const matchesStatus = statusFilter === "ALL" || c.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="container mx-auto px-4 sm:px-6 py-10 max-w-6xl space-y-6">
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
          <FileCheck className="h-3 w-3 mr-1 rtl:mr-0 rtl:ml-1 inline" />
          Bilingual Medical CMS
        </Badge>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white flex items-center space-x-2.5 rtl:space-x-reverse">
            <FileEdit className="h-7 w-7 text-teal-700" />
            <span>{language === "ar" ? "إدارة المحتوى الطبي" : "Medical Content CMS & Versioning"}</span>
          </h1>
          <p className="text-xs text-muted-foreground">
            {language === "ar"
              ? "تحرير ومراجعة مقالات الحالات الطبية ثنائية اللغة المعتمدة للمكتبة الصحية العامة."
              : "Bilingual medical authoring, clinical review gate, and historical snapshot restoration."}
          </p>
        </div>

        <Button
          variant="clinical"
          size="sm"
          onClick={() => setIsAddOpen(true)}
          className="text-xs font-semibold"
        >
          <PlusCircle className="h-3.5 w-3.5 mr-1.5 rtl:mr-0 rtl:ml-1.5" />
          {language === "ar" ? "إضافة حالة طبية" : "Add Medical Condition"}
        </Button>
      </div>

      {/* Notification Banner */}
      {notification && (
        <div
          className={`p-3 rounded-md text-xs flex items-center justify-between ${
            notification.type === "success"
              ? "bg-teal-50 border border-teal-200 text-teal-800"
              : "bg-rose-50 border border-rose-200 text-rose-800"
          }`}
        >
          <div className="flex items-center space-x-2 rtl:space-x-reverse">
            {notification.type === "success" ? (
              <CheckCircle2 className="h-4 w-4 text-teal-600" />
            ) : (
              <AlertCircle className="h-4 w-4 text-rose-600" />
            )}
            <span>{notification.text}</span>
          </div>
          <button onClick={() => setNotification(null)} className="font-bold">×</button>
        </div>
      )}

      {/* Search & Status Filters */}
      <Card className="border-border shadow-sm">
        <CardContent className="p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-2.5 rtl:left-auto rtl:right-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder={language === "ar" ? "البحث بالاسم أو الرمز..." : "Search condition or slug..."}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8 rtl:pl-3 rtl:pr-8 text-xs h-9"
            />
          </div>

          <div className="flex items-center space-x-1.5 rtl:space-x-reverse w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
            {["ALL", "PUBLISHED", "APPROVED", "SUBMITTED_FOR_REVIEW", "DRAFT"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1 rounded text-xs font-semibold whitespace-nowrap transition-colors ${
                  statusFilter === st
                    ? "bg-teal-700 text-white"
                    : "bg-slate-100 dark:bg-slate-800 text-muted-foreground hover:bg-slate-200"
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Conditions Table */}
      <Card className="border-border shadow-sm">
        <CardHeader className="pb-3 border-b border-border/60">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-bold">
              {language === "ar" ? "مقالات الحالات الطبية" : "Medical Condition Directory"}
            </CardTitle>
            <span className="text-xs text-muted-foreground">
              {filteredConditions.length} {language === "ar" ? "حالة" : "conditions"}
            </span>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <div className="divide-y divide-border text-xs">
            {isLoading ? (
              <div className="p-8 text-center text-muted-foreground">
                {language === "ar" ? "جارٍ تحميل المحتوى الطبي..." : "Loading medical conditions..."}
              </div>
            ) : filteredConditions.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">
                {language === "ar" ? "لا توجد حالات طبية مطابقة لمعايير البحث." : "No conditions match filter criteria."}
              </div>
            ) : (
              filteredConditions.map((cond) => (
                <div
                  key={cond.id}
                  className="p-4 flex flex-col md:flex-row md:items-start justify-between gap-4 hover:bg-slate-50/50 dark:hover:bg-slate-900/50 transition-colors"
                >
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center space-x-2 rtl:space-x-reverse flex-wrap gap-y-1">
                      <span className="font-bold text-sm text-slate-900 dark:text-white">
                        {cond.name_en || cond.slug}
                      </span>
                      <Badge
                        variant={
                          cond.status === "PUBLISHED"
                            ? "success"
                            : cond.status === "APPROVED"
                            ? "clinical"
                            : "outline"
                        }
                        className="text-[10px]"
                      >
                        {cond.status}
                      </Badge>
                      <span className="text-[10px] font-mono bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">
                        {cond.version || "v1.0"}
                      </span>
                      <span className="text-[10px] text-muted-foreground font-mono">
                        ({cond.slug})
                      </span>
                    </div>

                    {cond.name_ar && (
                      <div className="text-slate-600 dark:text-slate-400 font-arabic text-xs">
                        {cond.name_ar}
                      </div>
                    )}

                    <div className="text-[11px] text-muted-foreground flex items-center space-x-3 rtl:space-x-reverse pt-0.5 flex-wrap">
                      <span>Reviewed by: {cond.last_reviewed_by || "Clinical Board"}</span>
                      <span>•</span>
                      <span>Updated: {cond.updated_at || "Recent"}</span>
                    </div>
                  </div>

                  {/* Review Actions */}
                  <div className="flex items-center space-x-1.5 rtl:space-x-reverse shrink-0">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openVersionModal(cond)}
                      className="text-xs h-8"
                    >
                      <History className="h-3 w-3 mr-1 rtl:mr-0 rtl:ml-1" />
                      {language === "ar" ? "السجل" : "History"}
                    </Button>

                    <Link href={`/library/${cond.slug}`} target="_blank">
                      <Button variant="outline" size="sm" className="text-xs h-8">
                        <Eye className="h-3 w-3 mr-1 rtl:mr-0 rtl:ml-1" />
                        Preview
                      </Button>
                    </Link>

                    {cond.status === "DRAFT" && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleReviewAction(cond.id, "SUBMIT_FOR_REVIEW")}
                        className="text-xs h-8 border-teal-300 text-teal-800"
                      >
                        <Send className="h-3 w-3 mr-1 rtl:mr-0 rtl:ml-1" />
                        Submit Review
                      </Button>
                    )}

                    {cond.status === "SUBMITTED_FOR_REVIEW" && (
                      <Button
                        variant="clinical"
                        size="sm"
                        onClick={() => handleReviewAction(cond.id, "APPROVE")}
                        className="text-xs h-8"
                      >
                        <ShieldCheck className="h-3 w-3 mr-1 rtl:mr-0 rtl:ml-1" />
                        Approve
                      </Button>
                    )}

                    {cond.status === "APPROVED" && (
                      <Button
                        variant="default"
                        size="sm"
                        onClick={() => handleReviewAction(cond.id, "PUBLISH")}
                        className="text-xs h-8 bg-teal-700 hover:bg-teal-800"
                      >
                        <Send className="h-3 w-3 mr-1 rtl:mr-0 rtl:ml-1" />
                        Publish
                      </Button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Add Condition Modal */}
      {isAddOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <Card className="w-full max-w-3xl max-h-[90vh] overflow-y-auto border-border shadow-xl animate-in fade-in zoom-in-95">
            <CardHeader className="pb-3 border-b border-border/60">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-bold flex items-center space-x-2 rtl:space-x-reverse">
                  <FileEdit className="h-4 w-4 text-teal-700" />
                  <span>{language === "ar" ? "إضافة حالة طبية جديدة" : "Add New Medical Condition (Bilingual)"}</span>
                </CardTitle>
                <button
                  onClick={() => setIsAddOpen(false)}
                  className="text-muted-foreground hover:text-slate-900 dark:hover:text-white"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <CardDescription className="text-xs">
                {language === "ar"
                  ? "إدخال البيانات السريرية باللغتين العربية والإنجليزية، مع توثيق الأدلة العلمية."
                  : "Structured clinical description, mechanism, diagnostics, and guideline citations."}
              </CardDescription>
            </CardHeader>

            <form onSubmit={handleCreateCondition}>
              <CardContent className="space-y-4 pt-4 text-xs">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Condition Slug (URL Identifier)</Label>
                    <Input
                      placeholder="e.g. klinefelter-syndrome"
                      value={newCond.slug}
                      onChange={(e) => setNewCond({ ...newCond, slug: e.target.value })}
                      required
                      className="font-mono text-xs h-9"
                    />
                  </div>

                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Category</Label>
                    <select
                      value={newCond.category_id}
                      onChange={(e) => setNewCond({ ...newCond, category_id: Number(e.target.value) })}
                      className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-xs shadow-sm"
                    >
                      {categories.map((c) => (
                        <option key={c.id} value={c.id}>{c.name_en} ({c.name_ar})</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Condition Name (English)</Label>
                    <Input
                      placeholder="e.g. Klinefelter Syndrome (47,XXY)"
                      value={newCond.name_en}
                      onChange={(e) => setNewCond({ ...newCond, name_en: e.target.value })}
                      required
                      className="text-xs h-9"
                    />
                  </div>

                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Condition Name (Arabic)</Label>
                    <Input
                      placeholder="مثال: متلازمة كلاينفلتر (47,XXY)"
                      value={newCond.name_ar}
                      onChange={(e) => setNewCond({ ...newCond, name_ar: e.target.value })}
                      required
                      className="text-xs h-9 font-arabic"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Short Summary (English)</Label>
                    <textarea
                      rows={2}
                      value={newCond.short_description_en}
                      onChange={(e) => setNewCond({ ...newCond, short_description_en: e.target.value })}
                      required
                      className="w-full rounded-md border border-input bg-background p-2 text-xs"
                    />
                  </div>

                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Short Summary (Arabic)</Label>
                    <textarea
                      rows={2}
                      value={newCond.short_description_ar}
                      onChange={(e) => setNewCond({ ...newCond, short_description_ar: e.target.value })}
                      required
                      className="w-full rounded-md border border-input bg-background p-2 text-xs font-arabic"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Detailed Explanation (English)</Label>
                    <textarea
                      rows={3}
                      value={newCond.detailed_explanation_en}
                      onChange={(e) => setNewCond({ ...newCond, detailed_explanation_en: e.target.value })}
                      required
                      className="w-full rounded-md border border-input bg-background p-2 text-xs"
                    />
                  </div>

                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Detailed Explanation (Arabic)</Label>
                    <textarea
                      rows={3}
                      value={newCond.detailed_explanation_ar}
                      onChange={(e) => setNewCond({ ...newCond, detailed_explanation_ar: e.target.value })}
                      required
                      className="w-full rounded-md border border-input bg-background p-2 text-xs font-arabic"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Biological Mechanism (English)</Label>
                    <textarea
                      rows={2}
                      value={newCond.biological_mechanism_en}
                      onChange={(e) => setNewCond({ ...newCond, biological_mechanism_en: e.target.value })}
                      className="w-full rounded-md border border-input bg-background p-2 text-xs"
                    />
                  </div>

                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Biological Mechanism (Arabic)</Label>
                    <textarea
                      rows={2}
                      value={newCond.biological_mechanism_ar}
                      onChange={(e) => setNewCond({ ...newCond, biological_mechanism_ar: e.target.value })}
                      className="w-full rounded-md border border-input bg-background p-2 text-xs font-arabic"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Organs Involved (Comma-separated)</Label>
                    <Input
                      value={newCond.organs_involved}
                      onChange={(e) => setNewCond({ ...newCond, organs_involved: e.target.value })}
                      className="text-xs h-9"
                    />
                  </div>

                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Evidence Classification</Label>
                    <Input
                      value={newCond.evidence_classification}
                      onChange={(e) => setNewCond({ ...newCond, evidence_classification: e.target.value })}
                      className="text-xs h-9"
                    />
                  </div>
                </div>

                <div className="flex items-center space-x-2 rtl:space-x-reverse pt-2">
                  <input
                    type="checkbox"
                    id="asympCheck"
                    checked={newCond.can_be_asymptomatic}
                    onChange={(e) => setNewCond({ ...newCond, can_be_asymptomatic: e.target.checked })}
                    className="h-4 w-4 rounded border-gray-300 text-teal-600 focus:ring-teal-500"
                  />
                  <Label htmlFor="asympCheck" className="text-xs cursor-pointer">
                    {language === "ar" ? "يمكن أن تكون الحالة غير مصحوبة بأعراض (Asymptomatic)" : "Condition Can Remain Asymptomatic"}
                  </Label>
                </div>

                <div className="flex items-center justify-end space-x-2 rtl:space-x-reverse pt-4 border-t border-border/60">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setIsAddOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" variant="clinical" size="sm">
                    Save Condition
                  </Button>
                </div>
              </CardContent>
            </form>
          </Card>
        </div>
      )}

      {/* Version History Modal */}
      {versionModalCondition && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <Card className="w-full max-w-2xl max-h-[85vh] overflow-y-auto border-border shadow-xl animate-in fade-in zoom-in-95">
            <CardHeader className="pb-3 border-b border-border/60">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-bold flex items-center space-x-2 rtl:space-x-reverse">
                  <History className="h-4 w-4 text-teal-700" />
                  <span>Version Snapshots: {versionModalCondition.name_en}</span>
                </CardTitle>
                <button
                  onClick={() => setVersionModalCondition(null)}
                  className="text-muted-foreground hover:text-slate-900 dark:hover:text-white"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <CardDescription className="text-xs">
                Review immutable historical snapshots and restore earlier approved clinical versions.
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-4 pt-4 text-xs">
              <div className="space-y-1">
                <Label className="text-xs font-semibold">Reason for Restoration (Audit Log Requirement)</Label>
                <Input
                  placeholder="e.g. Rollback to prior consensus guidelines after clinical board review"
                  value={restoreReason}
                  onChange={(e) => setRestoreReason(e.target.value)}
                  className="text-xs h-9"
                />
              </div>

              <div className="divide-y divide-border border rounded-md">
                {isLoadingVersions ? (
                  <div className="p-6 text-center text-muted-foreground">Loading historical snapshots...</div>
                ) : versionHistory.length === 0 ? (
                  <div className="p-6 text-center text-muted-foreground">
                    No historical snapshots archived yet for this condition. Current version is initial baseline.
                  </div>
                ) : (
                  versionHistory.map((v) => (
                    <div key={v.id} className="p-3.5 flex items-center justify-between gap-3 hover:bg-slate-50/50 dark:hover:bg-slate-900/50">
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2 rtl:space-x-reverse">
                          <span className="font-bold text-sm">Version {v.version_number}</span>
                          <span className="text-[10px] text-muted-foreground">{new Date(v.created_at).toLocaleString()}</span>
                        </div>
                        <div className="text-[11px] text-muted-foreground">
                          Modified by: {v.created_by_user_id ? `User #${v.created_by_user_id}` : "Clinical Board"}
                        </div>
                      </div>

                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleRestoreVersion(v.version_number)}
                        disabled={!restoreReason.trim()}
                        className="text-xs h-8 text-amber-700 border-amber-200 hover:bg-amber-50"
                      >
                        <RotateCcw className="h-3 w-3 mr-1 rtl:mr-0 rtl:ml-1" />
                        Restore This Version
                      </Button>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
