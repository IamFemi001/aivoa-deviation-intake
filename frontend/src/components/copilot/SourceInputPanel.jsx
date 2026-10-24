import { useRef, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { selectSource } from '../../store/selectors';
import { setSourceType, setSourceText, setSourceFile } from '../../store/deviationSlice';
import { runAnalysis } from '../../store/thunks';

const MAX_FILE_MB = 10;

export default function SourceInputPanel() {
  const dispatch = useDispatch();
  const source = useSelector(selectSource);
  const [mode, setMode] = useState('paste'); // 'paste' | 'upload'
  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [fileError, setFileError] = useState(null);
  const inputRef = useRef(null);

  const acceptFile = (candidate) => {
    setFileError(null);
    if (!candidate) return;
    const isPdfOrTxt = /\.(pdf|txt)$/i.test(candidate.name);
    if (!isPdfOrTxt) {
      setFileError('Only PDF and TXT files are supported.');
      return;
    }
    if (candidate.size > MAX_FILE_MB * 1024 * 1024) {
      setFileError(`File is larger than ${MAX_FILE_MB}MB.`);
      return;
    }
    setFile(candidate);
    dispatch(setSourceFile(candidate));
    dispatch(setSourceType(/\.pdf$/i.test(candidate.name) ? 'pdf' : 'txt'));
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    acceptFile(e.dataTransfer.files?.[0]);
  };

  const handleAnalyze = () => {
    if (mode === 'upload') {
      dispatch(runAnalysis({ mode: 'file', file }));
    } else {
      dispatch(setSourceType('text'));
      dispatch(runAnalysis({ mode: 'text', text: source.text, sourceType: 'text' }));
    }
  };

  const canAnalyze = mode === 'upload' ? !!file && !fileError : source.text.trim().length > 0;

  return (
    <div>
      <div className="source-tabs">
        <button
          className={`source-tabs__tab ${mode === 'upload' ? 'source-tabs__tab--active' : ''}`}
          onClick={() => setMode('upload')}
        >
          Upload document
        </button>
        <button
          className={`source-tabs__tab ${mode === 'paste' ? 'source-tabs__tab--active' : ''}`}
          onClick={() => setMode('paste')}
        >
          Paste text / email
        </button>
      </div>

      {mode === 'upload' && (
        <>
          {!file && (
            <div
              className={`dropzone ${dragActive ? 'dropzone--active' : ''}`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={() => setDragActive(false)}
              onDrop={handleDrop}
              onClick={() => inputRef.current?.click()}
              role="button"
              tabIndex={0}
            >
              📄 Drag &amp; drop a deviation report here
              <div className="source-hint">or click to browse — PDF or TXT, max {MAX_FILE_MB}MB</div>
              <input
                ref={inputRef}
                type="file"
                accept=".pdf,.txt,application/pdf,text/plain"
                style={{ display: 'none' }}
                onChange={(e) => acceptFile(e.target.files?.[0])}
              />
            </div>
          )}
          {file && (
            <div className="dropzone__filename">
              <span>📎 {file.name}</span>
              <button
                className="btn btn--ghost btn--sm"
                onClick={() => {
                  setFile(null);
                  dispatch(setSourceFile(null));
                }}
              >
                Remove
              </button>
            </div>
          )}
          {fileError && <div className="field__error" style={{ marginTop: 6 }}>{fileError}</div>}
        </>
      )}

      {mode === 'paste' && (
        <textarea
          className="source-textarea"
          placeholder="Paste the deviation report, lab result, or email content here…"
          value={source.text}
          onChange={(e) => dispatch(setSourceText(e.target.value))}
        />
      )}

      <button className="btn btn--primary analyze-btn" onClick={handleAnalyze} disabled={!canAnalyze}>
        ✨ Analyze with AI
      </button>
    </div>
  );
}
