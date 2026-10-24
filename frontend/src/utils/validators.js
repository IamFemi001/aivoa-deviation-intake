/**
 * Minimum bar for saving a deviation. Kept deliberately small — the spec's
 * MVP scope favors a reliable end-to-end flow over exhaustive validation,
 * and the AI is explicitly allowed to leave fields null/unidentified.
 */
export function validateForSave(deviationState) {
  const errors = {};
  const { data } = deviationState.deviationForm;

  if (!data.title || !data.title.trim()) {
    errors.title = 'A deviation title is required before saving.';
  }
  if (!data.description || !data.description.trim()) {
    errors.description = 'A description is required before saving.';
  }
  if (!deviationState.severity.final) {
    errors.final_severity = 'Choose a final severity before saving.';
  }

  return errors;
}
