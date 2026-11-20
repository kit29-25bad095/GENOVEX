"use client";

import React from "react";
import Link from "next/link";
import { useLanguage } from "@/context/LanguageContext";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { UrgentAlertBanner } from "@/components/urgent-alert-banner";
import {
  ShieldAlert,
  Activity,
  CheckCircle2,
  FileText,
  Lock,
  ArrowRight,
  BookOpen,
  Stethoscope,
  Heart,
  Scale,
  Sparkles,
} from "lucide-react";

export default function HomePage() {
  const { t, language } = useLanguage();

  const domainPillars = [
    {
      title_en: "Urgent Red-Flag Triage",
      title_ar: "فرز الرايات الحمراء العاجلة",
      desc_en: "Immediate detection of acute scrotal pain within the 6-hour surgical salvage window and painless testicular lumps.",
      desc_ar: "الكشف الفوري عن آلام الخصية الحادة خلال نافذة الإنقاذ الجراحي (6 ساعات) وكتل الخصية غير المؤلمة.",
      icon: ShieldAlert,
      badge: "Tier 4 Safety Circuit",
      badgeColor: "urgent" as const,
    },
    {
      title_en: "Time-to-Conception & Fertility",
      title_ar: "مدة محاولة الإنجاب والخصوبة",
      desc_en: "Clinical evaluation for couples with 12+ months of unsuccessful pregnancy attempts, adhering to AUA/ASRM Rec 1.",
      desc_ar: "تقييم سريري للأزواج بعد 12 شهراً أو أكثر من محاولات الحمل غير الناجحة وفقاً لمعايير AUA/ASRM.",
      icon: Stethoscope,
      badge: "Tier 3 Specialist",
      badgeColor: "warning" as const,
    },
    {
      title_en: "Medication & Anabolic Gonadotoxins",
      title_ar: "الأدوية والستيرويدات البنائية",
      desc_en: "Evaluation of HPG axis suppression from testosterone, anabolic steroids, and 5-alpha reductase inhibitors (finasteride).",
      desc_ar: "تقييم تثبيط المحور الهرموني الناتج عن التستوستيرون والستيرويدات البنائية ومثبطات 5-ألفا رديوكتيز.",
      icon: Activity,
      badge: "Endocrine Recovery",
      badgeColor: "secondary" as const,
    },
    {
      title_en: "Regional Lifestyle & Dokha Hazard",
      title_ar: "نمط الحياة والتعرض للدخّة الإقليمية",
      desc_en: "Targeted assessment of regional high-nicotine dokha/medwakh, shisha, scrotal hyperthermia, and obstructive sleep apnea.",
      desc_ar: "تقييم مخصص للتدخين الإقليمي عالي النيكوتين (الدخّة/المدواخ)، الشيشة، فرط حرارة الصفن، وانقطاع النفس النومي.",
      icon: Heart,
      badge: "Tier 2 Modifiable",
      badgeColor: "success" as const,
    },
  ];

  return (
    <div className="flex flex-col space-y-12 pb-16">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-teal-50/60 via-background to-background dark:from-slate-900/40 dark:via-background dark:to-background border-b border-border/60 py-16 sm:py-24">
        <div className="container mx-auto px-4 sm:px-6">
          <div className="max-w-4xl mx-auto text-center space-y-6">
            <Badge variant="outline" className="px-3.5 py-1 text-xs font-semibold text-teal-800 dark:text-teal-300 border-teal-300 bg-teal-50/80 dark:bg-teal-950/40 shadow-sm">
              <Sparkles className="h-3.5 w-3.5 mr-1.5 rtl:mr-0 rtl:ml-1.5 text-teal-600 inline" />
              {t("hero.badge")}
            </Badge>

            <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-900 dark:text-white leading-[1.15]">
              {t("hero.title")}
            </h1>

            <p className="text-base sm:text-xl text-muted-foreground leading-relaxed max-w-2xl mx-auto">
              {t("hero.subtitle")}
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
              <Link href="/assessment" className="w-full sm:w-auto">
                <Button size="lg" variant="clinical" className="w-full sm:w-auto text-base font-semibold shadow-md flex items-center justify-center space-x-2 rtl:space-x-reverse">
                  <span>{t("hero.cta.start")}</span>
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link href="/library" className="w-full sm:w-auto">
                <Button size="lg" variant="outline" className="w-full sm:w-auto text-base">
                  <BookOpen className="h-4 w-4 mr-2 rtl:mr-0 rtl:ml-2 text-teal-700" />
                  {t("hero.cta.library")}
                </Button>
              </Link>
            </div>

            {/* Quick Trust Badges */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-8 border-t border-border/60 text-xs font-medium text-slate-600 dark:text-slate-400">
              <div className="flex items-center justify-center space-x-1.5 rtl:space-x-reverse">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                <span>{t("hero.stats.rules")}</span>
              </div>
              <div className="flex items-center justify-center space-x-1.5 rtl:space-x-reverse">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                <span>{t("hero.stats.domains")}</span>
              </div>
              <div className="flex items-center justify-center space-x-1.5 rtl:space-x-reverse">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                <span>{t("hero.stats.guidelines")}</span>
              </div>
              <div className="flex items-center justify-center space-x-1.5 rtl:space-x-reverse">
                <Lock className="h-4 w-4 text-emerald-600" />
                <span>{t("hero.stats.confidential")}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Main Container */}
      <div className="container mx-auto px-4 sm:px-6 space-y-12 max-w-6xl">
        {/* Emergency Guidance Banner */}
        <UrgentAlertBanner
          type="acute_pain"
          referralGuidance="Sudden onset severe testicular pain is a medical emergency. Do not wait for an online assessment."
        />

        {/* Clinical Domain Pillars */}
        <section className="space-y-6">
          <div className="text-center space-y-2">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
              {language === "ar" ? "المحاور الإكلينيكية الرئيسية للتقييم" : "Core Clinical Assessment Domains"}
            </h2>
            <p className="text-sm text-muted-foreground max-w-2xl mx-auto">
              {language === "ar"
                ? "تقييم شامل ومصمم وفق بروتوكولات الجمعية الأوروبية والجمعية الأمريكية لجراحة المسالك البولية."
                : "Comprehensive multi-domain triage aligned with international and regional urological guidelines."}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {domainPillars.map((pillar, idx) => {
              const IconComp = pillar.icon;
              return (
                <Card key={idx} className="border-border hover:shadow-md transition-shadow">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div className="h-10 w-10 rounded-lg bg-teal-50 dark:bg-teal-950/60 flex items-center justify-center text-teal-700">
                        <IconComp className="h-5 w-5" />
                      </div>
                      <Badge variant={pillar.badgeColor}>{pillar.badge}</Badge>
                    </div>
                    <CardTitle className="text-lg mt-3">
                      {language === "ar" ? pillar.title_ar : pillar.title_en}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      {language === "ar" ? pillar.desc_ar : pillar.desc_en}
                    </p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </section>

        {/* 4 Outcome Tiers Overview */}
        <section className="bg-slate-50 dark:bg-slate-900/60 rounded-2xl p-6 sm:p-8 border border-border space-y-6">
          <div className="space-y-2">
            <Badge variant="outline" className="text-xs">
              {language === "ar" ? "نظام الفرز الحتمي" : "Deterministic Triage Engine"}
            </Badge>
            <h3 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white">
              {language === "ar" ? "مستويات النتائج الإكلينيكية الأربعة" : "The Four Deterministic Clinical Outcome Tiers"}
            </h3>
            <p className="text-xs sm:text-sm text-muted-foreground">
              {language === "ar"
                ? "كل استجابة يتم تصنيفها بدقة وبشكل حتمي دون الاعتماد على تشخيص عشوائي أو نماذج ذكاء اصطناعي غير متحكم بها."
                : "Every response is evaluated deterministically by backend rules without non-deterministic AI halluncinations."}
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white dark:bg-slate-950 p-4 rounded-xl border border-slate-200 dark:border-slate-800 space-y-2">
              <Badge variant="outline" className="bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200">
                Tier 1
              </Badge>
              <h4 className="font-semibold text-sm">
                {language === "ar" ? "رعاية وقائية روتينية" : "Routine Preventive Care"}
              </h4>
              <p className="text-xs text-muted-foreground">
                {language === "ar"
                  ? "لا توجد عوامل خطر معلنة. تثقيف صحي وإرشادات للحفاظ على الخصوبة."
                  : "No risk factors reported. Fertility preservation and wellness guidance."}
              </p>
            </div>

            <div className="bg-white dark:bg-slate-950 p-4 rounded-xl border border-slate-200 dark:border-slate-800 space-y-2">
              <Badge variant="success">Tier 2</Badge>
              <h4 className="font-semibold text-sm">
                {language === "ar" ? "عوامل نمط حياة قابلة للتعديل" : "Modifiable Lifestyle Factors"}
              </h4>
              <p className="text-xs text-muted-foreground">
                {language === "ar"
                  ? "عوامل خطر قابلة للتعديل كالدخّة، الحرارة، انقطاع النفس، أو مضادات تساقط الشعر."
                  : "Identified reversible exposures: tobacco/dokha, heat, sleep apnea, 5-ARIs."}
              </p>
            </div>

            <div className="bg-white dark:bg-slate-950 p-4 rounded-xl border border-slate-200 dark:border-slate-800 space-y-2">
              <Badge variant="warning">Tier 3</Badge>
              <h4 className="font-semibold text-sm">
                {language === "ar" ? "تقييم أخصائي موصى به" : "Specialist Evaluation Recommended"}
              </h4>
              <p className="text-xs text-muted-foreground">
                {language === "ar"
                  ? "تأخر الإنجاب لأكثر من 12 شهراً، ستيرويدات سابقة، تاريخ خصية هاجرة، أو دم في المني."
                  : "Prolonged TTC, steroid exposure, cryptorchidism, hematospermia."}
              </p>
            </div>

            <div className="bg-white dark:bg-slate-950 p-4 rounded-xl border border-red-200 dark:border-red-900/50 space-y-2 bg-red-50/20">
              <Badge variant="urgent">Tier 4</Badge>
              <h4 className="font-semibold text-sm text-red-700 dark:text-red-400">
                {language === "ar" ? "تقييم طبي عاجل" : "URGENT Medical Assessment"}
              </h4>
              <p className="text-xs text-red-900/80 dark:text-red-300/80">
                {language === "ar"
                  ? "ألم صفن حاد ومفاجئ (طوارئ 6 ساعات) أو كتلة غير مؤلمة (مسالك بولية 48 ساعة)."
                  : "Acute severe testicular pain (ED 6h) or painless testicular mass (urology 48h)."}
              </p>
            </div>
          </div>
        </section>

        {/* CTA Block */}
        <section className="bg-teal-800 text-white rounded-2xl p-8 sm:p-12 text-center space-y-6 shadow-lg">
          <h2 className="text-2xl sm:text-4xl font-extrabold max-w-2xl mx-auto">
            {language === "ar"
              ? "ابدأ تقييمك السريري الآن بسرية تامة ودقة إكلينيكية"
              : "Take Control of Your Reproductive Health with Clinical Accuracy"}
          </h2>
          <p className="text-teal-100 text-sm sm:text-base max-w-xl mx-auto">
            {language === "ar"
              ? "19 سؤالاً تكيفياً مدروساً تستغرق 4 دقائق وتمنحك تقريراً موثقاً بالأدلة الطبية ومستنداً لارشادات EAU و AUA."
              : "19 adaptive questions taking less than 4 minutes. Get an immediate evidence-linked report ready for specialist consultation."}
          </p>
          <div className="pt-2">
            <Link href="/assessment">
              <Button size="lg" className="bg-white text-teal-900 hover:bg-teal-50 font-bold px-8 shadow-md">
                {t("hero.cta.start")}
              </Button>
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
