import { NextRequest, NextResponse } from "next/server";
import { saveDomainResponses } from "@/lib/standaloneAssessment";

export async function POST(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const backendUrl = process.env.BACKEND_API_URL;
  if (backendUrl) {
    try {
      const body = await req.text();
      const res = await fetch(
        `${backendUrl.replace(/\/$/, "")}/api/v1/questionnaire/assessments/${params.id}/save-domain`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Cookie: req.headers.get("cookie") || "",
            "X-Session-Token": req.headers.get("X-Session-Token") || "",
            "X-CSRF-Token": req.headers.get("X-CSRF-Token") || "",
          },
          body,
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

  let domainIndex = 0;
  let responses: Record<string, any> = {};
  try {
    const json = await req.json();
    domainIndex = json?.domain_index ?? 0;
    responses = json?.responses ?? json?.answers ?? {};
  } catch {
    // Empty body
  }

  const result = saveDomainResponses(params.id, domainIndex, responses);
  return NextResponse.json(result, { status: 200 });
}
