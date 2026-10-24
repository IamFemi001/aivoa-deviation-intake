export default function EmptyState({ icon = '📄', title, body }) {
  return (
    <div className="empty-state">
      <div style={{ fontSize: 28, marginBottom: 10 }}>{icon}</div>
      <div className="empty-state__title">{title}</div>
      <div className="empty-state__body">{body}</div>
    </div>
  );
}
