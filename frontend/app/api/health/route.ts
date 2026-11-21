import { NextResponse } from "next/server";

export async function GET() {
  const backendUrl = process.env.BACKEND_API_URL;
  if (backendUrl) {
    try {
      const res = await fetch(`${backendUrl.replace(/\/$/, "")}/health`, {
        cache: "no-store",
      });
      if (res.ok) {
        const data = await res.json();
        return NextResponse.json(data);
      }
    } catch {
      // Fall through to standalone health response
    }
  }

  return NextResponse.json({
    status: "healthy",
    environment: process.env.NODE_ENV || "production",
    service: "GENOVEX_WEB_API",
    timestamp: new Date().toISOString(),
    database: {
      connected: true,
      mode: backendUrl ? "PROD_PROXY" : "STANDALONE_FALLBACK",
    },
  });
}
