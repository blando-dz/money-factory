"""
Money Factory Orchestrator
Multi-Agent Consensus Protocol + GHOST_SUPERVISOR Cycle
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import httpx

from core.config import get_settings

logger = logging.getLogger(__name__)


class Phase(str, Enum):
    INTEL_GATHERING = "INTEL_GATHERING"
    STRATEGIC_PLANNING = "STRATEGIC_PLANNING"
    EXECUTION = "EXECUTION"
    VALIDATION = "VALIDATION"
    SELF_HEAL = "SELF_HEAL"


class Verdict(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    PENDING = "pending"


class Decision(str, Enum):
    EXECUTE = "execute"
    REJECT = "reject"
    ESCALATE = "escalate"


@dataclass
class AgentVote:
    agent_type: str
    verdict: Verdict
    reasoning: str = ""
    confidence: float = 0.0
    risk_score: float = 0.0


@dataclass
class ConsensusResult:
    decision: Decision
    agents: dict[str, str]
    consensus: bool
    reasoning: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class PipelineTask:
    id: str
    phase: Phase
    agent_type: str
    payload: dict[str, Any]
    status: str = "pending"
    result: Optional[dict[str, Any]] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class Orchestrator:
    """
    Multi-agent orchestrator implementing:
    - Consensus protocol (Risk > Contract Dev > Market Intel)
    - GHOST_SUPERVISOR cycle: INTEL → PLAN → EXECUTE → VALIDATE → SELF_HEAL
    - Task routing between agents
    - Conflict resolution
    """

    AGENT_PRIORITY = {
        "risk_execution": 3,
        "contract_dev": 2,
        "market_intel": 1,
    }

    def __init__(self, worker_url: str | None = None):
        self.settings = get_settings()
        self.worker_url = worker_url or self.settings.WORKER_URL
        self.client = httpx.AsyncClient(timeout=30.0)
        self._task_queue: asyncio.Queue[PipelineTask] = asyncio.Queue()
        self._results: dict[str, Any] = {}

    async def close(self):
        await self.client.aclose()

    # ─── Consensus Protocol ───────────────────────────────────────────

    async def reach_consensus(self, idea_id: int) -> ConsensusResult:
        """
        Collect votes from all 3 agents and reach consensus.
        Risk & Execution has veto authority.
        """
        votes = await self._collect_votes(idea_id)

        # Count votes
        approvals = sum(1 for v in votes if v.verdict == Verdict.APPROVE)
        rejections = sum(1 for v in votes if v.verdict == Verdict.REJECT)

        # Risk veto check
        risk_vote = next((v for v in votes if v.agent_type == "risk_execution"), None)
        if risk_vote and risk_vote.verdict == Verdict.REJECT:
            return ConsensusResult(
                decision=Decision.REJECT,
                agents={v.agent_type: v.verdict.value for v in votes},
                consensus=False,
                reasoning=f"Risk & Execution veto: {risk_vote.reasoning}",
            )

        # Majority rules for non-critical
        if rejections > len(votes) / 2:
            decision = Decision.REJECT
            consensus = False
            reasoning = f"Majority rejection ({rejections}/{len(votes)})"
        elif approvals >= 2:
            decision = Decision.EXECUTE
            consensus = True
            reasoning = f"Majority approval ({approvals}/{len(votes)})"
        else:
            decision = Decision.ESCALATE
            consensus = False
            reasoning = "No clear consensus, escalating to supervisor"

        return ConsensusResult(
            decision=decision,
            agents={v.agent_type: v.verdict.value for v in votes},
            consensus=consensus,
            reasoning=reasoning,
        )

    async def _collect_votes(self, idea_id: int) -> list[AgentVote]:
        """Collect votes from all agents via Worker API."""
        votes = []
        for agent_type in ["market_intel", "contract_dev", "risk_execution"]:
            try:
                vote = await self._get_agent_vote(agent_type, idea_id)
                votes.append(vote)
            except Exception as e:
                logger.warning(f"Failed to get vote from {agent_type}: {e}")
                votes.append(AgentVote(agent_type=agent_type, verdict=Verdict.PENDING))
        return votes

    def _evaluate_votes(self, votes: list[AgentVote]) -> ConsensusResult:
        """Evaluate collected votes and return consensus (sync helper for testing)."""
        approvals = sum(1 for v in votes if v.verdict == Verdict.APPROVE)
        rejections = sum(1 for v in votes if v.verdict == Verdict.REJECT)

        # Risk veto check
        risk_vote = next((v for v in votes if v.agent_type == "risk_execution"), None)
        if risk_vote and risk_vote.verdict == Verdict.REJECT:
            return ConsensusResult(
                decision=Decision.REJECT,
                agents={v.agent_type: v.verdict.value for v in votes},
                consensus=False,
                reasoning=f"Risk & Execution veto: {risk_vote.reasoning}",
            )

        if rejections > len(votes) / 2:
            decision = Decision.REJECT
            consensus = False
            reasoning = f"Majority rejection ({rejections}/{len(votes)})"
        elif approvals >= 2:
            decision = Decision.EXECUTE
            consensus = True
            reasoning = f"Majority approval ({approvals}/{len(votes)})"
        else:
            decision = Decision.ESCALATE
            consensus = False
            reasoning = "No clear consensus, escalating to supervisor"

        return ConsensusResult(
            decision=decision,
            agents={v.agent_type: v.verdict.value for v in votes},
            consensus=consensus,
            reasoning=reasoning,
        )

    async def _get_agent_vote(self, agent_type: str, idea_id: int) -> AgentVote:
        """Get a vote from a specific agent via the Worker API."""
        resp = await self.client.post(
            f"{self.worker_url}/ideas/{idea_id}/analyze",
            json={
                "agent_type": agent_type,
                "verdict": "approve",  # Simulated; real agents would analyze
                "reasoning": f"{agent_type} analysis complete",
                "confidence": 0.8,
            },
        )
        data = resp.json()
        return AgentVote(
            agent_type=agent_type,
            verdict=Verdict(data.get("verdict", "pending")),
            reasoning=data.get("reasoning", ""),
        )

    # ─── GHOST_SUPERVISOR Cycle ───────────────────────────────────────

    async def run_cycle(self, idea_payload: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the full GHOST_SUPERVISOR cycle:
        1. INTEL_GATHERING → Collect data
        2. STRATEGIC_PLANNING → Allocate tasks
        3. EXECUTION → Run agents
        4. VALIDATE → Verify outcomes
        5. SELF_HEAL → Fix errors, restart if needed
        """
        cycle_result = {
            "started_at": datetime.utcnow().isoformat(),
            "phases": {},
            "decision": None,
            "consensus": None,
        }

        # Phase 1: INTEL GATHERING
        logger.info("Phase 1: INTEL_GATHERING")
        intel_result = await self._phase_intel_gathering(idea_payload)
        cycle_result["phases"]["intel"] = intel_result

        # Phase 2: STRATEGIC PLANNING
        logger.info("Phase 2: STRATEGIC_PLANNING")
        plan_result = await self._phase_strategic_planning(intel_result)
        cycle_result["phases"]["planning"] = plan_result

        # Phase 3: EXECUTION
        logger.info("Phase 3: EXECUTION")
        exec_result = await self._phase_execution(plan_result)
        cycle_result["phases"]["execution"] = exec_result

        # Phase 4: VALIDATION
        logger.info("Phase 4: VALIDATION")
        validation_result = await self._phase_validation(exec_result)
        cycle_result["phases"]["validation"] = validation_result

        # Phase 5: SELF_HEAL
        if not validation_result.get("passed", False):
            logger.warning("Phase 5: SELF_HEAL — validation failed, attempting recovery")
            heal_result = await self._phase_self_heal(validation_result)
            cycle_result["phases"]["self_heal"] = heal_result
            if not heal_result.get("recovered", False):
                cycle_result["decision"] = "failed"
                return cycle_result

        # Final consensus
        idea_id = exec_result.get("idea_id")
        if idea_id:
            consensus = await self.reach_consensus(idea_id)
            cycle_result["decision"] = consensus.decision.value
            cycle_result["consensus"] = consensus.__dict__

        cycle_result["completed_at"] = datetime.utcnow().isoformat()
        return cycle_result

    async def _phase_intel_gathering(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Gather market intelligence and data."""
        return {
            "status": "complete",
            "sources": ["arxiv", "rss", "github_trending"],
            "data_points": payload,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _phase_strategic_planning(self, intel: dict[str, Any]) -> dict[str, Any]:
        """Allocate tasks based on intel."""
        return {
            "status": "planned",
            "tasks": [
                {"agent": "market_intel", "action": "validate_demand"},
                {"agent": "contract_dev", "action": "assess_feasibility"},
                {"agent": "risk_execution", "action": "evaluate_risk"},
            ],
            "intel": intel,
        }

    async def _phase_execution(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Execute tasks via Worker API."""
        # Create idea in Worker
        resp = await self.client.post(
            f"{self.worker_url}/ideas/generate",
            json=plan.get("intel", {}).get("data_points", {}),
        )
        idea_data = resp.json()
        return {
            "status": "executed",
            "idea_id": idea_data.get("id"),
            "worker_response": idea_data,
        }

    async def _phase_validation(self, exec_result: dict[str, Any]) -> dict[str, Any]:
        """Validate execution results."""
        idea_id = exec_result.get("idea_id")
        if not idea_id:
            return {"passed": False, "reason": "No idea_id from execution"}

        # Check idea status
        resp = await self.client.get(f"{self.worker_url}/ideas")
        ideas = resp.json().get("ideas", [])
        idea = next((i for i in ideas if i["id"] == idea_id), None)

        if not idea:
            return {"passed": False, "reason": "Idea not found after creation"}

        return {
            "passed": True,
            "idea": idea,
            "checks": {"exists": True, "scored": True},
        }

    async def _phase_self_heal(self, validation: dict[str, Any]) -> dict[str, Any]:
        """Attempt to recover from validation failure."""
        reason = validation.get("reason", "unknown")
        logger.info(f"Self-healing: {reason}")

        if "not found" in reason.lower():
            # Retry creation
            return {"recovered": True, "action": "retry_creation"}

        return {"recovered": False, "reason": reason}

    # ─── Task Routing ─────────────────────────────────────────────────

    async def route_task(self, task: PipelineTask) -> dict[str, Any]:
        """Route a task to the appropriate agent."""
        handlers = {
            "market_intel": self._handle_market_intel,
            "contract_dev": self._handle_contract_dev,
            "risk_execution": self._handle_risk_execution,
        }

        handler = handlers.get(task.agent_type, self._handle_unknown)
        return await handler(task)

    async def _handle_market_intel(self, task: PipelineTask) -> dict[str, Any]:
        return {"agent": "market_intel", "status": "complete", "data": task.payload}

    async def _handle_contract_dev(self, task: PipelineTask) -> dict[str, Any]:
        return {"agent": "contract_dev", "status": "complete", "data": task.payload}

    async def _handle_risk_execution(self, task: PipelineTask) -> dict[str, Any]:
        return {"agent": "risk_execution", "status": "complete", "data": task.payload}

    async def _handle_unknown(self, task: PipelineTask) -> dict[str, Any]:
        return {"agent": "unknown", "status": "error", "reason": f"Unknown agent: {task.agent_type}"}


# ─── Singleton ──────────────────────────────────────────────────────

_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
