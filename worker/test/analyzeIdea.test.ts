import { describe, it, expect } from "vitest";
import app from "../src/index";

const mockIdea = {
  id: 1,
  title: "AI Code Review Bot",
  problem: "Manual code review is slow",
  solution: "AI automated code review",
  market_fit: "B2B SaaS",
  novelty_score: 80,
  feasibility_score: 75,
  monetizability_score: 85,
  overall_score: 80,
  status: "pending",
  citations: "[]",
};

const createMockEnv = (overrides = {}) => {
  let insertCount = 0;
  return {
    DB: {
      prepare: (sql: string) => ({
        bind: (...args: any[]) => ({
          first: async () => mockIdea,
          all: async () => {
            if (sql.includes("SELECT agent_type")) {
              return {
                results: [
                  { agent_type: "market_intel", verdict: "approve" },
                  { agent_type: "contract_dev", verdict: "approve" },
                ],
              };
            }
            return { results: [] };
          },
          run: async () => {
            insertCount++;
            return { meta: { last_row_id: insertCount } };
          },
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
  };
};

describe("POST /ideas/:id/analyze", () => {
  it("records analysis from an agent", async () => {
    const env = createMockEnv();
    const req = new Request("https://worker.local/ideas/1/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        agent_type: "market_intel",
        verdict: "approve",
        reasoning: "Strong market demand detected",
        confidence: 0.85,
      }),
    });

    const res = await app.fetch(req, env as any);
    expect(res.status).toBe(201);

    const body: any = await res.json();
    expect(body.idea_id).toBe(1);
    expect(body.agent_type).toBe("market_intel");
    expect(body.verdict).toBe("approve");
  });

  it("returns 400 for missing fields", async () => {
    const env = createMockEnv();
    const req = new Request("https://worker.local/ideas/1/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });

    const res = await app.fetch(req, env as any);
    expect(res.status).toBe(400);
  });

  it("returns 404 for non-existent idea", async () => {
    const env = createMockEnv({
      DB: {
        prepare: () => ({
          bind: () => ({
            first: async () => null,
            all: async () => ({ results: [] }),
            run: async () => ({}),
          }),
        }),
      } as any,
    });
    const req = new Request("https://worker.local/ideas/999/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        agent_type: "risk_execution",
        verdict: "approve",
      }),
    });

    const res = await app.fetch(req, env as any);
    expect(res.status).toBe(404);
  });
});
