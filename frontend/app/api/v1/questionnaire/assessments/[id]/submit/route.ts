import { NextRequest, NextResponse } from "next/server";
import { submitAssessment } from "@/lib/standaloneAssessment";

export async function POST(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const backendUrl = process.env.BACKEND_API_URL;
  if (backendUrl) {
    try {
      const res = await fetch(
        `${backendUrl.replace(/\/$/, "")}/api/v1/questionnaire/assessments/${params.id}/submit`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Cookie: req.headers.get("cookie") || "",
            "X-Session-Token": req.headers.get("X-Session-Token") || "",
            "X-CSRF-Token": req.headers.get("X-CSRF-Token") || "",
          },
          cache: "no-store",
        }
      );
      if (res.ok) {
        const data = await res.json();
        return NextResponse.json(data);
      }
    } catch {
      // Fall through to standalone handler
    }
  }

  const result = submitAssessment(params.id);
  return NextResponse.json(result, { status: 200 });
}
