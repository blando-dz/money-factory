import type { Env } from "../index";

// Simple in-memory rate limiting (per-isolate)
// For production, use Cloudflare's built-in rate limiting or a KV-backed limiter
const requestCounts = new Map<string, { count: number; resetAt: number }>();

export async function rateLimitMiddleware(
  c: { req: any; env: Env; json: Function },
  next: Function
) {
  const max = parseInt(c.env.RATE_LIMIT_MAX || "100");
  const window = parseInt(c.env.RATE_LIMIT_WINDOW || "60") * 1000;

  // Use CF connecting IP as identifier
  const ip = c.req.header("cf-connecting-ip") || "unknown";
  const key = `ratelimit:${ip}`;

  const now = Date.now();
  const record = requestCounts.get(key);

  if (!record || now > record.resetAt) {
    requestCounts.set(key, { count: 1, resetAt: now + window });
  } else {
    record.count++;
    if (record.count > max) {
      return c.json(
        {
          error: "Rate limit exceeded",
          retry_after: Math.ceil((record.resetAt - now) / 1000),
        },
        429
      );
    }
  }

  await next();
}
