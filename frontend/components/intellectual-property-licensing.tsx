"use client";

import React from "react";
import { useLanguage } from "@/context/LanguageContext";

interface LicenseItem {
  license: string;
  software: string;
  licenseAr?: string;
  isServiceTerms?: boolean;
}

const THIRD_PARTY_SOFTWARE: LicenseItem[] = [
  { license: "MIT", software: "React" },
  { license: "MIT", software: "Next.js" },
  { license: "Apache 2.0", software: "TypeScript" },
  { license: "PSF License", software: "Python" },
  { license: "MIT", software: "FastAPI" },
  { license: "PostgreSQL Lic.", software: "PostgreSQL" },
  { license: "MIT", software: "Tailwind CSS" },
  { license: "Service terms", software: "OpenAI API", licenseAr: "شروط الخدمة", isServiceTerms: true },
];

export const IntellectualPropertyLicensing: React.FC<{ className?: string }> = ({ className = "" }) => {
  const { language } = useLanguage();
  const isAr = language === "ar";

  return (
    <div
      className={`relative w-full rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-6 sm:p-8 shadow-sm overflow-hidden bg-[radial-gradient(#e2e8f0_1px,transparent_1px)] dark:bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:18px_18px] ${className}`}
    >
      {/* Top Header Row with Title and Logo */}
      <div className="flex items-center justify-between gap-4 mb-4">
        <div>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            {isAr ? (
              <>
                <span>الملكية الفكرية و</span>{" "}
                <span className="text-indigo-600 dark:text-indigo-400">التراخيص</span>
              </>
            ) : (
              <>
                <span>Intellectual Property &amp; </span>
                <span className="text-indigo-600 dark:text-indigo-400">Licensing</span>
              </>
            )}
          </h2>
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mt-1">
            {isAr ? "البرمجيات مفتوحة المصدر والطرف الثالث" : "OPEN-SOURCE & THIRD-PARTY SOFTWARE"}
          </p>
        </div>

        {/* Genovex Stylized Logo Badge */}
        <div className="flex-shrink-0">
          <div className="relative flex items-center justify-center w-11 h-11 rounded-2xl bg-gradient-to-br from-indigo-500 via-teal-500 to-cyan-400 p-[2px] shadow-sm">
            <div className="w-full h-full bg-white dark:bg-slate-950 rounded-[14px] flex items-center justify-center">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                className="w-6 h-6 text-indigo-600 dark:text-cyan-400"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 2a10 10 0 1 0 10 10" />
                <path d="M12 12h8" />
                <path d="m16 8 4 4-4 4" />
                <circle cx="12" cy="12" r="3" fill="currentColor" fillOpacity="0.2" />
              </svg>
            </div>
            {/* Sparkle Dot */}
            <span className="absolute -top-1 -right-1 flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-cyan-500"></span>
            </span>
          </div>
        </div>
      </div>

      {/* Cards Grid / Flex Row */}
      <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3 sm:gap-3.5">
        {THIRD_PARTY_SOFTWARE.map((item, idx) => {
          if (item.isServiceTerms) {
            return (
              <div
                key={idx}
                className="group relative flex flex-col items-center justify-center p-3.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white shadow-md transition-all duration-200 transform hover:-translate-y-0.5 text-center cursor-default select-none min-h-[82px]"
              >
                <span className="text-xs font-semibold text-blue-100 tracking-tight">
                  {isAr && item.licenseAr ? item.licenseAr : item.license}
                </span>
                <span className="text-sm font-bold text-white mt-1 whitespace-nowrap">
                  {item.software}
                </span>
              </div>
            );
          }

          return (
            <div
              key={idx}
              className="group relative flex flex-col items-center justify-center p-3.5 rounded-xl bg-white dark:bg-slate-950/80 border border-slate-200/90 dark:border-slate-800 shadow-sm hover:shadow-md transition-all duration-200 transform hover:-translate-y-0.5 text-center cursor-default select-none min-h-[82px]"
            >
              <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400 tracking-tight">
                {item.license}
              </span>
              <span className="text-sm font-semibold text-slate-800 dark:text-slate-200 mt-1 whitespace-nowrap">
                {item.software}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
