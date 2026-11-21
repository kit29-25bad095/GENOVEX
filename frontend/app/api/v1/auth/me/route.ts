import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const backendUrl = process.env.BACKEND_API_URL;
  if (backendUrl) {
    try {
      const res = await fetch(`${backendUrl.replace(/\/$/, "")}/api/v1/auth/me`, {
        headers: {
          Authorization: req.headers.get("authorization") || "",
          Cookie: req.headers.get("cookie") || "",
        },
        cache: "no-store",
      });
      const data = await res.json();
      return NextResponse.json(data, { status: res.status });
    } catch {
      // Fall through
    }
  }

  const auth = req.headers.get("authorization");
  if (!auth) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  return NextResponse.json({
    id: 1,
    email: "patient@genovex.ae",
    full_name: "GENOVEX Patient",
    role: "PATIENT",
    is_active: true,
    created_at: new Date().toISOString(),
  });
}
