import type { Env } from "../index";

export async function healthHandler(c: { env: Env; json: Function }) {
  const dbHealthy = await checkDatabase(c.env.DB);
  const cacheHealthy = await checkCache(c.env.CACHE);

  const status = dbHealthy && cacheHealthy ? "healthy" : "degraded";
  const code = status === "healthy" ? 200 : 503;

  return c.json(
    {
      status,
      service: "money-factory-worker",
      version: "1.0.0",
      timestamp: new Date().toISOString(),
      environment: c.env.ENVIRONMENT,
      checks: {
        database: dbHealthy ? "up" : "down",
        cache: cacheHealthy ? "up" : "down",
      },
    },
    code
  );
}

async function checkDatabase(db: D1Database): Promise<boolean> {
  try {
    const result = await db.prepare("SELECT 1 as ok").first();
    return result?.ok === 1;
  } catch {
    return false;
  }
}

async function checkCache(cache: KVNamespace): Promise<boolean> {
  try {
    await cache.put("__health__", "ok", { expirationTtl: 10 });
    const val = await cache.get("__health__");
    return val === "ok";
  } catch {
    return false;
  }
}
