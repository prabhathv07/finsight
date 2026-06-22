<h1 align="center">FinSight — Pre-Market Intelligence Platform</h1>

<p align="center">
  <b>FastAPI · PostgreSQL + pgvector · Gemini 2.5 Flash · RAG Q&A · Resend · Render</b>
  <br/>
  Live at <a href="https://prabhathv07.github.io/finsight/">prabhathv07.github.io/finsight</a>
  <br/><br/>
  <a href="https://github.com/prabhathv07/finsight/actions/workflows/ci.yml">
    <img src="https://github.com/prabhathv07/finsight/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
  <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Gemini-2.5_Flash-4285F4?logo=google&logoColor=white" alt="Gemini">
  <img src="https://img.shields.io/badge/Tests-68_passing-brightgreen?logo=pytest&logoColor=white" alt="Tests">
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
  </a>
</p>

---

FinSight is a production pre-market briefing system that runs automatically every weekday morning. It pulls ~130 market symbols across futures, macro indicators, sector ETFs, and a watchlist; computes RSI and moving-average indicators; feeds a structured summary to Gemini 2.5 Flash; stores the full analysis in Postgres; and emails the briefing to confirmed subscribers. A retrieval-augmented Q&A layer lets you query the entire briefing history by asking plain-English questions.

---

## What It Does

- **Ingests ~130 symbols** across 5 categories every weekday via yfinance with a Polygon.io keyed fallback
- **Computes RSI-14, MA9/MA20/MA50, and 20-day sparklines** per watchlist symbol; identifies the top-5 gainers and top-5 losers from a 71-symbol mover universe
- **Generates pre-market commentary** with Gemini 2.5 Flash — every call is logged with the exact prompt, output, model name, latency, and status; failures fall back to a template so the briefing always sends
- **Retrieval-augmented Q&A** — each briefing is chunked and embedded (`text-embedding-004`) into a pgvector column; `POST /ask` retrieves the most relevant past chunks and answers with inline date citations
- **Delivers HTML email** via Resend (production) or Gmail SMTP (local) with double opt-in and per-address unsubscribe tokens
- **68 tests** across 9 modules — fully offline using SQLite and deterministic fakes; no network or API keys needed

---

## Architecture

```
GitHub Actions cron  (14:00 UTC, Mon–Fri)
          │
          ▼
  run_briefing.py
          │
          ├── INGESTION ──────────────────────────────────────────────┐
          │   daily_pull.py — 5 symbol groups (~130 total)            │
          │   FallbackProvider: Polygon.io (equities) → yfinance      │
          │   ingestion/store.py → raw_quotes table                   │
          │                                                           │
          ├── FEATURES ─────────────────────────────────────────────┐ │
          │   RSI-14 (Wilder), MA9 / MA20 / MA50, 20-day sparkline  │ │
          │   top-5 gainers + top-5 losers from mover universe       │ │
          │   features/store.py → indicators table                   │ │
          │                                                          │ │
          ├── ANALYSIS ────────────────────────────────────────────┐ │ │
          │   summary.py — compact one-line-per-symbol text        │ │ │
          │   llm.py — GeminiCommentator (Gemini 2.5 Flash)        │ │ │
          │   service.py — logs every call, falls back on error     │ │ │
          │   analysis/store.py → briefings table                  │ │ │
          │                                                        │ │ │
          │   RAG INDEXING (best-effort, on briefing write)        │ │ │
          │   chunk.py — split summary + commentary                │ │ │
          │   embed.py — GeminiEmbedder (text-embedding-004)       │ │ │
          │   rag/store.py → briefing_chunks table (pgvector)      │ │ │
          │                                                        │ │ │
          └── DELIVERY ─────────────────────────────────────────────┘─┘─┘
              render.py — build HTML email
              backends.py — ResendBackend (prod) / SMTPBackend (local)
              send.py — deliver to confirmed subscribers + EMAIL_TO

          FastAPI service (always running on Render)
          ┌───────────────────────────────────────────┐
          │  GET  /                   dashboard         │
          │  POST /subscribe          double opt-in     │
          │  GET  /confirm?token=…    activate email    │
          │  GET  /unsubscribe?token… remove email      │
          │  GET  /health             Render health check│
          │  POST /briefings/run      trigger manually   │
          │  GET  /briefings/latest   latest briefing    │
          │  GET  /briefings/{date}   briefing by date   │
          │  POST /ask                RAG Q&A            │
          │  POST /rag/reindex        rebuild index      │
          └───────────────────────────────────────────┘
```

---

## Database: SQLite locally, PostgreSQL + pgvector in production

| Environment | Database | Vector search |
|---|---|---|
| Local / demo | SQLite (`sqlite:///./demo.db`) | Cosine computed in Python — no Docker, no extension |
| Test suite | SQLite in-process | Same Python cosine path — zero setup, fully offline |
| Production (Render + Neon) | PostgreSQL 16 + pgvector | `embedding <=> query` — native HNSW cosine index |

The ORM model uses `with_variant` so the `Vector(768)` column silently degrades to a JSON column on SQLite. Everything works on either backend; the only difference is query speed at scale. **If you are running the quick-start below, you do not need Docker or Postgres** — set `DATABASE_URL=sqlite:///./demo.db` and skip step 2.

---

## Data Coverage

| Category | Symbols | Detail |
|---|---:|---|
| Index futures | 4 | ES=F · NQ=F · YM=F · RTY=F |
| Macro | 8 | ^VIX · GC=F · CL=F · BTC-USD · ETH-USD · ^TNX · ^TYX · DX-Y.NYB |
| Sector ETFs | 12 | XLK · SOXX · XLC · XLY · XLP · XLF · XLV · XLE · XLB · XLI · XLU · XLRE |
| Mover universe | ~71 | AAPL · MSFT · NVDA · AMZN · GOOGL · META · TSLA · AMD · AVGO · JPM · BAC · GS … |
| Watchlist | 10 | NVDA · MSFT · META · GOOGL · AMZN · TSLA · AAPL · AMD · AVGO · JPM |

Watchlist symbols receive full indicator detail (RSI + all MAs + sparkline). The mover universe is scanned each morning for the top-5 gainers and top-5 losers. Futures and macro feed narrative context into the Gemini prompt.

---

## Technical Indicators

| Indicator | Method | Window |
|---|---|---|
| RSI | Wilder smoothing — avg gain / avg loss · returns 100 if all gains, 0 if all losses | 14 periods |
| MA9 | Simple moving average | 9 days |
| MA20 | Simple moving average | 20 days |
| MA50 | Simple moving average | 50 days |
| Sparkline | Block-character trend string (▁▂▄▆█ …) | 20 days |
| Top gainers | Sorted by `change_pct` descending | 5 from mover universe |
| Top losers | Sorted by `change_pct` ascending | 5 from mover universe |

All indicator functions take a plain `list[float]` of closing prices (oldest first) and return `None` when there is insufficient history — no sentinel values, no exceptions.

---

## LLM Integration & Monitoring

`analysis/summary.py` builds a compact text block — one line per symbol (`SYMBOL price (±%) RSI x.x MA20 y.yy`). Keeping the input small is deliberate: early versions that passed raw JSON caused responses to truncate and break parsing.

`analysis/llm.py` wraps Gemini 2.5 Flash via `google-genai`. The prompt instructs the model to produce a concise, data-driven pre-market briefing without individual financial advice.

`analysis/service.py` writes exactly one `briefings` row per run, regardless of outcome:

| Scenario | `status` | `error` | Email content |
|---|---|---|---|
| Model responds | `ok` | `null` | Gemini output |
| Model errors | `failed` | error text | Template fallback |

Every row stores the exact prompt input, the raw output, model name, latency, and status. A model regression, latency spike, or run of failures surfaces as a query on `briefings` — no external monitoring service required.

---

## Retrieval-Augmented Q&A

The daily pipeline already accumulates one analysed briefing per weekday in Postgres. The RAG layer turns that corpus into something queryable without changing the existing `ingestion → features → analysis → delivery` flow.

**Write path.** When a briefing is stored, `rag.chunk.chunk_briefing` splits it into chunks — the structured summary input is kept whole; the commentary is broken on blank lines with short fragments merged forward. Each chunk is embedded with Gemini `text-embedding-004` (768-dim) and written to `briefing_chunks`. Indexing is idempotent per briefing. Embedding is best-effort: a failure there never prevents the briefing row from being written.

**Storage.** The embedding lives in a pgvector `Vector(768)` column with cosine indexing on Postgres. Under SQLite (the test suite) the same column degrades to JSON via `with_variant`, and similarity is computed in plain Python — so offline tests need no extension, no key, no network.

**Read path.** `POST /ask` embeds the question, retrieves the top-k closest chunks (`embedding <=> query` on Postgres, a cosine scan on SQLite), assembles a date-labelled context block, and passes it to Gemini to answer using only those excerpts — with inline date citations like `(2026-01-06)`. The response includes both the answer and the source chunks with similarity scores, so every answer is traceable.

```bash
curl -X POST "$BASE_URL/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "How have semiconductors been trending lately?", "top_k": 5}'
```

To bootstrap the index over briefings written before RAG existed, call `POST /rag/reindex` once after deploy.

---

## Email Delivery

Two backends share a common `send(subject, html, recipient)` interface:

| Backend | When used | Required config |
|---|---|---|
| `SMTPBackend` | Local development | `EMAIL_BACKEND=smtp` · Gmail app password |
| `ResendBackend` | Production | `EMAIL_BACKEND=resend` · `RESEND_API_KEY` |

**Double opt-in flow.** `POST /subscribe` saves the address with `status=pending` and emails a confirmation link. `GET /confirm?token=…` flips the status to `confirmed`. Every outbound email carries a unique `unsubscribe_token` so `GET /unsubscribe?token=…` resolves to exactly one address. The same response is returned whether or not an address was already on file, so the endpoint does not reveal the subscriber list.

---

## Test Suite

**68 tests · 9 modules · fully offline** — SQLite in-process, fake providers, no API keys.

| Module | What it covers |
|---|---|
| `test_indicators.py` | SMA, RSI edge cases: all-gains → 100, all-losses → 0, range bounds, insufficient history |
| `test_features.py` | Sparkline output length, flat-series, endpoints; indicator_set key set; mover sorting |
| `test_providers.py` | Polygon ticker mapping, quote and history shapes; FallbackProvider primary/secondary logic |
| `test_pipeline.py` | `ingest()` and `compute()` end-to-end against SQLite + FakeProvider; idempotency |
| `test_analysis.py` | `build_summary()` section structure; `generate_and_store()` success and error/fallback paths |
| `test_api.py` | All FastAPI briefing routes — `/briefings/run`, `/latest`, `/{date}`, 404 on missing date |
| `test_rag.py` | Chunking, fake-embedder indexing, retrieval ranking, `/ask`, `/rag/reindex`; empty corpus path |
| `test_delivery.py` | Email HTML rendering, subject format, multi-recipient send, per-failure recording |
| `test_subscribe.py` | Subscribe → confirm → unsubscribe lifecycle; bad-token handling; home page render |

Run with:

```bash
python -m pytest
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| API framework | FastAPI 0.110 + uvicorn |
| Database | PostgreSQL (Neon in production) · SQLAlchemy 2.0 · psycopg2 |
| Vector search | pgvector — `Vector(768)` column, cosine distance; SQLite fallback for tests |
| ORM models | `RawQuote` · `Indicator` · `Briefing` · `Subscriber` · `BriefingChunk` |
| LLM / embeddings | Gemini 2.5 Flash (commentary) · `text-embedding-004` (RAG) via `google-genai` |
| Data providers | yfinance 0.2.40+ (primary) · Polygon.io REST (keyed fallback) |
| Email | Resend (production) · smtplib / Gmail (local) |
| Infrastructure | Docker · Render (web service) · Neon (Postgres) |
| CI/CD | GitHub Actions — tests on push · daily briefing cron 14:00 UTC weekdays |
| Local dev DB | Docker Compose (`infra/docker-compose.yml`) |

---

## Repo Layout

```
finsight/
├── ingestion/
│   ├── universe.py              # FUTURES, MACRO, SECTORS, MOVER_UNIVERSE, WATCHLIST
│   ├── daily_pull.py            # pull() + history_for() — FallbackProvider (Polygon → yfinance)
│   ├── store.py                 # save_quotes() → raw_quotes
│   └── providers/
│       ├── base.py              # Quote dataclass · MarketDataProvider protocol
│       ├── polygon_provider.py  # REST client, ticker type filtering, FallbackProvider
│       └── yfinance_provider.py
├── features/
│   ├── indicators.py            # simple_moving_average(), relative_strength_index(), indicator_set()
│   ├── movers.py                # top_gainers(), top_losers()
│   ├── sparkline.py             # 20-day block-character sparkline
│   └── store.py                 # save_indicator()
├── analysis/
│   ├── llm.py                   # GeminiCommentator, PROMPT, strip_code_fence()
│   ├── summary.py               # build_summary() — compact one-line-per-symbol LLM input
│   ├── service.py               # generate_and_store() — always writes a row, falls back on error
│   └── store.py                 # save_briefing(), latest_briefing(), briefing_for()
├── rag/
│   ├── chunk.py                 # chunk_briefing() — split summary + commentary on blank lines
│   ├── embed.py                 # GeminiEmbedder · cosine_similarity() (SQLite path)
│   ├── store.py                 # index_briefing() · retrieve() (pgvector / Python cosine)
│   ├── answer.py                # GeminiAnswerer · build_context() with date labels
│   └── service.py               # answer_question() · reindex_all()
├── api/
│   └── main.py                  # FastAPI app — 10 routes, injected dependencies
├── dashboard/
│   └── page.py                  # dark-theme HTML renderer, _md_to_html()
├── delivery/
│   ├── backends.py              # SMTPBackend · ResendBackend · backend_from_settings()
│   ├── render.py                # HTML email builder, confirmation email
│   ├── send.py                  # send_briefing() — renders and delivers
│   └── subscribers.py           # request_subscription() · confirm() · unsubscribe()
├── core/
│   ├── config.py                # Settings (lru_cache) — all env vars in one place
│   ├── db.py                    # SQLAlchemy engine, session factory
│   ├── models.py                # ORM models — RawQuote, Indicator, Briefing, Subscriber, BriefingChunk
│   └── pipeline.py              # ingest() · compute() · run()
├── infra/
│   ├── docker-compose.yml       # local Postgres on port 5433 (with pgvector)
│   ├── render.yaml              # Render blueprint (web service config)
│   └── init_db.py               # table creation helper
├── tests/                       # 68 tests — 9 modules, all offline
├── .github/workflows/
│   ├── ci.yml                   # pytest on every push
│   └── daily.yml                # cron 14:00 UTC Mon–Fri → run_briefing.py
├── Dockerfile                   # builds API image, creates tables on start
├── run_briefing.py              # CLI: ingest → compute → analyze → deliver
├── run_daily.py                 # CLI: ingest → compute only (no email)
├── requirements.txt
├── requirements-dev.txt         # adds pytest, httpx, ruff
└── .env.example
```

---

## Local Setup

### 1. Clone and install

```bash
git clone https://github.com/prabhathv07/finsight.git
cd finsight
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

### 2. Choose your database

**Quick start (SQLite — no Docker needed):**

```env
DATABASE_URL=sqlite:///./demo.db
```

Set this in `.env` and skip Docker entirely. SQLite is the right choice for a local demo or exploring the codebase. The RAG layer works on SQLite using a Python cosine fallback.

**Full local stack (Postgres + pgvector):**

```bash
docker compose -f infra/docker-compose.yml up -d
```

This starts Postgres with the pgvector extension on `localhost:5433`. Use `DATABASE_URL=postgresql://finsight:finsight@localhost:5433/finsight`. Required if you want to test production-identical vector indexing locally.

### 3. Configure `.env`

The minimum required to run a full briefing locally:

```env
GEMINI_API_KEY=<your-key>          # free at aistudio.google.com/apikey
EMAIL_BACKEND=smtp
EMAIL_USER=you@gmail.com
EMAIL_PASSWORD=<gmail-app-password>
EMAIL_TO=you@gmail.com
MAILING_ADDRESS=<your physical address>   # required for CAN-SPAM compliance
```

> **Before sharing the live URL**: replace `MAILING_ADDRESS` with a real address. The dashboard and every outbound email shows this value in the footer. `123 Demo St` is a placeholder — leave it in place and your emails may be flagged as spam.

See [Environment Variables](#environment-variables) below for the full list.

### 4. Run the briefing

```bash
python run_briefing.py
```

Expected output:

```
2026-06-20: 66 quotes, 16 indicators, analysis ok, delivered 1
```

`delivered 0` is correct when `EMAIL_TO` is empty — data is still ingested and stored. Check the `briefings` table to see the full output and metadata.

### 5. Start the web service

```bash
uvicorn api.main:app --reload
# → http://localhost:8000
```

### 6. Run the test suite

```bash
python -m pytest
```

No Postgres, no network, no API keys — the suite runs entirely on SQLite with fake providers.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | local Postgres | SQLAlchemy connection string |
| `GEMINI_API_KEY` | *(required for analysis/RAG)* | Gemini API key from Google AI Studio |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Model for commentary and `/ask` answers |
| `EMBED_MODEL` | `text-embedding-004` | Gemini embedding model for RAG indexing |
| `EMBED_DIM` | `768` | Embedding dimension — must match the model and pgvector column |
| `RAG_TOP_K` | `5` | Default number of chunks retrieved per `/ask` request |
| `POLYGON_API_KEY` | *(empty = yfinance only)* | Enables Polygon.io as the primary equity provider |
| `EMAIL_BACKEND` | `smtp` | `smtp` for Gmail · `resend` for production |
| `EMAIL_USER` | — | Gmail address (SMTP) |
| `EMAIL_PASSWORD` | — | Gmail app password (SMTP) |
| `EMAIL_FROM` | `EMAIL_USER` | Sender address shown in outgoing emails |
| `EMAIL_TO` | — | Comma-separated direct recipients (in addition to subscribers) |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server hostname |
| `SMTP_PORT` | `465` | SMTP port (SSL) |
| `RESEND_API_KEY` | — | Resend API key for production email |
| `MAILING_ADDRESS` | — | Physical address in email footer (bulk email compliance) |
| `PUBLIC_BASE_URL` | `http://localhost:8000` | Base URL for confirm and unsubscribe links |
| `FINSIGHT_TZ` | `America/Chicago` | Timezone for run scheduling |

---

## API Reference

| Method | Route | Description |
|---|---|---|
| `GET` | `/` | Public dashboard — latest briefing as HTML with signup form |
| `POST` | `/subscribe` | Start double opt-in — saves address, sends confirmation email |
| `GET` | `/confirm?token=…` | Activate a subscription from the emailed link |
| `GET` | `/unsubscribe?token=…` | Remove an address from the emailed link |
| `GET` | `/health` | Returns `{"status": "ok"}` — used by Render health checks |
| `POST` | `/briefings/run` | Trigger a briefing for today or `?run_date=YYYY-MM-DD` |
| `GET` | `/briefings/latest` | Latest stored briefing as JSON |
| `GET` | `/briefings/{run_date}` | Briefing for a specific date as JSON |
| `POST` | `/ask` | RAG Q&A — body `{"question": "…", "top_k": 5}`; returns answer + cited source chunks |
| `POST` | `/rag/reindex` | Rebuild the chunk/embedding index from all stored briefings |

Error responses follow FastAPI's standard JSON shape. `/ask` and `/rag/reindex` return `502 Bad Gateway` when the Gemini embedding or answer call fails (e.g. invalid key, quota exceeded), so the root cause is always visible in the response body rather than a generic 500.

---

## Deployment

Full step-by-step in [`DEPLOY.md`](DEPLOY.md). Quick summary:

| Layer | Service | Notes |
|---|---|---|
| Web service | [Render](https://render.com) (free tier) | Dockerized; health check at `/health`; blueprint at `infra/render.yaml` |
| Database | [Neon](https://neon.tech) (free tier) | Postgres with pgvector — does not expire like Render's built-in Postgres |
| Email | [Resend](https://resend.com) (free tier) | Set `EMAIL_BACKEND=resend` and `RESEND_API_KEY` |

The `Dockerfile` runs `python infra/init_db.py` on startup to create all tables including `briefing_chunks`, so schema bootstrap is automatic on first deploy.

---

## Scheduling

The daily briefing runs via GitHub Actions cron (`.github/workflows/daily.yml`) at **14:00 UTC on weekdays**. GitHub's free-tier scheduler can fire 30–90 minutes late. For tighter timing, trigger the workflow dispatch from [cron-job.org](https://cron-job.org):

```
POST https://api.github.com/repos/prabhathv07/finsight/actions/workflows/daily.yml/dispatches
```

Or call `POST /briefings/run` directly against the live Render URL from any external scheduler.

---

## License

MIT — see [LICENSE](LICENSE) for details.
