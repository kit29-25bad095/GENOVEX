import { NextRequest, NextResponse } from "next/server";
import { getAssessmentReview } from "@/lib/standaloneAssessment";

export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const backendUrl = process.env.BACKEND_API_URL;
  if (backendUrl) {
    try {
      const res = await fetch(
        `${backendUrl.replace(/\/$/, "")}/api/v1/questionnaire/assessments/${params.id}/review`,
        {
          headers: {
            Cookie: req.headers.get("cookie") || "",
            "X-Session-Token": req.headers.get("X-Session-Token") || "",
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

  const result = getAssessmentReview(params.id);
  return NextResponse.json(result, { status: 200 });
}
