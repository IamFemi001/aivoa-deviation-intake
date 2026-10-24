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

export default function IdentificationSection({ locked }) {
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
      <div className="section-card__title">1. Deviation Identification</div>
      <div className="section-card__subtitle">Who, where, and when the deviation occurred.</div>
      <div className="form-grid">
        {field('title', 'text', 'full')}
        {field('event_datetime', 'datetime')}
        {field('reported_datetime', 'datetime')}
        {field('department')}
        {field('manufacturing_stage')}
        {field('batch_number')}
      </div>
    </div>
  );
}
