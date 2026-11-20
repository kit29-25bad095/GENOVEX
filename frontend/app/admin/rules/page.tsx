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
  Sliders,
  ArrowLeft,
  CheckCircle2,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Lock,
  PlusCircle,
  History,
  X,
  FileCheck,
  Send,
  Eye,
  RefreshCw,
  Search,
} from "lucide-react";

export default function ClinicalRulesPage() {
  const { t, language } = useLanguage();
  const { user } = useAuth();

  const [rules, setRules] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedTier, setSelectedTier] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState("");
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Modal states
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [reviewingRule, setReviewingRule] = useState<any | null>(null);
  const [reviewNotes, setReviewNotes] = useState("");
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);

  const [versionHistoryRule, setVersionHistoryRule] = useState<any | null>(null);
  const [ruleVersions, setRuleVersions] = useState<any[]>([]);
  const [isLoadingVersions, setIsLoadingVersions] = useState(false);

  // New Rule Form State
  const [newRule, setNewRule] = useState({
    rule_code: "",
    title_en: "",
    title_ar: "",
    domain_code: "TESTICULAR_HISTORY",
    relevant_question_keys: "",
    outcome_tier: "CLINICAL_EVALUATION_RECOMMENDED",
    is_urgent_red_flag: false,
    priority_rank: 50,
    recommended_specialty: "Reproductive Urologist / Andrologist",
    trigger_question_key: "",
    trigger_operator: "eq",
    trigger_value: "yes",
    clinical_rationale_en: "",
    clinical_rationale_ar: "",
    evidence_title: "EAU Guidelines on Sexual and Reproductive Health (2024)",
    evidence_classification: "Level 1a",
  });

  const fetchRules = async () => {
    setIsLoading(true);
    try {
      const data = await ApiClient.getAdminRules();
      if (data && data.length > 0) {
        setRules(data);
      } else {
        throw new Error("Empty rules returned");
      }
    } catch (err) {
      console.error("Failed to fetch live rules:", err);
      // Fallback baseline
      setRules([
        {
          id: 1,
          rule_code: "R-URG-ACUTE-SCROTAL-PAIN",
          title_en: "Acute Scrotal Pain Emergency Pathway",
          title_ar: "مسار طوارئ ألم الصفن الحاد",
          priority_rank: 1,
          outcome_tier: "URGENT_MEDICAL_ASSESSMENT",
          is_urgent_red_flag: true,
          status: "PUBLISHED",
          rule_version: "1.0.0",
          recommended_specialty: "Emergency Medicine / Acute Urology",
          clinical_rationale_en: "Immediate evaluation required to rule out testicular torsion within 6 hours.",
          clinical_rationale_ar: "يلزم إجراء تقييم فوري لاستبعاد انفتال الخصية في غضون 6 ساعات.",
          evidence_references: [{ title: "EAU Guidelines on Urological Emergencies (2024)" }],
        },
        {
          id: 2,
          rule_code: "R-URG-TESTIS-LUMP",
          title_en: "Painless Testicular Mass Evaluation",
          title_ar: "تقييم كتلة الخصية غير المؤلمة",
          priority_rank: 2,
          outcome_tier: "URGENT_MEDICAL_ASSESSMENT",
          is_urgent_red_flag: true,
          status: "PUBLISHED",
          rule_version: "1.0.0",
          recommended_specialty: "Urologist (Oncologic / General)",
          clinical_rationale_en: "Painless mass carries strong clinical index of suspicion for testicular malignancy.",
          clinical_rationale_ar: "تحمل الكتلة غير المؤلمة مؤشراً سريرياً مرتفعاً للاشتباه في الأورام الخبيثة للخصية.",
          evidence_references: [{ title: "EAU Guidelines on Testicular Cancer (2024)" }],
        },
        {
          id: 3,
          rule_code: "R-REP-PROLONGED-TTC",
          title_en: "Prolonged Time-to-Conception (12+ Months)",
          title_ar: "تأخر الإنجاب لمدة 12 شهراً أو أكثر",
          priority_rank: 20,
          outcome_tier: "CLINICAL_EVALUATION_RECOMMENDED",
          is_urgent_red_flag: false,
          status: "PUBLISHED",
          rule_version: "1.0.0",
          recommended_specialty: "Reproductive Urologist / Andrologist",
          clinical_rationale_en: "Evaluation of male partner indicated after 12 months of regular unprotected intercourse.",
          clinical_rationale_ar: "يوصى بتقييم الشريك الذكر بعد 12 شهراً من المحاولة المنتظمة دون حمل.",
          evidence_references: [{ title: "AUA/ASRM Male Infertility Guideline (2021)" }],
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
  }, []);

  const handleCreateRule = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        rule_code: newRule.rule_code.trim().toUpperCase(),
        title_en: newRule.title_en,
        title_ar: newRule.title_ar,
        domain_code: newRule.domain_code,
        relevant_question_keys: newRule.relevant_question_keys.split(",").map(k => k.trim()).filter(Boolean),
        outcome_tier: newRule.outcome_tier,
        is_urgent_red_flag: newRule.is_urgent_red_flag,
        priority_rank: Number(newRule.priority_rank),
        recommended_specialty: newRule.recommended_specialty,
        trigger_criteria: {
          all_of: [
            {
              question_key: newRule.trigger_question_key || newRule.relevant_question_keys.split(",")[0]?.trim(),
              operator: newRule.trigger_operator,
              value: newRule.trigger_value,
            }
          ]
        },
        missing_response_handling: "NEVER_NEGATIVE",
        clinical_rationale_en: newRule.clinical_rationale_en,
        clinical_rationale_ar: newRule.clinical_rationale_ar,
        evidence_references: [
          {
            title: newRule.evidence_title,
            guideline_body: "EAU",
            year: 2024,
            recommendation_grade: newRule.evidence_classification,
          }
        ],
        evidence_classification: newRule.evidence_classification,
      };

      await ApiClient.createAdminRule(payload);
      setActionMessage(language === "ar" ? "تم إنشاء مسودة القاعدة الإكلينيكية بنجاح" : "Draft clinical rule created successfully.");
      setIsCreateOpen(false);
      await fetchRules();
    } catch (err: any) {
      setActionMessage(`Error: ${err.message}`);
    }
  };

  const handleReviewAction = async (action: "APPROVE" | "REJECT") => {
    if (!reviewingRule) return;
    setIsSubmittingReview(true);
    try {
      await ApiClient.reviewAdminRule(reviewingRule.id, action, reviewNotes);
      setActionMessage(
        language === "ar" 
          ? `تم اعتماد الإجراء (${action}) للقاعدة ${reviewingRule.rule_code}`
          : `Review action (${action}) completed for rule ${reviewingRule.rule_code}`
      );
      setReviewingRule(null);
      setReviewNotes("");
      await fetchRules();
    } catch (err: any) {
      setActionMessage(`Review Error: ${err.message}`);
    } finally {
      setIsSubmittingReview(false);
    }
  };

  const handlePublishRule = async (ruleId: number) => {
    try {
      await ApiClient.publishAdminRule(ruleId);
      setActionMessage(language === "ar" ? "تم نشر القاعدة إلى المحرك المباشر بنجاح" : "Rule successfully published to live evaluation engine.");
      await fetchRules();
    } catch (err: any) {
      setActionMessage(`Publishing Error: ${err.message}`);
    }
  };

  const handleViewVersions = async (rule: any) => {
    setVersionHistoryRule(rule);
    setIsLoadingVersions(true);
    try {
      const versions = await ApiClient.getAdminRuleVersions(rule.id);
      setRuleVersions(versions);
    } catch (err) {
      setRuleVersions([]);
    } finally {
      setIsLoadingVersions(false);
    }
  };

  const filteredRules = rules.filter((r) => {
    const matchesTier = selectedTier === "ALL" || r.outcome_tier === selectedTier;
    const matchesSearch =
      r.rule_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.title_en.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (r.title_ar && r.title_ar.includes(searchTerm));
    return matchesTier && matchesSearch;
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
          <Lock className="h-3 w-3 mr-1 rtl:mr-0 rtl:ml-1 inline" />
          Deterministic Rule Governance
        </Badge>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white flex items-center space-x-2.5 rtl:space-x-reverse">
            <Sliders className="h-7 w-7 text-teal-700" />
            <span>{language === "ar" ? "حوكمة القواعد الإكلينيكية" : "Deterministic Clinical Rules CMS"}</span>
          </h1>
          <p className="text-xs text-muted-foreground">
            {language === "ar"
              ? "مراجعة واعتماد القواعد السريرية المبنية على الأدلة والمستندة إلى إرشادات الجمعية الأوروبية والجمعية الأمريكية للمسالك البولية."
              : "Authoring, three-valued logic verification, and formal clinician approval under EAU / AUA guidelines."}
          </p>
        </div>

        <Button
          variant="clinical"
          size="sm"
          onClick={() => setIsCreateOpen(true)}
          className="text-xs font-semibold"
        >
          <PlusCircle className="h-3.5 w-3.5 mr-1.5 rtl:mr-0 rtl:ml-1.5" />
          {language === "ar" ? "إضافة مسودة قاعدة" : "New Rule Draft"}
        </Button>
      </div>

      {/* Action Notification Message */}
      {actionMessage && (
        <div className="p-3 bg-teal-50 border border-teal-200 rounded-md text-xs text-teal-800 flex items-center justify-between">
          <div className="flex items-center space-x-2 rtl:space-x-reverse">
            <CheckCircle2 className="h-4 w-4 text-teal-600" />
            <span>{actionMessage}</span>
          </div>
          <button onClick={() => setActionMessage(null)} className="text-teal-600 font-bold hover:text-teal-900">×</button>
        </div>
      )}

      {/* Search & Tier Filters */}
      <Card className="border-border shadow-sm">
        <CardContent className="p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-2.5 rtl:left-auto rtl:right-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder={language === "ar" ? "البحث برمز القاعدة أو العنوان..." : "Search code or title..."}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8 rtl:pl-3 rtl:pr-8 text-xs h-9"
            />
          </div>

          <div className="flex items-center space-x-1.5 rtl:space-x-reverse w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
            {[
              { id: "ALL", labelEn: "All Tiers", labelAr: "كافة المستويات" },
              { id: "URGENT_MEDICAL_ASSESSMENT", labelEn: "Urgent Tier 4", labelAr: "طوارئ (المستوى 4)" },
              { id: "CLINICAL_EVALUATION_RECOMMENDED", labelEn: "Tier 3 Specialist", labelAr: "استشاري (المستوى 3)" },
              { id: "RISK_FACTORS_IDENTIFIED", labelEn: "Tier 2 Lifestyle", labelAr: "عوامل خطر (المستوى 2)" },
            ].map((t) => (
              <button
                key={t.id}
                onClick={() => setSelectedTier(t.id)}
                className={`px-3 py-1 rounded text-xs font-semibold whitespace-nowrap transition-colors ${
                  selectedTier === t.id
                    ? "bg-teal-700 text-white"
                    : "bg-slate-100 dark:bg-slate-800 text-muted-foreground hover:bg-slate-200"
                }`}
              >
                {language === "ar" ? t.labelAr : t.labelEn}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Rules Table */}
      <Card className="border-border shadow-sm">
        <CardHeader className="pb-3 border-b border-border/60">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-bold">
              {language === "ar" ? "القواعد السريرية المعتمدة" : "Active & Draft Clinical Rules"}
            </CardTitle>
            <span className="text-xs text-muted-foreground">
              {filteredRules.length} {language === "ar" ? "قاعدة" : "rules"}
            </span>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <div className="divide-y divide-border text-xs">
            {isLoading ? (
              <div className="p-8 text-center text-muted-foreground">
                {language === "ar" ? "جارٍ تحميل القواعد الإكلينيكية..." : "Loading clinical rules..."}
              </div>
            ) : filteredRules.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">
                {language === "ar" ? "لا توجد قواعد مطابقة للبحث." : "No clinical rules match criteria."}
              </div>
            ) : (
              filteredRules.map((r) => (
                <div
                  key={r.id}
                  className="p-4 flex flex-col md:flex-row md:items-start justify-between gap-4 hover:bg-slate-50/50 dark:hover:bg-slate-900/50 transition-colors"
                >
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center space-x-2 rtl:space-x-reverse flex-wrap gap-y-1">
                      <span className="font-mono font-bold text-xs bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded text-slate-800 dark:text-slate-200">
                        {r.rule_code}
                      </span>
                      <span className="font-bold text-sm text-slate-900 dark:text-white">
                        {language === "ar" && r.title_ar ? r.title_ar : r.title_en}
                      </span>
                      {r.is_urgent_red_flag && (
                        <Badge variant="destructive" className="text-[10px]">
                          RED FLAG
                        </Badge>
                      )}
                      <Badge
                        variant={
                          r.status === "PUBLISHED"
                            ? "success"
                            : r.status === "APPROVED"
                            ? "clinical"
                            : "outline"
                        }
                        className="text-[10px]"
                      >
                        {r.status}
                      </Badge>
                      <span className="text-[10px] text-muted-foreground font-mono">
                        v{r.rule_version}
                      </span>
                    </div>

                    <div className="text-[11px] text-slate-600 dark:text-slate-400">
                      {language === "ar" && r.clinical_rationale_ar
                        ? r.clinical_rationale_ar
                        : r.clinical_rationale_en}
                    </div>

                    <div className="flex items-center space-x-3 rtl:space-x-reverse text-[10px] text-muted-foreground flex-wrap pt-0.5">
                      <span>Priority Rank: <strong>{r.priority_rank}</strong></span>
                      <span>•</span>
                      <span>Tier: <strong>{r.outcome_tier}</strong></span>
                      <span>•</span>
                      <span>Specialty: <strong>{r.recommended_specialty || "Urology"}</strong></span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center space-x-2 rtl:space-x-reverse shrink-0">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleViewVersions(r)}
                      className="text-xs h-8"
                    >
                      <History className="h-3 w-3 mr-1 rtl:mr-0 rtl:ml-1" />
                      {language === "ar" ? "الإصدارات" : "Versions"}
                    </Button>

                    {r.status === "DRAFT" || r.status === "SUBMITTED_FOR_REVIEW" ? (
                      <Button
                        variant="clinical"
                        size="sm"
                        onClick={() => {
                          setReviewingRule(r);
                          setReviewNotes("");
                        }}
                        className="text-xs h-8"
                      >
                        <ShieldCheck className="h-3.5 w-3.5 mr-1 rtl:mr-0 rtl:ml-1" />
                        {language === "ar" ? "مراجعة الطبيب" : "Clinical Review"}
                      </Button>
                    ) : r.status === "APPROVED" ? (
                      <Button
                        variant="default"
                        size="sm"
                        onClick={() => handlePublishRule(r.id)}
                        className="text-xs h-8 bg-teal-700 hover:bg-teal-800"
                      >
                        <Send className="h-3 w-3 mr-1 rtl:mr-0 rtl:ml-1" />
                        {language === "ar" ? "نشر للمحرك" : "Publish"}
                      </Button>
                    ) : (
                      <span className="inline-flex items-center text-[11px] text-emerald-600 font-medium px-2 py-1 bg-emerald-50 dark:bg-emerald-950/40 rounded">
                        <CheckCircle2 className="h-3 w-3 mr-1 rtl:mr-0 rtl:ml-1" />
                        Live in Engine
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Create New Rule Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto border-border shadow-xl animate-in fade-in zoom-in-95">
            <CardHeader className="pb-3 border-b border-border/60">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-bold flex items-center space-x-2 rtl:space-x-reverse">
                  <Sliders className="h-4 w-4 text-teal-700" />
                  <span>{language === "ar" ? "إنشاء مسودة قاعدة إكلينيكية جديدة" : "Author New Deterministic Clinical Rule"}</span>
                </CardTitle>
                <button
                  onClick={() => setIsCreateOpen(false)}
                  className="text-muted-foreground hover:text-slate-900 dark:hover:text-white"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <CardDescription className="text-xs">
                {language === "ar"
                  ? "القواعد الجديدة تبدأ كمسودة (DRAFT) وتتطلب اعتماد طبيب مرخص قبل دخول حيز النشر."
                  : "All new clinical rules start in DRAFT status and require formal clinician review."}
              </CardDescription>
            </CardHeader>

            <form onSubmit={handleCreateRule}>
              <CardContent className="space-y-4 pt-4 text-xs">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Rule Code</Label>
                    <Input
                      placeholder="e.g. R-HOR-TESTOSTERONE-LOW"
                      value={newRule.rule_code}
                      onChange={(e) => setNewRule({ ...newRule, rule_code: e.target.value })}
                      required
                      className="font-mono text-xs h-9"
                    />
                  </div>

                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Priority Rank (1 = Emergency, 100 = Low)</Label>
                    <Input
                      type="number"
                      min={1}
                      max={100}
                      value={newRule.priority_rank}
                      onChange={(e) => setNewRule({ ...newRule, priority_rank: Number(e.target.value) })}
                      required
                      className="text-xs h-9"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Title (English)</Label>
                    <Input
                      placeholder="e.g. Hypogonadism and Low Morning Testosterone"
                      value={newRule.title_en}
                      onChange={(e) => setNewRule({ ...newRule, title_en: e.target.value })}
                      required
                      className="text-xs h-9"
                    />
                  </div>

                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Title (Arabic)</Label>
                    <Input
                      placeholder="مثال: قصور الغدد التناسلية وانخفاض التستوستيرون الصباحي"
                      value={newRule.title_ar}
                      onChange={(e) => setNewRule({ ...newRule, title_ar: e.target.value })}
                      required
                      className="text-xs h-9 font-arabic"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Questionnaire Domain</Label>
                    <select
                      value={newRule.domain_code}
                      onChange={(e) => setNewRule({ ...newRule, domain_code: e.target.value })}
                      className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-xs shadow-sm"
                    >
                      <option value="BASIC_HEALTH">1. Basic Health</option>
                      <option value="REPRODUCTIVE_HISTORY">2. Reproductive History</option>
                      <option value="TESTICULAR_HISTORY">3. Testicular History</option>
                      <option value="MEDICAL_HISTORY">4. Medical History</option>
                      <option value="HORMONAL_HEALTH">5. Hormonal Health</option>
                      <option value="METABOLIC_HEALTH">6. Metabolic Health</option>
                      <option value="LIFESTYLE_HABITS">7. Lifestyle & Habits</option>
                      <option value="MEDICATIONS_SUBSTANCES">8. Medications & Substances</option>
                      <option value="OCCUPATIONAL_ENVIRONMENTAL">9. Occupational & Environmental</option>
                      <option value="SEXUAL_HEALTH">10. Sexual Health</option>
                      <option value="FAMILY_GENETIC_HISTORY">11. Family & Genetic History</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Outcome Tier</Label>
                    <select
                      value={newRule.outcome_tier}
                      onChange={(e) => setNewRule({ ...newRule, outcome_tier: e.target.value })}
                      className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-xs shadow-sm"
                    >
                      <option value="NO_REPORTED_RISK_FACTORS">Tier 1: No Reported Risk Factors</option>
                      <option value="RISK_FACTORS_IDENTIFIED">Tier 2: Risk Factors Identified</option>
                      <option value="CLINICAL_EVALUATION_RECOMMENDED">Tier 3: Clinical Evaluation Recommended</option>
                      <option value="URGENT_MEDICAL_ASSESSMENT">Tier 4: Urgent Medical Assessment</option>
                    </select>
                  </div>
                </div>

                {/* Deterministic Trigger Condition */}
                <div className="p-3 bg-slate-50 dark:bg-slate-900 rounded border border-border space-y-2">
                  <Label className="text-xs font-bold text-teal-800 dark:text-teal-400">
                    Deterministic Trigger Condition (Predicate)
                  </Label>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    <div>
                      <span className="text-[10px] text-muted-foreground block mb-0.5">Question Key</span>
                      <Input
                        placeholder="e.g. Q_ANABOLIC_STEROIDS"
                        value={newRule.trigger_question_key}
                        onChange={(e) => setNewRule({ ...newRule, trigger_question_key: e.target.value })}
                        required
                        className="font-mono text-xs h-8"
                      />
                    </div>
                    <div>
                      <span className="text-[10px] text-muted-foreground block mb-0.5">Operator</span>
                      <select
                        value={newRule.trigger_operator}
                        onChange={(e) => setNewRule({ ...newRule, trigger_operator: e.target.value })}
                        className="w-full h-8 rounded-md border border-input bg-background px-2 text-xs"
                      >
                        <option value="eq">Equals (==)</option>
                        <option value="neq">Not Equals (!=)</option>
                        <option value="in">Contains In Array</option>
                        <option value="gt">Greater Than (&gt;)</option>
                      </select>
                    </div>
                    <div>
                      <span className="text-[10px] text-muted-foreground block mb-0.5">Expected Value</span>
                      <Input
                        placeholder="e.g. yes"
                        value={newRule.trigger_value}
                        onChange={(e) => setNewRule({ ...newRule, trigger_value: e.target.value })}
                        required
                        className="font-mono text-xs h-8"
                      />
                    </div>
                  </div>
                </div>

                <div className="space-y-1">
                  <Label className="text-xs font-semibold">Clinical Rationale (English)</Label>
                  <textarea
                    rows={2}
                    value={newRule.clinical_rationale_en}
                    onChange={(e) => setNewRule({ ...newRule, clinical_rationale_en: e.target.value })}
                    required
                    className="w-full rounded-md border border-input bg-background p-2 text-xs shadow-sm"
                  />
                </div>

                <div className="space-y-1">
                  <Label className="text-xs font-semibold">Clinical Rationale (Arabic)</Label>
                  <textarea
                    rows={2}
                    value={newRule.clinical_rationale_ar}
                    onChange={(e) => setNewRule({ ...newRule, clinical_rationale_ar: e.target.value })}
                    required
                    className="w-full rounded-md border border-input bg-background p-2 text-xs shadow-sm font-arabic"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Evidence Reference</Label>
                    <Input
                      value={newRule.evidence_title}
                      onChange={(e) => setNewRule({ ...newRule, evidence_title: e.target.value })}
                      required
                      className="text-xs h-9"
                    />
                  </div>

                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Evidence Grade</Label>
                    <Input
                      value={newRule.evidence_classification}
                      onChange={(e) => setNewRule({ ...newRule, evidence_classification: e.target.value })}
                      required
                      className="text-xs h-9"
                    />
                  </div>
                </div>

                <div className="flex items-center space-x-2 rtl:space-x-reverse pt-2">
                  <input
                    type="checkbox"
                    id="urgentFlagCheck"
                    checked={newRule.is_urgent_red_flag}
                    onChange={(e) => setNewRule({ ...newRule, is_urgent_red_flag: e.target.checked })}
                    className="h-4 w-4 rounded border-gray-300 text-rose-600 focus:ring-rose-500"
                  />
                  <Label htmlFor="urgentFlagCheck" className="text-xs cursor-pointer text-rose-800 dark:text-rose-400 font-semibold">
                    Mark as Urgent Emergency Red Flag
                  </Label>
                </div>

                <div className="flex items-center justify-end space-x-2 rtl:space-x-reverse pt-4 border-t border-border/60">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setIsCreateOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" variant="clinical" size="sm">
                    Create Draft Rule
                  </Button>
                </div>
              </CardContent>
            </form>
          </Card>
        </div>
      )}

      {/* Clinician Review & Sign-off Modal */}
      {reviewingRule && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <Card className="w-full max-w-lg border-border shadow-xl animate-in fade-in zoom-in-95">
            <CardHeader className="pb-3 border-b border-border/60">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-bold flex items-center space-x-2 rtl:space-x-reverse">
                  <ShieldCheck className="h-4 w-4 text-teal-700" />
                  <span>{language === "ar" ? "اعتماد المراجعة السريرية للقاعدة" : "Formal Clinician Review Sign-Off"}</span>
                </CardTitle>
                <button
                  onClick={() => setReviewingRule(null)}
                  className="text-muted-foreground hover:text-slate-900 dark:hover:text-white"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <CardDescription className="text-xs">
                Rule: <span className="font-mono font-bold text-slate-800 dark:text-slate-200">{reviewingRule.rule_code}</span> ({reviewingRule.title_en})
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-4 pt-4 text-xs">
              <div className="p-3 bg-slate-50 dark:bg-slate-900 rounded border border-border text-[11px] space-y-1">
                <div>Tier: <strong>{reviewingRule.outcome_tier}</strong></div>
                <div>Rationale: {reviewingRule.clinical_rationale_en}</div>
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-semibold">
                  {language === "ar" ? "ملاحظات الطبيب المعتمد (إلزامية في حال الرفض)" : "Clinician Review Notes (Required for rejection)"}
                </Label>
                <textarea
                  rows={3}
                  value={reviewNotes}
                  onChange={(e) => setReviewNotes(e.target.value)}
                  placeholder="e.g. Verified against EAU 2024 Guidelines, Section 8. Criteria sound."
                  className="w-full rounded-md border border-input bg-background p-2 text-xs shadow-sm"
                />
              </div>

              <div className="flex items-center justify-end space-x-2 rtl:space-x-reverse pt-3 border-t border-border/60">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setReviewingRule(null)}
                  disabled={isSubmittingReview}
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  variant="destructive"
                  size="sm"
                  onClick={() => handleReviewAction("REJECT")}
                  disabled={isSubmittingReview || !reviewNotes.trim()}
                >
                  Reject Rule
                </Button>
                <Button
                  type="button"
                  variant="clinical"
                  size="sm"
                  onClick={() => handleReviewAction("APPROVE")}
                  disabled={isSubmittingReview}
                >
                  Approve Rule
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Version History Modal */}
      {versionHistoryRule && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <Card className="w-full max-w-xl max-h-[80vh] overflow-y-auto border-border shadow-xl animate-in fade-in zoom-in-95">
            <CardHeader className="pb-3 border-b border-border/60">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-bold flex items-center space-x-2 rtl:space-x-reverse">
                  <History className="h-4 w-4 text-teal-700" />
                  <span>Version History: {versionHistoryRule.rule_code}</span>
                </CardTitle>
                <button
                  onClick={() => setVersionHistoryRule(null)}
                  className="text-muted-foreground hover:text-slate-900 dark:hover:text-white"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <CardDescription className="text-xs">
                Immutable audit record of historical rule iterations.
              </CardDescription>
            </CardHeader>

            <CardContent className="p-4 text-xs">
              {isLoadingVersions ? (
                <div className="py-6 text-center text-muted-foreground">Loading versions...</div>
              ) : ruleVersions.length === 0 ? (
                <div className="py-6 text-center text-muted-foreground">
                  No historical versions archived yet. The current version (v{versionHistoryRule.rule_version}) is the initial baseline.
                </div>
              ) : (
                <div className="space-y-3">
                  {ruleVersions.map((v) => (
                    <div key={v.id} className="p-3 bg-slate-50 dark:bg-slate-900 rounded border border-border text-xs space-y-1">
                      <div className="flex items-center justify-between font-bold">
                        <span>Version {v.version_tag}</span>
                        <span className="text-[10px] text-muted-foreground">{new Date(v.created_at).toLocaleString()}</span>
                      </div>
                      <div className="text-[11px] text-muted-foreground">{v.title_en}</div>
                      <div className="text-[10px] text-teal-700 font-mono">Tier: {v.outcome_tier}</div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
