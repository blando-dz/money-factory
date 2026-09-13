import { describe, it, expect, beforeEach } from "vitest";
import app from "../src/index";

// Mock environment
const createMockEnv = (overrides = {}) => ({
  DB: {
    prepare: () => ({
      bind: () => ({
        first: async () => ({ ok: 1 }),
        all: async () => ({ results: [] }),
        run: async () => ({}),
      }),
      first: async () => ({ ok: 1 }),
      all: async () => ({ results: [] }),
      run: async () => ({}),
    }),
  } as any,
  CACHE: {
    get: async () => "ok",
    put: async () => undefined,
    delete: async () => undefined,
  } as any,
  ENVIRONMENT: "test",
  ALLOWED_ORIGINS: "http://localhost:3000",
  RATE_LIMIT_MAX: "100",
  RATE_LIMIT_WINDOW: "60",
  ...overrides,
});

describe("GET /health", () => {
  it("returns healthy status when all checks pass", async () => {
    const env = createMockEnv();
    const req = new Request("https://worker.local/health");
    const res = await app.fetch(req, env as any);

    expect(res.status).toBe(200);
    const body: any = await res.json();
    expect(body.status).toBe("healthy");
    expect(body.checks.database).toBe("up");
    expect(body.checks.cache).toBe("up");
  });

  it("returns degraded status when database is down", async () => {
    const env = createMockEnv({
      DB: {
        prepare: () => ({
          bind: () => ({
            first: async () => { throw new Error("DB down"); },
          }),
          first: async () => { throw new Error("DB down"); },
        }),
      } as any,
    });
    const req = new Request("https://worker.local/health");
    const res = await app.fetch(req, env as any);

    expect(res.status).toBe(503);
    const body: any = await res.json();
    expect(body.status).toBe("degraded");
    expect(body.checks.database).toBe("down");
  });

  it("includes version and timestamp", async () => {
    const env = createMockEnv();
    const req = new Request("https://worker.local/health");
    const res = await app.fetch(req, env as any);

    const body: any = await res.json();
    expect(body.version).toBe("1.0.0");
    expect(body.timestamp).toBeDefined();
  });
});
