import { createSlice } from '@reduxjs/toolkit';
import { IDENTIFICATION_FIELDS, DETAILS_FIELDS, IMPACT_CATEGORIES } from '../types/deviation';

/**
 * A brand-new, empty deviation form. Every scalar starts as null (never
 * ""), matching the AI's own null convention — "unidentified" is a real
 * value, not the absence of one.
 */
function emptyFormData() {
  const data = {};
  [...IDENTIFICATION_FIELDS, ...DETAILS_FIELDS].forEach((f) => {
    data[f] = null;
  });
  data.reported_datetime = new Date().toISOString();
  return data;
}

function emptyImpactData() {
  const data = {};
  IMPACT_CATEGORIES.forEach(({ key }) => {
    data[key] = { level: 'unknown', reason: '' };
  });
  data.overall_summary = '';
  return data;
}

const initialState = {
  source: {
    type: null, // 'text' | 'email' | 'pdf' | 'txt' | null
    text: '',
    filename: null,
  },
  extraction: {
    status: 'idle', // idle | processing | success | error
    stage: null, // current staged-progress key while processing
    data: null,
    missingInformation: [],
    error: null,
  },
  deviationForm: {
    data: emptyFormData(),
    aiFields: [], // field names populated by the AI
    editedFields: [], // field names the user has since changed
    dirty: false,
  },
  impactAssessment: {
    data: emptyImpactData(),
    aiFields: [],
    editedFields: [],
  },
  severity: {
    recommendation: null, // the AI's original SeverityRecommendation object, untouched
    final: null, // 'minor' | 'major' | 'critical' | 'unknown' | null — the user's decision
    finalEdited: false,
  },
  ui: {
    saving: false,
    saveSuccess: false,
    saveError: null,
    deviationId: null,
    validationErrors: {},
  },
};

const deviationSlice = createSlice({
  name: 'deviation',
  initialState,
  reducers: {
    setSourceType(state, action) {
      state.source.type = action.payload;
    },
    setSourceText(state, action) {
      state.source.text = action.payload;
      state.source.filename = null;
      // A new source invalidates the previous AI result. The form remains
      // visible but becomes locked until this new source is analyzed.
      state.extraction.status = 'idle';
      state.extraction.data = null;
      state.extraction.stage = null;
      state.extraction.error = null;
      state.severity.recommendation = null;
      state.severity.final = null;
      state.severity.finalEdited = false;
      state.ui.saveSuccess = false;
      state.ui.saveError = null;
      state.ui.deviationId = null;
    },
    setSourceFile(state, action) {
      state.source.filename = action.payload?.name ?? null;
      state.source.text = '';
      // A new/removed file invalidates the previous AI result.
      state.extraction.status = 'idle';
      state.extraction.data = null;
      state.extraction.stage = null;
      state.extraction.error = null;
      state.severity.recommendation = null;
      state.severity.final = null;
      state.severity.finalEdited = false;
      state.ui.saveSuccess = false;
      state.ui.saveError = null;
      state.ui.deviationId = null;
    },
    startExtraction(state) {
      state.extraction.status = 'processing';
      state.extraction.stage = null;
      state.extraction.error = null;
      state.ui.saveSuccess = false;
      state.ui.saveError = null;
    },
    setExtractionStage(state, action) {
      state.extraction.stage = action.payload;
    },
    extractionSuccess(state, action) {
      const { extraction, impact_assessment, severity, missing_information } = action.payload;

      state.extraction.status = 'success';
      state.extraction.stage = null;
      state.extraction.data = extraction;
      state.extraction.missingInformation = missing_information || [];
      state.extraction.error = null;

      // Populate the form fresh from the AI result. This intentionally
      // replaces rather than merges — a new analysis represents a new
      // reviewed source, not an incremental patch (Contract 6/7).
      state.deviationForm.data = { ...state.deviationForm.data, ...extraction };
      state.deviationForm.aiFields = Object.keys(extraction).filter((k) => extraction[k] !== null);
      state.deviationForm.editedFields = [];
      state.deviationForm.dirty = false;

      state.impactAssessment.data = impact_assessment;
      state.impactAssessment.aiFields = Object.keys(impact_assessment);
      state.impactAssessment.editedFields = [];

      state.severity.recommendation = severity;
      state.severity.final = severity.recommended_level;
      state.severity.finalEdited = false;
    },
    extractionFailure(state, action) {
      state.extraction.status = 'error';
      state.extraction.stage = null;
      state.extraction.error = action.payload;
    },
    updateDeviationField(state, action) {
      const { field, value } = action.payload;
      state.deviationForm.data[field] = value;
      state.deviationForm.dirty = true;
      if (!state.deviationForm.editedFields.includes(field)) {
        state.deviationForm.editedFields.push(field);
      }
      if (state.ui.validationErrors[field]) {
        delete state.ui.validationErrors[field];
      }
    },
    updateImpactField(state, action) {
      const { category, field, value } = action.payload;
      if (category === 'overall_summary') {
        state.impactAssessment.data.overall_summary = value;
      } else {
        state.impactAssessment.data[category][field] = value;
      }
      const key = category === 'overall_summary' ? 'overall_summary' : category;
      if (!state.impactAssessment.editedFields.includes(key)) {
        state.impactAssessment.editedFields.push(key);
      }
    },
    setFinalSeverity(state, action) {
      state.severity.final = action.payload;
      state.severity.finalEdited = state.severity.recommendation
        ? action.payload !== state.severity.recommendation.recommended_level
        : false;
    },
    setValidationErrors(state, action) {
      state.ui.validationErrors = action.payload;
    },
    startSave(state) {
      state.ui.saving = true;
      state.ui.saveSuccess = false;
      state.ui.saveError = null;
    },
    saveSuccess(state, action) {
      state.ui.saving = false;
      state.ui.saveSuccess = true;
      state.ui.saveError = null;
      state.ui.deviationId = action.payload.deviation_id;
      state.deviationForm.dirty = false;
    },
    saveFailure(state, action) {
      state.ui.saving = false;
      state.ui.saveSuccess = false;
      state.ui.saveError = action.payload;
    },
    resetDeviation() {
      return initialState;
    },
  },
});

export const {
  setSourceType,
  setSourceText,
  setSourceFile,
  startExtraction,
  setExtractionStage,
  extractionSuccess,
  extractionFailure,
  updateDeviationField,
  updateImpactField,
  setFinalSeverity,
  setValidationErrors,
  startSave,
  saveSuccess,
  saveFailure,
  resetDeviation,
} = deviationSlice.actions;

export default deviationSlice.reducer;
