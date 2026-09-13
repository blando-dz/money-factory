import { describe, it, expect } from "vitest";
import app from "../src/index";

const mockIdeas = [
  { id: 1, title: "Idea A", overall_score: 90, status: "approved", citations: "[]" },
  { id: 2, title: "Idea B", overall_score: 75, status: "pending", citations: "[]" },
  { id: 3, title: "Idea C", overall_score: 60, status: "approved", citations: "[]" },
];

const createMockEnv = (overrides = {}) => ({
  DB: {
    prepare: (_sql: string) => ({
      bind: (..._args: any[]) => ({
        first: async () => mockIdeas[0],
        all: async () => ({ results: mockIdeas }),
        run: async () => ({ meta: { last_row_id: 1 } }),
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

describe("GET /ideas", () => {
  it("returns list of ideas", async () => {
    const env = createMockEnv();
    const req = new Request("https://worker.local/ideas");
    const res = await app.fetch(req, env as any);

    expect(res.status).toBe(200);
    const body: any = await res.json();
    expect(body.ideas).toBeInstanceOf(Array);
    expect(body.ideas.length).toBeGreaterThan(0);
  });

  it("includes pagination info", async () => {
    const env = createMockEnv();
    const req = new Request("https://worker.local/ideas");
    const res = await app.fetch(req, env as any);

    const body: any = await res.json();
    expect(body.pagination).toBeDefined();
    expect(body.pagination.limit).toBe(50);
  });
});
