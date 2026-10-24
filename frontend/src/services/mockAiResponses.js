/**
 * Mock responses for the two /analyze endpoints.
 *
 * These exist purely so the frontend can be built, demoed, and reviewed
 * before the real FastAPI + LangGraph + Groq pipeline exists. Every
 * response conforms exactly to Section 12 ("Exact AI Output Schema") of
 * the technical spec, including deliberate nulls, so the UI's
 * missing-information handling is exercised honestly rather than against
 * best-case data.
 */

const now = () => new Date().toISOString();

/** A "good" extraction — most fields identified, one missing. */
function richMockResponse(rawText) {
  return {
    extraction: {
      title: 'Process Parameter Excursion — Batch API-2026-014',
      event_datetime: '2026-09-24T03:15:00Z',
      reported_datetime: now(),
      department: 'API Manufacturing',
      manufacturing_stage: 'Crystallization',
      batch_number: 'API-2026-014',
      description:
        rawText && rawText.length > 0
          ? 'Operator noted that the crystallizer temperature exceeded the approved upper limit during the hold step, as described in the submitted source text.'
          : 'Crystallizer temperature exceeded the approved upper limit during the hold step.',
      expected_condition: 'Crystallizer temperature held at 18-22°C during the hold step.',
      actual_condition: 'Crystallizer temperature reached 27°C for approximately 40 minutes.',
      process_parameter: 'Crystallizer hold temperature',
      expected_value: '18-22°C',
      actual_value: '27°C',
      immediate_action: 'Batch quarantined; QA notified; crystallizer cooling circuit inspected.',
    },
    impact_assessment: {
      product_quality: {
        level: 'potential',
        reason: 'Elevated hold temperature may affect crystal size distribution and purity.',
      },
      patient_safety: {
        level: 'none',
        reason: 'No evidence of a patient-facing safety concern at this stage of manufacturing.',
      },
      process: {
        level: 'confirmed',
        reason: 'The hold temperature confirmedly exceeded the approved process range.',
      },
      regulatory: {
        level: 'potential',
        reason: 'An out-of-range process parameter may require regulatory notification depending on batch disposition.',
      },
      data_integrity: {
        level: 'none',
        reason: 'No indication of missing, altered, or inconsistent records.',
      },
      batch_product: {
        level: 'potential',
        reason: 'Batch API-2026-014 may require additional quality review before release.',
      },
      overall_summary:
        'A confirmed process excursion during crystallization with potential downstream effects on product quality and batch disposition; no patient safety or data integrity signal identified.',
    },
    severity: {
      recommended_level: 'major',
      confidence: 0.78,
      reason:
        'The process parameter exceeded its approved range during manufacturing and may affect the quality of the affected batch.',
      evidence: [
        'Actual hold temperature (27°C) exceeded the approved range (18-22°C)',
        'Deviation occurred during an active manufacturing stage (crystallization)',
        'Batch was quarantined pending quality review',
      ],
    },
    missing_information: ['Exact duration of the temperature excursion beyond "approximately 40 minutes"'],
  };
}

/** A "thin" extraction — simulates a sparse source document with several nulls. */
function sparseMockResponse() {
  return {
    extraction: {
      title: 'Deviation Reported — Details Pending Review',
      event_datetime: null,
      reported_datetime: now(),
      department: null,
      manufacturing_stage: null,
      batch_number: null,
      description: 'An unspecified deviation was reported; the source text did not include enough detail for full extraction.',
      expected_condition: null,
      actual_condition: null,
      process_parameter: null,
      expected_value: null,
      actual_value: null,
      immediate_action: null,
    },
    impact_assessment: {
      product_quality: { level: 'unknown', reason: 'Insufficient information to assess product quality impact.' },
      patient_safety: { level: 'unknown', reason: 'Insufficient information to assess patient safety impact.' },
      process: { level: 'unknown', reason: 'Insufficient information to assess process impact.' },
      regulatory: { level: 'unknown', reason: 'Insufficient information to assess regulatory impact.' },
      data_integrity: { level: 'unknown', reason: 'Insufficient information to assess data integrity impact.' },
      batch_product: { level: 'unknown', reason: 'Insufficient information to assess batch/product impact.' },
      overall_summary: 'The supplied source did not contain enough detail for a confident impact assessment.',
    },
    severity: {
      recommended_level: 'unknown',
      confidence: null,
      reason: 'Insufficient evidence in the supplied source to recommend a severity level with confidence.',
      evidence: [],
    },
    missing_information: [
      'Batch/Lot Number',
      'Exact event time',
      'Department/Area',
      'Process parameter and expected/actual values',
    ],
  };
}

/**
 * Chooses a mock response deterministically from the input so the demo is
 * reproducible: short/empty input yields the sparse response (exercising
 * the "unidentified" / missing-information UI), longer input yields the
 * rich one.
 */
export function pickMockResponse(sourceText) {
  const length = (sourceText || '').trim().length;
  return length > 40 ? richMockResponse(sourceText) : sparseMockResponse();
}

export const MOCK_ANALYZE_DELAY_MS = 2200;

export const MOCK_SAVE_DELAY_MS = 700;

let mockIdCounter = 1;
export function nextMockDeviationId() {
  const id = `DEV-2026-${String(mockIdCounter).padStart(4, '0')}`;
  mockIdCounter += 1;
  return id;
}
