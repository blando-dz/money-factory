import { describe, it, expect, beforeEach } from "vitest";
import app from "../src/index";

const createMockEnv = (overrides = {}) => ({
  DB: {
    prepare: (sql: string) => ({
      bind: (...args: any[]) => ({
        first: async () => ({ ok: 1 }),
        all: async () => ({ results: [] }),
        run: async () => ({
          meta: { last_row_id: 1 },
        }),
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

describe("POST /ideas/generate", () => {
  it("creates a new idea with valid input", async () => {
    const env = createMockEnv();
    const req = new Request("https://worker.local/ideas/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: "AI Code Review Bot",
        problem: "Manual code review is slow and error-prone",
        solution: "AI-powered automated code review with existing APIs",
        market_fit: "B2B SaaS for development teams",
        citations: [
          { source: "arxiv", url: "https://arxiv.org/abs/2401.001", title: "AI Code Review" },
        ],
      }),
    });

    const res = await app.fetch(req, env as any);
    expect(res.status).toBe(201);

    const body: any = await res.json();
    expect(body.title).toBe("AI Code Review Bot");
    expect(body.status).toBe("pending");
    expect(body.overall_score).toBeGreaterThan(0);
    expect(body.id).toBeDefined();
  });

  it("returns 400 for missing required fields", async () => {
    const env = createMockEnv();
    const req = new Request("https://worker.local/ideas/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "Only Title" }),
    });

    const res = await app.fetch(req, env as any);
    expect(res.status).toBe(400);

    const body: any = await res.json();
    expect(body.error).toContain("Missing required fields");
  });

  it("calculates score for AI-related ideas", async () => {
    const env = createMockEnv();
    const req = new Request("https://worker.local/ideas/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: "Novel AI Automation Platform",
        problem: "New innovative approach to AI-driven automation",
        solution: "Simple API-based SaaS MVP with open-source tools",
        market_fit: "B2B enterprise subscription marketplace",
      }),
    });

    const res = await app.fetch(req, env as any);
    const body: any = await res.json();

    expect(body.overall_score).toBeGreaterThan(50);
  });
});
