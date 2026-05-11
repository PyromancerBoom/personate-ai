import { afterEach, describe, expect, it, vi } from "vitest";
import { API_BASE_URL, listRuns, parseError, resolveScreenshotUrl } from "./api";

describe("api helpers", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("resolves backend-relative screenshot urls", () => {
    expect(resolveScreenshotUrl("/api/runs/run_123/screenshots/step_001.png")).toBe(
      `${API_BASE_URL}/api/runs/run_123/screenshots/step_001.png`
    );
  });

  it("leaves absolute screenshot urls absolute", () => {
    expect(resolveScreenshotUrl("https://example.com/step.png")).toBe("https://example.com/step.png");
  });

  it("parses mixed FastAPI validation detail arrays", async () => {
    const response = new Response(
      JSON.stringify({
        detail: ["plain error", { msg: "structured error" }, null]
      }),
      { status: 400 }
    );

    expect(await parseError(response)).toBe("plain error, structured error, null");
  });

  it("parses object-shaped error details", async () => {
    const response = new Response(JSON.stringify({ detail: { msg: "object error" } }), { status: 500 });

    expect(await parseError(response)).toBe("object error");
  });

  it("lists run summaries from the backend", async () => {
    const payload = [
      {
        id: "abcdef012345",
        url: "http://localhost:3000",
        goal: "test onboarding",
        status: "completed",
        createdAt: "2026-01-01T00:00:00+00:00",
        updatedAt: "2026-01-02T00:00:00+00:00",
        steps: 4,
        findings: 1,
        outcome: "success"
      }
    ];
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(listRuns()).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/runs`,
      expect.objectContaining({ headers: expect.objectContaining({ "Content-Type": "application/json" }) })
    );
  });
});
