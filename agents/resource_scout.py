"""
Resource Scout Agent — Scans free tier registries, matches OSS tools,
calculates $0 cost path, checks API rate limits.
"""
import os
import logging
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv
load_dotenv(r"C:\Users\Ghost\.env")

logger = logging.getLogger(__name__)


@dataclass
class FreeTierResource:
    name: str
    category: str  # hosting, database, auth, storage, ai, monitoring
    free_tier: str
    rate_limit: str
    url: str
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OSSTool:
    name: str
    category: str  # frontend, backend, database, ai/ml, auth, devops
    url: str
    license: str
    stars: int = 0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResourceManifest:
    idea_id: str
    resources: List[FreeTierResource]
    oss_tools: List[OSSTool]
    total_monthly_cost: float
    cost_breakdown: Dict[str, float]
    feasibility: bool
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "idea_id": self.idea_id,
            "resources": [r.to_dict() for r in self.resources],
            "oss_tools": [t.to_dict() for t in self.oss_tools],
            "total_monthly_cost": self.total_monthly_cost,
            "cost_breakdown": self.cost_breakdown,
            "feasibility": self.feasibility,
            "created_at": self.created_at,
        }


def web_search(query: str, limit: int = 5) -> Dict[str, Any]:
    """Wrapper for web search."""
    try:
        from hermes_tools import web_search as hs_search
        result = hs_search(query=query, limit=limit)
        return result
    except ImportError:
        logger.warning("hermes_tools not available, returning empty search")
        return {"data": {"web": []}}


class ResourceScout:
    """
    Scouts free resources and OSS tools for building an idea with $0 cost path.
    """

    # Free tier registry — known generous free tiers
    FREE_TIER_REGISTRY: List[Dict[str, str]] = [
        # Hosting
        {"name": "Vercel", "category": "hosting", "free_tier": "Hobby plan — 100GB bandwidth, unlimited sites", "rate_limit": "1000 requests/day", "url": "https://vercel.com/pricing"},
        {"name": "Cloudflare Pages", "category": "hosting", "free_tier": "Unlimited sites, 500 builds/month", "rate_limit": "Fair use", "url": "https://pages.cloudflare.com"},
        {"name": "Render", "category": "hosting", "free_tier": "Free web services, 750 hours/month", "rate_limit": "100K requests/month", "url": "https://render.com/pricing"},
        {"name": "Railway", "category": "hosting", "free_tier": "$5 free credit/month", "rate_limit": "Fair use", "url": "https://railway.app/pricing"},
        {"name": "Fly.io", "category": "hosting", "free_tier": "3 shared VMs, 3GB persistent volumes", "rate_limit": "Fair use", "url": "https://fly.io/pricing"},
        {"name": "Netlify", "category": "hosting", "free_tier": "100GB bandwidth, 300 build minutes", "rate_limit": "Fair use", "url": "https://netlify.com/pricing"},
        # Database
        {"name": "Supabase", "category": "database", "free_tier": "500MB PostgreSQL, 2GB file storage", "rate_limit": "50K API requests/day", "url": "https://supabase.com/pricing"},
        {"name": "PlanetScale", "category": "database", "free_tier": "5GB storage, 1B row reads/month", "rate_limit": "Fair use", "url": "https://planetscale.com/pricing"},
        {"name": "Neon", "category": "database", "free_tier": "512MB PostgreSQL, 10K CU", "rate_limit": "Fair use", "url": "https://neon.tech/pricing"},
        {"name": "Turso", "category": "database", "free_tier": "500 databases, 9GB storage", "rate_limit": "25B reads/month", "url": "https://turso.tech/pricing"},
        {"name": "MongoDB Atlas", "category": "database", "free_tier": "512MB M0 cluster", "rate_limit": "Fair use", "url": "https://mongodb.com/pricing"},
        {"name": "Upstash Redis", "category": "database", "free_tier": "10K commands/day", "rate_limit": "10K/day", "url": "https://upstash.com/pricing"},
        # Auth
        {"name": "Clerk", "category": "auth", "free_tier": "10K monthly active users", "rate_limit": "Fair use", "url": "https://clerk.com/pricing"},
        {"name": "Auth0", "category": "auth", "free_tier": "7K active users, unlimited logins", "rate_limit": "Fair use", "url": "https://auth0.com/pricing"},
        {"name": "Supabase Auth", "category": "auth", "free_tier": "50K monthly active users", "rate_limit": "Fair use", "url": "https://supabase.com/pricing"},
        # Storage
        {"name": "Cloudflare R2", "category": "storage", "free_tier": "10GB storage, free egress", "rate_limit": "1M Class A ops/month", "url": "https://r2.cloudflare.com"},
        {"name": "Backblaze B2", "category": "storage", "free_tier": "10GB storage, 1GB/day download", "rate_limit": "Fair use", "url": "https://backblaze.com/cloud-storage"},
        # AI/ML
        {"name": "Groq", "category": "ai", "free_tier": "Free tier with rate limits", "rate_limit": "30 requests/min", "url": "https://console.groq.com"},
        {"name": "Together AI", "category": "ai", "free_tier": "$5 free credit", "rate_limit": "Fair use", "url": "https://together.ai"},
        {"name": "Hugging Face Inference", "category": "ai", "free_tier": "Free Inference API", "rate_limit": "30K characters/month", "url": "https://huggingface.co/inference-api"},
        {"name": "OpenRouter", "category": "ai", "free_tier": "Free models available", "rate_limit": "Varies by model", "url": "https://openrouter.ai"},
        {"name": "Cohere", "category": "ai", "free_tier": "100 calls/min free tier", "rate_limit": "100 calls/min", "url": "https://cohere.com/pricing"},
        # Monitoring
        {"name": "Sentry", "category": "monitoring", "free_tier": "5K errors, 10K transactions", "rate_limit": "Fair use", "url": "https://sentry.io/pricing"},
        {"name": "Vercel Analytics", "category": "monitoring", "free_tier": "25K events/month", "rate_limit": "Fair use", "url": "https://vercel.com/analytics"},
        {"name": "Logtail", "category": "monitoring", "free_tier": "1GB/month logs", "rate_limit": "Fair use", "url": "https://logtail.com/pricing"},
        # Email
        {"name": "Resend", "category": "email", "free_tier": "100 emails/day", "rate_limit": "100/day", "url": "https://resend.com/pricing"},
        {"name": "Mailgun", "category": "email", "free_tier": "5K emails/month for 3 months", "rate_limit": "Fair use", "url": "https://mailgun.com/pricing"},
        {"name": "SendGrid", "category": "email", "free_tier": "100 emails/day", "rate_limit": "100/day", "url": "https://sendgrid.com/pricing"},
    ]

    # OSS tool registry
    OSS_REGISTRY: List[Dict[str, Any]] = [
        # Frontend
        {"name": "Next.js", "category": "frontend", "url": "https://nextjs.org", "license": "MIT", "stars": 125000, "description": "React framework"},
        {"name": "Svelte", "category": "frontend", "url": "https://svelte.dev", "license": "MIT", "stars": 78000, "description": "Compile-time reactive UI"},
        {"name": "Vue.js", "category": "frontend", "url": "https://vuejs.org", "license": "MIT", "stars": 207000, "description": "Progressive framework"},
        {"name": "Astro", "category": "frontend", "url": "https://astro.build", "license": "MIT", "stars": 46000, "description": "Content-focused framework"},
        # Backend
        {"name": "FastAPI", "category": "backend", "url": "https://fastapi.tiangolo.com", "license": "MIT", "stars": 78000, "description": "Modern Python web framework"},
        {"name": "Express", "category": "backend", "url": "https://expressjs.com", "license": "MIT", "stars": 65000, "description": "Minimal Node.js framework"},
        {"name": "Django", "category": "backend", "url": "https://djangoproject.com", "license": "BSD-3", "stars": 78000, "description": "Python web framework"},
        {"name": "Hono", "category": "backend", "url": "https://hono.dev", "license": "MIT", "stars": 18000, "description": "Ultrafast web framework"},
        # Database
        {"name": "PostgreSQL", "category": "database", "url": "https://postgresql.org", "license": "PostgreSQL", "stars": 15000, "description": "Advanced RDBMS"},
        {"name": "SQLite", "category": "database", "url": "https://sqlite.org", "license": "Public Domain", "stars": 0, "description": "Embedded database"},
        {"name": "Redis", "category": "database", "url": "https://redis.io", "license": "BSD-3", "stars": 65000, "description": "In-memory data store"},
        # AI/ML
        {"name": "LangChain", "category": "ai", "url": "https://langchain.com", "license": "MIT", "stars": 92000, "description": "LLM orchestration"},
        {"name": "LlamaIndex", "category": "ai", "url": "https://llamaindex.ai", "license": "MIT", "stars": 36000, "description": "Data framework for LLMs"},
        {"name": "Ollama", "category": "ai", "url": "https://ollama.com", "license": "MIT", "stars": 100000, "description": "Run LLMs locally"},
        {"name": "Transformers", "category": "ai", "url": "https://huggingface.co/transformers", "license": "Apache-2.0", "stars": 130000, "description": "Model library"},
        # Auth
        {"name": "NextAuth.js", "category": "auth", "url": "https://next-auth.js.org", "license": "ISC", "stars": 23000, "description": "Auth for Next.js"},
        {"name": "Lucia", "category": "auth", "url": "https://lucia-auth.com", "license": "MIT", "stars": 9000, "description": "Auth library"},
        # DevOps
        {"name": "Docker", "category": "devops", "url": "https://docker.com", "license": "Apache-2.0", "stars": 68000, "description": "Container platform"},
        {"name": "GitHub Actions", "category": "devops", "url": "https://github.com/features/actions", "license": "MIT", "stars": 0, "description": "CI/CD"},
        {"name": "Terraform", "category": "devops", "url": "https://terraform.io", "license": "MPL-2.0", "stars": 42000, "description": "Infrastructure as code"},
        # Monitoring
        {"name": "Prometheus", "category": "monitoring", "url": "https://prometheus.io", "license": "Apache-2.0", "stars": 55000, "description": "Metrics & alerting"},
        {"name": "Grafana", "category": "monitoring", "url": "https://grafana.com", "license": "AGPL-3.0", "stars": 62000, "description": "Visualization"},
    ]

    # Category to layer mapping
    LAYER_TO_CATEGORY = {
        "hosting": "hosting",
        "database": "database",
        "auth": "auth",
        "storage": "storage",
        "ai": "ai",
        "ml": "ai",
        "monitoring": "monitoring",
        "email": "email",
        "frontend": "frontend",
        "backend": "backend",
        "devops": "devops",
    }

    def get_free_tier_registry(self) -> List[FreeTierResource]:
        """Return the free tier registry as typed objects."""
        return [FreeTierResource(**r) for r in self.FREE_TIER_REGISTRY]

    def get_oss_registry(self) -> List[OSSTool]:
        """Return the OSS tool registry as typed objects."""
        return [OSSTool(**t) for t in self.OSS_REGISTRY]

    def scout(
        self,
        idea_id: str,
        title: str,
        description: str,
        stack_layers: List[str]
    ) -> ResourceManifest:
        """
        Scout free resources and OSS tools for an idea.
        Returns a ResourceManifest with $0 cost path if feasible.
        """
        # Scan free tiers for needed categories
        needed_categories = self._resolve_categories(stack_layers)
        resources = self.scan_free_tiers(needed_categories)

        # Match OSS tools
        oss_tools = self.match_oss_tools(stack_layers)

        # Calculate cost
        total_cost, cost_breakdown = self._calculate_cost_detailed(resources)

        # Check feasibility
        feasibility = self._check_feasibility(resources, needed_categories, oss_tools, stack_layers)

        manifest = ResourceManifest(
            idea_id=idea_id,
            resources=resources,
            oss_tools=oss_tools,
            total_monthly_cost=total_cost,
            cost_breakdown=cost_breakdown,
            feasibility=feasibility,
            created_at=datetime.utcnow().isoformat()
        )

        # Persist to database
        self._save_to_db(manifest)

        return manifest

    def scan_free_tiers(self, categories: List[str]) -> List[FreeTierResource]:
        """Scan free tier resources matching the given categories."""
        results = []
        for cat in categories:
            for resource_dict in self.FREE_TIER_REGISTRY:
                if resource_dict["category"] == cat:
                    results.append(FreeTierResource(**resource_dict))
        return results

    def match_oss_tools(self, stack_layers: List[str]) -> List[OSSTool]:
        """Match OSS tools to stack layers."""
        results = []
        seen_categories = set()
        for layer in stack_layers:
            cat = self.LAYER_TO_CATEGORY.get(layer, layer)
            if cat in seen_categories:
                continue
            seen_categories.add(cat)
            for tool_dict in self.OSS_REGISTRY:
                if tool_dict["category"] == cat:
                    results.append(OSSTool(**tool_dict))
        return results

    def _resolve_categories(self, stack_layers: List[str]) -> List[str]:
        """Resolve stack layers to free tier categories."""
        categories = set()
        for layer in stack_layers:
            cat = self.LAYER_TO_CATEGORY.get(layer, layer)
            if cat in ("hosting", "database", "auth", "storage", "ai", "monitoring", "email"):
                categories.add(cat)
        return list(categories)

    def _calculate_cost(self, resources: List[FreeTierResource], estimated_usage: Dict[str, str] = None) -> float:
        """Calculate total monthly cost. Free tiers = $0."""
        if estimated_usage is None:
            estimated_usage = {}
        total = 0.0
        for r in resources:
            usage = estimated_usage.get(r.category, "normal")
            if usage == "high":
                # Some free tiers don't scale
                if r.name in ("Railway", "Render"):
                    total += 7.0  # Upgrade cost
        return total

    def _calculate_cost_detailed(self, resources: List[FreeTierResource]) -> tuple:
        """Calculate detailed cost breakdown. Returns (total, breakdown)."""
        breakdown = {}
        total = 0.0
        # Group by category, take first free option
        seen = set()
        for r in resources:
            if r.category not in seen:
                seen.add(r.category)
                breakdown[r.category] = 0.0  # Free tier = $0
        return total, breakdown

    def _check_feasibility(
        self,
        resources: List[FreeTierResource],
        needed_categories: List[str],
        oss_tools: List[OSSTool],
        stack_layers: List[str]
    ) -> bool:
        """
        Check if the idea can be built for $0.
        Feasible if all needed resource categories have free options
        and all stack layers have OSS matches.
        """
        # Check resources
        covered_categories = {r.category for r in resources}
        for cat in needed_categories:
            if cat not in covered_categories:
                logger.warning(f"No free tier found for category: {cat}")
                return False

        # Check OSS tools
        covered_layers = set()
        for tool in oss_tools:
            covered_layers.add(tool.category)
        for layer in stack_layers:
            cat = self.LAYER_TO_CATEGORY.get(layer, layer)
            if cat in ("frontend", "backend", "database", "auth", "ai", "devops", "monitoring"):
                if cat not in covered_layers:
                    logger.warning(f"No OSS tool found for layer: {cat}")
                    return False

        return True

    def _get_rate_limit_info(self, resource_name: str) -> str:
        """Get rate limit information for a named resource."""
        for r in self.FREE_TIER_REGISTRY:
            if r["name"] == resource_name:
                return r["rate_limit"]
        return "Check provider docs"

    def _get_known_free_tiers(self) -> Dict[str, List[str]]:
        """Return a dict of category -> list of known free tier providers."""
        result = {}
        for r in self.FREE_TIER_REGISTRY:
            cat = r["category"]
            if cat not in result:
                result[cat] = []
            result[cat].append(r["name"])
        return result

    def _save_to_db(self, manifest: ResourceManifest) -> None:
        """Persist resource manifest to database."""
        try:
            from db.storage import save_resources
            save_resources(manifest)
        except ImportError:
            logger.debug("DB storage not available, skipping save")
        except Exception as e:
            logger.warning(f"Failed to save resources to DB: {e}")
