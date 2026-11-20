"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLanguage } from "@/context/LanguageContext";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Shield, Globe, Menu, X, User, Activity } from "lucide-react";

export const Navbar: React.FC = () => {
  const { t, language, toggleLanguage } = useLanguage();
  const { user, isAuthenticated, logout } = useAuth();
  const pathname = usePathname();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const navLinks = [
    { href: "/", label: t("nav.home") },
    { href: "/library", label: t("nav.library") },
    { href: "/assessment", label: t("nav.assessment"), highlight: true },
    ...(isAuthenticated ? [{ href: "/dashboard", label: t("nav.dashboard") }] : []),
    ...(user?.role === "CLINICIAN" || user?.role === "SUPERADMIN"
      ? [{ href: "/clinician", label: t("nav.clinician") }]
      : []),
    ...(user?.role === "ADMIN" || user?.role === "SUPERADMIN"
      ? [{ href: "/admin", label: t("nav.admin") }]
      : []),
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 shadow-sm">
      <div className="container mx-auto flex h-16 items-center justify-between px-4 sm:px-6">
        {/* Brand */}
        <Link href="/" className="flex items-center space-x-2.5 rtl:space-x-reverse font-bold text-xl text-primary-900 dark:text-primary-100">
          <div className="h-9 w-9 rounded-lg bg-teal-700 flex items-center justify-center text-white shadow-sm">
            <Activity className="h-5 w-5" />
          </div>
          <div className="flex flex-col">
            <span className="leading-none font-extrabold tracking-tight text-teal-800 dark:text-teal-400">GENOVEX</span>
            <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">Health Platform</span>
          </div>
        </Link>

        {/* Desktop Navigation Links */}
        <nav className="hidden md:flex items-center space-x-6 rtl:space-x-reverse text-sm font-medium">
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`transition-colors hover:text-teal-700 ${
                  isActive
                    ? "text-teal-700 dark:text-teal-400 font-semibold border-b-2 border-teal-700 pb-1"
                    : "text-muted-foreground"
                } ${link.highlight ? "text-teal-800 dark:text-teal-300 font-bold" : ""}`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Action Controls */}
        <div className="flex items-center space-x-3 rtl:space-x-reverse">
          {/* Language Switch */}
          <Button
            variant="outline"
            size="sm"
            onClick={toggleLanguage}
            className="flex items-center space-x-1.5 rtl:space-x-reverse text-xs font-semibold px-2.5 h-8 border-slate-300 dark:border-slate-700"
          >
            <Globe className="h-3.5 w-3.5 text-teal-700" />
            <span>{language === "en" ? "العربية" : "English"}</span>
          </Button>

          {/* User Auth */}
          {isAuthenticated ? (
            <div className="hidden sm:flex items-center space-x-3 rtl:space-x-reverse">
              <span className="text-xs text-muted-foreground flex items-center space-x-1 rtl:space-x-reverse">
                <User className="h-3.5 w-3.5 text-teal-700" />
                <span className="font-medium text-foreground">{user?.full_name}</span>
                <span className="text-[10px] bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 px-1.5 py-0.5 rounded font-mono">
                  {user?.role}
                </span>
              </span>
              <Button variant="ghost" size="sm" onClick={logout} className="text-xs h-8">
                {t("nav.logout")}
              </Button>
            </div>
          ) : (
            <div className="hidden sm:flex items-center space-x-2 rtl:space-x-reverse">
              <Link href="/auth/login">
                <Button variant="ghost" size="sm" className="text-xs h-8">
                  {t("nav.login")}
                </Button>
              </Link>
              <Link href="/auth/register">
                <Button variant="clinical" size="sm" className="text-xs h-8">
                  {t("nav.register")}
                </Button>
              </Link>
            </div>
          )}

          {/* Mobile menu toggle */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="md:hidden p-2 rounded-md hover:bg-accent"
          >
            {isMobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {isMobileMenuOpen && (
        <div className="md:hidden border-b border-border bg-background px-4 pt-2 pb-4 space-y-2">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              onClick={() => setIsMobileMenuOpen(false)}
              className="block py-2 text-sm font-medium hover:text-teal-700"
            >
              {link.label}
            </Link>
          ))}
          <div className="pt-2 border-t border-border flex justify-between items-center">
            {isAuthenticated ? (
              <div className="flex items-center justify-between w-full">
                <span className="text-xs text-muted-foreground">{user?.full_name}</span>
                <Button variant="ghost" size="sm" onClick={logout} className="text-xs">
                  {t("nav.logout")}
                </Button>
              </div>
            ) : (
              <div className="flex space-x-2 rtl:space-x-reverse w-full">
                <Link href="/auth/login" className="flex-1">
                  <Button variant="outline" size="sm" className="w-full text-xs">
                    {t("nav.login")}
                  </Button>
                </Link>
                <Link href="/auth/register" className="flex-1">
                  <Button variant="clinical" size="sm" className="w-full text-xs">
                    {t("nav.register")}
                  </Button>
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
};
