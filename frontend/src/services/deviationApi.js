/**
 * Deviation API service layer.
 *
 * This is the ONLY module that knows whether it's talking to the mock
 * pipeline or the real FastAPI backend. Components and Redux thunks call
 * these functions and never touch fetch/axios or the mock data directly —
 * see the "Swapping mocks for the real API" section in README.md.
 *
 * API contracts implemented here (Section 16 / Implementation Contracts
 * 1, 2 and 5 of the spec):
 *   POST /api/deviations/analyze        { source_type, text }
 *   POST /api/deviations/analyze-file   multipart/form-data { file }
 *   POST /api/deviations                full reviewed deviation record
 *   GET  /api/health
 */

import { pickMockResponse, MOCK_ANALYZE_DELAY_MS, MOCK_SAVE_DELAY_MS, nextMockDeviationId } from './mockAiResponses';

const USE_MOCK = import.meta.env.VITE_USE_MOCK_API === 'true';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * The four stages surfaced in the UI while an analysis is running,
 * matching Section 21 ("Loading-State Strategy") — a checklist of real
 * stages, never a fabricated percentage.
 */
export const ANALYSIS_STAGES = [
  { key: 'reading', label: 'Reading source' },
  { key: 'extracting', label: 'Extracting deviation details' },
  { key: 'impact', label: 'Assessing potential impact' },
  { key: 'severity', label: 'Preparing severity recommendation' },
];

class ApiError extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
  }
}

async function parseErrorResponse(response) {
  try {
    const body = await response.json();
    if (body && body.error) {
      return new ApiError(body.error.code || 'UNKNOWN_ERROR', body.error.message || 'The request failed.');
    }
  } catch (_) {
    // response wasn't JSON — fall through to a generic error
  }
  return new ApiError('UNKNOWN_ERROR', `Request failed with status ${response.status}.`);
}

/**
 * Analyze pasted text or email content.
 * @param {string} text
 * @param {'text'|'email'} sourceType
 * @param {(stageKey: string) => void} [onStageChange] called as each stage begins (mock only — see README)
 * @returns {Promise<import('../types/deviation').AiOutputSchema>}
 */
export async function analyzeText(text, sourceType = 'text', onStageChange) {
  if (!text || !text.trim()) {
    throw new ApiError('EMPTY_SOURCE', 'Paste some deviation text or an email before analyzing.');
  }

  if (USE_MOCK) {
    return mockAnalyze(() => pickMockResponse(text), onStageChange);
  }

  const response = await fetch(`${API_BASE_URL}/api/deviations/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source_type: sourceType, text }),
  });
  if (!response.ok) throw await parseErrorResponse(response);
  const body = await response.json();
  return body.data;
}

/**
 * Analyze an uploaded deviation document (PDF/TXT for the MVP).
 * @param {File} file
 * @param {(stageKey: string) => void} [onStageChange]
 * @returns {Promise<import('../types/deviation').AiOutputSchema>}
 */
export async function analyzeFile(file, onStageChange) {
  if (!file) {
    throw new ApiError('INVALID_FILE', 'No file was provided.');
  }
  if (!/\.(pdf|txt)$/i.test(file.name)) {
    throw new ApiError('UNSUPPORTED_FILE_TYPE', 'Only PDF and TXT files are supported.');
  }

  if (USE_MOCK) {
    return mockAnalyze(() => pickMockResponse(file.name), onStageChange);
  }

  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch(`${API_BASE_URL}/api/deviations/analyze-file`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) throw await parseErrorResponse(response);
  const body = await response.json();
  return body.data;
}

/**
 * Persist the user-reviewed deviation record.
 * @param {object} deviationRecord — matches Contract 5 ("Save API") exactly
 * @returns {Promise<{deviation_id: string, message: string}>}
 */
export async function saveDeviation(deviationRecord) {
  if (USE_MOCK) {
    await wait(MOCK_SAVE_DELAY_MS);
    // Simulate an occasional server error only for an explicit "trigger" title,
    // so error states are reachable in the demo without being flaky otherwise.
    if ((deviationRecord.title || '').toLowerCase().includes('__forceerror')) {
      throw new ApiError('DATABASE_ERROR', 'The deviation could not be saved. Please try again.');
    }
    return { deviation_id: nextMockDeviationId(), message: 'Deviation saved successfully' };
  }

  const response = await fetch(`${API_BASE_URL}/api/deviations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(deviationRecord),
  });
  if (!response.ok) throw await parseErrorResponse(response);
  const body = await response.json();
  return { deviation_id: body.deviation_id, message: body.message };
}

export async function checkHealth() {
  if (USE_MOCK) return { status: 'ok (mock)' };
  const response = await fetch(`${API_BASE_URL}/api/health`);
  if (!response.ok) throw await parseErrorResponse(response);
  return response.json();
}

// ---- internal helpers -------------------------------------------------

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Drives the mock through the same staged progression a real
 * LangGraph run would report, then resolves with the mock payload.
 * When the real backend is connected this entire function disappears —
 * onStageChange simply won't be called (see README), and the UI falls
 * back to a single indeterminate "Analyzing..." state.
 */
async function mockAnalyze(buildResponse, onStageChange) {
  const perStage = MOCK_ANALYZE_DELAY_MS / ANALYSIS_STAGES.length;
  for (const stage of ANALYSIS_STAGES) {
    onStageChange?.(stage.key);
    await wait(perStage);
  }
  return buildResponse();
}

export { ApiError };
