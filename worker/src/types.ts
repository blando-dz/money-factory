export interface Idea {
  id: number;
  title: string;
  problem: string;
  solution: string;
  market_fit: string;
  novelty_score: number;
  feasibility_score: number;
  monetizability_score: number;
  overall_score: number;
  status: "pending" | "approved" | "rejected";
  citations: Citation[];
  created_at: string;
  updated_at: string;
}

export interface Citation {
  source: string;
  url: string;
  title: string;
  published?: string;
}

export interface Analysis {
  id: number;
  idea_id: number;
  agent_type: "market_intel" | "contract_dev" | "risk_execution";
  verdict: "approve" | "reject" | "pending";
  reasoning: string | null;
  risk_score: number;
  confidence: number;
  created_at: string;
}

export interface Resource {
  id: number;
  idea_id: number;
  resource_type: string;
  name: string;
  url: string | null;
  cost_estimate: number;
  priority: number;
  created_at: string;
}

export interface ConsensusResult {
  decision: "execute" | "reject" | "escalate";
  agents: {
    market_intel: "approve" | "reject" | "pending";
    contract_dev: "approve" | "reject" | "pending";
    risk_execution: "approve" | "reject" | "pending";
  };
  consensus: boolean;
  reasoning: string;
}
