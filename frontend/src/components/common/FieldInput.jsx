import { ProvenanceBadge } from './Badge';
import { toDatetimeLocalValue, fromDatetimeLocalValue } from '../../utils/formatters';

/**
 * @param {string} name - field key
 * @param {string} label
 * @param {string|null} value
 * @param {'text'|'textarea'|'datetime'} [type]
 * @param {boolean} [locked] - true before the first successful extraction; renders a disabled placeholder
 * @param {'ai'|'edited'|'none'} [provenance]
 * @param {string} [error]
 * @param {(value: string|null) => void} onChange
 * @param {string} [span] - 'full' to span both grid columns
 */
export default function FieldInput({
  name,
  label,
  value,
  type = 'text',
  locked = false,
  provenance = 'none',
  error,
  onChange,
  span,
}) {
  const wrapperClass = span === 'full' ? 'field field--span-2' : 'field';

  if (locked) {
    return (
      <div className={wrapperClass}>
        <div className="field__label-row">
          <span className="field__label">{label}</span>
        </div>
        <div className="field__placeholder">Not yet analyzed</div>
      </div>
    );
  }

  const inputClass = (base) => `${base}${error ? ` ${base}--error` : ''}`;

  return (
    <div className={wrapperClass}>
      <div className="field__label-row">
        <span className="field__label">{label}</span>
        <ProvenanceBadge provenance={provenance} />
      </div>

      {type === 'textarea' && (
        <textarea
          className={inputClass('field__textarea')}
          value={value ?? ''}
          placeholder="Not identified — enter manually"
          onChange={(e) => onChange(e.target.value || null)}
        />
      )}

      {type === 'datetime' && (
        <input
          type="datetime-local"
          className={inputClass('field__input')}
          value={toDatetimeLocalValue(value)}
          onChange={(e) => onChange(fromDatetimeLocalValue(e.target.value))}
        />
      )}

      {type === 'text' && (
        <input
          type="text"
          className={inputClass('field__input')}
          value={value ?? ''}
          placeholder="Not identified — enter manually"
          onChange={(e) => onChange(e.target.value || null)}
        />
      )}

      {error && <span className="field__error">{error}</span>}
    </div>
  );
}
