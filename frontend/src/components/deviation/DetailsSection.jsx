import { useDispatch, useSelector } from 'react-redux';
import FieldInput from '../common/FieldInput';
import { selectDeviationForm, selectUi } from '../../store/selectors';
import { updateDeviationField } from '../../store/deviationSlice';
import { FIELD_LABELS } from '../../types/deviation';

function provenanceOf(form, name) {
  if (form.editedFields.includes(name)) return 'edited';
  if (form.aiFields.includes(name)) return 'ai';
  return 'none';
}

export default function DetailsSection({ locked }) {
  const dispatch = useDispatch();
  const form = useSelector(selectDeviationForm);
  const { data } = form;
  const ui = useSelector(selectUi);

  const field = (name, type = 'text', span) => (
    <FieldInput
      name={name}
      label={FIELD_LABELS[name]}
      value={data[name]}
      type={type}
      span={span}
      locked={locked}
      provenance={provenanceOf(form, name)}
      error={ui.validationErrors[name]}
      onChange={(value) => dispatch(updateDeviationField({ field: name, value }))}
    />
  );

  return (
    <div className="section-card">
      <div className="section-card__title">2. Deviation Details</div>
      <div className="section-card__subtitle">What happened, and how it compares to the approved process.</div>
      <div className="form-grid">
        {field('description', 'textarea', 'full')}
        {field('expected_condition', 'textarea')}
        {field('actual_condition', 'textarea')}
        {field('process_parameter')}
        {field('expected_value')}
        {field('actual_value')}
        {field('immediate_action', 'textarea', 'full')}
      </div>
    </div>
  );
}
