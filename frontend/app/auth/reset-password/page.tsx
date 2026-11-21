"use client";

import React, { useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useLanguage } from "@/context/LanguageContext";
import { ApiClient } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Lock, AlertCircle, CheckCircle2, ArrowLeft, ArrowRight, ShieldCheck, Eye, EyeOff } from "lucide-react";

function ResetPasswordContent() {
  const { t, direction, language } = useLanguage();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const BackIcon = direction === "rtl" ? ArrowRight : ArrowLeft;

  // Real-time password strength calculation
  const hasMinLength = newPassword.length >= 8;
  const hasNumber = /[0-9]/.test(newPassword);
  const hasLetter = /[a-zA-Z]/.test(newPassword);
  const hasSpecial = /[^a-zA-Z0-9]/.test(newPassword);

  const calculateStrengthScore = () => {
    let score = 0;
    if (newPassword.length >= 8) score += 1;
    if (newPassword.length >= 12) score += 1;
    if (hasNumber) score += 1;
    if (hasLetter) score += 1;
    if (hasSpecial) score += 1;
    return score;
  };

  const strengthScore = calculateStrengthScore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!token) {
      setError(t("auth.reset.invalid_token"));
      return;
    }

    if (newPassword.length < 8) {
      setError(t("auth.reset.password_too_short"));
      return;
    }

    if (newPassword !== confirmPassword) {
      setError(t("auth.reset.password_mismatch"));
      return;
    }

    setIsLoading(true);

    try {
      await ApiClient.resetPassword({
        token,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      setSuccess(true);
    } catch (err: any) {
      setError(err.message || t("auth.reset.invalid_token"));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-md border-border shadow-md">
      <CardHeader className="space-y-2 text-center">
        <div className="mx-auto h-12 w-12 rounded-full bg-teal-100 dark:bg-teal-950 flex items-center justify-center text-teal-700">
          <Lock className="h-6 w-6" />
        </div>
        <CardTitle className="text-2xl font-bold tracking-tight">
          {t("auth.reset.title")}
        </CardTitle>
        <CardDescription className="text-xs">
          {t("auth.reset.subtitle")}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {error && (
          <Alert variant="destructive" className="py-2.5 text-xs">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="ml-2 rtl:ml-0 rtl:mr-2">
              {error}
              <div className="mt-2">
                <Link
                  href="/auth/forgot-password"
                  className="font-semibold underline hover:text-white"
                >
                  {language === "ar" ? "طلب رابط جديد لإعادة التعيين" : "Request a new password reset link"}
                </Link>
              </div>
            </AlertDescription>
          </Alert>
        )}

        {success ? (
          <div className="space-y-4">
            <Alert className="py-3 text-xs bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200">
              <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              <div className="ml-2 rtl:ml-0 rtl:mr-2">
                <p className="font-semibold">{t("auth.reset.success_title")}</p>
                <AlertDescription className="mt-1 text-xs">
                  {t("auth.reset.success_message")}
                </AlertDescription>
              </div>
            </Alert>

            <Link href="/auth/login" className="block w-full">
              <Button variant="clinical" className="w-full font-semibold">
                {t("auth.signin")}
              </Button>
            </Link>
          </div>
        ) : !token ? (
          <Alert variant="destructive" className="py-2.5 text-xs">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="ml-2 rtl:ml-0 rtl:mr-2">
              {t("auth.reset.invalid_token")}
              <div className="mt-2">
                <Link
                  href="/auth/forgot-password"
                  className="font-semibold underline hover:text-white"
                >
                  {language === "ar" ? "طلب رابط جديد لإعادة التعيين" : "Request a new password reset link"}
                </Link>
              </div>
            </AlertDescription>
          </Alert>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label htmlFor="new-password">{t("auth.reset.new_password")}</Label>
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="text-xs text-muted-foreground hover:text-foreground flex items-center space-x-1 rtl:space-x-reverse"
                >
                  {showPassword ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                  <span>{showPassword ? "Hide" : "Show"}</span>
                </button>
              </div>
              <Input
                id="new-password"
                type={showPassword ? "text" : "password"}
                placeholder="••••••••"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                disabled={isLoading}
                autoComplete="new-password"
              />
            </div>

            {/* Password strength indicators */}
            {newPassword.length > 0 && (
              <div className="space-y-1.5 p-2.5 rounded-lg border border-border bg-muted/30 text-xs">
                <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                  <span>Password Strength</span>
                  <span className="font-medium">
                    {strengthScore <= 2 ? "Weak" : strengthScore <= 4 ? "Good" : "Strong"}
                  </span>
                </div>
                <div className="w-full bg-slate-200 dark:bg-slate-700 h-1.5 rounded-full overflow-hidden flex">
                  <div
                    className={`h-full transition-all duration-300 ${
                      strengthScore <= 2
                        ? "w-1/3 bg-amber-500"
                        : strengthScore <= 4
                        ? "w-2/3 bg-teal-500"
                        : "w-full bg-emerald-500"
                    }`}
                  />
                </div>
                <div className="grid grid-cols-2 gap-1 text-[11px] text-muted-foreground pt-1">
                  <span className={hasMinLength ? "text-emerald-600 font-medium" : ""}>
                    • 8+ characters
                  </span>
                  <span className={hasNumber ? "text-emerald-600 font-medium" : ""}>
                    • Contains number
                  </span>
                  <span className={hasLetter ? "text-emerald-600 font-medium" : ""}>
                    • Contains letter
                  </span>
                  <span className={hasSpecial ? "text-emerald-600 font-medium" : ""}>
                    • Special character
                  </span>
                </div>
              </div>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="confirm-password">{t("auth.reset.confirm_password")}</Label>
              <Input
                id="confirm-password"
                type={showPassword ? "text" : "password"}
                placeholder="••••••••"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={isLoading}
                autoComplete="new-password"
              />
            </div>

            <Button
              type="submit"
              variant="clinical"
              className="w-full font-semibold"
              disabled={isLoading || !newPassword || !confirmPassword}
            >
              {isLoading ? "Updating..." : t("auth.reset.submit_button")}
            </Button>
          </form>
        )}
      </CardContent>

      <CardFooter className="flex justify-center border-t border-border pt-4 text-xs text-muted-foreground">
        <Link
          href="/auth/login"
          className="flex items-center space-x-1.5 rtl:space-x-reverse text-teal-700 hover:text-teal-800 dark:text-teal-400 dark:hover:text-teal-300 font-semibold hover:underline"
        >
          <BackIcon className="h-3.5 w-3.5" />
          <span>{t("auth.forgot.back_to_login")}</span>
        </Link>
      </CardFooter>
    </Card>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="container mx-auto px-4 py-16 flex items-center justify-center min-h-[calc(100vh-8rem)]">
      <Suspense fallback={<div className="p-8 text-center text-sm text-muted-foreground">Loading reset verification...</div>}>
        <ResetPasswordContent />
      </Suspense>
    </div>
  );
}
