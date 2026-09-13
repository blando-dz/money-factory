import { describe, it, expect } from "vitest";
import app from "../src/index";

const createMockEnv = (overrides = {}) => ({
  DB: {
    prepare: (sql: string) => ({
      bind: (...args: any[]) => ({
        first: async () => ({ avg: 72.5 }),
        all: async () => {
          if (sql.includes("GROUP BY status")) {
            return {
              results: [
                { status: "approved", count: 5 },
                { status: "pending", count: 3 },
                { status: "rejected", count: 2 },
              ],
            };
          }
          return { results: [] };
        },
        run: async () => ({}),
      }),
    }),
  } as any,
  CACHE: {
    get: async () => null,
    put: async () => undefined,
    delete: async () => undefined,
  } as any,
  ENVIRONMENT: "test",
  ALLOWED_ORIGINS: "http://localhost:3000",
  RATE_LIMIT_MAX: "100",
  RATE_LIMIT_WINDOW: "60",
  ...overrides,
});

describe("GET /status", () => {
  it("returns pipeline status overview", async () => {
    const env = createMockEnv();
    const req = new Request("https://worker.local/status");
    const res = await app.fetch(req, env as any);

    expect(res.status).toBe(200);
    const body: any = await res.json();
    expect(body.pipeline).toBeDefined();
    expect(body.pipeline.ideas_by_status).toBeInstanceOf(Array);
    expect(body.pipeline.average_score).toBe(72.5);
  });

  it("includes worker info", async () => {
    const env = createMockEnv();
    const req = new Request("https://worker.local/status");
    const res = await app.fetch(req, env as any);

    const body: any = await res.json();
    expect(body.worker.version).toBe("1.0.0");
    expect(body.worker.timestamp).toBeDefined();
  });
});
