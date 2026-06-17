# FinSight

A pre-market intelligence platform. Each weekday morning it pulls futures,
macro, sector, and watchlist data, computes technical indicators, generates
LLM commentary, stores everything in Postgres, and emails the briefing to
confirmed subscribers. A public page shows the latest briefing and takes
signups.

This is the productionized version of a daily market-briefing script that
once ran as a single GitHub Actions cron job. The rewrite splits that script
into layers that can be tested, scheduled, and deployed on their own.

## Layout

- `ingestion/` data providers and the morning pull
- `features/` indicator math: RSI, moving averages, sparklines, movers
- `analysis/` the summary builder, the Gemini wrapper, and the logging service
- `api/` the FastAPI service and the public routes
- `dashboard/` the public page and message screens
- `delivery/` email backends, rendering, sending, and the subscriber store
- `core/` shared config, database engine, ORM models, and the pipeline
- `infra/` Docker Compose, the Prefect flow, deploy config, and table setup
- `tests/` one module per layer

## Requirements

- Python 3.11 or newer
- Docker, for local Postgres

## Setup

    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements-dev.txt
    cp .env.example .env

Start the local database:

    docker compose -f infra/docker-compose.yml up -d

## Running the briefing

Run the whole thing once. It creates the tables on first run:

    python run_briefing.py

That ingests data, computes indicators, generates the analysis, and sends to
any confirmed subscribers plus the addresses in `EMAIL_TO`. With a
`GEMINI_API_KEY` set and a network connection you will see a line like
`2026-01-06: 66 quotes, 16 indicators, analysis ok, delivered 3`.

To run only the data half:

    python run_daily.py

## The web service

    export GEMINI_API_KEY=your_key
    uvicorn api.main:app --reload

Routes:

- `GET /` the public page: latest briefing and a signup form
- `POST /subscribe` starts a double opt-in signup and emails a confirm link
- `GET /confirm` confirms a subscription from the emailed link
- `GET /unsubscribe` removes an address from the emailed link
- `GET /health`
- `POST /briefings/run` runs the analysis for today, or pass `?run_date=YYYY-MM-DD`
- `GET /briefings/latest`
- `GET /briefings/{run_date}`

## Monitoring

Every analysis run writes one row to the `briefings` table: the exact model
input, the output, the model name, the latency, and a status. If the model
errors, the row is still written with status `failed` and the error text, and
the reader gets a plain fallback. That table is the monitoring record. A model
regression, a latency spike, or a string of failures all show up as a query
against it.

## Scheduling

Two paths, pick one.

The Prefect flow in `infra/flow.py` is the orchestrated path. Each step
retries on a transient failure. Serve it on a weekday schedule:

    python -m infra.flow

The GitHub Actions workflow in `.github/workflows/daily.yml` is the simpler
fallback. It runs `run_briefing.py` on a weekday cron with no orchestration
server. GitHub's free scheduler can fire 30 to 90 minutes late; trigger the
dispatch endpoint from cron-job.org if you need exact timing.

## Tests

    python -m pytest

The suite runs offline against a temporary SQLite database with fake data and
mail backends, so no network, database, or keys are needed.

## Deploying

See `DEPLOY.md` for the full step-by-step. In short: app on Render or Fly, database on Neon. Neon's free Postgres does not expire,
unlike Render's, which is deleted after 30 days. `infra/render.yaml` is a
Render blueprint; set `DATABASE_URL` to your Neon connection string and the
rest of the secrets in the dashboard. The `Dockerfile` builds the API service
and creates tables on start.

## Going live with subscribers

Signups are double opt-in and every email carries an unsubscribe link, so the
mechanics are in place. Before opening the form to the public, set
`MAILING_ADDRESS` so it appears in the footer, switch `EMAIL_BACKEND` to
`resend` with a real `RESEND_API_KEY`, and set `PUBLIC_BASE_URL` to the live
URL so confirm and unsubscribe links resolve. Operating a public mailing list
carries obligations around consent and unsubscribe handling; confirm you are
comfortable with those before sharing the link.

## Notes

- yfinance is an unofficial client and can break without warning. A keyed
  fallback provider slots in behind the `MarketDataProvider` interface; set
  `POLYGON_API_KEY` to enable it once that provider is written.
- The mover universe and watchlist in `ingestion/universe.py` are starting
  lists. Reconcile them against the tuned lists from the original script
  before relying on the output.
