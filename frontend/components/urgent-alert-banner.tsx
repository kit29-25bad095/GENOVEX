"use client";

import React from "react";
import { useLanguage } from "@/context/LanguageContext";
import { AlertCircle, AlertTriangle, PhoneCall } from "lucide-react";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";

interface UrgentAlertBannerProps {
  type: "acute_pain" | "testis_lump" | "general_urgent";
  referralGuidance?: string;
}

export const UrgentAlertBanner: React.FC<UrgentAlertBannerProps> = ({ type, referralGuidance }) => {
  const { t, language } = useLanguage();

  const isPain = type === "acute_pain";
  const isLump = type === "testis_lump";

  return (
    <Alert variant="urgent" className="mb-6 border-2 border-red-600 bg-red-50 text-red-950 dark:bg-red-950/40 dark:text-red-100 shadow-md">
      <div className="flex items-start space-x-3 rtl:space-x-reverse">
        {isPain ? (
          <AlertCircle className="h-6 w-6 text-red-600 flex-shrink-0 animate-pulse mt-0.5" />
        ) : (
          <AlertTriangle className="h-6 w-6 text-amber-600 flex-shrink-0 mt-0.5" />
        )}
        <div className="flex-1">
          <AlertTitle className="text-base font-bold text-red-700 dark:text-red-300 flex items-center justify-between">
            <span>{t("alert.urgent.title")}</span>
            <span className="text-xs bg-red-600 text-white font-mono px-2 py-0.5 rounded-full uppercase tracking-wider">
              {isPain ? "EMERGENCY - 6H WINDOW" : "URGENT UROLOGY - 48H"}
            </span>
          </AlertTitle>
          <AlertDescription className="mt-2 text-sm text-red-900 dark:text-red-200 font-medium">
            {isPain && <p className="leading-relaxed">{t("alert.urgent.pain")}</p>}
            {isLump && <p className="leading-relaxed">{t("alert.urgent.lump")}</p>}
            {!isPain && !isLump && (
              <p className="leading-relaxed">{referralGuidance || t("alert.urgent.disclaimer")}</p>
            )}
            <div className="mt-3 p-3 bg-red-100 dark:bg-red-900/50 rounded-md border border-red-200 dark:border-red-800 text-xs flex items-center space-x-2 rtl:space-x-reverse">
              <PhoneCall className="h-4 w-4 text-red-700 dark:text-red-300 flex-shrink-0" />
              <span>
                {language === "ar"
                  ? "في حال وجود أعراض حادة ومفاجئة، يرجى التوجه فوراً لأقرب قسم طوارئ أو الاتصال بالرقم 998 (الإمارات) أو طوارئ منطقتك."
                  : "If experiencing acute sudden symptoms, present immediately to the nearest Emergency Department or dial 998 (UAE) / local emergency services."}
              </span>
            </div>
          </AlertDescription>
        </div>
      </div>
    </Alert>
  );
};
