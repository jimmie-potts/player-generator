import type {
  FormulaDocument,
  FormulaMetricDefinition,
  MetricMetadata,
} from "../api/types";
import { normalizedComponentWeights } from "../domain/editor";
import { formatPercent, identifierLabel } from "../domain/format";
import { SectionHelp } from "./SectionHelp";

interface GlossaryEntry {
  definition: string;
  term: string;
}

interface GlossaryCategory {
  description: string;
  entries: readonly GlossaryEntry[];
  id: string;
  title: string;
}

const GLOSSARY_CATEGORIES: readonly GlossaryCategory[] = [
  {
    id: "formula-design",
    title: "Formula design",
    description:
      "The building blocks that turn reference metrics into explainable player ratings.",
    entries: [
      {
        term: "Attribute",
        definition:
          "A named player rating produced by the declarative formula, such as Playmaking or Overall. The current scales use the configured 25–99 rating range.",
      },
      {
        term: "Metric",
        definition:
          "A direct reference-data field or a declared derived measure used by a formula component.",
      },
      {
        term: "Component",
        definition:
          "One metric together with its weight and direction inside an attribute formula.",
      },
      {
        term: "Input metric",
        definition:
          "A metric read directly from the validated reference package without a browser-side calculation.",
      },
      {
        term: "Ratio metric",
        definition: "A declared numerator divided by a declared denominator.",
      },
      {
        term: "Stabilized percentage",
        definition:
          "A shooting percentage blended with the season league percentage and a configured number of prior attempts. The shared engine calculates (made + league percentage × prior attempts) ÷ (attempted + prior attempts).",
      },
      {
        term: "Scheduled ratio",
        definition:
          "An observed value compared with a formula-declared season schedule. The current availability metric divides games played by scheduled games and bounds the result from 0 through 1.",
      },
      {
        term: "Weight",
        definition:
          "A component’s declared nonnegative allocation before authoritative normalization.",
      },
      {
        term: "Normalized weight",
        definition:
          "The final component share used by the evaluator after all declared weights are normalized to sum to 1.",
      },
      {
        term: "Direction",
        definition:
          "Whether higher or lower metric values are treated as better. A lower direction reverses only the component percentile; it does not change the raw metric.",
      },
      {
        term: "Contribution",
        definition:
          "A component percentile multiplied by its normalized weight. Component contributions are added to form the weighted composite.",
      },
      {
        term: "Weighted composite",
        definition: "The sum of every weighted component contribution for an attribute.",
      },
      {
        term: "Rerank composite",
        definition:
          "A formula instruction to rank the weighted composite within its eligible cohort before the rating scale is applied.",
      },
      {
        term: "Rating scale",
        definition:
          "The declared mapping from a composite percentile to the attribute’s final rating range.",
      },
      {
        term: "Percentile anchor",
        definition:
          "A percentile-and-rating control point on a rating scale. The evaluator linearly interpolates between adjacent anchors and applies the formula’s rounding rule.",
      },
      {
        term: "Formula version",
        definition:
          "The human-managed version stored inside a formula document. A proposal version identifies an exported candidate but does not activate it.",
      },
    ],
  },
  {
    id: "calculation-explanation",
    title: "Calculation and explanation",
    description:
      "Terms used by the server-owned trace that explains how one player received a rating.",
    entries: [
      {
        term: "Authoritative",
        definition:
          "Calculated or validated by the preview API and shared Python attribute engine rather than recreated in TypeScript.",
      },
      {
        term: "Baseline",
        definition:
          "The result produced by the active formula before any workbench session adjustments.",
      },
      {
        term: "Preview",
        definition:
          "A request-local evaluation of a server-validated temporary formula over the same complete season cohort. A preview is discarded after the response and does not overwrite active configuration.",
      },
      {
        term: "Raw metric",
        definition:
          "The source or derived numerical value used before percentile ranking and component weighting.",
      },
      {
        term: "Component percentile",
        definition:
          "The player’s direction-aware relative position for one component within the eligible cohort.",
      },
      {
        term: "Composite percentile",
        definition:
          "The player’s relative position for the combined weighted composite when the formula declares composite reranking.",
      },
      {
        term: "Rating",
        definition:
          "The final value produced by mapping the authoritative composite percentile through the declared rating scale and rounding rule.",
      },
      {
        term: "Eligibility gate",
        definition:
          "The required metrics and minimum sample thresholds a player must satisfy for an attribute calculation.",
      },
      {
        term: "Eligible cohort",
        definition:
          "The players who pass the selected attribute’s eligibility gate and participate in its population-relative calculation.",
      },
      {
        term: "Excluded",
        definition:
          "Present in the reference cohort but omitted from an attribute calculation after failing its eligibility gate. Excluded values are not imputed.",
      },
      {
        term: "Missing",
        definition:
          "A required value was unavailable. The workbench labels missing values instead of estimating replacements.",
      },
      {
        term: "Unsupported",
        definition:
          "The selected formula or returned explanation does not define the requested value.",
      },
      {
        term: "Delta (Δ)",
        definition:
          "The preview value minus the baseline value. A zero delta means the displayed value did not change.",
      },
      {
        term: "Impact cue",
        definition:
          "A green upward or positive marker means an outcome value increased; a red downward or negative marker means it decreased. For ranks, green means movement toward rank 1 and red means movement away. Blue marks a changed formula allocation, which is not inherently a gain or loss. Text and symbols always accompany color.",
      },
    ],
  },
  {
    id: "comparison-session",
    title: "Comparison and session",
    description:
      "How the workbench selects players and keeps baseline and preview effects comparable.",
    entries: [
      {
        term: "Cohort",
        definition:
          "The complete configured season population used for priors, percentiles, and ranks. It is larger than the players visible in the comparison table.",
      },
      {
        term: "Fixed cohort",
        definition:
          "The same complete player population used for baseline and preview so their percentiles and ranks can be compared.",
      },
      {
        term: "Comparison set",
        definition:
          "The players currently shown in the table and requested for detailed preview results. Changing this visible set does not change the complete cohort used to calculate ratings and ranks.",
      },
      {
        term: "Representative player",
        definition:
          "One of the highest baseline-overall eligible players selected from a populated talent tier for the default comparison.",
      },
      {
        term: "Tier sample",
        definition:
          "The default comparison set, containing a chosen number of representative players from every populated talent tier.",
      },
      {
        term: "Top 25",
        definition:
          "The 25 highest players by the active formula’s baseline overall rank. Membership and order stay fixed while a proposal is edited so the before-and-after comparison remains stable.",
      },
      {
        term: "Custom list",
        definition:
          "A session-only comparison set containing up to 25 players selected through search. It replaces the visible tier or Top 25 set while active and disappears when the page is reloaded.",
      },
      {
        term: "Talent tier",
        definition:
          "A label derived from the formula’s configured overall-rating ranges, such as Rotation, Starter, or Superstar.",
      },
      {
        term: "Overall (OVR)",
        definition:
          "A declared attribute built from its own configured components. It is not an average of the other displayed attributes.",
      },
      {
        term: "Rank",
        definition:
          "A player’s position across the complete cohort, with rank 1 highest. Comparison ties share the minimum occupied rank.",
      },
      {
        term: "Baseline overall rank",
        definition:
          "A player’s overall position under the active formula before session edits. The Top 25 set uses this value for stable membership and ordering.",
      },
      {
        term: "Rank movement",
        definition:
          "The baseline rank minus the preview rank, so positive movement is toward rank 1.",
      },
      {
        term: "Largest gain or loss",
        definition:
          "Every displayed player tied for the largest positive or negative selected-attribute delta.",
      },
    ],
  },
  {
    id: "identity-integrity",
    title: "Identity and integrity",
    description:
      "Version and hash terms that prevent results from different data or formula states from being mixed.",
    entries: [
      {
        term: "Active formula",
        definition:
          "The configured formula used for baselines and as the source document for temporary proposals.",
      },
      {
        term: "Proposal version",
        definition:
          "The designer-supplied formula version embedded in a temporary and exported proposal. It does not replace the active formula identity.",
      },
      {
        term: "Reference package",
        definition:
          "The integrity-checked, versioned reference-data package loaded by the preview API.",
      },
      {
        term: "Content hash",
        definition:
          "A SHA-256 identity for the exact reference-package contents.",
      },
      {
        term: "Formula document hash",
        definition: "A SHA-256 identity for the exact active formula document.",
      },
      {
        term: "API version",
        definition: "The version of the preview service’s HTTP request and response contract.",
      },
      {
        term: "Stale context",
        definition:
          "The reference package, active formula, or configured season changed after the browser loaded its baseline, so the workbench must reload rather than combine mismatched results.",
      },
      {
        term: "Session change",
        definition:
          "An unsaved in-memory edit that disappears on reset, reload, or close.",
      },
      {
        term: "Exported proposal",
        definition:
          "The exact full formula document returned by the latest successful server preview. Export downloads the document but does not save or activate it on the server.",
      },
    ],
  },
];

export interface GlossaryPageProps {
  formula: FormulaDocument | null;
  metrics: readonly MetricMetadata[];
}

function metricKindDetails(definition: FormulaMetricDefinition | undefined): string {
  if (!definition) return "Definition unavailable";
  if (definition.kind === "input") {
    return `Reference field: ${identifierLabel(definition.field)}`;
  }
  if (definition.kind === "stabilizedPercentage") {
    return `${identifierLabel(definition.kind)} · ${definition.priorAttempts.toLocaleString()} prior attempts`;
  }
  if (definition.kind === "scheduledRatio") {
    return `${identifierLabel(definition.kind)} · ${Object.keys(definition.schedule).length} declared seasons`;
  }
  return identifierLabel(definition.kind);
}

function componentDirection(direction: "higher" | "lower"): string {
  return direction === "higher" ? "Higher is better" : "Lower is better";
}

function LoadedModelCatalog({
  formula,
  metrics,
}: GlossaryPageProps) {
  if (!formula) {
    return (
      <p className="glossary-page__empty" role="status">
        Load the workbench to see the active attributes, component allocations, metrics, scales,
        and talent tiers.
      </p>
    );
  }

  const metadataByName = new Map(metrics.map((metric) => [metric.name, metric]));
  const normalizedWeightsByAttribute = new Map(
    formula.attributes.map((attribute) => {
      const shares = normalizedComponentWeights(
        attribute.components.map(({ weight }) => weight),
      );
      return [
        attribute.name,
        new Map(
          attribute.components.map((component, index) => [
            component.metric,
            shares[index] ?? 0,
          ]),
        ),
      ];
    }),
  );

  return (
    <div className="model-catalog">
      <p className="model-catalog__identity">
        Active formula <strong>{formula.formulaVersion}</strong> · schema {formula.schemaVersion}
      </p>

      <section className="model-catalog__section" aria-labelledby="catalog-attributes-title">
        <h3 id="catalog-attributes-title">Attributes</h3>
        <p>
          These definitions come from the loaded formula. Component percentages are the active
          weights normalized to shares of their attribute; directions also describe the active
          baseline, not unsaved workbench changes.
        </p>
        <div className="model-catalog__attributes">
          {formula.attributes.map((attribute) => {
            const eligibility = formula.eligibilityRules[attribute.eligibilityRule];
            const cohort = formula.cohorts[attribute.cohort];
            const scale = formula.ratingScales[attribute.ratingScale];
            return (
              <article className="model-catalog-card" key={attribute.name}>
                <h4>{identifierLabel(attribute.name)}</h4>
                <p>
                  {attribute.rerankComposite
                    ? "Its weighted composite is reranked in the eligible cohort before the rating scale is applied."
                    : "Its weighted composite is mapped directly through the declared rating scale."}
                </p>
                <dl className="model-catalog-card__facts">
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
                      {scale ? ` · ${scale.minimum}–${scale.maximum}` : ""}
                    </dd>
                  </div>
                  <div>
                    <dt>Minimum samples</dt>
                    <dd>
                      {eligibility && Object.keys(eligibility.minimumSamples).length
                        ? Object.entries(eligibility.minimumSamples)
                            .map(
                              ([field, minimum]) =>
                                `${identifierLabel(field)} ${minimum.toLocaleString()}`,
                            )
                            .join(" · ")
                        : "None declared"}
                    </dd>
                  </div>
                </dl>
                <h5>Active components</h5>
                <ul className="model-catalog-card__components">
                  {attribute.components.map((component) => {
                    const metadata = metadataByName.get(component.metric);
                    const normalizedWeight =
                      normalizedWeightsByAttribute
                        .get(attribute.name)
                        ?.get(component.metric) ?? 0;
                    return (
                      <li key={component.metric}>
                        <strong>{metadata?.label ?? identifierLabel(component.metric)}</strong>
                        <span>
                          {formatPercent(normalizedWeight)} · {componentDirection(component.direction)}
                        </span>
                        <p>{metadata?.description ?? "Metric description unavailable."}</p>
                      </li>
                    );
                  })}
                </ul>
              </article>
            );
          })}
        </div>
      </section>

      <section className="model-catalog__section" aria-labelledby="catalog-metrics-title">
        <h3 id="catalog-metrics-title">Metrics</h3>
        <p>
          Metric descriptions are supplied by the preview API. Uses list the active attributes that
          consume each metric.
        </p>
        {metrics.length ? (
          <dl className="model-catalog__metrics">
            {metrics.map((metric) => (
              <div key={metric.name}>
                <dt>{metric.label}</dt>
                <dd>
                  <p>{metric.description}</p>
                  <small>{metricKindDetails(formula.metrics[metric.name])}</small>
                  <span>
                    Used by: {metric.usedBy.length
                      ? metric.usedBy
                          .map(
                            (usage) => {
                              const normalizedWeight =
                                normalizedWeightsByAttribute
                                  .get(usage.attribute)
                                  ?.get(metric.name) ?? 0;
                              return `${identifierLabel(usage.attribute)} (${formatPercent(normalizedWeight)}, ${usage.direction})`;
                            },
                          )
                          .join("; ")
                      : "No active attribute"}
                  </span>
                </dd>
              </div>
            ))}
          </dl>
        ) : (
          <p role="status">Metric metadata is unavailable for the loaded formula.</p>
        )}
      </section>

      <section className="model-catalog__section" aria-labelledby="catalog-tiers-title">
        <h3 id="catalog-tiers-title">Talent tiers</h3>
        <p>
          Tiers are assigned from the final overall rating. They select representative comparison
          groups but do not change the formula cohort.
        </p>
        <ul className="model-catalog__tiers">
          {formula.talentTiers.map((tier) => (
            <li key={tier.name}>
              <strong>{identifierLabel(tier.name)}</strong>
              <span>{tier.minimum}–{tier.maximum}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

export function GlossaryPage({ formula, metrics }: GlossaryPageProps) {
  return (
    <main className="glossary-page" id="glossary" aria-labelledby="glossary-title">
      <header className="glossary-page__header">
        <p className="eyebrow">Formula Workbench guide</p>
        <h1 id="glossary-title">Glossary</h1>
        <p>
          Learn the model, calculation, comparison, and integrity terms used throughout the
          workbench. Stable concepts are documented here; the loaded model catalog is generated from
          the active API formula and metric metadata so its details stay current.
        </p>
      </header>

      <nav className="glossary-page__nav" aria-label="Glossary sections">
        <ul>
          {GLOSSARY_CATEGORIES.map((category) => (
            <li key={category.id}>
              <a href={`#glossary-${category.id}`}>{category.title}</a>
            </li>
          ))}
          <li><a href="#loaded-model-catalog">Loaded model catalog</a></li>
        </ul>
      </nav>

      <div className="glossary-page__categories">
        {GLOSSARY_CATEGORIES.map((category) => (
          <section
            className="glossary-category"
            id={`glossary-${category.id}`}
            key={category.id}
            aria-labelledby={`glossary-${category.id}-title`}
          >
            <h2 id={`glossary-${category.id}-title`}>{category.title}</h2>
            <p>{category.description}</p>
            <dl className="glossary-list">
              {category.entries.map((entry) => (
                <div className="glossary-entry" key={entry.term}>
                  <dt><dfn>{entry.term}</dfn></dt>
                  <dd>{entry.definition}</dd>
                </div>
              ))}
            </dl>
          </section>
        ))}
      </div>

      <section
        className="glossary-category glossary-category--model"
        id="loaded-model-catalog"
        aria-labelledby="loaded-model-catalog-title"
      >
        <h2 id="loaded-model-catalog-title">Loaded model catalog</h2>
        <p>
          This catalog describes the active formula returned by the preview API. It is a reference
          view only and does not include or apply unsaved session adjustments.
        </p>
        <SectionHelp title="Why this catalog follows the API">
          <p>
            Attributes, component allocations, directions, scales, and tiers can change when a new
            formula version is loaded. Reading them from the API avoids presenting old hardcoded
            details as current. The browser displays this metadata but does not evaluate it.
          </p>
        </SectionHelp>
        <LoadedModelCatalog formula={formula} metrics={metrics} />
      </section>
    </main>
  );
}
