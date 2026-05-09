import { completeMockRun, createDraftMockRun, createFailedMockRun } from "../mocks/mockRun";
import type { SimulationInput, SimulationRun } from "../types/simulation";

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const USE_MOCK_API = import.meta.env.VITE_MOCK_API === "true";

export class ApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function parseError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown; error?: unknown; message?: unknown };
    const detail = body.detail ?? body.error ?? body.message;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (typeof item === "string") {
            return item;
          }
          if (item && typeof item === "object" && "msg" in item && typeof item.msg === "string") {
            return item.msg;
          }
          return JSON.stringify(item);
        })
        .join(", ");
    }
    if (detail && typeof detail === "object") {
      if ("msg" in detail && typeof detail.msg === "string") {
        return detail.msg;
      }
      return JSON.stringify(detail);
    }
  } catch {
    // Fall through to generic message.
  }
  return `Request failed with status ${response.status}.`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {})
      },
      ...init
    });
  } catch {
    throw new ApiError(`Could not reach the backend at ${API_BASE_URL}.`);
  }

  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status);
  }

  return response.json() as Promise<T>;
}

let mockDraftRun: SimulationRun | null = null;

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export async function createRun(input: SimulationInput): Promise<SimulationRun> {
  if (USE_MOCK_API) {
    await wait(450);
    mockDraftRun = createDraftMockRun(input);
    return mockDraftRun;
  }

  return request<SimulationRun>("/api/runs", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function startRun(runId: string): Promise<SimulationRun> {
  if (USE_MOCK_API) {
    await wait(1400);
    if (!mockDraftRun || mockDraftRun.id !== runId) {
      throw new ApiError("Mock run was not found.", 404);
    }
    if (mockDraftRun.url.includes("fail")) {
      return createFailedMockRun(mockDraftRun);
    }
    return completeMockRun(mockDraftRun);
  }

  return request<SimulationRun>(`/api/runs/${encodeURIComponent(runId)}/start`, {
    method: "POST"
  });
}

export async function getRun(runId: string): Promise<SimulationRun> {
  if (USE_MOCK_API) {
    await wait(200);
    if (!mockDraftRun || mockDraftRun.id !== runId) {
      throw new ApiError("Mock run was not found.", 404);
    }
    return mockDraftRun;
  }

  return request<SimulationRun>(`/api/runs/${encodeURIComponent(runId)}`);
}

export function resolveScreenshotUrl(screenshot: string): string {
  try {
    return new URL(screenshot, `${API_BASE_URL}/`).toString();
  } catch {
    return screenshot;
  }
}
