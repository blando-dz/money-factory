"""Application settings loaded from environment via .env."""
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "money-factory"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    DATABASE_URL: str = "sqlite:///./money_factory.db"

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    ARXIV_MAX_RESULTS: int = 20
    ARXIV_CATEGORIES: str = "cs.AI,cs.CE,q-fin.TR"

    RSS_FEEDS: str = "https://hnrss.org/frontpage,https://dev.to/feed"

    WEIGHT_NOVELTY: float = 0.35
    WEIGHT_FEASIBILITY: float = 0.30
    WEIGHT_MONETIZABILITY: float = 0.35

    API_KEY_SECRET: str = "change-me-in-production"

    WORKER_URL: str = "https://money-factory.blando-dz.workers.dev"

    @property
    def arxiv_categories_list(self) -> list[str]:
        return [c.strip() for c in self.ARXIV_CATEGORIES.split(",") if c.strip()]

    @property
    def rss_feeds_list(self) -> list[str]:
        return [f.strip() for f in self.RSS_FEEDS.split(",") if f.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
