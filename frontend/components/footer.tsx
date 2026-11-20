"use client";

import React from "react";
import Link from "next/link";
import { useLanguage } from "@/context/LanguageContext";
import { ShieldCheck, Lock, Award, HeartPulse } from "lucide-react";

export const Footer: React.FC = () => {
  const { t, language } = useLanguage();

  return (
    <footer className="border-t border-border bg-slate-50 dark:bg-slate-950 text-muted-foreground text-xs py-10">
      <div className="container mx-auto px-4 sm:px-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* Col 1: Platform Info */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2 rtl:space-x-reverse text-foreground font-bold text-base">
              <HeartPulse className="h-5 w-5 text-teal-700" />
              <span>GENOVEX Healthcare</span>
            </div>
            <p className="leading-relaxed">
              {language === "ar"
                ? "منصة طبية متخصصة في صحة الرجل الإنجابية والجنسية، تعتمد على قواعد إكلينيكية حتمية مستندة إلى إرشادات EAU و AUA/ASRM و WHO."
                : "Dedicated male reproductive and sexual health platform powered by deterministic clinical decision support grounded in EAU, AUA/ASRM, and WHO guidelines."}
            </p>
          </div>

          {/* Col 2: Navigation */}
          <div className="space-y-2">
            <h4 className="font-semibold text-foreground text-sm">
              {language === "ar" ? "روابط سريعة" : "Quick Links"}
            </h4>
            <ul className="space-y-1.5">
              <li>
                <Link href="/" className="hover:text-teal-700 transition-colors">
                  {t("nav.home")}
                </Link>
              </li>
              <li>
                <Link href="/library" className="hover:text-teal-700 transition-colors">
                  {t("nav.library")}
                </Link>
              </li>
              <li>
                <Link href="/assessment" className="hover:text-teal-700 transition-colors">
                  {t("nav.assessment")}
                </Link>
              </li>
              <li>
                <Link href="/privacy" className="hover:text-teal-700 transition-colors">
                  {t("footer.privacy")}
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 3: Clinical Integrity & Standards */}
          <div className="space-y-2">
            <h4 className="font-semibold text-foreground text-sm">
              {language === "ar" ? "المعايير الإكلينيكية" : "Clinical Standards"}
            </h4>
            <div className="space-y-1.5 text-[11px]">
              <div className="flex items-center space-x-1.5 rtl:space-x-reverse">
                <Award className="h-3.5 w-3.5 text-teal-700" />
                <span>EAU Male Infertility & Sexual Health (2024)</span>
              </div>
              <div className="flex items-center space-x-1.5 rtl:space-x-reverse">
                <Award className="h-3.5 w-3.5 text-teal-700" />
                <span>AUA/ASRM Male Infertility Guidelines (2021)</span>
              </div>
              <div className="flex items-center space-x-1.5 rtl:space-x-reverse">
                <Award className="h-3.5 w-3.5 text-teal-700" />
                <span>WHO Semen Examination Manual (6th Ed, 2021)</span>
              </div>
            </div>
          </div>

          {/* Col 4: Confidentiality & Trust */}
          <div className="space-y-2">
            <h4 className="font-semibold text-foreground text-sm">
              {language === "ar" ? "السرية والأمان" : "Confidentiality & Privacy"}
            </h4>
            <div className="space-y-2 text-[11px]">
              <div className="flex items-center space-x-1.5 rtl:space-x-reverse">
                <Lock className="h-3.5 w-3.5 text-emerald-600" />
                <span>{language === "ar" ? "تشفير تام للبيانات الصحية" : "End-to-End Encrypted Data"}</span>
              </div>
              <div className="flex items-center space-x-1.5 rtl:space-x-reverse">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                <span>{language === "ar" ? "متوافق مع معايير حماية البيانات الصحية" : "Compliant Health Record Protocols"}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Legal Disclaimer & Copyright */}
        <div className="border-t border-border pt-6 text-center space-y-2">
          <p className="max-w-3xl mx-auto text-[11px] leading-relaxed text-muted-foreground/80">
            {t("footer.disclaimer")}
          </p>
          <p className="text-[10px] text-muted-foreground/60">{t("footer.copyright")}</p>
        </div>
      </div>
    </footer>
  );
};
