import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const urlLang = request.nextUrl.searchParams.get("lang");
  const response = NextResponse.next();

  if (urlLang === "ar" || urlLang === "en") {
    // Forward cookie to server components on current request
    request.cookies.set("genovex_lang", urlLang);
    const forwardResponse = NextResponse.next({
      request: {
        headers: request.headers,
      },
    });
    forwardResponse.cookies.set("genovex_lang", urlLang, {
      path: "/",
      maxAge: 31536000,
      sameSite: "lax",
    });
    return forwardResponse;
  }

  // If no cookie exists, detect Accept-Language
  const existingCookie = request.cookies.get("genovex_lang")?.value;
  if (!existingCookie) {
    const acceptLang = request.headers.get("accept-language") || "";
    const preferredLang = acceptLang.toLowerCase().startsWith("ar") ? "ar" : "en";
    request.cookies.set("genovex_lang", preferredLang);
    const forwardResponse = NextResponse.next({
      request: {
        headers: request.headers,
      },
    });
    forwardResponse.cookies.set("genovex_lang", preferredLang, {
      path: "/",
      maxAge: 31536000,
      sameSite: "lax",
    });
    return forwardResponse;
  }

  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for:
     * - api routes
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};
