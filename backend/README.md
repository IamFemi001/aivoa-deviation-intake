# AIVOA Deviation Intake — Backend

FastAPI backend for the AI-Powered Deviation Intake Module. Implements the
exact API contract the React frontend already expects
(`frontend/src/services/deviationApi.js`), so switching the frontend from
its mock to this backend is a one-line env change.

## 1. Folder structure

```
backend/
├── app/
│   ├── main.py                        # FastAPI app, CORS, startup, router mounting
│   ├── api/
│   │   ├── deviations.py              # /api/deviations* routes
│   │   └── health.py                  # /api/health
│   ├── schemas/
│   │   └── deviation.py               # Pydantic request/response models (the contract)
│   ├── services/
│   │   ├── ai_service.py              # AiService interface + get_ai_service() DI switch
│   │   ├── ai_service_stub.py         # Deterministic placeholder (no AI needed to run)
│   │   ├── ai_service_langgraph.py    # Real LangGraph+Groq implementation (AiService wrapper)
│   │   ├── langgraph_pipeline.py      # The actual LangGraph graph + nodes + prompts
│   │   ├── document_extraction.py     # PDF/TXT -> raw text
│   │   └── deviation_service.py       # DB persistence (create/get/list)
│   ├── models/
│   │   └── deviation.py               # SQLAlchemy ORM model
│   ├── database/
│   │   └── session.py                 # Engine/session/init_db
│   ├── core/
│   │   ├── config.py                  # Settings (env vars)
│   │   ├── errors.py                  # AppError hierarchy + exception handlers
│   │   └── logging_config.py
│   └── utils/                         # (reserved for shared helpers)
├── requirements.txt
├── .env.example
└── README.md
```

**Layering rule:** routes (`api/`) never touch the DB or call an AI SDK
directly — they call into `services/`. This keeps each route a thin
"validate → call service → shape response" function, which is what makes
this easy to walk through in a code review.

## 2. Local setup

### 2a. Create the PostgreSQL database

PostgreSQL is the required database for this project (see `.env.example`).
Docker is optional — not assumed. Any of these work:

- **Already have PostgreSQL installed locally:**
  ```bash
  createuser aivoa -P            # set a password when prompted
  createdb aivoa_deviations -O aivoa
  ```
- **Don't have PostgreSQL installed:** install it via your OS package
  manager (`apt install postgresql`, `brew install postgresql@16`, or the
  official installer on Windows), then run the two commands above.
- **Prefer Docker:** `docker run -d --name aivoa-pg -e POSTGRES_USER=aivoa -e POSTGRES_PASSWORD=password -e POSTGRES_DB=aivoa_deviations -p 5432:5432 postgres:16`
- **Prefer a hosted instance** (Supabase, Neon, Render, RDS, etc.): create
  the database there and copy the connection string it gives you into
  `DATABASE_URL` below — the format is the same either way.

### 2b. Install and run

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt  # includes psycopg2-binary for Postgres
cp .env.example .env
```

Edit `.env` and set `DATABASE_URL` to match what you created in step 2a,
e.g.:

```
DATABASE_URL=postgresql+psycopg2://aivoa:password@localhost:5432/aivoa_deviations
```

Then start the app — tables are created automatically on startup
(`init_db()` in `app/database/session.py`, called from `main.py`'s
`on_startup` hook), no separate migration step needed for the MVP:

```bash
uvicorn app.main:app --reload
```

The API is now at `http://localhost:8000`, interactive docs at
`http://localhost:8000/docs`.

By default `AI_SERVICE_ENABLED=true`, so the application uses the real
LangGraph + Groq pipeline required by the assessment. For offline/local
testing only, set `AI_SERVICE_ENABLED=false` to use the deterministic stub
service.

### SQLite test fallback (not the final application configuration)

The application requires an explicit `DATABASE_URL`. SQLite is retained only
for isolated automated tests and temporary local experiments; it is not a
documented runtime configuration for the submission.

If you intentionally want to run a local experiment with SQLite, add this
line to `.env`:

```
DATABASE_URL=sqlite:///./deviations.db
```

This is **not** the submission configuration. Switch back to the
`postgresql+psycopg2://...` URL before treating the application as complete.

### Switching to MySQL instead

Swap `psycopg2-binary` for `pymysql` in `requirements.txt`, then set
`DATABASE_URL=mysql+pymysql://...` in `.env` (example in `.env.example`).
No code changes needed — SQLAlchemy handles the dialect switch.

## 3. API documentation

All responses use a stable JSON contract. Errors always look like:

```json
{ "error": { "code": "EMPTY_SOURCE", "message": "Paste some deviation text or an email before analyzing." } }
```

### `POST /api/deviations/analyze`

Analyze pasted text or email content.

**Request**
```json
{ "source_type": "text", "text": "Batch API-2026-014 crystallizer temp hit 27C during hold, limit is 22C..." }
```

**Response `200`**
```json
{
  "data": {
    "extraction": {
      "title": "Process Parameter Excursion — Batch API-2026-014",
      "event_datetime": "2026-09-24T03:15:00Z",
      "reported_datetime": "2026-09-26T07:00:00+00:00",
      "department": "API Manufacturing",
      "manufacturing_stage": "Crystallization",
      "batch_number": "API-2026-014",
      "description": "...",
      "expected_condition": "Crystallizer temperature held at 18-22°C during the hold step.",
      "actual_condition": "Crystallizer temperature reached 27°C for approximately 40 minutes.",
      "process_parameter": "Crystallizer hold temperature",
      "expected_value": "18-22°C",
      "actual_value": "27°C",
      "immediate_action": "Batch quarantined; QA notified; crystallizer cooling circuit inspected."
    },
    "impact_assessment": {
      "product_quality": { "level": "potential", "reason": "..." },
      "patient_safety": { "level": "none", "reason": "..." },
      "process": { "level": "confirmed", "reason": "..." },
      "regulatory": { "level": "potential", "reason": "..." },
      "data_integrity": { "level": "none", "reason": "..." },
      "batch_product": { "level": "potential", "reason": "..." },
      "overall_summary": "..."
    },
    "severity": {
      "recommended_level": "major",
      "confidence": 0.78,
      "reason": "...",
      "evidence": ["...", "...", "..."]
    },
    "missing_information": ["Exact duration of the temperature excursion beyond \"approximately 40 minutes\""]
  }
}
```

**Errors:** `400 EMPTY_SOURCE`, `502 EXTRACTION_FAILED`, `503 AI_SERVICE_UNAVAILABLE`

### `POST /api/deviations/analyze-file`

Same response shape as above. `multipart/form-data` with a `file` field
(PDF or TXT, ≤10MB by default).

**Errors:** `400 INVALID_FILE`, `415 UNSUPPORTED_FILE_TYPE`, `413 FILE_TOO_LARGE`, `502 EXTRACTION_FAILED`

### `POST /api/deviations`

Persist the user-reviewed record. Body matches
`frontend/src/utils/buildSaveRecord.js` exactly.

**Request**
```json
{
  "title": "Process Parameter Excursion — Batch API-2026-014",
  "event_datetime": "2026-09-24T03:15:00Z",
  "reported_datetime": "2026-09-26T07:00:00+00:00",
  "department": "API Manufacturing",
  "manufacturing_stage": "Crystallization",
  "batch_number": "API-2026-014",
  "description": "...",
  "expected_condition": "...",
  "actual_condition": "...",
  "process_parameter": "...",
  "expected_value": "...",
  "actual_value": "...",
  "immediate_action": "...",
  "impact_assessment": { "...": "same shape as above" },
  "final_severity": "major",
  "source_type": "text",
  "source_filename": null
}
```

**Response `201`**
```json
{ "deviation_id": "DEV-2026-A1B2C3", "message": "Deviation saved successfully" }
```

**Errors:** `422 VALIDATION_ERROR` (e.g. missing `title`), `500 DATABASE_ERROR`

### `GET /api/deviations/{id}`

Returns the full saved record (same fields as save, plus `id` and `created_at`).
**Errors:** `404 DEVIATION_NOT_FOUND`

### `GET /api/deviations?limit=50&offset=0`

Returns `{ "items": [...], "total": n }`, most recent first. Included for
testing/demo purposes (viewing what's been saved without a DB client).

### `GET /api/health`

`{ "status": "ok", "environment": "development", "ai_service": "stub" }`

## 4. Frontend integration

The frontend already speaks this exact contract (see its
`src/services/deviationApi.js` and `README.md`). To connect it:

```bash
# in frontend/.env
VITE_USE_MOCK_API=false
VITE_API_BASE_URL=http://localhost:8000
```

Make sure `CORS_ORIGINS` in the backend `.env` includes the frontend's dev
server origin (`http://localhost:5173` by default — already set). No
frontend code changes are required; `deviationApi.js` was written against
this contract from the start.

## 5. The LangGraph + Groq pipeline

The real AI pipeline is implemented in `app/services/langgraph_pipeline.py`
(graph + nodes) and wired into the `AiService` contract by
`app/services/ai_service_langgraph.py`. To turn it on:

1. `pip install -r requirements.txt` (langgraph/langchain-groq/groq are no
   longer commented out).
2. Set `AI_SERVICE_ENABLED=true` and `GROQ_API_KEY=...` in `.env`.
3. Nothing else changes — `get_ai_service()` in `app/services/ai_service.py`
   is the single switch point, and routes/schemas were already correct.

**Graph (`build_deviation_graph`)**: `receive_source → extract_deviation →
validate_extraction → assess_impact → recommend_severity →
identify_missing_information → format_response`. The three LLM nodes each
call Groq via `ChatGroq(...).with_structured_output(<PydanticModel>)`
against the exact models in `app/schemas/deviation.py`, so a malformed
model response fails Pydantic validation immediately rather than reaching
the frontend. `identify_missing_information` is pure Python (a required-
field diff against the extraction) — no LLM call, so it's deterministic.
Every prompt explicitly instructs the model never to fabricate a value and
to use `null`/`"unknown"` instead — see `_NO_FABRICATION_RULE` in
`langgraph_pipeline.py`.

Both `/analyze` (pasted text/email) and `/analyze-file` (PDF/TXT, extracted
to text by `document_extraction.py`) call the same
`LangGraphAiService._run_graph()`, so there is exactly one AI workflow.

Tests: `tests/test_langgraph_pipeline.py` and
`tests/test_ai_service_langgraph.py` exercise the graph and the error
wrapper with a `FakeLLM` (no real Groq calls), covering: a normal
deviation, a missing batch number, a missing event date, malformed
structured output, and a simulated provider failure/timeout. Run with
`pytest tests/ -v`.

## 6. Design notes

- **Service interfaces over concrete calls:** `AiService` is an ABC so the
  stub and the real LangGraph service are interchangeable; routes depend
  on the abstraction via FastAPI's `Depends(get_ai_service)`.
- **One error contract:** every raised `AppError` subclass (see
  `app/core/errors.py`) is caught by a single handler and rendered as
  `{ error: { code, message } }` — this is what the frontend already
  parses, including its `__forceerror` demo path being replaceable by a
  real `DATABASE_ERROR`.
- **PostgreSQL is the documented database** (`DATABASE_URL` in
  `.env.example`); SQLite is kept as an explicitly-labeled, opt-in
  local-dev fallback only. Switching between Postgres/SQLite/MySQL is a
  one-line `DATABASE_URL` change (plus the matching driver in
  `requirements.txt`) since everything goes through SQLAlchemy —
  `app/database/session.py` is the only place that reads it.
- **Impact/severity stored as JSON:** the MVP doesn't need six relational
  columns per deviation for each impact category — a JSON column keeps
  the schema simple while still being validated at the API boundary.
