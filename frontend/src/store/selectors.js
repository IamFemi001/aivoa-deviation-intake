export const selectSource = (state) => state.deviation.source;
export const selectExtraction = (state) => state.deviation.extraction;
export const selectDeviationForm = (state) => state.deviation.deviationForm;
export const selectImpactAssessment = (state) => state.deviation.impactAssessment;
export const selectSeverity = (state) => state.deviation.severity;
export const selectUi = (state) => state.deviation.ui;

export const selectIsFormUnlocked = (state) =>
  state.deviation.extraction.status === 'success';

export const selectFieldProvenance = (state, field) => {
  const { aiFields, editedFields } = state.deviation.deviationForm;
  if (editedFields.includes(field)) return 'edited';
  if (aiFields.includes(field)) return 'ai';
  return 'none';
};

export const selectImpactFieldProvenance = (state, category) => {
  const { aiFields, editedFields } = state.deviation.impactAssessment;
  if (editedFields.includes(category)) return 'edited';
  if (aiFields.includes(category)) return 'ai';
  return 'none';
};
