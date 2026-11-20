"use client";

import React, { useState, useEffect } from "react";
import { useLanguage } from "@/context/LanguageContext";
import { ApiClient } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Search, BookOpen, ShieldCheck, ExternalLink, Stethoscope, FileText } from "lucide-react";

interface ConditionItem {
  id: number;
  slug: string;
  name_en: string;
  name_ar: string;
  category_name_en?: string;
  category_name_ar?: string;
  summary_en: string;
  summary_ar: string;
  prevalence_info_en?: string;
  prevalence_info_ar?: string;
  guideline_reference?: string;
  evidence_level?: string;
}

export default function HealthLibraryPage() {
  const { t, language } = useLanguage();
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [conditions, setConditions] = useState<ConditionItem[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Fallback canonical conditions if backend API is offline during build/demo
  const defaultConditions: ConditionItem[] = [
    {
      id: 1,
      slug: "varicocele",
      name_en: "Clinical Varicocele (Scrotal Vein Dilation)",
      name_ar: "دوالي الخصية السريرية (توسع الأوردة المنوية)",
      category_name_en: "Scrotal & Vascular",
      category_name_ar: "الصفن والأوعية الدموية",
      summary_en: "Abnormal tortuosity and dilation of the pampiniform venous plexus, representing the most common identifiable and surgically correctable cause of primary and secondary male subfertility.",
      summary_ar: "توسع والتواء غير طبيعي في الضفيرة الوريدية المحلاقية، ويشكل السبب الأكثر شيوعاً للعقم الأولي والثانوي القابل للتصحيح جراحياً لدى الرجال.",
      prevalence_info_en: "15% of healthy adult men; up to 35-40% of men presenting with primary infertility.",
      prevalence_info_ar: "15٪ من الرجال البالغين؛ وما يصل إلى 35-40٪ من المراجعين لعقم أولي.",
      guideline_reference: "EAU Guidelines on Male Sexual and Reproductive Health (2024), Sec 4.1",
      evidence_level: "Level 1a (Systematic Reviews)",
    },
    {
      id: 2,
      slug: "non-obstructive-azoospermia",
      name_en: "Non-Obstructive Azoospermia (NOA)",
      name_ar: "فقد النطاف غير الانسدادي (NOA)",
      category_name_en: "Spermatogenic Failure",
      category_name_ar: "فشل تكوين الحيوانات المنوية",
      summary_en: "Complete absence of spermatozoa in the ejaculate after centrifugation due to intrinsic testicular failure or primary spermatogenic arrest. Evaluated via Micro-TESE and genetic karyotyping.",
      summary_ar: "الغياب التام للنطاف في السائل المنوي بعد التثفيل نتيجة فشل وظيفي في الخصية. يتم تقييمها بواسطة التفتيش الميكروسكوبي الدقيق micro-TESE والفحوصات الجينية.",
      prevalence_info_en: "Found in approximately 1% of all men and 10-15% of infertile men.",
      prevalence_info_ar: "يصيب حوالي 1٪ من عامة الرجال و 10-15٪ من الرجال المصابين بالعقم.",
      guideline_reference: "AUA/ASRM Guideline on Male Infertility (2021), Rec 14-16",
      evidence_level: "Level 1b (Randomized Trials & Cohorts)",
    },
    {
      id: 3,
      slug: "hypogonadotropic-hypogonadism",
      name_en: "Secondary Hypogonadism & Steroid Suppression",
      name_ar: "قصور الغدد التناسلية الثانوي وتثبيط الستيرويدات",
      category_name_en: "Endocrine & Metabolic",
      category_name_ar: "الغدد الصماء والتمثيل الغذائي",
      summary_en: "Suppression of pituitary LH/FSH secretion by exogenous testosterone or anabolic androgenic steroids, halting spermatogenesis. Potentially reversible via gonadotropin therapy (hCG/hMG).",
      summary_ar: "تثبيط إفراز هرموني LH و FSH النخاميين نتيجة التستوستيرون الخارجي أو الستيرويدات البنائية. قابل للعلاج بواسطة محفزات الغدد التناسلية مثل hCG و hMG.",
      prevalence_info_en: "Rising significantly among gym attendees and athletes using AAS regimens.",
      prevalence_info_ar: "تزايد ملحوظ بين مرتادي الصالات الرياضية ومستخدمي الستيرويدات.",
      guideline_reference: "EAU Guidelines on Sexual and Reproductive Health (2024), Sec 8.4",
      evidence_level: "Level 2a (Clinical Cohorts)",
    },
    {
      id: 4,
      slug: "acute-scrotal-pain-torsion",
      name_en: "Acute Scrotal Pain & Testicular Torsion",
      name_ar: "ألم الصفن الحاد والتواء الخصية",
      category_name_en: "Urological Emergencies",
      category_name_ar: "طوارئ المسالك البولية",
      summary_en: "Sudden ischemic rotation of the spermatic cord requiring immediate surgical exploration within 6 hours. High-priority red-flag emergency requiring zero diagnostic delay.",
      summary_ar: "دوران إقفاري مفاجئ للحبل المنوي يستوجب استكشافاً جراحياً عاجلاً خلال 6 ساعات. حالة طوارئ قصوى تتطلب عدم التأخير.",
      prevalence_info_en: "1 in 4,000 males under age 25 annually; can occur at any age.",
      prevalence_info_ar: "1 من كل 4000 ذكر سنوياً تحت سن 25، وقد يحدث في أي عمر.",
      guideline_reference: "EAU Guidelines on Urological Emergencies (2024), Sec 3.1",
      evidence_level: "Level 1b (Emergency Consensus)",
    },
    {
      id: 5,
      slug: "testicular-germ-cell-tumors",
      name_en: "Testicular Mass & Neoplasm Screening",
      name_ar: "فحص وتقييم كتل الخصية والأورام",
      category_name_en: "Oncologic Screening",
      category_name_ar: "الفحص الورمي",
      summary_en: "Typically presents as a firm, non-tender intrascrotal mass. Prompt physical examination and high-frequency scrotal Doppler ultrasound are mandatory within 48-72 hours.",
      summary_ar: "تظهر عادة ككتلة صلبة غير مؤلمة داخل كيس الصفن. الفحص السريري والتصوير بالموجات فوق الصوتية الدوبلر إلزامي خلال 48-72 ساعة.",
      prevalence_info_en: "Most common solid malignancy in young men aged 15-35; cure rate exceeds 95% when detected early.",
      prevalence_info_ar: "أكثر الأورام الصلبة شيوعاً بين 15 و 35 عاماً؛ ونسبة الشفاء تفوق 95٪ عند الكشف المبكر.",
      guideline_reference: "EAU Guidelines on Testicular Cancer (2024), Sec 4.2",
      evidence_level: "Level 1a (Multicenter Oncology Protocols)",
    },
  ];

  useEffect(() => {
    async function loadData() {
      try {
        const fetchedCats = await ApiClient.getCategories();
        if (fetchedCats && fetchedCats.length > 0) setCategories(fetchedCats);

        const fetchedConds = await ApiClient.getConditions();
        if (fetchedConds && fetchedConds.length > 0) {
          setConditions(fetchedConds);
        } else {
          setConditions(defaultConditions);
        }
      } catch (err) {
        setConditions(defaultConditions);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  const filteredConditions = conditions.filter((c) => {
    const matchesSearch =
      c.name_en.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.name_ar.includes(searchTerm) ||
      c.summary_en.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.summary_ar.includes(searchTerm);
    return matchesSearch;
  });

  return (
    <div className="container mx-auto px-4 sm:px-6 py-10 max-w-6xl space-y-8">
      {/* Header */}
      <div className="space-y-3">
        <Badge variant="outline" className="text-teal-700 dark:text-teal-400 border-teal-300">
          <BookOpen className="h-3.5 w-3.5 mr-1 rtl:mr-0 rtl:ml-1 inline" />
          {language === "ar" ? "المكتبة التثقيفية الطبية" : "Clinical Education Library"}
        </Badge>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          {language === "ar" ? "دليل أمراض الجهاز التناسلي والخصوبة الذكورية" : "Male Reproductive & Fertility Health Guide"}
        </h1>
        <p className="text-muted-foreground text-sm max-w-2xl">
          {language === "ar"
            ? "مقالات إكلينيكية موثوقة ومبنية على أحدث إرشادات EAU 2024 و AUA 2021 لتوضيح الحالات وطرق التقييم دون إثارة القلق."
            : "Peer-reviewed, evidence-linked clinical summaries grounded in EAU 2024 and AUA/ASRM 2021 guidelines."}
        </p>
      </div>

      {/* Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 rtl:left-auto rtl:right-3.5 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder={language === "ar" ? "ابحث عن حالة أو عرض (مثال: دوالي، ألم، هرمونات)..." : "Search condition or symptom (e.g., varicocele, pain, steroids)..."}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 rtl:pl-4 rtl:pr-10 h-10 bg-white dark:bg-slate-900"
          />
        </div>
      </div>

      {/* Condition Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {filteredConditions.map((cond) => (
          <Card key={cond.id} className="border-border hover:border-teal-400 transition-all shadow-sm flex flex-col justify-between">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between gap-2">
                <Badge variant="secondary" className="text-xs">
                  {language === "ar" ? cond.category_name_ar || "طب المسالك" : cond.category_name_en || "Urology"}
                </Badge>
                {cond.evidence_level && (
                  <span className="text-[10px] text-teal-800 dark:text-teal-300 font-mono bg-teal-50 dark:bg-teal-950/60 px-2 py-0.5 rounded">
                    {cond.evidence_level}
                  </span>
                )}
              </div>
              <CardTitle className="text-lg mt-2 text-slate-900 dark:text-white">
                {language === "ar" ? cond.name_ar : cond.name_en}
              </CardTitle>
            </CardHeader>

            <CardContent className="space-y-4 text-sm">
              <p className="text-muted-foreground leading-relaxed">
                {language === "ar" ? cond.summary_ar : cond.summary_en}
              </p>

              {cond.prevalence_info_en && (
                <div className="p-2.5 bg-slate-50 dark:bg-slate-900 rounded-md text-xs border border-border">
                  <span className="font-semibold text-slate-700 dark:text-slate-300">
                    {language === "ar" ? "معدل الانتشار: " : "Prevalence: "}
                  </span>
                  <span className="text-muted-foreground">
                    {language === "ar" ? cond.prevalence_info_ar : cond.prevalence_info_en}
                  </span>
                </div>
              )}

              {cond.guideline_reference && (
                <div className="flex items-center space-x-1.5 rtl:space-x-reverse text-xs text-teal-700 dark:text-teal-400 font-medium">
                  <ShieldCheck className="h-4 w-4 flex-shrink-0" />
                  <span className="truncate">{cond.guideline_reference}</span>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredConditions.length === 0 && (
        <div className="text-center py-12 text-muted-foreground text-sm">
          {language === "ar" ? "لم يتم العثور على نتائج تطابق بحثك." : "No health conditions found matching your search term."}
        </div>
      )}
    </div>
  );
}
