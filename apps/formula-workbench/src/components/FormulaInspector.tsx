import type {
  AttributeFormula,
  Direction,
  EligibilityRule,
  FormulaCohort,
  MetricMetadata,
  RatingScale,
} from "../api/types";
import { formatPercent, identifierLabel } from "../domain/format";
import { SectionHelp } from "./SectionHelp";
import { StatusPanel } from "./StatusPanel";

export interface FormulaComponentEditorRow {
  metric: MetricMetadata;
  weight: number | string;
  direction: Direction;
  baselineDirection: Direction;
  inverseDirection: boolean;
  weightError?: string;
  directionError?: string;
}

export interface RatingAnchorEditorRow {
  percentile: number | string;
  rating: number | string;
  percentileError?: string;
  ratingError?: string;
}

export interface FormulaInspectorProps {
  attribute: AttributeFormula | null;
  formulaVersion: string;
  eligibilityRule: EligibilityRule | null;
  cohort: FormulaCohort | null;
  ratingScale: RatingScale | null;
  components: readonly FormulaComponentEditorRow[];
  anchors: readonly RatingAnchorEditorRow[];
  dirty?: boolean;
  disabled?: boolean;
  validationMessages?: readonly string[];
  onWeightChange: (metricName: string, value: number) => void;
  onInverseDirectionChange: (metricName: string, inverse: boolean) => void;
  onAnchorChange: (
    index: number,
    field: "percentile" | "rating",
    value: string,
  ) => void;
  onResetAttribute: () => void;
}

function inputId(attributeName: string, part: string): string {
  return `formula-${attributeName}-${part}`.replace(/[^A-Za-z0-9_-]/g, "-");
}

function metricDefinition(row: FormulaComponentEditorRow): string {
  const details = [identifierLabel(row.metric.kind)];
  if (row.metric.field) {
    details.push(`field: ${row.metric.field}`);
  } else if (row.metric.inputs.length) {
    details.push(`inputs: ${row.metric.inputs.join(", ")}`);
  }
  return details.join(" · ");
}

function numericWeight(weight: FormulaComponentEditorRow["weight"]): number {
  return typeof weight === "number" && Number.isFinite(weight)
    ? Math.max(0, Math.min(1, weight))
    : 0;
}

export function FormulaInspector({
  attribute,
  formulaVersion,
  eligibilityRule,
  cohort,
  ratingScale,
  components,
  anchors,
  dirty = false,
  disabled = false,
  validationMessages = [],
  onWeightChange,
  onInverseDirectionChange,
  onAnchorChange,
  onResetAttribute,
}: FormulaInspectorProps) {
  if (!attribute) {
    return (
      <StatusPanel title="Select an attribute" tone="empty">
        Choose an attribute to inspect its authoritative components and calculation rules.
      </StatusPanel>
    );
  }

  const attributeLabel = identifierLabel(attribute.name);

  return (
    <section
      className="formula-inspector workbench-panel"
      aria-labelledby="formula-inspector-title"
      aria-label={`${attributeLabel} formula controls`}
      tabIndex={0}
    >
      <div className="panel-heading panel-heading--with-actions">
        <div>
          <p className="eyebrow">Formula · v{formulaVersion}</p>
          <h2 id="formula-inspector-title">{attributeLabel}</h2>
          <p>
            {attribute.rerankComposite
              ? "Components are combined, reranked in the fixed cohort, then mapped to the rating scale."
              : "Components are combined and mapped through the declared rating scale."}
          </p>
          <SectionHelp title="How the selected formula produces a rating">
            <p>
              Each component becomes a direction-aware percentile inside the eligible cohort. The
              shared engine combines those percentiles using the normalized allocation below and,
              when declared, reranks the composite before applying the 25–99 rating scale. This
              browser changes only existing weights, directions, anchors, and proposal identity;
              the preview API remains the evaluator and validator.
            </p>
          </SectionHelp>
        </div>
        <button
          className="button button--ghost"
          type="button"
          onClick={onResetAttribute}
          disabled={!dirty || disabled}
        >
          Reset attribute
        </button>
      </div>

      <dl className="formula-facts">
        <div>
          <dt>Eligibility</dt>
          <dd>{identifierLabel(attribute.eligibilityRule)}</dd>
        </div>
        <div>
          <dt>Cohort</dt>
          <dd>{cohort?.groupBy.map(identifierLabel).join(" + ") || "Not declared"}</dd>
        </div>
        <div>
          <dt>Scale</dt>
          <dd>
            {identifierLabel(attribute.ratingScale)}
            {ratingScale ? ` · ${ratingScale.minimum}–${ratingScale.maximum}` : ""}
          </dd>
        </div>
        <div>
          <dt>Percentile output</dt>
          <dd>{attribute.percentileOutput ? identifierLabel(attribute.percentileOutput) : "Internal"}</dd>
        </div>
      </dl>

      <details className="formula-disclosure">
        <summary>Eligibility and rating rules</summary>
        <div className="formula-disclosure__content">
          <SectionHelp title="Why eligibility and cohorts matter">
            <p>
              Eligibility decides which players participate in this attribute’s percentile
              calculation. Required metrics must be present and every minimum sample threshold must
              pass; excluded players receive no imputed replacement. Because percentiles are
              population-relative, the cohort definition and eligible count affect every result.
            </p>
          </SectionHelp>
          <div className="formula-rule-grid">
            <section className="formula-rule-card" aria-labelledby="eligibility-heading">
              <h3 id="eligibility-heading">Eligibility gate</h3>
              {eligibilityRule ? (
                <>
                  <p>
                    Requires {eligibilityRule.requiredMetrics.map(identifierLabel).join(", ") || "no metrics"}.
                  </p>
                  {Object.keys(eligibilityRule.minimumSamples).length ? (
                    <dl className="mini-facts">
                      {Object.entries(eligibilityRule.minimumSamples).map(([field, minimum]) => (
                        <div key={field}>
                          <dt>{identifierLabel(field)}</dt>
                          <dd>≥ {minimum.toLocaleString()}</dd>
                        </div>
                      ))}
                    </dl>
                  ) : null}
                </>
              ) : (
                <p className="muted-copy">Eligibility metadata is unavailable.</p>
              )}
            </section>
            <section className="formula-rule-card" aria-labelledby="scale-heading">
              <h3 id="scale-heading">Rating scale</h3>
              <p>
                The complete anchor curve maps the authoritative composite percentile to a rating.
                All anchors travel together in a preview request.
              </p>
            </section>
          </div>
        </div>
      </details>

      {validationMessages.length ? (
        <div className="validation-summary" role="alert">
          <strong>Resolve {validationMessages.length} formula issue{validationMessages.length === 1 ? "" : "s"}</strong>
          <ul>
            {validationMessages.map((message, index) => (
              <li key={`${message}-${index}`}>{message}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <section className="formula-section" aria-labelledby="component-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Declared inputs</p>
            <h3 id="component-heading">Components</h3>
          </div>
          <p>The selected attribute always keeps one complete 100% component allocation.</p>
        </div>

        <SectionHelp title="How component weights rebalance">
          <p>
            Each slider controls one metric’s share of this attribute. Increasing or decreasing a
            component proportionally redistributes the remaining percentage across its peers, using
            stable formula order to resolve rounding, so the allocation always totals exactly 100%.
            A one-component attribute remains fixed at 100%. Direction inversion is independent and
            stays relative to the active formula.
          </p>
        </SectionHelp>

        <div className="weight-allocation" aria-labelledby="weight-allocation-title">
          <div className="weight-allocation__heading">
            <strong id="weight-allocation-title">100% component allocation</strong>
            <span>{components.length} component{components.length === 1 ? "" : "s"}</span>
          </div>
          <div
            className="weight-allocation__bar"
            role="img"
            aria-label={`${attributeLabel} component allocation totals 100 percent`}
          >
            {components.map((component, index) => (
              <span
                className={`weight-allocation__segment weight-allocation__segment--${index % 6}`}
                key={component.metric.name}
                style={{ width: `${numericWeight(component.weight) * 100}%` }}
              />
            ))}
          </div>
          <ul className="weight-allocation__legend">
            {components.map((component, index) => (
              <li key={component.metric.name}>
                <span
                  className={`weight-allocation__swatch weight-allocation__segment--${index % 6}`}
                  aria-hidden="true"
                />
                <span>{component.metric.label}</span>
                <strong>{formatPercent(numericWeight(component.weight))}</strong>
              </li>
            ))}
          </ul>
        </div>

        <div className="component-editor-list">
          {components.map((component) => {
            const weightId = inputId(attribute.name, `${component.metric.name}-weight`);
            const weightErrorId = `${weightId}-error`;
            const inverseId = inputId(attribute.name, `${component.metric.name}-inverse`);
            const directionErrorId = `${inverseId}-error`;
            const weight = numericWeight(component.weight);

            return (
              <article className="component-editor" key={component.metric.name}>
                <div className="component-editor__description">
                  <div className="component-editor__title-row">
                    <h4>{component.metric.label}</h4>
                    <span className="metric-kind">{identifierLabel(component.metric.kind)}</span>
                  </div>
                  <p>{component.metric.description}</p>
                  <small>{metricDefinition(component)}</small>
                </div>

                <label className="field-control weight-slider" htmlFor={weightId}>
                  <span className="weight-slider__heading">
                    <span>Weight</span>
                    <output htmlFor={weightId}>{formatPercent(weight)}</output>
                  </span>
                  <input
                    id={weightId}
                    name={weightId}
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={weight}
                    onChange={(event) =>
                      onWeightChange(component.metric.name, Number(event.target.value))
                    }
                    aria-label={`${component.metric.label} weight`}
                    aria-valuetext={`${Math.round(weight * 100)} percent`}
                    aria-invalid={Boolean(component.weightError)}
                    aria-describedby={component.weightError ? weightErrorId : undefined}
                    disabled={disabled || components.length === 1}
                  />
                  <small>
                    {components.length === 1
                      ? "The only component remains fixed at 100%."
                      : "Moving this slider rebalances the other component shares."}
                  </small>
                  {component.weightError ? (
                    <small className="field-error" id={weightErrorId}>
                      {component.weightError}
                    </small>
                  ) : null}
                </label>

                <div className="direction-control">
                  <span>Direction</span>
                  <strong>{identifierLabel(component.direction)}</strong>
                  <label className="switch-control" htmlFor={inverseId}>
                    <input
                      id={inverseId}
                      name={inverseId}
                      type="checkbox"
                      checked={component.inverseDirection}
                      onChange={(event) =>
                        onInverseDirectionChange(component.metric.name, event.target.checked)
                      }
                      aria-invalid={Boolean(component.directionError)}
                      aria-describedby={component.directionError ? directionErrorId : undefined}
                      disabled={disabled}
                    />
                    <span className="switch-control__track" aria-hidden="true" />
                    <span>Invert baseline {identifierLabel(component.baselineDirection)}</span>
                  </label>
                  {component.directionError ? (
                    <small className="field-error" id={directionErrorId}>
                      {component.directionError}
                    </small>
                  ) : null}
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <details className="formula-disclosure formula-disclosure--anchors">
        <summary>Rating scale and percentile anchors</summary>
        <section className="formula-section" aria-labelledby="anchor-heading">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Complete curve</p>
              <h3 id="anchor-heading">Percentile anchors</h3>
            </div>
            <p>Percentiles must rise from 0 to 1; ratings must be nondecreasing from 25 to 99.</p>
          </div>

          <SectionHelp title="How percentile anchors map ratings">
            <p>
              Anchors map a composite percentile from 0 through 1 onto the 25–99 rating scale. The
              shared engine interpolates between adjacent points and applies its declared rounding
              rule. Percentiles must increase strictly, ratings cannot decrease, and the complete
              curve is submitted together because a scale may be shared by multiple attributes.
            </p>
          </SectionHelp>

          <div className="anchor-editor-grid">
            {anchors.map((anchor, index) => {
              const percentileId = inputId(attribute.name, `anchor-${index}-percentile`);
              const ratingId = inputId(attribute.name, `anchor-${index}-rating`);
              const percentileErrorId = `${percentileId}-error`;
              const ratingErrorId = `${ratingId}-error`;

              return (
                <fieldset className="anchor-editor" key={index}>
                  <legend>Anchor {index + 1}</legend>
                  <label className="field-control" htmlFor={percentileId}>
                    <span>Percentile</span>
                    <input
                      id={percentileId}
                      name={percentileId}
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      inputMode="decimal"
                      value={anchor.percentile}
                      onChange={(event) => onAnchorChange(index, "percentile", event.target.value)}
                      aria-invalid={Boolean(anchor.percentileError)}
                      aria-describedby={anchor.percentileError ? percentileErrorId : undefined}
                      disabled={disabled}
                    />
                    {anchor.percentileError ? (
                      <small className="field-error" id={percentileErrorId}>
                        {anchor.percentileError}
                      </small>
                    ) : null}
                  </label>
                  <label className="field-control" htmlFor={ratingId}>
                    <span>Rating</span>
                    <input
                      id={ratingId}
                      name={ratingId}
                      type="number"
                      min="25"
                      max="99"
                      step="1"
                      inputMode="numeric"
                      value={anchor.rating}
                      onChange={(event) => onAnchorChange(index, "rating", event.target.value)}
                      aria-invalid={Boolean(anchor.ratingError)}
                      aria-describedby={anchor.ratingError ? ratingErrorId : undefined}
                      disabled={disabled}
                    />
                    {anchor.ratingError ? (
                      <small className="field-error" id={ratingErrorId}>
                        {anchor.ratingError}
                      </small>
                    ) : null}
                  </label>
                </fieldset>
              );
            })}
          </div>
        </section>
      </details>
    </section>
  );
}
