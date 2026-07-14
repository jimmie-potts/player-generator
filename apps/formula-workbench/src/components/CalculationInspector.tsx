import type { AttributeCalculation, JsonScalar, MetricMetadata } from "../api/types";
import {
  formatNumber,
  formatPercent,
  formatSignedNumber,
  identifierLabel,
} from "../domain/format";
import { SectionHelp } from "./SectionHelp";
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

export type CalculationValueState = "available" | "missing" | "pending" | "unsupported";

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
  pending?: boolean;
  previewError?: string;
  status?: CalculationInspectorStatus;
  statusMessage?: string;
}

const SIGNED_PERCENT_FORMAT = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 3,
  signDisplay: "always",
  style: "percent",
});

function hasOwn(record: Record<string, unknown>, key: string): boolean {
  return Object.prototype.hasOwnProperty.call(record, key);
}

function metricMetadataMap(metrics: readonly MetricMetadata[]): Map<string, MetricMetadata> {
  return new Map(metrics.map((metric) => [metric.name, metric]));
}

export function buildCalculationRawMetricRows(
  baseline: AttributeCalculation,
  preview: AttributeCalculation | null | undefined,
  pending = false,
): CalculationRawMetricRow[] {
  const names = new Set([...Object.keys(baseline.rawInputs), ...Object.keys(preview?.rawInputs ?? {})]);
  return [...names].sort().map((metric) => {
    const baselineSupported = hasOwn(baseline.rawInputs, metric);
    const previewSupported = pending
      ? baselineSupported
      : preview
        ? hasOwn(preview.rawInputs, metric)
        : baselineSupported;
    const baselineValue = baseline.rawInputs[metric];
    const previewValue = pending
      ? undefined
      : preview
        ? preview.rawInputs[metric]
        : baselineValue;
    const state: CalculationValueState =
      pending
        ? "pending"
        : !baselineSupported && !previewSupported
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
  pending = false,
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
    const previewPercentile = pending
      ? undefined
      : preview
        ? preview.componentPercentiles[metric]
        : baselinePercentile;
    const baselineWeight = baseline.normalizedWeights[metric];
    const previewWeight = pending
      ? undefined
      : preview
        ? preview.normalizedWeights[metric]
        : baselineWeight;
    const baselineContribution = baseline.contributions[metric];
    const previewContribution = pending
      ? undefined
      : preview
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
    const state: CalculationValueState = pending
      ? "pending"
      : !supported
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
  if (state === "pending" && value === undefined) {
    return "Updating…";
  }
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

type ChangeDirection = "decrease" | "increase" | "unchanged" | "unavailable";

function changeDirection(
  baseline: number | null | undefined,
  preview: number | null | undefined,
): ChangeDirection {
  if (
    typeof baseline !== "number" ||
    !Number.isFinite(baseline) ||
    typeof preview !== "number" ||
    !Number.isFinite(preview)
  ) {
    return "unavailable";
  }
  if (preview > baseline) return "increase";
  if (preview < baseline) return "decrease";
  return "unchanged";
}

function changeIcon(direction: ChangeDirection): string {
  if (direction === "increase") return "▲";
  if (direction === "decrease") return "▼";
  if (direction === "unchanged") return "=";
  return "";
}

function formatSignedPercent(value: number): string {
  if (value === 0) return formatPercent(0);
  if (Math.abs(value) < 0.000005) {
    return value > 0 ? "+<0.001%" : "−<0.001%";
  }
  return SIGNED_PERCENT_FORMAT.format(value);
}

interface PreviewChangeProps {
  baseline: number | null | undefined;
  preview: number | null | undefined;
  pending: boolean;
  formatValue: (value: unknown) => string;
  formatDelta: (value: number) => string;
  tone?: "allocation" | "impact";
  variant: "scoreboard" | "table";
}

function PreviewChange({
  baseline,
  preview,
  pending,
  formatValue,
  formatDelta,
  tone = "impact",
  variant,
}: PreviewChangeProps) {
  if (pending) {
    return variant === "scoreboard" ? (
      <small className="preview-impact preview-impact--pending">Preview updating…</small>
    ) : (
      <>Updating…</>
    );
  }

  const direction = changeDirection(baseline, preview);
  const delta = summaryDelta(baseline ?? null, preview);
  const previewText = formatValue(preview);
  const baselineText = formatValue(baseline);
  const directionText =
    direction === "increase"
      ? "increase"
      : direction === "decrease"
        ? "decrease"
        : direction === "unchanged"
          ? "no change"
          : "change unavailable";
  const deltaText = delta === null ? "" : formatDelta(delta);
  const magnitudeText = delta === null ? "" : formatDelta(Math.abs(delta)).replace(/^\+/, "");
  const presentation =
    tone === "allocation" && (direction === "increase" || direction === "decrease")
      ? "allocation-change"
      : direction;
  const accessibleText =
    direction === "unavailable"
      ? `Preview ${previewText}. Change unavailable.`
      : direction === "unchanged"
        ? `Preview ${previewText}. No change from baseline.`
        : `Preview ${previewText}. ${direction === "increase" ? "Increased" : "Decreased"} by ${magnitudeText} from baseline ${baselineText}.`;
  const visual = (
    <>
      <span aria-hidden="true" className="preview-change__value">
        {variant === "scoreboard" ? "Preview " : ""}
        {previewText}
      </span>
      {direction !== "unavailable" ? (
        <span aria-hidden="true" className="preview-change__delta">
          {changeIcon(direction)} {deltaText} {directionText}
        </span>
      ) : null}
      <span className="sr-only">{accessibleText}</span>
    </>
  );

  return variant === "scoreboard" ? (
    <small className={`preview-impact preview-impact--${direction}`}>{visual}</small>
  ) : (
    <span className={`preview-value preview-value--${presentation}`}>{visual}</span>
  );
}

function previewAnnouncement(
  label: string,
  baseline: number | null | undefined,
  preview: number | null | undefined,
  formatValue: (value: unknown) => string,
): string {
  const direction = changeDirection(baseline, preview);
  if (direction === "unavailable") return `${label} unavailable.`;
  if (direction === "unchanged") return `${label} unchanged at ${formatValue(preview)}.`;
  return `${label} ${direction === "increase" ? "increased" : "decreased"} to ${formatValue(preview)}.`;
}

export function CalculationInspector({
  player,
  attributeName,
  baseline,
  preview = null,
  metrics = [],
  pending = false,
  previewError,
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

  const rawRows = buildCalculationRawMetricRows(baseline, preview, pending);
  const componentRows = buildCalculationComponentRows(baseline, preview, metrics, pending);
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
    <section
      className="calculation-inspector workbench-panel"
      aria-busy={pending}
      aria-label={`${identifierLabel(attributeName)} authoritative explanation for ${player.displayName}`}
      role="region"
      tabIndex={0}
    >
      <div className="calculation-inspector__summary">
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

        <SectionHelp title="How to read this authoritative explanation">
          <p>
            This panel traces the selected player through the shared server-side attribute
            evaluator. Baseline values come from the active formula; preview values come from the
            latest validated session proposal. The browser presents those results without
            recreating or approximating the rating calculation.
          </p>
          <p>
            Rating is the final 25–99 output. Composite percentile describes the player’s position
            within the eligible cohort, while weighted composite is the server’s combined value
            before the rating scale is applied. The cohort count shows how many comparable players
            participated in that population-relative calculation.
          </p>
          <p>
            The eligibility badge indicates whether the player passed the formula’s required-input
            and minimum-sample gates. When a preview is still being validated, the workbench does
            not present an older result as though it belonged to the current edits.
          </p>
          <p>
            Preview cards use green with an upward arrow for an increased returned value and red
            with a downward arrow for a decrease. The signed delta and direction word repeat that
            meaning without color; unchanged and unavailable results remain neutral.
          </p>
        </SectionHelp>

        {pending ? (
          <p className="preview-pending" role="status">
            Updating the authoritative preview. Baseline stats remain visible while prior preview
            values stay hidden.
          </p>
        ) : null}

        {!pending && previewError ? (
          <StatusPanel title="Preview unavailable" tone="error" compact>
            {previewError} Baseline stats remain available for reference.
          </StatusPanel>
        ) : null}

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
          {!pending && preview ? (
            <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">
              Authoritative preview updated. {previewAnnouncement("Rating", baseline.rating, preview.rating, formatNumber)}{" "}
              {previewAnnouncement(
                "Composite percentile",
                baseline.compositePercentile,
                preview.compositePercentile,
                formatPercent,
              )}{" "}
              {previewAnnouncement(
                "Weighted composite",
                baseline.composite,
                preview.composite,
                formatNumber,
              )}
            </p>
          ) : null}
          <article>
            <span>Rating</span>
            <strong className="calculation-scoreboard__baseline">
              <span>Baseline</span> {formatNumber(baseline.rating)}
            </strong>
            <PreviewChange
              baseline={baseline.rating}
              preview={preview?.rating}
              pending={pending}
              formatValue={formatNumber}
              formatDelta={formatSignedNumber}
              variant="scoreboard"
            />
          </article>
          <article>
            <span>Composite percentile</span>
            <strong className="calculation-scoreboard__baseline">
              <span>Baseline</span> {formatPercent(baseline.compositePercentile)}
            </strong>
            <PreviewChange
              baseline={baseline.compositePercentile}
              preview={preview?.compositePercentile}
              pending={pending}
              formatValue={formatPercent}
              formatDelta={formatSignedPercent}
              variant="scoreboard"
            />
          </article>
          <article>
            <span>Weighted composite</span>
            <strong className="calculation-scoreboard__baseline">
              <span>Baseline</span> {formatNumber(baseline.composite)}
            </strong>
            <PreviewChange
              baseline={baseline.composite}
              preview={preview?.composite}
              pending={pending}
              formatValue={formatNumber}
              formatDelta={formatSignedNumber}
              variant="scoreboard"
            />
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
      </div>

      <div className="calculation-inspector__details">
        <details className="calculation-section calculation-detail" open>
          <summary className="section-heading calculation-detail__summary">
            <span>
              <span className="eyebrow">Source values</span>
              <span
                className="calculation-detail__title"
                id="raw-metrics-heading"
                role="heading"
                aria-level={3}
              >
                Raw metrics
              </span>
            </span>
            <span className="calculation-detail__summary-copy">
              Missing values remain empty; the client does not impute or calculate replacements.
            </span>
          </summary>
          <div className="calculation-detail__content" aria-labelledby="raw-metrics-heading">
            <SectionHelp title="How to read raw metrics">
              <p>
                Raw metrics are the source or derived player values supplied to the selected
                attribute formula. They are the evidence the evaluator ranks or transforms before
                applying component weights. Formula tuning normally changes how these inputs are
                interpreted, not the underlying player data itself.
              </p>
              <p>
                Baseline and preview columns let you verify that a proposal is being tested against
                the same player inputs. A missing state is intentional: the client leaves absent
                values empty and relies on the server’s eligibility rules instead of inventing a
                replacement.
              </p>
            </SectionHelp>
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
          </div>
        </details>

        <details className="calculation-section calculation-detail" open>
          <summary className="section-heading calculation-detail__summary">
            <span>
              <span className="eyebrow">API calculation detail</span>
              <span
                className="calculation-detail__title"
                id="component-breakdown-heading"
                role="heading"
                aria-level={3}
              >
                Component breakdown
              </span>
            </span>
            <span className="calculation-detail__summary-copy">
              Values below are rendered exactly as returned; no rating formula runs in the browser.
            </span>
          </summary>
          <div className="calculation-detail__content" aria-labelledby="component-breakdown-heading">
            <SectionHelp title="How to read the component breakdown">
              <p>
                Each row follows one declared formula component from its cohort-relative percentile
                through its normalized weight to its contribution. Direction rules determine which
                performance values rank favorably; changing a direction can therefore change the
                percentile before the weight is applied.
              </p>
              <p>
                Normalized weights are the server-validated shares used by the evaluator and total
                100% across the attribute. Contribution shows the amount each component supplies to
                the weighted composite. Compare baseline and preview columns to see exactly where a
                proposed weight or direction change altered the calculation; displayed rounding may
                make tiny differences appear equal.
              </p>
              <p>
                Each changed preview cell includes its new value, signed difference, and an arrow:
                percentile and contribution increases are green, while decreases are red. A changed
                normalized weight is blue because it describes an allocation shift—not a judgment
                that the formula is inherently better or worse. Its arrow still shows direction.
              </p>
            </SectionHelp>
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
                      <td>
                        <PreviewChange
                          baseline={row.baselinePercentile}
                          preview={row.previewPercentile}
                          pending={pending}
                          formatValue={formatPercent}
                          formatDelta={formatSignedPercent}
                          variant="table"
                        />
                      </td>
                      <td>{formatPercent(row.baselineWeight)}</td>
                      <td>
                        <PreviewChange
                          baseline={row.baselineWeight}
                          preview={row.previewWeight}
                          pending={pending}
                          formatValue={formatPercent}
                          formatDelta={formatSignedPercent}
                          tone="allocation"
                          variant="table"
                        />
                      </td>
                      <td>{formatNumber(row.baselineContribution)}</td>
                      <td>
                        <PreviewChange
                          baseline={row.baselineContribution}
                          preview={row.previewContribution}
                          pending={pending}
                          formatValue={formatNumber}
                          formatDelta={formatSignedNumber}
                          variant="table"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </details>
      </div>
    </section>
  );
}
