import type { Env } from "../index";

export function errorHandler(err: Error, c: { json: Function; env: Env }) {
  console.error("Worker error:", err.message);

  // Don't leak internal details in production
  const isProd = c.env.ENVIRONMENT === "production";
  const message = isProd ? "Internal Server Error" : err.message;

  return c.json(
    {
      error: message,
      status: 500,
      timestamp: new Date().toISOString(),
    },
    500
  );
}
