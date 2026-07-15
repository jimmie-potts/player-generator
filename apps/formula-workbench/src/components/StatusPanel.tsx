import type { ReactNode } from "react";

export type StatusPanelTone =
  | "empty"
  | "error"
  | "excluded"
  | "info"
  | "loading"
  | "stale"
  | "unsupported";

export interface StatusPanelProps {
  title: string;
  tone?: StatusPanelTone;
  children?: ReactNode;
  action?: ReactNode;
  compact?: boolean;
}

const STATUS_SYMBOLS: Record<StatusPanelTone, string> = {
  empty: "—",
  error: "!",
  excluded: "×",
  info: "i",
  loading: "",
  stale: "↻",
  unsupported: "?",
};

export function StatusPanel({
  title,
  tone = "info",
  children,
  action,
  compact = false,
}: StatusPanelProps) {
  const urgent = tone === "error" || tone === "stale";

  return (
    <section
      className={`status-panel status-panel--${tone}${compact ? " status-panel--compact" : ""}`}
      role={urgent ? "alert" : "status"}
      aria-live={urgent ? "assertive" : "polite"}
      aria-busy={tone === "loading"}
    >
      <span
        className={`status-panel__symbol${tone === "loading" ? " status-panel__spinner" : ""}`}
        aria-hidden="true"
      >
        {STATUS_SYMBOLS[tone]}
      </span>
      <div className="status-panel__body">
        <h3>{title}</h3>
        {children ? <div className="status-panel__message">{children}</div> : null}
      </div>
      {action ? <div className="status-panel__action">{action}</div> : null}
    </section>
  );
}
