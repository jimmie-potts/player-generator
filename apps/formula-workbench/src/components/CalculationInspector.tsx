import type { AttributeCalculation, JsonScalar, MetricMetadata } from "../api/types";
import {
  formatNumber,
  formatPercent,
  formatSignedNumber,
  identifierLabel,
} from "../domain/format";
import { StatusPanel } from "./StatusPanel";

export type CalculationInspectorStatus =
  | "empty"
  | "error"
  | "loading"
  | "ready"
  | "stale"
  | "unsupported";

export interface CalculationPlayerIdentity {
  playerId: string;
  displayName: string;
  season: number | null;
}

export type CalculationValueState = "available" | "missing" | "unsupported";

export interface CalculationRawMetricRow {
  metric: string;
  label: string;
  baseline: number | null | undefined;
  preview: number | null | undefined;
  state: CalculationValueState;
}

export interface CalculationComponentRow {
  metric: string;
  label: string;
  description?: string;
  baselinePercentile: number | null | undefined;
  previewPercentile: number | null | undefined;
  baselineWeight: number | undefined;
  previewWeight: number | undefined;
  baselineContribution: number | null | undefined;
  previewContribution: number | null | undefined;
  state: CalculationValueState;
}

export interface CalculationInspectorProps {
  player: CalculationPlayerIdentity | null;
  attributeName: string | null;
  baseline: AttributeCalculation | null;
  preview?: AttributeCalculation | null;
  metrics?: readonly MetricMetadata[];
  status?: CalculationInspectorStatus;
  statusMessage?: string;
}

function hasOwn(record: Record<string, unknown>, key: string): boolean {
  return Object.prototype.hasOwnProperty.call(record, key);
}

function metricMetadataMap(metrics: readonly MetricMetadata[]): Map<string, MetricMetadata> {
  return new Map(metrics.map((metric) => [metric.name, metric]));
}

export function buildCalculationRawMetricRows(
  baseline: AttributeCalculation,
  preview: AttributeCalculation | null | undefined,
): CalculationRawMetricRow[] {
  const names = new Set([...Object.keys(baseline.rawInputs), ...Object.keys(preview?.rawInputs ?? {})]);
  return [...names].sort().map((metric) => {
    const baselineSupported = hasOwn(baseline.rawInputs, metric);
    const previewSupported = preview ? hasOwn(preview.rawInputs, metric) : baselineSupported;
    const baselineValue = baseline.rawInputs[metric];
    const previewValue = preview
      ? preview.rawInputs[metric]
      : baselineValue;
    const state: CalculationValueState =
      !baselineSupported && !previewSupported
        ? "unsupported"
        : baselineValue == null || previewValue == null
          ? "missing"
          : "available";
    return {
      metric,
      label: identifierLabel(metric),
      baseline: baselineValue,
      preview: previewValue,
      state,
    };
  });
}

export function buildCalculationComponentRows(
  baseline: AttributeCalculation,
  preview: AttributeCalculation | null | undefined,
  metrics: readonly MetricMetadata[] = [],
): CalculationComponentRow[] {
  const metadata = metricMetadataMap(metrics);
  const names = new Set([
    ...Object.keys(baseline.componentPercentiles),
    ...Object.keys(baseline.normalizedWeights),
    ...Object.keys(baseline.contributions),
    ...Object.keys(preview?.componentPercentiles ?? {}),
    ...Object.keys(preview?.normalizedWeights ?? {}),
    ...Object.keys(preview?.contributions ?? {}),
  ]);

  return [...names].map((metric) => {
    const details = metadata.get(metric);
    const baselinePercentile = baseline.componentPercentiles[metric];
    const previewPercentile = preview
      ? preview.componentPercentiles[metric]
      : baselinePercentile;
    const baselineWeight = baseline.normalizedWeights[metric];
    const previewWeight = preview
      ? preview.normalizedWeights[metric]
      : baselineWeight;
    const baselineContribution = baseline.contributions[metric];
    const previewContribution = preview
      ? preview.contributions[metric]
      : baselineContribution;
    const supported =
      hasOwn(baseline.componentPercentiles, metric) ||
      hasOwn(baseline.normalizedWeights, metric) ||
      hasOwn(baseline.contributions, metric) ||
      Boolean(
        preview &&
          (hasOwn(preview.componentPercentiles, metric) ||
            hasOwn(preview.normalizedWeights, metric) ||
            hasOwn(preview.contributions, metric)),
      );
    const state: CalculationValueState = !supported
      ? "unsupported"
      : baselinePercentile == null ||
          previewPercentile == null ||
          baselineWeight == null ||
          previewWeight == null ||
          baselineContribution == null ||
          previewContribution == null
        ? "missing"
        : "available";

    return {
      metric,
      label: details?.label ?? identifierLabel(metric),
      description: details?.description,
      baselinePercentile,
      previewPercentile,
      baselineWeight,
      previewWeight,
      baselineContribution,
      previewContribution,
      state,
    };
  });
}

function displayValue(value: JsonScalar | undefined, state: CalculationValueState): string {
  if (state === "unsupported") {
    return "Unsupported";
  }
  if (value === null || value === undefined) {
    return "Missing";
  }
  return formatNumber(value);
}

function ineligibilityMessage(
  reason: AttributeCalculation["ineligibilityReasons"][number],
): string {
  const metric = identifierLabel(reason.metric);
  if (reason.kind === "minimumSample") {
    return `${metric}: ${formatNumber(reason.actual)} observed; ${formatNumber(reason.minimum)} required.`;
  }
  if (reason.actual === null) {
    return `${metric}: required input is missing.`;
  }
  return `${metric}: ${identifierLabel(reason.kind)}.`;
}

function summaryDelta(
  baseline: number | null,
  preview: number | null | undefined,
): number | null {
  return baseline !== null && typeof preview === "number" ? preview - baseline : null;
}

export function CalculationInspector({
  player,
  attributeName,
  baseline,
  preview = null,
  metrics = [],
  status = "ready",
  statusMessage,
}: CalculationInspectorProps) {
  if (status !== "ready") {
    const statusCopy: Record<Exclude<CalculationInspectorStatus, "ready">, [string, string]> = {
      empty: ["Select a player", "Choose a comparison player to inspect an authoritative calculation."],
      error: ["Calculation unavailable", statusMessage ?? "The preview API did not return a current calculation."],
      loading: ["Loading calculation", "Fetching the selected player’s authoritative explanation."],
      stale: ["Calculation context changed", statusMessage ?? "Reload the formula and player data before continuing."],
      unsupported: ["Attribute unsupported", statusMessage ?? "The selected calculation does not contain this attribute."],
    };
    const [title, message] = statusCopy[status];
    const tone = status === "error" ? "error" : status;
    return (
      <StatusPanel title={title} tone={tone}>
        {message}
      </StatusPanel>
    );
  }

  if (!player || !attributeName || !baseline) {
    return (
      <StatusPanel title="Select a player and attribute" tone="empty">
        Calculation details appear after both selections are available.
      </StatusPanel>
    );
  }

  const rawRows = buildCalculationRawMetricRows(baseline, preview);
  const componentRows = buildCalculationComponentRows(baseline, preview, metrics);
  const excluded = !baseline.eligible || (preview ? !preview.eligible : false);
  const reasons = [
    ...baseline.ineligibilityReasons,
    ...(preview?.ineligibilityReasons ?? []),
  ].filter(
    (reason, index, all) =>
      all.findIndex(
        (candidate) =>
          candidate.kind === reason.kind &&
          candidate.metric === reason.metric &&
          candidate.minimum === reason.minimum &&
          candidate.actual === reason.actual,
      ) === index,
  );

  return (
    <section className="calculation-inspector workbench-panel" aria-labelledby="calculation-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Authoritative explanation</p>
          <h2 id="calculation-title">{player.displayName}</h2>
          <p>
            {identifierLabel(attributeName)} · {player.season ?? "Season unavailable"} · {player.playerId}
          </p>
        </div>
        <span className={`eligibility-badge eligibility-badge--${excluded ? "excluded" : "eligible"}`}>
          {excluded ? "Excluded" : "Eligible"}
        </span>
      </div>

      {excluded ? (
        <StatusPanel title="Excluded from this attribute cohort" tone="excluded" compact>
          {reasons.length ? (
            <ul className="reason-list">
              {reasons.map((reason, index) => (
                <li key={`${reason.kind}-${reason.metric}-${index}`}>{ineligibilityMessage(reason)}</li>
              ))}
            </ul>
          ) : (
            "The API marked this calculation ineligible without an additional reason."
          )}
        </StatusPanel>
      ) : null}

      <div className="calculation-scoreboard" aria-label="Calculation summary">
        <article>
          <span>Rating</span>
          <strong>{formatNumber(baseline.rating)}</strong>
          <small>
            Preview {formatNumber(preview?.rating)} · Δ {formatSignedNumber(summaryDelta(baseline.rating, preview?.rating))}
          </small>
        </article>
        <article>
          <span>Composite percentile</span>
          <strong>{formatPercent(baseline.compositePercentile)}</strong>
          <small>Preview {formatPercent(preview?.compositePercentile)}</small>
        </article>
        <article>
          <span>Weighted composite</span>
          <strong>{formatNumber(baseline.composite)}</strong>
          <small>Preview {formatNumber(preview?.composite)}</small>
        </article>
        <article>
          <span>Eligible cohort</span>
          <strong>{baseline.cohort.eligibleCount.toLocaleString()}</strong>
          <small>
            {identifierLabel(baseline.cohort.name)}
            {Object.keys(baseline.cohort.values).length
              ? ` · ${Object.entries(baseline.cohort.values)
                  .map(([field, value]) => `${identifierLabel(field)} ${formatNumber(value)}`)
                  .join(" · ")}`
              : ""}
          </small>
        </article>
      </div>

      <section className="calculation-section" aria-labelledby="raw-metrics-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Source values</p>
            <h3 id="raw-metrics-heading">Raw metrics</h3>
          </div>
          <p>Missing values remain empty; the client does not impute or calculate replacements.</p>
        </div>
        <div className="data-table-wrap" tabIndex={0} role="region" aria-label="Raw metric values">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Metric</th>
                <th scope="col">Baseline</th>
                <th scope="col">Preview</th>
                <th scope="col">State</th>
              </tr>
            </thead>
            <tbody>
              {rawRows.map((row) => (
                <tr key={row.metric} className={`value-row value-row--${row.state}`}>
                  <th scope="row">{row.label}</th>
                  <td>{displayValue(row.baseline, row.state)}</td>
                  <td>{displayValue(row.preview, row.state)}</td>
                  <td><span className={`value-state value-state--${row.state}`}>{identifierLabel(row.state)}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="calculation-section" aria-labelledby="component-breakdown-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">API calculation detail</p>
            <h3 id="component-breakdown-heading">Component breakdown</h3>
          </div>
          <p>Values below are rendered exactly as returned; no rating formula runs in the browser.</p>
        </div>
        <div className="data-table-wrap" tabIndex={0} role="region" aria-label="Component calculation breakdown">
          <table className="data-table data-table--calculation">
            <thead>
              <tr>
                <th rowSpan={2} scope="col">Component</th>
                <th colSpan={2} scope="colgroup">Percentile</th>
                <th colSpan={2} scope="colgroup">Normalized weight</th>
                <th colSpan={2} scope="colgroup">Contribution</th>
              </tr>
              <tr>
                <th scope="col">Base</th>
                <th scope="col">Preview</th>
                <th scope="col">Base</th>
                <th scope="col">Preview</th>
                <th scope="col">Base</th>
                <th scope="col">Preview</th>
              </tr>
            </thead>
            <tbody>
              {componentRows.map((row) => (
                <tr key={row.metric} className={`value-row value-row--${row.state}`}>
                  <th scope="row">
                    {row.label}
                    {row.description ? <small>{row.description}</small> : null}
                  </th>
                  <td>{formatPercent(row.baselinePercentile)}</td>
                  <td>{formatPercent(row.previewPercentile)}</td>
                  <td>{formatPercent(row.baselineWeight)}</td>
                  <td>{formatPercent(row.previewWeight)}</td>
                  <td>{formatNumber(row.baselineContribution)}</td>
                  <td>{formatNumber(row.previewContribution)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
