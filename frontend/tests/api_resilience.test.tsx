import { describe, it, expect, vi } from "vitest";
import { ApiClient } from "@/lib/api";

describe("API Error Resilience & Network Handling", () => {
  it("throws readable error on failed login attempt", async () => {
    // Mock fetch rejection
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ detail: "Incorrect email or password" }),
    } as Response);

    await expect(ApiClient.login("bad@email.com", "wrongpass")).rejects.toThrow(
      "Incorrect email or password"
    );
  });

  it("handles missing content gracefully by returning empty array", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({}),
    } as Response);

    const categories = await ApiClient.getCategories();
    expect(categories).toEqual([]);
  });
});
