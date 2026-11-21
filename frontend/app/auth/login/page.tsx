"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/context/LanguageContext";
import { useAuth } from "@/context/AuthContext";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ShieldCheck, Lock, KeyRound, AlertCircle, Sparkles } from "lucide-react";

export default function LoginPage() {
  const { t, language } = useLanguage();
  const { login } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Authentication failed. Please verify your credentials.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickLogin = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
  };

  return (
    <div className="container mx-auto px-4 py-16 flex items-center justify-center min-h-[calc(100vh-8rem)]">
      <Card className="w-full max-w-md border-border shadow-md">
        <CardHeader className="space-y-2 text-center">
          <div className="mx-auto h-12 w-12 rounded-full bg-teal-100 dark:bg-teal-950 flex items-center justify-center text-teal-700">
            <Lock className="h-6 w-6" />
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight">
            {t("auth.login.title")}
          </CardTitle>
          <CardDescription className="text-xs">
            {t("auth.login.subtitle")}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {error && (
            <Alert variant="destructive" className="py-2.5 text-xs">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email">{t("auth.email")}</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@domain.com"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label htmlFor="password">{t("auth.password")}</Label>
                <Link
                  href="/auth/forgot-password"
                  className="text-xs text-teal-700 hover:text-teal-800 dark:text-teal-400 dark:hover:text-teal-300 hover:underline font-medium"
                >
                  {t("auth.forgot_password_link")}
                </Link>
              </div>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <Button type="submit" variant="clinical" className="w-full font-semibold" disabled={isLoading}>
              {isLoading ? "Signing in..." : t("auth.signin")}
            </Button>
          </form>

          {/* Quick Demo System Personas */}
          <div className="pt-4 border-t border-border space-y-2">
            <div className="flex items-center space-x-1.5 rtl:space-x-reverse text-xs text-muted-foreground font-semibold">
              <Sparkles className="h-3.5 w-3.5 text-amber-500" />
              <span>{t("auth.demo_credentials")}</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="text-[11px] h-8 justify-start"
                onClick={() => handleQuickLogin("patient@genovex.health", "Patient@2026")}
              >
                👤 Patient (Rashid)
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="text-[11px] h-8 justify-start"
                onClick={() => handleQuickLogin("clinician@genovex.health", "Clinician@2026")}
              >
                🩺 Clinician (Dr. Tarek)
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="text-[11px] h-8 justify-start"
                onClick={() => handleQuickLogin("admin@genovex.health", "Admin@2026")}
              >
                ⚙️ Admin (Sarah)
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="text-[11px] h-8 justify-start"
                onClick={() => handleQuickLogin("superadmin@genovex.health", "SuperAdmin@2026")}
              >
                🛡️ SuperAdmin (CMO)
              </Button>
            </div>
          </div>
        </CardContent>

        <CardFooter className="flex justify-center border-t border-border pt-4 text-xs text-muted-foreground">
          <span>{t("auth.no_account")}</span>
          <Link href="/auth/register" className="ml-1 rtl:ml-0 rtl:mr-1 text-teal-700 font-semibold hover:underline">
            {t("auth.signup")}
          </Link>
        </CardFooter>
      </Card>
    </div>
  );
}
