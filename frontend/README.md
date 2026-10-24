# AIVOA.AI — Deviation Intake Module (Frontend)

React/Redux frontend implementation of the AI-Powered Deviation Intake workflow for
the AIVOA.AI AI Product Engineer Challenge. Built with **React + Redux
Toolkit**, following the Technical Product Specification exactly (state
shape, AI output schema, API contracts, folder structure).

This frontend contains the React/Redux UI and API service layer for the
integrated application. By default it calls the real FastAPI backend, which
connects to LangGraph, Groq, and PostgreSQL. The bundled mock responses remain
available by setting `VITE_USE_MOCK_API=true` for offline/local testing.

---

## 1. Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open the printed local URL (default `http://localhost:5173`).

### Environment variables

| Variable              | Default                | Purpose                                                   |
|------------------------|-------------------------|------------------------------------------------------------|
| `VITE_USE_MOCK_API`    | `false`                 | `true` = use in-browser mock AI responses. `false` = call the real backend. |
| `VITE_API_BASE_URL`    | `http://localhost:8000` | Base URL of the FastAPI backend. Only used when mocking is off. |

---

## 2. The workflow this implements

```
Paste deviation text/email  ──┐
                               ├──► AI Copilot Panel ──► AI extraction
Upload deviation document  ───┘                              │
                                                               ▼
                                                    Log Deviation form
                                                    (auto-populated)
                                                               │
                                                               ▼
                                              AI impact & severity assistance
                                                               │
                                                               ▼
                                                     User review / edit
                                                               │
                                                               ▼
                                                             Save
```

**The left-side form is intentionally locked and empty until the first
successful AI analysis.** Every field renders as a disabled "Not yet
analyzed" placeholder (see `FieldInput`'s `locked` prop) so it is
impossible to hand-fill the form before using the AI Copilot — this
directly satisfies the assignment's explicit requirement. Once an
analysis succeeds, the form unlocks and every field becomes editable.

---

## 3. Component tree

```
App
└── DeviationPage
    ├── Header
    ├── workspace
    │   ├── DeviationForm                      (left column)
    │   │   ├── IdentificationSection
    │   │   ├── DetailsSection
    │   │   ├── ImpactSection
    │   │   └── SeveritySection
    │   └── AICopilot                          (right column, sticky)
    │       ├── SourceInputPanel   (idle state — upload/paste + Analyze)
    │       │   ├── (upload tab: dropzone + file input)
    │       │   └── (paste tab: textarea)
    │       ├── ProcessingState    (processing state — staged checklist)
    │       └── ExtractionSummary  (success state — chat-style AI summary)
    └── SaveBar                                (fixed footer)

common/
├── Badge.jsx          (ProvenanceBadge, ImpactLevelBadge, SeverityBadge)
├── FieldInput.jsx      (generic labeled field: text / textarea / datetime)
└── EmptyState.jsx
```

Each `deviation/*Section` and `copilot/*` component is self-contained and
reads/writes Redux directly via `useSelector`/`useDispatch` — no prop
drilling of form data between sections.

---

## 4. Redux architecture

Single slice, `src/store/deviationSlice.js`, state shape:

```js
{
  source: { type, text, filename },
  extraction: { status, stage, data, missingInformation, error },
  deviationForm: { data, aiFields, editedFields, dirty },
  impactAssessment: { data, aiFields, editedFields },
  severity: { recommendation, final, finalEdited },
  ui: { saving, saveSuccess, saveError, deviationId, validationErrors },
}
```

`aiFields` / `editedFields` are what drive the "✨ AI extracted" vs "Edited
by user" provenance badges next to every field — this is how AI-generated
content stays visually distinct from user edits per the spec's
Human-in-the-Loop requirement (Section 23).

**Actions:** `setSourceType`, `setSourceText`, `setSourceFile`,
`startExtraction`, `setExtractionStage`, `extractionSuccess`,
`extractionFailure`, `updateDeviationField`, `updateImpactField`,
`setFinalSeverity`, `setValidationErrors`, `startSave`, `saveSuccess`,
`saveFailure`, `resetDeviation`.

**Thunks** (`src/store/thunks.js`, plain async functions — no
`createAsyncThunk` needed for two flows this size):
- `runAnalysis({ mode, text, sourceType, file })` — drives
  `extraction.status` through `processing → success/error`.
- `saveReviewedDeviation()` — validates, builds the exact Save API
  payload (`utils/buildSaveRecord.js`), and persists it. **Always sends
  the current Redux state, never the raw AI response** — this is what
  makes "AI result → database" (without review) structurally impossible,
  per Contract 7.

**Selectors** (`src/store/selectors.js`) keep components decoupled from
the exact state shape; e.g. `selectIsFormUnlocked` is the single source of
truth for the form-lock behavior described above.

---

## 5. Service layer / API contracts

`src/services/deviationApi.js` exposes exactly four functions and is the
**only** module that touches `fetch` or knows about mocking:

```js
analyzeText(text, sourceType, onStageChange)   → AiOutputSchema
analyzeFile(file, onStageChange)               → AiOutputSchema
saveDeviation(deviationRecord)                 → { deviation_id, message }
checkHealth()                                  → { status }
```

Request/response shapes match the spec's Implementation Contracts 1, 2 and
5 exactly:

```
POST /api/deviations/analyze         { source_type, text }
POST /api/deviations/analyze-file    multipart/form-data { file }
POST /api/deviations                 full reviewed deviation record
GET  /api/health
```

### Swapping mocks for the real FastAPI endpoints

1. Set `VITE_USE_MOCK_API=false` in `.env`.
2. Set `VITE_API_BASE_URL` to wherever FastAPI is running.
3. That's it — no component changes needed. `deviationApi.js` switches
   from `mockAiResponses.js` to real `fetch` calls automatically.

One behavioral note: the mock simulates the staged "Reading source →
Extracting → Assessing impact → Preparing severity" progress checklist
(`ANALYSIS_STAGES` in `deviationApi.js`) with client-side `setTimeout`s,
since a single mock call has no real intermediate steps to report. A
real LangGraph call is one request/response — `onStageChange` simply
won't fire, and `ProcessingState` will sit on the first stage with its
pulsing indicator until the response arrives. If you want genuine staged
progress from the real backend, the natural upgrade is a
Server-Sent-Events or WebSocket endpoint that emits stage names as
LangGraph nodes complete; `setExtractionStage` is already wired to accept
that with no other changes.

### Mock AI response format

Exactly the "Exact AI Output Schema" from the spec (Section 12):

```json
{
  "extraction": { "title": "string|null", "...": "..." },
  "impact_assessment": {
    "product_quality": { "level": "none|potential|confirmed|unknown", "reason": "string" },
    "...": "...",
    "overall_summary": "string"
  },
  "severity": {
    "recommended_level": "minor|major|critical|unknown",
    "confidence": "number|null",
    "reason": "string",
    "evidence": ["string"]
  },
  "missing_information": ["string"]
}
```

Two mock variants ship in `mockAiResponses.js`:
- **Rich** (triggered by pasted text/filename longer than 40 characters) —
  mostly-populated fields, `major` severity, realistic evidence.
- **Sparse** (short/empty input) — many `null` fields and `unknown`
  levels, so the "Not identified" / missing-information UI is reachable
  in the demo without needing a second contrived example.

To force the save-error state for a demo, save a deviation with `title`
containing `__forceerror` (case-insensitive) — this is mock-only and has
no effect once the real backend is connected.

---

## 6. States implemented

| Requirement            | Where |
|-------------------------|-------|
| Empty state              | Locked form placeholders + AI Copilot idle upload/paste view |
| Loading / processing     | `ProcessingState` — staged checklist, no fabricated percentage |
| AI extraction result     | `extractionSuccess` populates `deviationForm` + `impactAssessment` + `severity` in one dispatch |
| Editable AI fields       | Every field unlocks post-analysis; provenance badges track AI vs. edited |
| Impact assessment        | `ImpactSection` — level dropdown + reason per category, all editable |
| Severity recommendation  | `SeveritySection` — AI recommendation shown read-only; user picks the **final** severity |
| Validation                | `validators.js` — title, description, and final severity required before save |
| Save / success            | `SaveBar` + success banner with the returned `deviation_id` |
| Error (extraction)       | Inline banner in both the form and the Copilot panel, with retry via the same input |
| Error (save)              | Inline banner + save-bar status, form stays editable for another attempt |

---

## 7. What's deliberately out of scope

Per the spec's "MVP Scope vs Unnecessary Features": no auth, no user
management, no roles, no notifications, no audit/CAPA/investigation
modules, and — per the assignment's explicit instruction — **no Customer
Complaint module**. The reference demo video was used only to understand
the AI interaction pattern (staged loading, chat-style extraction
summary, human review before save), reproduced here for Deviations only.
