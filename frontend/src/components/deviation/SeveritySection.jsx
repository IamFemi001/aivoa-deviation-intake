import { useDispatch, useSelector } from 'react-redux';
import { selectSeverity, selectUi } from '../../store/selectors';
import { setFinalSeverity } from '../../store/deviationSlice';
import { SeverityBadge } from '../common/Badge';
import { SEVERITY_LEVELS } from '../../types/deviation';

export default function SeveritySection({ locked }) {
  const dispatch = useDispatch();
  const { recommendation, final, finalEdited } = useSelector(selectSeverity);
  const ui = useSelector(selectUi);

  if (locked) {
    return (
      <div className="section-card">
        <div className="section-card__title">4. Severity</div>
        <div className="section-card__subtitle">The AI's recommendation appears here after analysis.</div>
        <div className="field__placeholder">Not yet analyzed</div>
      </div>
    );
  }

  return (
    <div className="section-card">
      <div className="section-card__title">4. Severity</div>
      <div className="section-card__subtitle">The AI recommends a starting point — the final decision is yours.</div>

      {recommendation && (
        <div className="severity-callout">
          <div className="severity-callout__label">✨ AI-recommended severity</div>
          <SeverityBadge level={recommendation.recommended_level} />
          <div className="severity-callout__reason">{recommendation.reason}</div>
          {recommendation.evidence?.length > 0 && (
            <ul className="severity-callout__evidence">
              {recommendation.evidence.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          )}
          {recommendation.confidence != null && (
            <div className="severity-callout__reason" style={{ color: 'var(--ink-faint)' }}>
              Model confidence: {Math.round(recommendation.confidence * 100)}%
            </div>
          )}
        </div>
      )}

      <div className="field">
        <div className="field__label-row">
          <span className="field__label">Final Severity</span>
          {finalEdited && <span className="badge badge--edited">Edited by user</span>}
        </div>
        <div className="severity-options">
          {SEVERITY_LEVELS.map((lvl) => (
            <button
              key={lvl}
              type="button"
              className={`severity-option ${final === lvl ? `severity-option--selected-${lvl}` : ''}`}
              onClick={() => dispatch(setFinalSeverity(lvl))}
            >
              {lvl.charAt(0).toUpperCase() + lvl.slice(1)}
            </button>
          ))}
        </div>
        {ui.validationErrors.final_severity && <span className="field__error">{ui.validationErrors.final_severity}</span>}
        <div className="severity-recommendation-note">
          This is the severity that will be saved to the deviation record.
        </div>
      </div>
    </div>
  );
}
