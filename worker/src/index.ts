/**
 * Money Factory Cloudflare Worker API
 * Multi-Agent Idea → Validate → Plan → Monetize Pipeline
 */

import { Hono } from "hono";
import { cors } from "hono/cors";
import { logger } from "hono/logger";
import { prettyJSON } from "hono/pretty-json";

import { healthHandler } from "./handlers/health";
import { generateIdeaHandler } from "./handlers/generateIdea";
import { listIdeasHandler } from "./handlers/listIdeas";
import { analyzeIdeaHandler } from "./handlers/analyzeIdea";
import { getResourcesHandler } from "./handlers/getResources";
import { statusHandler } from "./handlers/status";
import { errorHandler } from "./middleware/errorHandler";
import { rateLimitMiddleware } from "./middleware/rateLimit";

export interface Env {
  DB: D1Database;
  CACHE: KVNamespace;
  API_KEY_SECRET: string;
  ORCHESTRATOR_URL: string;
  ENVIRONMENT: string;
  ALLOWED_ORIGINS: string;
  RATE_LIMIT_MAX: string;
  RATE_LIMIT_WINDOW: string;
}

const app = new Hono<{ Bindings: Env }>();

// Global middleware
app.use("*", prettyJSON());
app.use("*", logger());
app.use(
  "*",
  cors({
    origin: (origin, c) => {
      const allowed = c.env.ALLOWED_ORIGINS?.split(",") || [];
      if (allowed.includes(origin)) return origin;
      return allowed[0] || "";
    },
    allowMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allowHeaders: ["Content-Type", "Authorization"],
    credentials: true,
  })
);
app.use("*", rateLimitMiddleware);

// Error handler
app.onError(errorHandler);

// Routes
app.get("/health", healthHandler);
app.post("/ideas/generate", generateIdeaHandler);
app.get("/ideas", listIdeasHandler);
app.post("/ideas/:id/analyze", analyzeIdeaHandler);
app.get("/ideas/:id/resources", getResourcesHandler);
app.get("/status", statusHandler);

// 404
app.notFound((c) => {
  return c.json({ error: "Not Found", status: 404 }, 404);
});

export default app;
