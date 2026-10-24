import { useDispatch, useSelector } from 'react-redux';
import { selectImpactAssessment } from '../../store/selectors';
import { updateImpactField } from '../../store/deviationSlice';
import { ProvenanceBadge, ImpactLevelBadge } from '../common/Badge';
import { IMPACT_CATEGORIES, IMPACT_LEVELS } from '../../types/deviation';

export default function ImpactSection({ locked }) {
  const dispatch = useDispatch();
  const { data, aiFields, editedFields } = useSelector(selectImpactAssessment);

  const provenanceOf = (key) => (editedFields.includes(key) ? 'edited' : aiFields.includes(key) ? 'ai' : 'none');

  if (locked) {
    return (
      <div className="section-card">
        <div className="section-card__title">3. Impact Assessment</div>
        <div className="section-card__subtitle">Populated by the AI Copilot after analysis.</div>
        <div className="field__placeholder">Not yet analyzed</div>
      </div>
    );
  }

  return (
    <div className="section-card">
      <div className="section-card__title">3. Impact Assessment</div>
      <div className="section-card__subtitle">Review each category — the AI flags a level and a short reason for each.</div>

      {IMPACT_CATEGORIES.map(({ key, label }) => {
        const category = data[key];
        return (
          <div className="impact-category" key={key}>
            <div className="impact-category__head">
              <span className="impact-category__title">{label}</span>
              <ProvenanceBadge provenance={provenanceOf(key)} />
            </div>
            <div className="field" style={{ marginBottom: 8 }}>
              <select
                className="field__select"
                value={category.level}
                onChange={(e) => dispatch(updateImpactField({ category: key, field: 'level', value: e.target.value }))}
              >
                {IMPACT_LEVELS.map((lvl) => (
                  <option key={lvl} value={lvl}>
                    {lvl.charAt(0).toUpperCase() + lvl.slice(1)}
                  </option>
                ))}
              </select>
            </div>
            <textarea
              className="field__textarea"
              value={category.reason}
              placeholder="Reason not identified — enter manually"
              onChange={(e) => dispatch(updateImpactField({ category: key, field: 'reason', value: e.target.value }))}
            />
            <div style={{ marginTop: 8 }}>
              <ImpactLevelBadge level={category.level} />
            </div>
          </div>
        );
      })}

      <div className="field">
        <div className="field__label-row">
          <span className="field__label">Overall Impact Summary</span>
          <ProvenanceBadge provenance={provenanceOf('overall_summary')} />
        </div>
        <textarea
          className="field__textarea"
          value={data.overall_summary}
          placeholder="Not identified — enter manually"
          onChange={(e) => dispatch(updateImpactField({ category: 'overall_summary', field: null, value: e.target.value }))}
        />
      </div>
    </div>
  );
}
