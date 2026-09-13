import type { Env } from "../index";

interface AnalysisRequest {
  agent_type: "market_intel" | "contract_dev" | "risk_execution";
  verdict: "approve" | "reject" | "pending";
  reasoning?: string;
  risk_score?: number;
  confidence?: number;
}

export async function analyzeIdeaHandler(c: { env: Env; req: any; json: Function }) {
  const id = parseInt(c.req.param("id"));
  if (isNaN(id)) {
    return c.json({ error: "Invalid idea ID" }, 400);
  }

  // Check idea exists
  const idea = await c.env.DB.prepare("SELECT * FROM ideas WHERE id = ?")
    .bind(id)
    .first();
  if (!idea) {
    return c.json({ error: "Idea not found" }, 404);
  }

  const body = (await c.req.json()) as AnalysisRequest;

  if (!body.agent_type || !body.verdict) {
    return c.json({ error: "Missing required fields: agent_type, verdict" }, 400);
  }

  const result = await c.env.DB.prepare(
    `INSERT INTO analysis (idea_id, agent_type, verdict, reasoning, risk_score, confidence)
     VALUES (?, ?, ?, ?, ?, ?)`
  )
    .bind(
      id,
      body.agent_type,
      body.verdict,
      body.reasoning || null,
      body.risk_score ?? 0,
      body.confidence ?? 0
    )
    .run();

  // Update idea status based on consensus
  await updateConsensusStatus(c.env.DB, id);

  // Invalidate cache
  await c.env.CACHE.delete(`idea:${id}`);

  return c.json(
    {
      id: result.meta.last_row_id,
      idea_id: id,
      agent_type: body.agent_type,
      verdict: body.verdict,
      message: "Analysis recorded",
    },
    201
  );
}

async function updateConsensusStatus(db: D1Database, ideaId: number) {
  const analyses = await db
    .prepare("SELECT agent_type, verdict FROM analysis WHERE idea_id = ?")
    .bind(ideaId)
    .all();

  const votes = analyses.results || [];
  const approvals = votes.filter((v: any) => v.verdict === "approve").length;
  const rejections = votes.filter((v: any) => v.verdict === "reject").length;

  let status = "pending";
  if (rejections > 0) status = "rejected";
  else if (approvals >= 2) status = "approved";

  await db.prepare("UPDATE ideas SET status = ?, updated_at = datetime('now') WHERE id = ?")
    .bind(status, ideaId)
    .run();
}
