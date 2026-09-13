import type { Env } from "../index";

export async function getResourcesHandler(c: { env: Env; req: any; json: Function }) {
  const id = parseInt(c.req.param("id"));
  if (isNaN(id)) {
    return c.json({ error: "Invalid idea ID" }, 400);
  }

  // Check cache first
  const cached = await c.env.CACHE.get(`resources:${id}`);
  if (cached) {
    return c.json(JSON.parse(cached));
  }

  const idea = await c.env.DB.prepare("SELECT * FROM ideas WHERE id = ?")
    .bind(id)
    .first();
  if (!idea) {
    return c.json({ error: "Idea not found" }, 404);
  }

  const result = await c.env.DB.prepare(
    "SELECT * FROM resources WHERE idea_id = ? ORDER BY priority DESC"
  )
    .bind(id)
    .all();

  const resources = result.results || [];

  const response = {
    idea_id: id,
    resources: resources.map((r: any) => ({
      ...r,
    })),
  };

  // Cache for 5 minutes
  await c.env.CACHE.put(`resources:${id}`, JSON.stringify(response), {
    expirationTtl: 300,
  });

  return c.json(response);
}
