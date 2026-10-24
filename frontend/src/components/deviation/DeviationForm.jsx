import { useSelector } from 'react-redux';
import IdentificationSection from './IdentificationSection';
import DetailsSection from './DetailsSection';
import ImpactSection from './ImpactSection';
import SeveritySection from './SeveritySection';
import { selectExtraction, selectIsFormUnlocked, selectUi } from '../../store/selectors';

export default function DeviationForm() {
  const extraction = useSelector(selectExtraction);
  const isUnlocked = useSelector(selectIsFormUnlocked);
  const ui = useSelector(selectUi);
  const locked = !isUnlocked;

  return (
    <div>
      <div className="page-heading">
        <div className="page-heading__text">
          <h1>Log Deviation</h1>
          <p>Record any unexpected event, out-of-specification result, or non-conformance.</p>
        </div>
        {ui.saveSuccess ? (
          <span className="badge badge--success">Saved</span>
        ) : (
          <span className="badge badge--draft">Draft</span>
        )}
      </div>

      {locked && extraction.status === 'idle' && (
        <div className="banner banner--info">
          <span>💡</span>
          <span>
            This form fills itself in. Upload a deviation document or paste the deviation text/email in the AI
            Copilot panel, then click <strong>Analyze</strong> — the fields below will populate automatically for
            your review.
          </span>
        </div>
      )}

      {extraction.status === 'error' && (
        <div className="banner banner--error">
          <span>⚠️</span>
          <span>{extraction.error?.message}</span>
        </div>
      )}

      {ui.saveSuccess && ui.deviationId && (
        <div className="banner banner--success">
          <span>✅</span>
          <span>
            Deviation saved as <strong>{ui.deviationId}</strong>. Click Reset Form to log another deviation.
          </span>
        </div>
      )}

      {ui.saveError && (
        <div className="banner banner--error">
          <span>⚠️</span>
          <span>{ui.saveError.message}</span>
        </div>
      )}

      <IdentificationSection locked={locked} />
      <DetailsSection locked={locked} />
      <ImpactSection locked={locked} />
      <SeveritySection locked={locked} />
    </div>
  );
}
