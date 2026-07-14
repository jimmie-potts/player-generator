import type { ApiContext } from "../api/types";

export type WorkbenchPreviewStatus =
  | "baseline"
  | "error"
  | "loading"
  | "preview"
  | "queued";

export interface WorkbenchHeaderProps {
  context: ApiContext | null;
  dirty: boolean;
  dirtyCount?: number;
  previewStatus: WorkbenchPreviewStatus;
  previewStatusMessage?: string;
  proposalVersion?: string;
  canExport?: boolean;
  onResetAll: () => void;
  onExport: () => void;
}

const PREVIEW_STATUS_LABELS: Record<WorkbenchPreviewStatus, string> = {
  baseline: "Baseline current",
  error: "Preview failed",
  loading: "Calculating preview",
  preview: "Preview current",
  queued: "Preview queued",
};

function shortHash(value: string): string {
  return value.length > 12 ? `${value.slice(0, 8)}…${value.slice(-4)}` : value;
}

export function WorkbenchHeader({
  context,
  dirty,
  dirtyCount = 0,
  previewStatus,
  previewStatusMessage,
  proposalVersion,
  canExport = false,
  onResetAll,
  onExport,
}: WorkbenchHeaderProps) {
  const loading = previewStatus === "loading" || previewStatus === "queued";
  const dirtyLabel = dirty
    ? `${dirtyCount || "Unsaved"} session ${dirtyCount === 1 ? "change" : "changes"}`
    : "No session changes";

  return (
    <header className="workbench-header">
      <div className="workbench-header__brand">
        <p className="eyebrow">Player Generator · Design Lab</p>
        <div className="workbench-header__title-row">
          <h1>Formula Workbench</h1>
          <span className="workbench-header__read-only">Session preview</span>
        </div>
        <p className="workbench-header__lede">
          Inspect the authoritative rating model, test reversible adjustments, and compare their
          player-level impact.
        </p>
      </div>

      <div className="workbench-header__controls">
        <div className="workbench-header__status" aria-live="polite" aria-busy={loading}>
          <span
            className={`status-dot status-dot--${previewStatus}`}
            aria-hidden="true"
          />
          <span>
            <strong>{PREVIEW_STATUS_LABELS[previewStatus]}</strong>
            <small>{previewStatusMessage ?? dirtyLabel}</small>
          </span>
        </div>
        <div className="workbench-header__actions">
          <button
            className="button button--secondary"
            type="button"
            onClick={onResetAll}
            disabled={!dirty}
          >
            Reset all
          </button>
          <button
            className="button button--primary"
            type="button"
            onClick={onExport}
            disabled={!canExport || loading}
          >
            Export proposal
          </button>
        </div>
      </div>

      {context ? (
        <dl className="identity-strip" aria-label="Loaded formula and reference data identity">
          <div>
            <dt>API</dt>
            <dd>v{context.apiVersion}</dd>
          </div>
          <div>
            <dt>Formula</dt>
            <dd>{proposalVersion?.trim() || context.formula.formulaVersion}</dd>
          </div>
          <div>
            <dt>Season</dt>
            <dd>{context.season}</dd>
          </div>
          <div>
            <dt>Cohort</dt>
            <dd>{context.cohortSize.toLocaleString()} players</dd>
          </div>
          <div>
            <dt>Reference</dt>
            <dd>
              v{context.referencePackage.packageVersion} ·{" "}
              <abbr title={context.referencePackage.contentHash}>
                {shortHash(context.referencePackage.contentHash)}
              </abbr>
            </dd>
          </div>
          <div>
            <dt>Formula hash</dt>
            <dd>
              <abbr title={context.formula.documentHash}>
                {shortHash(context.formula.documentHash)}
              </abbr>
            </dd>
          </div>
        </dl>
      ) : (
        <p className="identity-strip identity-strip--empty" role="status">
          Waiting for formula and reference-package identity.
        </p>
      )}
    </header>
  );
}
