import type { Env } from "../index";

export async function listIdeasHandler(c: { env: Env; req: any; json: Function }) {
  const url = new URL(c.req.url);
  const status = url.searchParams.get("status");
  const limit = Math.min(parseInt(url.searchParams.get("limit") || "50"), 100);
  const offset = parseInt(url.searchParams.get("offset") || "0");

  let query = "SELECT * FROM ideas";
  const params: any[] = [];

  if (status) {
    query += " WHERE status = ?";
    params.push(status);
  }

  query += " ORDER BY overall_score DESC LIMIT ? OFFSET ?";
  params.push(limit, offset);

  const result = await c.env.DB.prepare(query)
    .bind(...params)
    .all();

  const ideas = (result.results || []).map((row: any) => ({
    ...row,
    citations: JSON.parse(row.citations || "[]"),
  }));

  return c.json({
    ideas,
    pagination: { limit, offset, total: ideas.length },
  });
}
