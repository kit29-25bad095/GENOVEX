import { NextRequest, NextResponse } from "next/server";
import { startOrResumeAssessment } from "@/lib/standaloneAssessment";

export async function POST(req: NextRequest) {
  const backendUrl = process.env.BACKEND_API_URL;
  if (backendUrl) {
    try {
      const body = await req.text();
      const res = await fetch(
        `${backendUrl.replace(/\/$/, "")}/api/v1/questionnaire/assessments/start`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Cookie: req.headers.get("cookie") || "",
            "X-Session-Token": req.headers.get("X-Session-Token") || "",
          },
          body: body || "{}",
          cache: "no-store",
        }
      );
      const data = await res.json();
      const response = NextResponse.json(data, { status: res.status });
      // Forward Set-Cookie headers if any
      const setCookie = res.headers.get("set-cookie");
      if (setCookie) {
        response.headers.set("set-cookie", setCookie);
      }
      return response;
    } catch {
      // Fall through to standalone handler
    }
  }

  let sessionToken: string | null = null;
  try {
    const json = await req.json();
    sessionToken = json?.session_token || null;
  } catch {
    // Empty body
  }

  const result = startOrResumeAssessment(sessionToken);

  const response = NextResponse.json(result, { status: 200 });
  response.cookies.set("genovex_session", result.session_token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
  });
  response.cookies.set("genovex_csrf", result.csrf_token, {
    httpOnly: false,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
  });

  return response;
}
