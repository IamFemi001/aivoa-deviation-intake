/**
 * Maps Redux state to the exact "Save API" request body (Contract 5).
 * This is the one place that assembles the outgoing save payload, so the
 * shape can't drift between components.
 */
export function buildSaveRecord(deviationState) {
  const { data } = deviationState.deviationForm;
  const { source } = deviationState;

  return {
    title: data.title,
    event_datetime: data.event_datetime,
    reported_datetime: data.reported_datetime,
    department: data.department,
    manufacturing_stage: data.manufacturing_stage,
    batch_number: data.batch_number,
    description: data.description,
    expected_condition: data.expected_condition,
    actual_condition: data.actual_condition,
    process_parameter: data.process_parameter,
    expected_value: data.expected_value,
    actual_value: data.actual_value,
    immediate_action: data.immediate_action,
    impact_assessment: deviationState.impactAssessment.data,
    final_severity: deviationState.severity.final,
    source_type: source.type,
    source_filename: source.filename,
  };
}
