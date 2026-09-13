# Money Factory v1.0

Multi-Agent **Idea → Validate → Plan → Monetize** pipeline.

## Idea Factory Core

A FastAPI service that generates ranked project ideas from arXiv research papers and RSS tech feeds, with full citation tracking.

### Stack

- Python 3.11, FastAPI, SQLAlchemy 2.0, Pydantic v2
- arxiv, feedparser, Celery + Redis
- pytest, GitHub Actions CI

### Quickstart

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/ideas/generate` | Trigger idea generation cycle |
| GET | `/ideas` | List ranked ideas |
| GET | `/ideas/{id}` | Get single idea |
| DELETE | `/ideas/{id}` | Delete idea |
| GET | `/health` | Health check |

### Running Tests

```bash
pytest tests/ -v --cov=. --cov-report=term-missing
```

### Docker

```bash
docker-compose up --build
```

## Project Structure

```
money-factory/
├── agents/idea_factory.py     # Core idea generation engine
├── api/
│   ├── routes/ideas.py        # FastAPI endpoints
│   └── models/idea.py         # Pydantic models
├── core/
│   ├── config.py              # Settings from .env
│   ├── database.py            # SQLAlchemy setup
│   └── models.py              # ORM models
├── integrations/
│   ├── arxiv_client.py        # arXiv API wrapper
│   └── rss_parser.py          # RSS feed parser
├── tests/test_idea_factory.py # pytest tests
├── .github/workflows/ci.yml   # CI/CD
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```
