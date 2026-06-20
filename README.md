<h1 align="center">FinSight — Pre-Market Intelligence Platform</h1>

<p align="center">
  <b>FastAPI · PostgreSQL + pgvector · Gemini 2.5 Flash · RAG Q&A · Resend email · deployed on Render</b><br/>
  Live at <a href="https://finsight-api-7ghk.onrender.com">finsight-api-7ghk.onrender.com</a>
  <br/><br/>
  <a href="https://github.com/prabhathv07/finsight/actions/workflows/ci.yml">
    <img src="https://github.com/prabhathv07/finsight/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
  <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/PostgreSQL-SQLAlchemy_2-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Gemini-2.5_Flash-4285F4?logo=google&logoColor=white" alt="Gemini">
  <img src="https://img.shields.io/badge/Docker-deployed-2496ED?logo=docker&logoColor=white" alt="Docker">
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
  </a>
</p>

---

A production pre-market briefing system that runs every weekday morning. It pulls ~130 market symbols across futures, macro, sector ETFs, and a watchlist; computes RSI and moving-average indicators; feeds a structured summary to Gemini 2.5 Flash; stores the full analysis in Postgres; and emails the briefing to confirmed subscribers. A public FastAPI service hosts the live dashboard and manages double opt-in signups.

---

## TL;DR

- Ingests **~130 symbols** across 5 categories (futures, macro, sector ETFs, mover universe, watchlist) every weekday via yfinance with a Polygon.io keyed fallback
- Computes **RSI-14, MA9/MA20/MA50, sparklines**, and top-5 gainers/losers from a 71-symbol mover universe; stores everything in Postgres (Neon)
- Generates pre-market commentary with **Gemini 2.5 Flash** — every call logged to `briefings` with the exact prompt input, LLM output, model name, latency, and status; model errors fall back to a template so the briefing always sends
- **Retrieval-augmented Q&A** over the briefing corpus — each briefing is chunked and embedded (`text-embedding-004`) into a **pgvector** column as it is stored; `POST /ask` embeds a question, retrieves the top-k most relevant past chunks, and answers with inline date citations
- Delivers HTML email via **Resend** (production) or Gmail SMTP (local); double opt-in with per-address unsubscribe tokens
- **68 tests** across 9 modules — fully offline (SQLite + deterministic fake providers, no network or API keys required); the RAG layer runs on pgvector in Postgres and degrades to an in-Python cosine scan under SQLite so tests need no extension
- Scheduled via **GitHub Actions cron** at 14:00 UTC weekdays; also triggerable via `POST /briefings/run` from the API

---

## Architecture

```
GitHub Actions cron  (14:00 UTC, Mon–Fri)
          │
          ▼
  run_briefing.py
          │
          ├── INGESTION ─────────────────────────────────────────────────┐
          │   daily_pull.py pulls 5 symbol groups                        │
          │   FallbackProvider: Polygon.io (equities) → yfinance (all)   │
          │   ~130 symbols → tagged (category, Quote) pairs              │
          │   ingestion/store.py → raw_quotes table                      │
          │                                                              │
          ├── FEATURES ────────────────────────────────────────────────┐ │
          │   indicators.py: RSI-14 (Wilder), MA9, MA20, MA50          │ │
          │   sparkline.py: 20-day block-character trend string         │ │
          │   movers.py: top-5 gainers + top-5 losers from 71 symbols  │ │
          │   features/store.py → indicators table                     │ │
          │                                                             │ │
          ├── ANALYSIS ───────────────────────────────────────────────┐│ │
          │   summary.py: compact one-line-per-symbol text for LLM    ││ │
          │   llm.py: GeminiCommentator calls Gemini 2.5 Flash        ││ │
          │   service.py: logs input/output/latency/status, fallback  ││ │
          │   analysis/store.py → briefings table                     ││ │
          │                                                            ││ │
          └── DELIVERY ────────────────────────────────────────────────┘┘─┘
              render.py: build HTML email from briefing
              backends.py: ResendBackend (prod) / SMTPBackend (local)
              send.py: deliver to confirmed subscribers + EMAIL_TO
                         │
                         ▼
            ┌──────────────────────────────┐
            │    FastAPI service (Render)   │
            │                              │
            │  GET  /                      │  dark-theme dashboard
            │  POST /subscribe             │  double opt-in flow
            │  GET  /confirm               │  activate from email link
            │  GET  /unsubscribe           │  remove from email link
            │  GET  /health                │  Render health check
            │  POST /briefings/run         │  trigger analysis manually
            │  GET  /briefings/latest      │  latest stored briefing
            │  GET  /briefings/{date}      │  briefing by date
            │  POST /ask                   │  RAG Q&A over past briefings
            │  POST /rag/reindex           │  rebuild the chunk index
            └──────────────────────────────┘
```

---

## Data Coverage

| Category | Count | Symbols |
|---|---:|---|
| Index futures | 4 | ES=F (S&P 500), NQ=F (Nasdaq), YM=F (Dow), RTY=F (Russell 2000) |
| Macro | 8 | ^VIX, GC=F (gold), CL=F (oil), BTC-USD, ETH-USD, ^TNX (10yr), ^TYX (30yr), DX-Y.NYB (dollar) |
| Sector ETFs | 12 | XLK, SOXX, XLC, XLY, XLP, XLF, XLV, XLE, XLB, XLI, XLU, XLRE (all 11 GICS + semiconductors) |
| Mover universe | ~71 | AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA, AMD, AVGO, JPM, BAC, GS, XOM, CVX, LLY, UNH, … |
| Watchlist | 10 | NVDA, MSFT, META, GOOGL, AMZN, TSLA, AAPL, AMD, AVGO, JPM |

Watchlist symbols get full indicator detail (RSI + all MAs + sparkline). The mover universe is scanned for top-5 gainers and top-5 losers each morning. Futures and macro inform the narrative context in the LLM prompt.

---

## Technical Indicators

| Indicator | Method | Window |
|---|---|---|
| RSI | Wilder smoothing — avg gain / avg loss, returns 100 if all gains, 0 if all losses | 14 periods |
| MA9 | Simple moving average | 9 days |
| MA20 | Simple moving average | 20 days |
| MA50 | Simple moving average | 50 days |
| Sparkline | Block-character trend string (▁▂▄▆█ etc.) | 20 days |
| Top gainers | Sorted by `change_pct` descending | 5 from mover universe |
| Top losers | Sorted by `change_pct` ascending | 5 from mover universe |

All indicator functions take a plain list of closing prices (oldest first) and return `None` when there is not enough history — no sentinel values, no exceptions.

---

## LLM Integration & Monitoring

`analysis/summary.py` builds a compact text block: one line per symbol (`SYMBOL price (±%) RSI x.x MA20 y.yy`). Keeping the input small is deliberate — early versions that dumped raw JSON at the model caused the response to truncate and break parsing.

`analysis/llm.py` wraps Gemini via `google-genai`. The prompt instructs the model to summarize the setup for the day as a concise, data-driven pre-market briefing without individual financial advice.

`analysis/service.py` guarantees one `briefings` row per run, regardless of outcome:

| Scenario | `status` | `error` | Email |
|---|---|---|---|
| Model responds | `ok` | null | LLM output |
| Model errors | `failed` | error text | Template fallback |

Because every call is stored with the exact input and output, a model regression, latency spike, or string of failures all show up as a query against `briefings`. No external monitoring service needed.

---

## Email Delivery

Two backends share the same `send(subject, html, recipient)` interface:

| Backend | When used | Config |
|---|---|---|
| `SMTPBackend` | Local development | `EMAIL_BACKEND=smtp`, Gmail app password |
| `ResendBackend` | Production | `EMAIL_BACKEND=resend`, `RESEND_API_KEY` |

**Double opt-in flow:** `POST /subscribe` saves the address with `status=pending` and emails a confirmation link. `GET /confirm?token=…` flips status to `confirmed`. Every outbound email carries a unique `unsubscribe_token` so `GET /unsubscribe?token=…` resolves to exactly one address. The same response is returned whether or not an address was already on file, so the endpoint does not reveal who is subscribed.

---

## Test Suite

68 tests across 9 modules — the entire suite runs offline:

| Module | What it covers |
|---|---|
| `test_indicators.py` | SMA, RSI edge cases (all gains → 100, all losses → 0, range bounds, insufficient history) |
| `test_features.py` | Sparkline output, indicator_set keys |
| `test_providers.py` | yfinance and Polygon provider shapes against fake HTTP responses |
| `test_pipeline.py` | `ingest()` and `compute()` end-to-end against SQLite + `FakeProvider` |
| `test_analysis.py` | `build_summary()` structure, `generate_and_store()` success and error paths |
| `test_api.py` | All FastAPI briefing/subscribe routes (HTTPx test client, injected fake session) |
| `test_rag.py` | Chunking, embedding/indexing, dialect-aware retrieval ranking, `/ask` and `/rag/reindex` (deterministic fake embedder + answerer) |
| `test_delivery.py` | Email rendering and backend send mechanics |
| `test_subscribe.py` | Confirm link activates, bad token handled, unsubscribe link works |

No network, no database, no API keys needed. `conftest.py` wires `FakeProvider` (deterministic quotes and history) and a per-test SQLite database with the full ORM schema.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| API | FastAPI 0.110 + uvicorn |
| Database | PostgreSQL (Neon in production) via SQLAlchemy 2.0 + psycopg2 |
| ORM models | SQLAlchemy declarative — `RawQuote`, `Indicator`, `Briefing`, `Subscriber` |
| LLM | Gemini 2.5 Flash (`google-genai`) |
| Data providers | yfinance 0.2.40+ (primary) · Polygon.io REST (keyed fallback) |
| Email | Resend (production) · smtplib/Gmail (local) |
| Infrastructure | Docker · Render (web service) · Neon (Postgres) |
| CI/CD | GitHub Actions — `tests` on push · `daily briefing` cron 14:00 UTC weekdays |
| Local dev DB | Docker Compose (`infra/docker-compose.yml`) |

---

## Repo Layout

```
finsight/
├── ingestion/
│   ├── universe.py            # symbol lists: FUTURES, MACRO, SECTORS, MOVER_UNIVERSE, WATCHLIST
│   ├── daily_pull.py          # pull() + history_for() — FallbackProvider chains Polygon → yfinance
│   ├── store.py               # save_quotes() to raw_quotes
│   └── providers/
│       ├── base.py            # Quote dataclass
│       ├── polygon_provider.py
│       └── yfinance_provider.py
├── features/
│   ├── indicators.py          # simple_moving_average(), relative_strength_index(), indicator_set()
│   ├── movers.py              # top_gainers(), top_losers()
│   ├── sparkline.py           # 20-day block-character sparkline
│   └── store.py               # save_indicator()
├── analysis/
│   ├── llm.py                 # GeminiCommentator, PROMPT, strip_code_fence()
│   ├── summary.py             # build_summary() — compact one-line-per-symbol LLM input
│   ├── service.py             # generate_and_store() — always writes a row, falls back on error
│   └── store.py               # save_briefing(), latest_briefing(), briefing_for()
├── api/
│   └── main.py                # FastAPI app — 10 routes, injected session/commentator/embedder/answerer/backend
├── dashboard/
│   └── page.py                # dark-theme HTML renderer, _md_to_html() Markdown converter
├── delivery/
│   ├── backends.py            # SMTPBackend, ResendBackend, backend_from_settings()
│   ├── render.py              # confirmation email HTML
│   ├── send.py                # send_briefing() — renders HTML, delivers to subscribers + EMAIL_TO
│   └── subscribers.py         # request_subscription(), confirm(), unsubscribe(), confirmed_count()
├── core/
│   ├── config.py              # Settings (lru_cache), all env vars in one place
│   ├── db.py                  # SQLAlchemy engine, session factory
│   ├── models.py              # RawQuote, Indicator, Briefing, Subscriber ORM models
│   └── pipeline.py            # ingest(), compute(), run() — orchestrates the daily steps
├── rag/
│   ├── chunk.py               # chunk_briefing() — split summary + commentary
│   ├── embed.py               # GeminiEmbedder, cosine_similarity()
│   ├── store.py               # index_briefing(), retrieve() — pgvector / Python cosine
│   ├── answer.py              # GeminiAnswerer, build_context() with date labels
│   └── service.py             # answer_question(), reindex_all()
├── infra/
│   ├── docker-compose.yml     # local Postgres on port 5433
│   ├── render.yaml            # Render blueprint (web service config)
│   └── init_db.py             # table creation helper
├── tests/                     # 68 tests — 9 modules, all offline
├── .github/workflows/
│   ├── ci.yml                 # pytest on every push
│   └── daily.yml              # cron 14:00 UTC Mon–Fri → run_briefing.py
├── Dockerfile                 # builds the API image, creates tables on start
├── run_briefing.py            # CLI one-shot: ingest → compute → analyze → deliver
├── run_daily.py               # CLI data-only: ingest → compute (no analysis or email)
├── requirements.txt
├── requirements-dev.txt       # adds pytest, httpx, ruff
└── .env.example
```

---

## Setup & Local Run

### 1. Install dependencies

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

### 2. Start the local database

```bash
docker compose -f infra/docker-compose.yml up -d
```

### 3. Configure `.env`

Set at minimum:

```
GEMINI_API_KEY=<your-key>         # get one free at aistudio.google.com/apikey
EMAIL_BACKEND=smtp                 # or resend in production
EMAIL_USER=you@gmail.com
EMAIL_PASSWORD=<gmail-app-password>
EMAIL_TO=you@gmail.com            # where the briefing goes when run locally
```

### 4. Run the full briefing

```bash
python run_briefing.py
```

You should see a line like:

```
2026-06-18: 66 quotes, 16 indicators, analysis ok, delivered 1
```

`delivered 0` is correct if `EMAIL_TO` is empty — data is still ingested and stored. Check the `briefings` table to see the full LLM output and metadata.

### 5. Run the web service

```bash
uvicorn api.main:app --reload
# → http://localhost:8000
```

### 6. Run tests

```bash
python -m pytest
```

No network, no Postgres, no API keys needed — the suite uses SQLite and fake providers.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | local Postgres | SQLAlchemy connection string — point at Neon in production |
| `GEMINI_API_KEY` | *(required for analysis)* | Gemini API key from Google AI Studio |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Model name passed to `google-genai` |
| `POLYGON_API_KEY` | *(empty = yfinance only)* | Enables Polygon.io as the primary equity provider |
| `EMAIL_BACKEND` | `smtp` | `smtp` for local Gmail; `resend` in production |
| `EMAIL_USER` | — | Gmail address (SMTP backend) |
| `EMAIL_PASSWORD` | — | Gmail app password (SMTP backend) |
| `EMAIL_FROM` | falls back to `EMAIL_USER` | Sender address shown in emails |
| `EMAIL_TO` | — | Comma-separated direct recipients (in addition to subscribers) |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | `465` | SMTP port (SSL) |
| `RESEND_API_KEY` | — | Resend API key (production email) |
| `MAILING_ADDRESS` | — | Physical address in email footer (bulk email compliance) |
| `PUBLIC_BASE_URL` | `http://localhost:8000` | Base URL for confirm and unsubscribe links |
| `FINSIGHT_TZ` | `America/Chicago` | Timezone for run scheduling |

---

## Deployment

See [`DEPLOY.md`](DEPLOY.md) for the full step-by-step. In brief:

| Layer | Service | Notes |
|---|---|---|
| Web service | [Render](https://render.com) (free tier) | Dockerized, health check at `/health`, blueprint in `infra/render.yaml` |
| Database | [Neon](https://neon.tech) (free tier) | Postgres that does not expire — set `DATABASE_URL` in the Render dashboard |
| Email | [Resend](https://resend.com) (free tier) | Set `EMAIL_BACKEND=resend` and `RESEND_API_KEY` |

Render's free Postgres expires after 30 days; Neon's does not. The `Dockerfile` creates all tables on startup via `core/models.py`, so schema migrations are handled automatically on first deploy.

---

## Scheduling

The daily briefing runs as a GitHub Actions cron job (`.github/workflows/daily.yml`) at 14:00 UTC on weekdays. GitHub's free-tier scheduler can fire 30–90 minutes late. For exact timing, trigger the dispatch endpoint from [cron-job.org](https://cron-job.org):

```
POST https://api.github.com/repos/prabhathv07/finsight/actions/workflows/daily.yml/dispatches
```

Or call `POST /briefings/run` directly from any external scheduler against the live Render URL.

---

## API Routes

| Method | Route | Description |
|---|---|---|
| `GET` | `/` | Public dashboard — latest briefing rendered as HTML + signup form |
| `POST` | `/subscribe` | Start double opt-in — saves address, sends confirmation email |
| `GET` | `/confirm?token=…` | Activate subscription from the emailed link |
| `GET` | `/unsubscribe?token=…` | Remove an address from the emailed link |
| `GET` | `/health` | Returns `{"status": "ok"}` — used by Render health checks |
| `POST` | `/briefings/run?run_date=YYYY-MM-DD` | Trigger analysis for today (or a specific date) |
| `GET` | `/briefings/latest` | Return the most recent stored briefing as JSON |
| `GET` | `/briefings/{run_date}` | Return the briefing for a specific date as JSON |
| `POST` | `/ask` | Ask a question over past briefings — body `{"question": "...", "top_k": 5}`; returns an answer plus the cited source chunks |
| `POST` | `/rag/reindex` | Rebuild the chunk/embedding index from every stored briefing |

---

## Retrieval-Augmented Q&A (RAG)

The daily pipeline already accumulates one analysed briefing per weekday in
Postgres, so the corpus a retrieval layer needs is already there and growing.
This feature turns that corpus into something queryable without changing the
existing `ingestion → features → analysis → api` flow.

**Indexing (write path).** When a briefing is stored, `rag.chunk.chunk_briefing`
splits it into chunks — the structured summary input is kept whole, and the
commentary is broken on blank lines with very short fragments merged forward.
Each chunk is embedded with Gemini `text-embedding-004` (768-dim) and written
to the `briefing_chunks` table. Indexing is idempotent per briefing: re-running
a day replaces its chunks rather than duplicating them. Embedding is
best-effort — a failure there never sinks the briefing write, preserving the
system's "the briefing always lands" guarantee.

**Storage.** The embedding lives in a **pgvector** column with an IVFFlat cosine
index on Postgres for fast nearest-neighbour search. Under SQLite (the test
suite) the same column degrades to JSON via `with_variant`, and similarity is
computed in Python — so the offline tests need no extension, no key, no network.

**Querying (read path).** `POST /ask` embeds the question, retrieves the top-k
most relevant chunks (`embedding <=> query` on Postgres, a cosine scan on
SQLite), assembles a date-labelled context block, and asks Gemini to answer
using only those excerpts with inline date citations like `(2026-01-06)`. The
response returns both the answer and the source chunks it drew on, each with a
similarity score, so every answer is traceable to the briefings behind it.

```bash
curl -X POST "$BASE_URL/ask" -H 'content-type: application/json' \
  -d '{"question": "How have semiconductors been trending lately?"}'
```

To bootstrap the index over briefings written before RAG existed, call
`POST /rag/reindex` once after deploy — it rebuilds the chunk/embedding
corpus from every row already in the `briefings` table.

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
