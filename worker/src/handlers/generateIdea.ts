import type { Env } from "../index";

interface IdeaRequest {
  title: string;
  problem: string;
  solution: string;
  market_fit: string;
  citations?: Array<{
    source: string;
    url: string;
    title: string;
    published?: string;
  }>;
}

export async function generateIdeaHandler(c: { env: Env; req: any; json: Function }) {
  const body = await c.req.json<IdeaRequest>();

  // Validate required fields
  if (!body.title || !body.problem || !body.solution || !body.market_fit) {
    return c.json(
      { error: "Missing required fields: title, problem, solution, market_fit" },
      400
    );
  }

  // Calculate weighted score
  const weights = { novelty: 0.35, feasibility: 0.30, monetizability: 0.35 };
  const noveltyScore = calculateNovelty(body.title, body.problem);
  const feasibilityScore = calculateFeasibility(body.solution);
  const monetizabilityScore = calculateMonetizability(body.market_fit);
  const overallScore =
    noveltyScore * weights.novelty +
    feasibilityScore * weights.feasibility +
    monetizabilityScore * weights.monetizability;

  const citations = JSON.stringify(body.citations || []);

  const result = await c.env.DB.prepare(
    `INSERT INTO ideas (title, problem, solution, market_fit, novelty_score, feasibility_score, monetizability_score, overall_score, citations, status)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
  )
    .bind(
      body.title,
      body.problem,
      body.solution,
      body.market_fit,
      noveltyScore,
      feasibilityScore,
      monetizabilityScore,
      overallScore,
      citations,
      "pending"
    )
    .run();

  const id = result.meta.last_row_id;

  // Cache the new idea
  await c.env.CACHE.put(
    `idea:${id}`,
    JSON.stringify({ id, ...body, overallScore, status: "pending" }),
    { expirationTtl: 300 }
  );

  return c.json(
    {
      id,
      title: body.title,
      overall_score: overallScore,
      status: "pending",
      message: "Idea created successfully",
    },
    201
  );
}

function calculateNovelty(title: string, problem: string): number {
  const text = `${title} ${problem}`.toLowerCase();
  const keywords = ["ai", "ml", "automation", "novel", "innovative", "disrupt", "new", "first"];
  let score = 50;
  for (const kw of keywords) {
    if (text.includes(kw)) score += 7;
  }
  return Math.min(100, score);
}

function calculateFeasibility(solution: string): number {
  const text = solution.toLowerCase();
  const highTerms = ["api", "existing", "open-source", "simple", "mvp", "saas", "plugin"];
  let score = 45;
  for (const t of highTerms) {
    if (text.includes(t)) score += 9;
  }
  return Math.min(100, score);
}

function calculateMonetizability(marketFit: string): number {
  const text = marketFit.toLowerCase();
  const terms = ["subscription", "saas", "b2b", "enterprise", "marketplace", "freemium", "paid"];
  let score = 40;
  for (const t of terms) {
    if (text.includes(t)) score += 10;
  }
  return Math.min(100, score);
}
