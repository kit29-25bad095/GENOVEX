"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useLanguage } from "@/context/LanguageContext";
import { ApiClient } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { KeyRound, AlertCircle, CheckCircle2, ArrowLeft, ArrowRight, Mail } from "lucide-react";

export default function ForgotPasswordPage() {
  const { t, direction } = useLanguage();

  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);
    setIsLoading(true);

    try {
      const response = await ApiClient.requestPasswordReset(email.trim());
      setSuccessMessage(response.message || t("auth.forgot.success_message"));
    } catch (err: any) {
      setError(err.message || "Failed to process request. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const BackIcon = direction === "rtl" ? ArrowRight : ArrowLeft;

  return (
    <div className="container mx-auto px-4 py-16 flex items-center justify-center min-h-[calc(100vh-8rem)]">
      <Card className="w-full max-w-md border-border shadow-md">
        <CardHeader className="space-y-2 text-center">
          <div className="mx-auto h-12 w-12 rounded-full bg-teal-100 dark:bg-teal-950 flex items-center justify-center text-teal-700">
            <KeyRound className="h-6 w-6" />
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight">
            {t("auth.forgot.title")}
          </CardTitle>
          <CardDescription className="text-xs">
            {t("auth.forgot.subtitle")}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {error && (
            <Alert variant="destructive" className="py-2.5 text-xs">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {successMessage ? (
            <div className="space-y-4">
              <Alert className="py-3 text-xs bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200">
                <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                <div className="ml-2 rtl:ml-0 rtl:mr-2">
                  <p className="font-semibold">{t("auth.forgot.success_title")}</p>
                  <AlertDescription className="mt-1 text-xs">
                    {successMessage}
                  </AlertDescription>
                </div>
              </Alert>

              <div className="rounded-lg border border-border p-3 text-xs text-muted-foreground bg-muted/40 flex items-center space-x-2 rtl:space-x-reverse">
                <Mail className="h-4 w-4 text-teal-600 flex-shrink-0" />
                <span>
                  Dispatched instructions to: <strong>{email}</strong>
                </span>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="reset-email">{t("auth.email")}</Label>
                <Input
                  id="reset-email"
                  type="email"
                  placeholder="you@domain.com"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                  autoComplete="email"
                />
              </div>

              <Button
                type="submit"
                variant="clinical"
                className="w-full font-semibold"
                disabled={isLoading || !email}
              >
                {isLoading ? "Dispatching..." : t("auth.forgot.send_button")}
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
    </div>
  );
}
