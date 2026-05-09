import { describe, expect, it } from "vitest";
import { API_BASE_URL, parseError, resolveScreenshotUrl } from "./api";

describe("api helpers", () => {
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
});
