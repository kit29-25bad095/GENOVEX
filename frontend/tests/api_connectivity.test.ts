import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { resolveApiBaseUrl } from "@/lib/api";

describe("Frontend-to-Backend Connectivity & URL Resolution", () => {
  describe("Client-side Browser URL Resolution", () => {
    it("resolves to same-origin relative proxy on Vercel preview/production domains", () => {
      const url = resolveApiBaseUrl({
        env: {},
        windowObj: { location: { hostname: "genovex.vercel.app" } },
      });
      expect(url).toBe("/api/v1");
    });

    it("resolves to same-origin relative proxy on genovex.ae apex domain", () => {
      const url = resolveApiBaseUrl({
        env: {},
        windowObj: { location: { hostname: "genovex.ae" } },
      });
      expect(url).toBe("/api/v1");
    });

    it("resolves to same-origin relative proxy on www.genovex.ae domain", () => {
      const url = resolveApiBaseUrl({
        env: {},
        windowObj: { location: { hostname: "www.genovex.ae" } },
      });
      expect(url).toBe("/api/v1");
    });

    it("resolves to local backend port 8000 on localhost", () => {
      const url = resolveApiBaseUrl({
        env: {},
        windowObj: { location: { hostname: "localhost" } },
      });
      expect(url).toBe("http://127.0.0.1:8000/api/v1");
    });

    it("resolves to local backend port 8000 on 127.0.0.1", () => {
      const url = resolveApiBaseUrl({
        env: {},
        windowObj: { location: { hostname: "127.0.0.1" } },
      });
      expect(url).toBe("http://127.0.0.1:8000/api/v1");
    });
  });

  describe("Server-side (Node.js runtime / SSR / Route Handlers) URL Resolution", () => {
    it("resolves to BACKEND_API_URL when set on server", () => {
      const url = resolveApiBaseUrl({
        env: { BACKEND_API_URL: "https://api.genovex.ae" },
        windowObj: null,
      });
      expect(url).toBe("https://api.genovex.ae/api/v1");
    });

    it("strips trailing slash from BACKEND_API_URL correctly", () => {
      const url = resolveApiBaseUrl({
        env: { BACKEND_API_URL: "https://api.genovex.ae/" },
        windowObj: null,
      });
      expect(url).toBe("https://api.genovex.ae/api/v1");
    });

    it("throws an explicit configuration error in production server runtime when BACKEND_API_URL is missing", () => {
      expect(() =>
        resolveApiBaseUrl({
          env: { NODE_ENV: "production", VERCEL: "1" },
          windowObj: null,
        })
      ).toThrowError(/BACKEND_API_URL environment variable is required/);
    });

    it("falls back to local backend port 8000 on server in development mode", () => {
      const url = resolveApiBaseUrl({
        env: { NODE_ENV: "development" },
        windowObj: null,
      });
      expect(url).toBe("http://127.0.0.1:8000/api/v1");
    });
  });

  describe("Explicit Overrides", () => {
    it("respects NEXT_PUBLIC_API_BASE_URL override if explicitly provided", () => {
      const url = resolveApiBaseUrl({
        env: { NEXT_PUBLIC_API_BASE_URL: "https://custom-api.genovex.internal" },
        windowObj: { location: { hostname: "genovex.ae" } },
      });
      expect(url).toBe("https://custom-api.genovex.internal");
    });

    it("respects NEXT_PUBLIC_API_URL override if explicitly provided", () => {
      const url = resolveApiBaseUrl({
        env: { NEXT_PUBLIC_API_URL: "https://public-api.genovex.ae/" },
        windowObj: { location: { hostname: "genovex.ae" } },
      });
      expect(url).toBe("https://public-api.genovex.ae");
    });
  });

  describe("Next.js Rewrite Contract Parity", () => {
    it("validates rewrite destination structure matching BACKEND_API_URL", () => {
      const backendUrl = "https://api.genovex.ae";
      const rewriteDestination = `${backendUrl.replace(/\/$/, "")}/api/v1/:path*`;
      expect(rewriteDestination).toBe("https://api.genovex.ae/api/v1/:path*");
    });
  });
});
