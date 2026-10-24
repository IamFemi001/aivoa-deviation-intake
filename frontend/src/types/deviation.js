/**
 * Shared type definitions (JSDoc only — the project is plain JS).
 * These mirror the "Exact AI Output Schema" and "Save API" contracts
 * in the technical spec, so the frontend never invents its own shape.
 */

/**
 * @typedef {'none'|'potential'|'confirmed'|'unknown'} ImpactLevel
 * @typedef {'minor'|'major'|'critical'|'unknown'} SeverityLevel
 * @typedef {'text'|'email'|'pdf'|'txt'|null} SourceType
 * @typedef {'idle'|'processing'|'success'|'error'} AsyncStatus
 */

/**
 * @typedef {Object} ExtractionFields
 * @property {string|null} title
 * @property {string|null} event_datetime
 * @property {string|null} reported_datetime
 * @property {string|null} department
 * @property {string|null} manufacturing_stage
 * @property {string|null} batch_number
 * @property {string|null} description
 * @property {string|null} expected_condition
 * @property {string|null} actual_condition
 * @property {string|null} process_parameter
 * @property {string|null} expected_value
 * @property {string|null} actual_value
 * @property {string|null} immediate_action
 */

/**
 * @typedef {Object} ImpactCategory
 * @property {ImpactLevel} level
 * @property {string} reason
 */

/**
 * @typedef {Object} ImpactAssessment
 * @property {ImpactCategory} product_quality
 * @property {ImpactCategory} patient_safety
 * @property {ImpactCategory} process
 * @property {ImpactCategory} regulatory
 * @property {ImpactCategory} data_integrity
 * @property {ImpactCategory} batch_product
 * @property {string} overall_summary
 */

/**
 * @typedef {Object} SeverityRecommendation
 * @property {SeverityLevel} recommended_level
 * @property {number|null} confidence
 * @property {string} reason
 * @property {string[]} evidence
 */

/**
 * @typedef {Object} AiOutputSchema
 * @property {ExtractionFields} extraction
 * @property {ImpactAssessment} impact_assessment
 * @property {SeverityRecommendation} severity
 * @property {string[]} missing_information
 */

/** The exact set of AI-generated / editable scalar fields on the form (Section 5/6/7). */
export const IDENTIFICATION_FIELDS = [
  'title',
  'event_datetime',
  'reported_datetime',
  'department',
  'manufacturing_stage',
  'batch_number',
];

export const DETAILS_FIELDS = [
  'description',
  'expected_condition',
  'actual_condition',
  'process_parameter',
  'expected_value',
  'actual_value',
  'immediate_action',
];

export const IMPACT_CATEGORIES = [
  { key: 'product_quality', label: 'Product Quality' },
  { key: 'patient_safety', label: 'Patient Safety' },
  { key: 'process', label: 'Process' },
  { key: 'regulatory', label: 'Regulatory' },
  { key: 'data_integrity', label: 'Data Integrity' },
  { key: 'batch_product', label: 'Batch / Product' },
];

export const IMPACT_LEVELS = ['none', 'potential', 'confirmed', 'unknown'];
export const SEVERITY_LEVELS = ['minor', 'major', 'critical', 'unknown'];

export const FIELD_LABELS = {
  title: 'Deviation Title',
  event_datetime: 'Date/Time of Event',
  reported_datetime: 'Date Reported',
  department: 'Department / Area',
  manufacturing_stage: 'Manufacturing Stage',
  batch_number: 'Batch / Lot Number',
  description: 'Description',
  expected_condition: 'Expected / Approved Condition',
  actual_condition: 'Actual Condition',
  process_parameter: 'Process Parameter',
  expected_value: 'Expected Value / Range',
  actual_value: 'Actual Value',
  immediate_action: 'Immediate Action Taken',
};
