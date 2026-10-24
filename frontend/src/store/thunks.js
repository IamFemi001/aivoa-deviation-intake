import {
  startExtraction,
  setExtractionStage,
  extractionSuccess,
  extractionFailure,
  startSave,
  saveSuccess,
  saveFailure,
  setValidationErrors,
} from './deviationSlice';
import { analyzeText, analyzeFile, saveDeviation } from '../services/deviationApi';
import { buildSaveRecord } from '../utils/buildSaveRecord';
import { validateForSave } from '../utils/validators';

/**
 * Runs analysis for whichever source the user provided (pasted text/email
 * or an uploaded file) and drives the extraction slice through its
 * processing -> success/error lifecycle.
 */
export function runAnalysis({ mode, text, sourceType, file }) {
  return async function (dispatch) {
    dispatch(startExtraction());
    try {
      const onStageChange = (stage) => dispatch(setExtractionStage(stage));
      const result =
        mode === 'file' ? await analyzeFile(file, onStageChange) : await analyzeText(text, sourceType, onStageChange);
      dispatch(extractionSuccess(result));
    } catch (err) {
      dispatch(
        extractionFailure({
          code: err.code || 'AI_PROCESSING_FAILED',
          message: err.message || 'The deviation could not be analyzed. Please try again.',
        })
      );
    }
  };
}

/**
 * Validates, then saves the user-reviewed deviation. Never sends the raw
 * AI output directly — always the current (possibly edited) Redux state,
 * per the Human Review Rule (Contract 7).
 */
export function saveReviewedDeviation() {
  return async function (dispatch, getState) {
    const state = getState().deviation;
    const errors = validateForSave(state);
    if (Object.keys(errors).length > 0) {
      dispatch(setValidationErrors(errors));
      return;
    }
    dispatch(setValidationErrors({}));
    dispatch(startSave());
    try {
      const record = buildSaveRecord(state);
      const result = await saveDeviation(record);
      dispatch(saveSuccess(result));
    } catch (err) {
      dispatch(
        saveFailure({
          code: err.code || 'DATABASE_ERROR',
          message: err.message || 'The deviation could not be saved. Please try again.',
        })
      );
    }
  };
}
