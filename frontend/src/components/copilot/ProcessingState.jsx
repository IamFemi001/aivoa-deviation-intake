import { useSelector } from 'react-redux';
import { selectExtraction } from '../../store/selectors';
import { ANALYSIS_STAGES } from '../../services/deviationApi';

export default function ProcessingState() {
  const extraction = useSelector(selectExtraction);
  const currentIndex = ANALYSIS_STAGES.findIndex((s) => s.key === extraction.stage);

  return (
    <div>
      <p style={{ fontSize: 13, color: 'var(--ink-soft)', marginBottom: 14 }}>Analyzing deviation…</p>
      <ul className="processing-list">
        {ANALYSIS_STAGES.map((stage, i) => {
          const done = currentIndex > i || (currentIndex === -1 && false);
          const active = currentIndex === i;
          return (
            <li
              key={stage.key}
              className={`processing-list__item ${done ? 'processing-list__item--done' : ''} ${
                active ? 'processing-list__item--active' : ''
              }`}
            >
              <span className={`processing-icon ${done ? 'processing-icon--done' : ''} ${active ? 'processing-icon--active' : ''}`}>
                {done ? '✓' : active ? '●' : '○'}
              </span>
              {stage.label}
            </li>
          );
        })}
      </ul>
      <p style={{ fontSize: 11.5, color: 'var(--ink-faint)', marginTop: 16 }}>
        This may take a few moments. AI responses may contain errors — you'll review everything before saving.
      </p>
    </div>
  );
}
