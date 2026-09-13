import type { Env } from "../index";

export async function statusHandler(c: { env: Env; json: Function }) {
  // Pipeline status overview
  const ideasByStatus = await c.env.DB.prepare(
    "SELECT status, COUNT(*) as count FROM ideas GROUP BY status"
  ).all();

  const recentRuns = await c.env.DB.prepare(
    "SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT 10"
  ).all();

  const avgScore = await c.env.DB.prepare(
    "SELECT AVG(overall_score) as avg FROM ideas"
  ).first<{ avg: number }>();

  return c.json({
    pipeline: {
      ideas_by_status: ideasByStatus.results || [],
      average_score: avgScore?.avg || 0,
      recent_runs: recentRuns.results || [],
    },
    worker: {
      version: "1.0.0",
      environment: c.env.ENVIRONMENT,
      timestamp: new Date().toISOString(),
    },
  });
}
