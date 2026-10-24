import { useSelector } from 'react-redux';
import { selectExtraction, selectSeverity, selectImpactAssessment } from '../../store/selectors';
import { SeverityBadge, ImpactLevelBadge } from '../common/Badge';
import { FIELD_LABELS, IMPACT_CATEGORIES } from '../../types/deviation';

export default function ExtractionSummary() {
  const extraction = useSelector(selectExtraction);
  const { recommendation } = useSelector(selectSeverity);
  const impact = useSelector(selectImpactAssessment);

  const identifiedFields = Object.entries(extraction.data || {})
    .filter(([, value]) => value !== null)
    .map(([key]) => FIELD_LABELS[key])
    .filter(Boolean);

  return (
    <div>
      <p className="extraction-summary__intro">
        I've analyzed the deviation report and applied the results to the form on the left for your review.
      </p>

      {identifiedFields.length > 0 && (
        <ul className="checklist">
          {identifiedFields.map((label) => (
            <li className="checklist__item" key={label}>
              <span className="checklist__mark">✓</span> {label}
            </li>
          ))}
        </ul>
      )}

      {extraction.missingInformation.length > 0 && (
        <div className="missing-info">
          <div className="missing-info__title">⚠ Missing information</div>
          <ul className="missing-info__list">
            {extraction.missingInformation.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {recommendation && (
        <div className="severity-callout">
          <div className="severity-callout__label">Recommended severity</div>
          <SeverityBadge level={recommendation.recommended_level} />
          <div className="severity-callout__reason">{recommendation.reason}</div>
        </div>
      )}

      <div className="impact-preview">
        {IMPACT_CATEGORIES.map(({ key, label }) => (
          <div className="impact-preview__row" key={key}>
            <span className="impact-preview__label">{label}</span>
            <ImpactLevelBadge level={impact.data[key].level} />
          </div>
        ))}
      </div>

      <p className="apply-note">Edit anything in the form — corrections and additions are expected.</p>
    </div>
  );
}
