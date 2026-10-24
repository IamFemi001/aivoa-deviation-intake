import { useSelector } from 'react-redux';
import { selectExtraction } from '../../store/selectors';
import SourceInputPanel from './SourceInputPanel';
import ProcessingState from './ProcessingState';
import ExtractionSummary from './ExtractionSummary';

export default function AICopilot() {
  const extraction = useSelector(selectExtraction);

  return (
    <div className="copilot">
      <div className="copilot__header">
        <div className="copilot__header-title">✨ AI Deviation Assistant</div>
        <span className="badge" style={{ background: '#fff', color: 'var(--ai)', border: '1px solid var(--ai-border)' }}>
          BETA
        </span>
      </div>

      <div className="copilot__body">
        {extraction.status === 'idle' && <SourceInputPanel />}

        {extraction.status === 'processing' && <ProcessingState />}

        {extraction.status === 'error' && (
          <>
            <div className="banner banner--error">
              <span>⚠️</span>
              <span>{extraction.error?.message}</span>
            </div>
            <SourceInputPanel />
          </>
        )}

        {extraction.status === 'success' && <ExtractionSummary />}
      </div>

      <div className="copilot-chat-hint">AI responses may contain errors. Please verify information.</div>
    </div>
  );
}
