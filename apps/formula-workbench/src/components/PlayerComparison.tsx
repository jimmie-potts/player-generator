import { formatNumber, formatSignedNumber } from "../domain/format";
import { StatusPanel } from "./StatusPanel";

export type ComparisonVisualState =
  | "changed"
  | "excluded"
  | "failure"
  | "largest-gain"
  | "largest-loss"
  | "missing"
  | "no-change";

export type ComparisonGroupKind = "pinned" | "tier";

export interface ComparisonMeasure {
  baseline: number | null;
  preview: number | null;
  delta: number | null;
  baselineRank: number | null;
  previewRank: number | null;
  rankMovement: number | null;
}

export interface PlayerComparisonRow {
  playerId: string;
  displayName: string;
  tier: string | null;
  pinned: boolean;
  selected?: boolean;
  state: ComparisonVisualState;
  stateMessage?: string;
  attribute: ComparisonMeasure;
  overall: ComparisonMeasure;
}

export interface PlayerComparisonGroup {
  id: string;
  label: string;
  kind: ComparisonGroupKind;
  rows: readonly PlayerComparisonRow[];
}

export interface PlayerComparisonProps {
  selectedAttributeLabel: string;
  groups: readonly PlayerComparisonGroup[];
  loading?: boolean;
  error?: string | null;
  onSelect: (playerId: string) => void;
  onUnpin: (playerId: string) => void;
}

const STATE_LABELS: Record<ComparisonVisualState, string> = {
  changed: "Changed",
  excluded: "Excluded",
  failure: "Preview failed",
  "largest-gain": "Largest gain",
  "largest-loss": "Largest loss",
  missing: "Missing input",
  "no-change": "No change",
};

function ratingTransition(measure: ComparisonMeasure): string {
  if (measure.baseline === null && measure.preview === null) {
    return "—";
  }
  return `${formatNumber(measure.baseline)} → ${formatNumber(measure.preview)}`;
}

function rankMovement(measure: ComparisonMeasure): string {
  if (measure.rankMovement === null) {
    return "—";
  }
  if (measure.rankMovement === 0) {
    return "No move";
  }
  return `${measure.rankMovement > 0 ? "▲" : "▼"} ${Math.abs(measure.rankMovement)}`;
}

function rankMovementLabel(measure: ComparisonMeasure): string {
  const ranks =
    measure.baselineRank === null || measure.previewRank === null
      ? "Ranks unavailable."
      : `Rank ${measure.baselineRank} to ${measure.previewRank}.`;
  if (measure.rankMovement === null) {
    return ranks;
  }
  if (measure.rankMovement === 0) {
    return `${ranks} No rank movement.`;
  }
  return `${ranks} Moved ${Math.abs(measure.rankMovement)} places ${
    measure.rankMovement > 0 ? "toward rank one" : "away from rank one"
  }.`;
}

export function PlayerComparison({
  selectedAttributeLabel,
  groups,
  loading = false,
  error = null,
  onSelect,
  onUnpin,
}: PlayerComparisonProps) {
  if (error) {
    return (
      <StatusPanel title="Player comparison unavailable" tone="error">
        {error} Prior preview results are not shown as current.
      </StatusPanel>
    );
  }

  if (loading) {
    return (
      <StatusPanel title="Recalculating comparison" tone="loading">
        Ratings and ranks are being evaluated against the fixed cohort.
      </StatusPanel>
    );
  }

  const populatedGroups = groups.filter((group) => group.rows.length);
  if (!populatedGroups.length) {
    return (
      <StatusPanel title="No comparison players" tone="empty">
        The loaded cohort did not return representative or pinned players.
      </StatusPanel>
    );
  }

  return (
    <section className="player-comparison workbench-panel" aria-labelledby="comparison-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Fixed-cohort impact</p>
          <h2 id="comparison-title">Player comparison</h2>
          <p>
            Baseline → preview values for {selectedAttributeLabel} and overall. Positive rank
            movement is toward rank 1.
          </p>
        </div>
      </div>

      {populatedGroups.map((group) => (
        <section className="comparison-group" key={group.id} aria-labelledby={`${group.id}-heading`}>
          <div className="comparison-group__heading">
            <h3 id={`${group.id}-heading`}>{group.label}</h3>
            <span>
              {group.rows.length} {group.kind === "pinned" ? "session pin" : "representative"}
              {group.rows.length === 1 ? "" : "s"}
            </span>
          </div>

          <div
            className="comparison-table-wrap"
            tabIndex={0}
            role="region"
            aria-label={`${group.label} player comparison`}
          >
            <table className="comparison-table">
              <thead>
                <tr>
                  <th scope="col">Player</th>
                  <th scope="col">{selectedAttributeLabel}</th>
                  <th scope="col">Δ</th>
                  <th scope="col">Attribute rank</th>
                  <th scope="col">Overall</th>
                  <th scope="col">Δ</th>
                  <th scope="col">Overall rank</th>
                  <th scope="col">Signal</th>
                  <th scope="col"><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {group.rows.map((player) => (
                  <tr
                    className={`comparison-row comparison-row--${player.state}${
                      player.selected ? " comparison-row--selected" : ""
                    }`}
                    key={player.playerId}
                  >
                    <th scope="row">
                      <button
                        className="player-select-button"
                        type="button"
                        onClick={() => onSelect(player.playerId)}
                        aria-current={player.selected ? "true" : undefined}
                      >
                        <strong>{player.displayName}</strong>
                        <span>{player.tier ?? "No tier"}</span>
                      </button>
                    </th>
                    <td className="rating-transition">{ratingTransition(player.attribute)}</td>
                    <td className="delta-value">{formatSignedNumber(player.attribute.delta)}</td>
                    <td
                      className="rank-movement"
                      aria-label={rankMovementLabel(player.attribute)}
                    >
                      {rankMovement(player.attribute)}
                    </td>
                    <td className="rating-transition">{ratingTransition(player.overall)}</td>
                    <td className="delta-value">{formatSignedNumber(player.overall.delta)}</td>
                    <td className="rank-movement" aria-label={rankMovementLabel(player.overall)}>
                      {rankMovement(player.overall)}
                    </td>
                    <td>
                      <span
                        className={`comparison-signal comparison-signal--${player.state}`}
                        title={player.stateMessage}
                      >
                        {STATE_LABELS[player.state]}
                      </span>
                      {player.stateMessage ? <span className="sr-only">: {player.stateMessage}</span> : null}
                    </td>
                    <td className="comparison-actions">
                      {player.pinned ? (
                        <button
                          className="icon-button"
                          type="button"
                          onClick={() => onUnpin(player.playerId)}
                          aria-label={`Unpin ${player.displayName}`}
                          title="Unpin player"
                        >
                          ×
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </section>
  );
}
