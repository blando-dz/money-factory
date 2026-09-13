"""
Database storage layer for Money Factory.
Saves analysis results and resource manifests to SQLite.
"""
import os
import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from dotenv import load_dotenv
load_dotenv(r"C:\Users\Ghost\.env")

logger = logging.getLogger(__name__)

# DB path — can be overridden via env
DB_PATH = os.getenv("MONEY_FACTORY_DB", str(Path(__file__).parent / "money_factory.db"))


def _get_db() -> sqlite3.Connection:
    """Get a database connection, creating tables if needed."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """Initialize database tables."""
    conn = _get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id TEXT NOT NULL,
            idea_title TEXT NOT NULL,
            viability_score INTEGER,
            demand_score INTEGER,
            competition_score INTEGER,
            decision TEXT NOT NULL,
            confidence REAL,
            sources TEXT,
            reasoning TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(idea_id, created_at)
        );

        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id TEXT NOT NULL,
            resources_json TEXT,
            oss_tools_json TEXT,
            total_monthly_cost REAL,
            cost_breakdown_json TEXT,
            feasibility INTEGER,
            created_at TEXT NOT NULL,
            UNIQUE(idea_id, created_at)
        );

        CREATE INDEX IF NOT EXISTS idx_analyses_idea_id ON analyses(idea_id);
        CREATE INDEX IF NOT EXISTS idx_resources_idea_id ON resources(idea_id);
    """)
    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {DB_PATH}")


def save_analysis(analysis_result) -> bool:
    """Save an AnalysisResult to the database."""
    try:
        conn = _get_db()
        conn.execute("""
            INSERT INTO analyses (idea_id, idea_title, viability_score, demand_score,
                                  competition_score, decision, confidence, sources,
                                  reasoning, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            analysis_result.idea_id,
            analysis_result.idea_title,
            analysis_result.viability_score,
            analysis_result.demand_score,
            analysis_result.competition_score,
            analysis_result.decision,
            analysis_result.confidence,
            json.dumps(analysis_result.sources),
            analysis_result.reasoning,
            analysis_result.created_at,
        ))
        conn.commit()
        conn.close()
        logger.info(f"Saved analysis for {analysis_result.idea_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to save analysis: {e}")
        return False


def get_analysis(idea_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve the latest analysis for an idea_id."""
    try:
        conn = _get_db()
        row = conn.execute(
            "SELECT * FROM analyses WHERE idea_id = ? ORDER BY created_at DESC LIMIT 1",
            (idea_id,)
        ).fetchone()
        conn.close()

        if row is None:
            return None

        return {
            "idea_id": row["idea_id"],
            "idea_title": row["idea_title"],
            "viability_score": row["viability_score"],
            "demand_score": row["demand_score"],
            "competition_score": row["competition_score"],
            "decision": row["decision"],
            "confidence": row["confidence"],
            "sources": json.loads(row["sources"]) if row["sources"] else [],
            "reasoning": row["reasoning"],
            "created_at": row["created_at"],
        }
    except Exception as e:
        logger.error(f"Failed to get analysis: {e}")
        return None


def save_resources(resource_manifest) -> bool:
    """Save a ResourceManifest to the database."""
    try:
        conn = _get_db()
        conn.execute("""
            INSERT INTO resources (idea_id, resources_json, oss_tools_json,
                                   total_monthly_cost, cost_breakdown_json,
                                   feasibility, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            resource_manifest.idea_id,
            json.dumps([r.to_dict() for r in resource_manifest.resources]),
            json.dumps([t.to_dict() for t in resource_manifest.oss_tools]),
            resource_manifest.total_monthly_cost,
            json.dumps(resource_manifest.cost_breakdown),
            1 if resource_manifest.feasibility else 0,
            resource_manifest.created_at,
        ))
        conn.commit()
        conn.close()
        logger.info(f"Saved resources for {resource_manifest.idea_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to save resources: {e}")
        return False


def get_resources(idea_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve the latest resource manifest for an idea_id."""
    try:
        conn = _get_db()
        row = conn.execute(
            "SELECT * FROM resources WHERE idea_id = ? ORDER BY created_at DESC LIMIT 1",
            (idea_id,)
        ).fetchone()
        conn.close()

        if row is None:
            return None

        return {
            "idea_id": row["idea_id"],
            "resources": json.loads(row["resources_json"]) if row["resources_json"] else [],
            "oss_tools": json.loads(row["oss_tools_json"]) if row["oss_tools_json"] else [],
            "total_monthly_cost": row["total_monthly_cost"],
            "cost_breakdown": json.loads(row["cost_breakdown_json"]) if row["cost_breakdown_json"] else {},
            "feasibility": bool(row["feasibility"]),
            "created_at": row["created_at"],
        }
    except Exception as e:
        logger.error(f"Failed to get resources: {e}")
        return None


# Initialize on import
try:
    init_db()
except Exception as e:
    logger.warning(f"DB init failed (non-critical): {e}")
