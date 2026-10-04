import { AlertTriangle, CheckCircle2 } from "lucide-react";

export default function ContextStatus({ context, onEdit }) {
  if (context.status === "READY") {
    return (
      <div className="ctx ctx-ok">
        <CheckCircle2 size={15} />
        <span>Financial context complete</span>
      </div>
    );
  }

  const conflicting = context.status === "CONFLICTING_CONTEXT";

  return (
    <div className="ctx ctx-warn">
      <AlertTriangle size={16} />
      <div className="ctx-body">
        <div className="ctx-title">
          {conflicting ? "Your financial information needs review." : "More information needed"}
        </div>
        <div className="ctx-text">{context.message}</div>
        {conflicting && (
          <ul>
            {context.conflicts.map((c) => (
              <li key={c.code}>{c.message}</li>
            ))}
          </ul>
        )}
        <button type="button" className="ctx-link" onClick={onEdit}>
          Review financial profile
        </button>
      </div>
    </div>
  );
}