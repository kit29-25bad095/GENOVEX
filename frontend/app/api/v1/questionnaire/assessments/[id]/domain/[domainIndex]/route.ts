import { NextRequest, NextResponse } from "next/server";
import { getDomainQuestions } from "@/lib/standaloneAssessment";

export async function GET(
  req: NextRequest,
  { params }: { params: { id: string; domainIndex: string } }
) {
  const backendUrl = process.env.BACKEND_API_URL;
  if (backendUrl) {
    try {
      const res = await fetch(
        `${backendUrl.replace(/\/$/, "")}/api/v1/questionnaire/assessments/${params.id}/domain/${params.domainIndex}`,
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

  const domainIndex = parseInt(params.domainIndex, 10);
  const result = getDomainQuestions(params.id, isNaN(domainIndex) ? 0 : domainIndex);
  return NextResponse.json(result, { status: 200 });
}
