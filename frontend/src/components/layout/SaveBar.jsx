import { useDispatch, useSelector } from 'react-redux';
import { selectUi, selectIsFormUnlocked } from '../../store/selectors';
import { saveReviewedDeviation } from '../../store/thunks';
import { resetDeviation } from '../../store/deviationSlice';

export default function SaveBar() {
  const dispatch = useDispatch();
  const ui = useSelector(selectUi);
  const isUnlocked = useSelector(selectIsFormUnlocked);

  const handleReset = () => {
    if (window.confirm('Reset this deviation? Any unsaved changes will be lost.')) {
      dispatch(resetDeviation());
    }
  };

  const handleSave = () => {
    dispatch(saveReviewedDeviation());
  };

  return (
    <div className="save-bar">
      <div className="save-bar__status">
        {ui.saving && 'Saving…'}
        {!ui.saving && ui.saveSuccess && ui.deviationId && (
          <span style={{ color: 'var(--success)', fontWeight: 600 }}>
            ✓ Saved as {ui.deviationId}
          </span>
        )}
        {!ui.saving && ui.saveError && (
          <span style={{ color: 'var(--danger)', fontWeight: 600 }}>{ui.saveError.message}</span>
        )}
        {!ui.saving && !ui.saveSuccess && !ui.saveError && Object.keys(ui.validationErrors).length > 0 && (
          <span style={{ color: 'var(--danger)', fontWeight: 600 }}>
            Please resolve the highlighted fields before saving.
          </span>
        )}
      </div>
      <div className="save-bar__actions">
        <button className="btn btn--secondary" onClick={handleReset}>
          ↺ Reset Form
        </button>
        <button className="btn btn--primary" onClick={handleSave} disabled={!isUnlocked || ui.saving}>
          {ui.saving ? 'Saving…' : '💾 Save Deviation'}
        </button>
      </div>
    </div>
  );
}
