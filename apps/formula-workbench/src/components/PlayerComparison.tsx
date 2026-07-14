import { formatNumber, formatSignedNumber } from "../domain/format";
import { SectionHelp } from "./SectionHelp";
import { StatusPanel } from "./StatusPanel";

export type ComparisonVisualState =
  | "changed"
  | "excluded"
  | "failure"
  | "largest-gain"
  | "largest-loss"
  | "missing"
  | "no-change";

export type ComparisonGroupKind = "tier" | "top25" | "custom";

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
  removable: boolean;
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
  emptyTitle?: string;
  emptyMessage?: string;
  onSelect: (playerId: string) => void;
  onRemove: (playerId: string) => void;
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

type ImpactDirection = "negative" | "neutral" | "positive" | "unavailable";

function impactDirection(value: number | null): ImpactDirection {
  if (value === null || !Number.isFinite(value)) return "unavailable";
  if (value > 0) return "positive";
  if (value < 0) return "negative";
  return "neutral";
}

function impactIcon(direction: ImpactDirection): string {
  if (direction === "positive") return "▲";
  if (direction === "negative") return "▼";
  if (direction === "neutral") return "=";
  return "";
}

function RatingImpact({ value }: { value: number | null }) {
  const direction = impactDirection(value);
  const accessibleText =
    direction === "positive"
      ? `Rating increased by ${formatNumber(value)}.`
      : direction === "negative"
        ? `Rating decreased by ${formatNumber(Math.abs(value ?? 0))}.`
        : direction === "neutral"
          ? "Rating did not change."
          : "Rating change unavailable.";

  return (
    <span className={`impact-value impact-value--${direction}`}>
      <span aria-hidden="true">
        {impactIcon(direction)} {formatSignedNumber(value)}
      </span>
      <span className="sr-only">{accessibleText}</span>
    </span>
  );
}

const GROUP_MEMBER_LABELS: Record<ComparisonGroupKind, string> = {
  tier: "representative",
  top25: "baseline-ranked player",
  custom: "custom player",
};

export function PlayerComparison({
  selectedAttributeLabel,
  groups,
  loading = false,
  error = null,
  emptyTitle = "No comparison players",
  emptyMessage = "The active player set did not return any players.",
  onSelect,
  onRemove,
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
      <StatusPanel title={emptyTitle} tone="empty">
        {emptyMessage}
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
      <SectionHelp title="How to read player impact">
        <p>
          Delta is preview minus baseline. Positive rank movement means movement toward rank 1,
          and every rank is calculated across the complete fixed cohort rather than only the rows
          shown here. Signals distinguish unchanged, missing, excluded, failed, and tied largest
          gain or loss results. Selecting a player updates the authoritative explanation above.
        </p>
        <p>
          Every nonzero rating delta is green with an upward arrow when the rating increased and red
          with a downward arrow when it decreased. Rank movement uses green for movement toward
          rank 1 and red for movement away. Signed values, arrows, and accessible direction labels
          carry the same meaning when color is unavailable.
        </p>
      </SectionHelp>

      {populatedGroups.map((group) => (
        <section className="comparison-group" key={group.id} aria-labelledby={`${group.id}-heading`}>
          <div className="comparison-group__heading">
            <h3 id={`${group.id}-heading`}>{group.label}</h3>
            <span>
              {group.rows.length} {GROUP_MEMBER_LABELS[group.kind]}
              {group.rows.length === 1 ? "" : "s"}
            </span>
          </div>

          <div
            className={`comparison-table-wrap${
              group.kind === "top25" || group.kind === "custom"
                ? " comparison-table-wrap--bounded"
                : ""
            }`}
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
                    <td className="delta-value">
                      <RatingImpact value={player.attribute.delta} />
                    </td>
                    <td
                      className={`rank-movement impact-value impact-value--${impactDirection(player.attribute.rankMovement)}`}
                      aria-label={rankMovementLabel(player.attribute)}
                    >
                      {rankMovement(player.attribute)}
                    </td>
                    <td className="rating-transition">{ratingTransition(player.overall)}</td>
                    <td className="delta-value">
                      <RatingImpact value={player.overall.delta} />
                    </td>
                    <td
                      className={`rank-movement impact-value impact-value--${impactDirection(player.overall.rankMovement)}`}
                      aria-label={rankMovementLabel(player.overall)}
                    >
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
                      {player.removable ? (
                        <button
                          className="icon-button"
                          type="button"
                          onClick={() => onRemove(player.playerId)}
                          aria-label={`Remove ${player.displayName} from custom list`}
                          title="Remove from custom list"
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
