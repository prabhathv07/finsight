# FinSight

A pre-market intelligence pipeline. It pulls futures, macro, sector, and
watchlist data each morning, computes technical indicators, and stores
everything in Postgres. Later phases add an LLM analysis service, a public
dashboard, email delivery, and scheduled orchestration.

This repo is the productionized version of a daily market-briefing script
that previously ran as a single GitHub Actions cron job. The rewrite splits
that script into layers that can be tested, scheduled, and deployed on their
own.

## Layout

- `ingestion/` data providers and the morning pull
- `features/` indicator math (RSI, moving averages, sparklines, movers)
- `analysis/` LLM summary and commentary (phase 2)
- `api/` FastAPI service (phase 2)
- `dashboard/` public page (phase 4)
- `core/` shared config, database engine, and ORM models
- `infra/` Docker Compose and deploy configuration
- `tests/` one module per layer

## Requirements

- Python 3.11 or newer
- Docker, for local Postgres

## Setup

Create a virtual environment and install dependencies:

    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements-dev.txt

Copy the environment template and fill in values as needed:

    cp .env.example .env

For phase 1 the defaults work as-is against the local database.

## Running locally

Start Postgres:

    docker compose -f infra/docker-compose.yml up -d

Run the daily pull. It creates the tables on first run:

    python run_daily.py

You should see a line like `2026-01-06: 66 quotes, 16 indicators`. Confirm
the data landed:

    docker exec -it finsight-postgres psql -U finsight -c \
      "select category, count(*) from raw_quotes group by category;"

## The analysis service

Running `run_daily.py` once creates every table, including the briefings
log. With data in the database, start the API:

    export GEMINI_API_KEY=your_key
    uvicorn api.main:app --reload

Then trigger an analysis and read it back:

    curl -X POST "http://localhost:8000/briefings/run"
    curl "http://localhost:8000/briefings/latest"

Every call to `/briefings/run` writes one row to the briefings table with the
exact model input, the output, the model name, the latency, and a status. If
the model errors, the row is still written with status `failed` and the error
text, and the reader gets a plain fallback. That table is the monitoring
record: it is how a model regression or a latency spike shows up.

Endpoints:

- `GET /health`
- `POST /briefings/run` runs the analysis for today, or pass `?run_date=YYYY-MM-DD`
- `GET /briefings/latest`
- `GET /briefings/{run_date}`

## Tests

    python -m pytest

The suite runs offline. It uses a temporary SQLite database and a fake data
provider, so no network or running Postgres is required.

## Notes

- yfinance is an unofficial client and can break without warning. A keyed
  fallback provider (Polygon) slots in behind the same interface; set
  `POLYGON_API_KEY` to enable it once that provider is added.
- The mover universe and watchlist in `ingestion/universe.py` are starting
  lists. Reconcile them against the tuned lists from the original script
  before relying on the output.
