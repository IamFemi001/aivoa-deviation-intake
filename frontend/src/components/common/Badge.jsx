export function ProvenanceBadge({ provenance }) {
  if (provenance === 'ai') {
    return <span className="badge badge--ai">✨ AI extracted</span>;
  }
  if (provenance === 'edited') {
    return <span className="badge badge--edited">Edited by user</span>;
  }
  return null;
}

export function ImpactLevelBadge({ level }) {
  const label = { none: 'None', potential: 'Potential', confirmed: 'Confirmed', unknown: 'Unknown' }[level] || level;
  return <span className={`badge badge--level-${level}`}>{label}</span>;
}

export function SeverityBadge({ level }) {
  const label = { minor: 'Minor', major: 'Major', critical: 'Critical', unknown: 'Unknown' }[level] || level;
  return <span className={`badge badge--severity-${level}`}>{label}</span>;
}
