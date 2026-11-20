"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useLanguage } from "@/context/LanguageContext";
import { ApiClient, FacilityItem } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Building2,
  MapPin,
  Phone,
  ExternalLink,
  Search,
  Filter,
  CheckCircle2,
  AlertTriangle,
  ArrowLeft,
  Shield,
  Stethoscope,
  Clock,
} from "lucide-react";

export default function ClinicalNavigationPage() {
  const { language } = useLanguage();
  const [facilities, setFacilities] = useState<FacilityItem[]>([]);
  const [emirates, setEmirates] = useState<string[]>([]);
  const [specialties, setSpecialties] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState<string>("");
  const [selectedEmirate, setSelectedEmirate] = useState<string>("");
  const [selectedSpecialty, setSelectedSpecialty] = useState<string>("");
  const [emergencyOnly, setEmergencyOnly] = useState<boolean>(false);

  useEffect(() => {
    async function loadDirectory() {
      setIsLoading(true);
      setError(null);
      try {
        const res = await ApiClient.getFacilities({
          search: search || undefined,
          emirate: selectedEmirate || undefined,
          specialty: selectedSpecialty || undefined,
          has_emergency: emergencyOnly ? true : undefined,
          page_size: 50,
        });
        setFacilities(res.items);
        if (res.emirates.length > 0) setEmirates(res.emirates);
        if (res.specialties.length > 0) setSpecialties(res.specialties);
      } catch (err: any) {
        setError(err.message || "Failed to load healthcare facilities directory");
      } finally {
        setIsLoading(false);
      }
    }

    const timer = setTimeout(() => {
      loadDirectory();
    }, 250);

    return () => clearTimeout(timer);
  }, [search, selectedEmirate, selectedSpecialty, emergencyOnly]);

  return (
    <div className="container mx-auto px-4 sm:px-6 py-10 max-w-6xl space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <Link
            href="/dashboard"
            className="text-xs text-muted-foreground hover:text-teal-700 flex items-center space-x-1.5 rtl:space-x-reverse mb-2"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>{language === "ar" ? "العودة للوحة التحكم" : "Back to Dashboard"}</span>
          </Link>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center space-x-2.5 rtl:space-x-reverse">
            <Building2 className="h-7 w-7 text-teal-700" />
            <span>
              {language === "ar"
                ? "دليل التوجيه السريري ومراكز الذكورة بالإمارات"
                : "UAE Clinical Navigation & Andrology Directory"}
            </span>
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground max-w-2xl">
            {language === "ar"
              ? "دليل المنشآت الطبية والمستشفيات المتخصصة في صحة الإنجاب وطب الذكورة والخصوبة المعتمدة في دولة الإمارات العربية المتحدة."
              : "Verified UAE hospital departments and specialized fertility centers offering andrology, male reproductive medicine, and microsurgical care."}
          </p>
        </div>

        <Link href="/assessment">
          <Button variant="clinical" size="sm" className="text-xs font-semibold">
            {language === "ar" ? "إجراء التقييم الإكلينيكي" : "Start Assessment"}
          </Button>
        </Link>
      </div>

      {/* Mandatory Non-Diagnostic Clinical Navigation Notice */}
      <div className="p-4 bg-teal-50/70 dark:bg-teal-950/30 border border-teal-200 dark:border-teal-900/60 rounded-xl space-y-1.5 text-xs text-teal-950 dark:text-teal-200">
        <div className="font-semibold flex items-center space-x-1.5 rtl:space-x-reverse">
          <Shield className="h-4 w-4 text-teal-700" />
          <span>{language === "ar" ? "إشعار التوجيه الإكلينيكي وحماية المرضى" : "Clinical Navigation & Patient Safety Notice"}</span>
        </div>
        <p className="leading-relaxed">
          {language === "ar"
            ? "يتم توفير هذا الدليل حصرياً لتسهيل وصول المراجعين إلى المنشآت الصحية المرخصة في الدولة (DHA, DOH, MOHAP). لا يشكل استعراض هذه البيانات علاقة علاجية أو إحالة طبية رسمية أو تشخيصاً. في حالات الألم الشديد أو الطوارئ، توجه فوراً إلى أقرب مستشفى طوارئ 24/7."
            : "This directory is provided solely for educational navigation to licensed UAE healthcare providers (DHA, DoH, MOHAP). This does NOT constitute a doctor-patient relationship, medical diagnosis, or formal referral. For acute scrotal pain or urgent swelling, visit a 24/7 emergency hospital immediately."}
        </p>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-border shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 rtl:left-auto rtl:right-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder={
                language === "ar"
                  ? "البحث باسم المركز، المستشفى، المدينة أو العنوان..."
                  : "Search by center name, hospital, city or location..."
              }
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 rtl:pl-3 rtl:pr-9 text-xs"
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={selectedEmirate}
              onChange={(e) => setSelectedEmirate(e.target.value)}
              className="text-xs bg-slate-50 dark:bg-slate-800 border border-border rounded-md px-3 py-2 text-slate-800 dark:text-slate-200"
            >
              <option value="">{language === "ar" ? "جميع الإمارات" : "All Emirates"}</option>
              {emirates.map((em) => (
                <option key={em} value={em}>
                  {em.replace(/_/g, " ")}
                </option>
              ))}
            </select>

            <select
              value={selectedSpecialty}
              onChange={(e) => setSelectedSpecialty(e.target.value)}
              className="text-xs bg-slate-50 dark:bg-slate-800 border border-border rounded-md px-3 py-2 text-slate-800 dark:text-slate-200"
            >
              <option value="">{language === "ar" ? "جميع التخصصات" : "All Specialties"}</option>
              {specialties.map((spec) => (
                <option key={spec} value={spec}>
                  {spec}
                </option>
              ))}
            </select>

            <Button
              variant={emergencyOnly ? "destructive" : "outline"}
              size="sm"
              onClick={() => setEmergencyOnly(!emergencyOnly)}
              className="text-xs shrink-0"
            >
              <Clock className="h-3.5 w-3.5 mr-1 rtl:mr-0 rtl:ml-1" />
              <span>{language === "ar" ? "طوارئ 24/7" : "24/7 ER"}</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Directory Grid */}
      {isLoading ? (
        <div className="py-20 text-center space-y-3">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-teal-700 border-r-transparent" />
          <p className="text-xs text-muted-foreground">
            {language === "ar" ? "جاري تحميل المنشآت الطبية المعتمدة..." : "Loading verified healthcare centers..."}
          </p>
        </div>
      ) : error ? (
        <Card className="border-red-200 bg-red-50/40 dark:bg-red-950/20">
          <CardContent className="p-6 text-center text-red-700 dark:text-red-400 text-xs">
            <AlertTriangle className="h-6 w-6 mx-auto mb-2" />
            <p>{error}</p>
          </CardContent>
        </Card>
      ) : facilities.length === 0 ? (
        <Card className="border-dashed border-border py-16 text-center space-y-3">
          <Building2 className="h-10 w-10 text-muted-foreground mx-auto" />
          <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
            {language === "ar" ? "لم يتم العثور على منشآت مطابقة" : "No Facilities Found"}
          </h3>
          <p className="text-xs text-muted-foreground max-w-sm mx-auto">
            {language === "ar"
              ? "جرب إزالة بعض معايير التصفية للبحث في كامل إمارات الدولة."
              : "Try clearing selected filters to broaden your search across all UAE Emirates."}
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setSearch("");
              setSelectedEmirate("");
              setSelectedSpecialty("");
              setEmergencyOnly(false);
            }}
            className="text-xs"
          >
            {language === "ar" ? "إعادة ضبط البحث" : "Reset Filters"}
          </Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {facilities.map((facility) => (
            <Card
              key={facility.id}
              className="border-border hover:shadow-md transition-all flex flex-col justify-between"
            >
              <CardHeader className="pb-3 space-y-2">
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <CardTitle className="text-base text-slate-900 dark:text-white leading-snug">
                      {language === "ar" ? facility.name_ar : facility.name_en}
                    </CardTitle>
                    <div className="flex items-center space-x-2 rtl:space-x-reverse text-xs text-muted-foreground">
                      <span className="flex items-center space-x-1 rtl:space-x-reverse">
                        <MapPin className="h-3 w-3 text-slate-400" />
                        <span>
                          {language === "ar" ? facility.city_ar : facility.city_en},{" "}
                          {facility.emirate.replace(/_/g, " ")}
                        </span>
                      </span>
                      <span>•</span>
                      <span className="font-mono text-[11px] text-teal-800 dark:text-teal-300">
                        {facility.regulatory_authority}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-1.5 shrink-0">
                    {facility.has_24_7_emergency && (
                      <Badge variant="destructive" className="text-[10px] font-bold">
                        24/7 ER
                      </Badge>
                    )}
                    {facility.is_verified && (
                      <Badge variant="outline" className="text-[10px] text-teal-700 dark:text-teal-400 font-semibold border-teal-300">
                        <CheckCircle2 className="h-3 w-3 mr-1 rtl:mr-0 rtl:ml-1" />
                        Verified
                      </Badge>
                    )}
                  </div>
                </div>

                <p className="text-[11px] text-slate-600 dark:text-slate-400">
                  {language === "ar" ? facility.address_ar : facility.address_en}
                </p>
              </CardHeader>

              <CardContent className="pt-0 space-y-3">
                {/* Specialties tags */}
                <div className="flex flex-wrap gap-1.5">
                  {(facility.offered_specialties || []).map((spec, idx) => (
                    <span
                      key={idx}
                      className="text-[10px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-medium"
                    >
                      {spec}
                    </span>
                  ))}
                </div>

                {/* Facilities capabilities indicators */}
                <div className="flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground pt-1">
                  {facility.has_andrology_specialist && (
                    <span className="flex items-center space-x-1 rtl:space-x-reverse text-teal-800 dark:text-teal-300">
                      <Stethoscope className="h-3 w-3" />
                      <span>{language === "ar" ? "طبيب ذكورة متخصص" : "Andrologist"}</span>
                    </span>
                  )}
                  {facility.has_who_semen_analysis_lab && (
                    <span>• {language === "ar" ? "مختبر سائل منوي معتمد (WHO)" : "WHO Semen Lab"}</span>
                  )}
                  {facility.has_micro_tese_capability && (
                    <span>• {language === "ar" ? "جراحة ميكروسكوبية (Micro-TESE)" : "Micro-TESE"}</span>
                  )}
                </div>

                {/* Contact and Booking Actions */}
                <div className="pt-3 border-t border-border flex items-center justify-between text-xs">
                  <a
                    href={`tel:${facility.phone_number}`}
                    className="text-teal-700 dark:text-teal-400 font-medium hover:underline flex items-center space-x-1.5 rtl:space-x-reverse"
                  >
                    <Phone className="h-3.5 w-3.5" />
                    <span>{facility.phone_number}</span>
                  </a>

                  <div className="flex items-center space-x-2 rtl:space-x-reverse">
                    {facility.website_url && (
                      <a
                        href={facility.website_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-muted-foreground hover:text-slate-900 dark:hover:text-white"
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                    )}
                    {facility.booking_url ? (
                      <a href={facility.booking_url} target="_blank" rel="noopener noreferrer">
                        <Button variant="outline" size="sm" className="text-xs h-7 px-2.5">
                          {language === "ar" ? "حجز موعد" : "Book Link"}
                        </Button>
                      </a>
                    ) : (
                      <a href={`tel:${facility.phone_number}`}>
                        <Button variant="outline" size="sm" className="text-xs h-7 px-2.5">
                          {language === "ar" ? "اتصال للحجز" : "Call Facility"}
                        </Button>
                      </a>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
