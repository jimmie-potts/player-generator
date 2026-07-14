import { useMemo, useState } from "react";

import type { PreviewApiClient } from "./api/client";
import type {
  AttributeCalculation,
  JsonScalar,
  PlayerSummary,
  PreviewPlayerResult,
} from "./api/types";
import {
  AttributeSidebar,
  type AttributeSidebarRow,
} from "./components/AttributeSidebar";
import {
  CalculationInspector,
} from "./components/CalculationInspector";
import { ComparisonModeTabs } from "./components/ComparisonModeTabs";
import { GlossaryPage } from "./components/GlossaryPage";
import {
  FormulaInspector,
  type FormulaComponentEditorRow,
  type RatingAnchorEditorRow,
} from "./components/FormulaInspector";
import {
  PlayerComparison,
  type ComparisonMeasure,
  type ComparisonVisualState,
  type PlayerComparisonGroup,
  type PlayerComparisonRow,
} from "./components/PlayerComparison";
import { PlayerSearch } from "./components/PlayerSearch";
import { SectionHelp } from "./components/SectionHelp";
import { StatusPanel } from "./components/StatusPanel";
import { WorkbenchHeader, type WorkbenchPreviewStatus } from "./components/WorkbenchHeader";
import { normalizedComponentWeights } from "./domain/editor";
import { identifierLabel } from "./domain/format";
import {
  MAX_CUSTOM_PLAYERS,
  useWorkbench,
  type WorkbenchController,
} from "./hooks/useWorkbench";

function numeric(value: JsonScalar | undefined): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function inverseDirection(direction: "higher" | "lower"): "higher" | "lower" {
  return direction === "higher" ? "lower" : "higher";
}

function issueFor(
  issues: ReadonlyArray<{ path: string; message: string }>,
  path: string,
): string | undefined {
  return issues.find((issue) => issue.path === path)?.message;
}

function calculationState(
  calculation: AttributeCalculation | undefined,
  rating: number | null,
): AttributeSidebarRow["ratingState"] {
  if (!calculation) return "unsupported";
  if (!calculation.eligible) {
    return calculation.ineligibilityReasons.some(({ kind }) => kind === "missingMetric")
      ? "missing"
      : "excluded";
  }
  return rating === null ? "missing" : "available";
}

function emptyMeasure(value: number | null, rank: number | null): ComparisonMeasure {
  return {
    baseline: value,
    preview: value,
    delta: value === null ? null : 0,
    baselineRank: rank,
    previewRank: rank,
    rankMovement: rank === null ? null : 0,
  };
}

function comparisonMeasure(
  result: PreviewPlayerResult | undefined,
  field: string,
  baseline: number | null,
  baselineRank: number | null,
  kind: "attribute" | "overall",
): ComparisonMeasure {
  if (!result) return emptyMeasure(baseline, baselineRank);
  const rank = kind === "attribute" ? result.attributeRank : result;
  const change = result.changes[field];
  return {
    baseline: numeric(change?.baselineValue),
    preview: numeric(change?.previewValue),
    delta: change?.delta ?? null,
    baselineRank: rank.baselineRank,
    previewRank: rank.previewRank,
    rankMovement: rank.rankMovement,
  };
}

function rowState(
  result: PreviewPlayerResult | undefined,
  attributeName: string,
  previewFailed: boolean,
): { state: ComparisonVisualState; message?: string } {
  if (previewFailed) {
    return { state: "failure", message: "The latest authoritative preview failed." };
  }
  if (!result) return { state: "no-change" };
  const calculation = result.previewCalculation.attributes[attributeName];
  if (!calculation) {
    return { state: "missing", message: "This attribute is unsupported in the preview." };
  }
  if (!calculation.eligible) {
    const missing = calculation.ineligibilityReasons.some(
      ({ kind }) => kind === "missingMetric",
    );
    return {
      state: missing ? "missing" : "excluded",
      message: missing
        ? "One or more required inputs are missing."
        : "The player did not pass the formula eligibility gate.",
    };
  }
  const delta = result.changes[attributeName]?.delta;
  return delta === null || delta === 0 ? { state: "no-change" } : { state: "changed" };
}

function withSignals(rows: PlayerComparisonRow[]): PlayerComparisonRow[] {
  const deltas = rows
    .map((row) => row.attribute.delta)
    .filter((value): value is number => typeof value === "number" && value !== 0);
  if (!deltas.length) return rows;
  const largestGain = Math.max(...deltas);
  const largestLoss = Math.min(...deltas);
  return rows.map((row) => {
    if (row.state !== "changed") return row;
    if (largestGain > 0 && row.attribute.delta === largestGain) {
      return { ...row, state: "largest-gain", stateMessage: "Largest positive change." };
    }
    if (largestLoss < 0 && row.attribute.delta === largestLoss) {
      return { ...row, state: "largest-loss", stateMessage: "Largest negative change." };
    }
    return row;
  });
}

export interface AppProps {
  client?: PreviewApiClient;
}

type WorkbenchPage = "workbench" | "glossary";

interface WorkbenchNavigationProps {
  page: WorkbenchPage;
  onNavigate: (page: WorkbenchPage) => void;
}

function WorkbenchNavigation({ page, onNavigate }: WorkbenchNavigationProps) {
  return (
    <nav className="workbench-page-nav" aria-label="Formula workbench pages">
      <button
        className="workbench-page-nav__item"
        type="button"
        aria-current={page === "workbench" ? "page" : undefined}
        onClick={() => onNavigate("workbench")}
      >
        Workbench
      </button>
      <button
        className="workbench-page-nav__item"
        type="button"
        aria-current={page === "glossary" ? "page" : undefined}
        onClick={() => onNavigate("glossary")}
      >
        Glossary
      </button>
    </nav>
  );
}

export function App({ client }: AppProps) {
  const workbench = useWorkbench(client);
  const [page, setPage] = useState<WorkbenchPage>("workbench");

  if (page === "glossary") {
    return (
      <div className="workbench-app glossary-app">
        <WorkbenchNavigation page={page} onNavigate={setPage} />
        <GlossaryPage formula={workbench.formula} metrics={workbench.metrics} />
      </div>
    );
  }

  return <WorkbenchView workbench={workbench} onNavigate={setPage} />;
}

interface WorkbenchViewProps {
  workbench: WorkbenchController;
  onNavigate: (page: WorkbenchPage) => void;
}

function WorkbenchView({ workbench, onNavigate }: WorkbenchViewProps) {
  const selectedFormula = workbench.formula?.attributes.find(
    ({ name }) => name === workbench.selectedAttribute,
  );
  const selectedEditor = workbench.editor?.attributes.find(
    ({ name }) => name === workbench.selectedAttribute,
  );
  const selectedScale = workbench.editor?.ratingScales.find(
    ({ name }) => name === selectedFormula?.ratingScale,
  );
  const activeScale = selectedFormula
    ? workbench.formula?.ratingScales[selectedFormula.ratingScale]
    : null;
  const selectedDetail =
    workbench.detail?.player.playerId === workbench.selectedPlayerId
      ? workbench.detail
      : null;
  const previewCandidate = workbench.preview;
  const previewMatchesActivePlayers = Boolean(
    previewCandidate &&
      previewCandidate.players.length === workbench.comparisonPlayers.length &&
      previewCandidate.players.every(
        ({ playerId }, index) =>
          playerId === workbench.comparisonPlayers[index]?.playerId,
      ),
  );
  const currentPreview =
    previewCandidate &&
    previewMatchesActivePlayers &&
    previewCandidate.players.every(
      ({ attributeRank }) => attributeRank.attribute === workbench.selectedAttribute,
    ) &&
    previewCandidate.previewDocument.formulaVersion ===
      workbench.editor?.proposalVersion.trim()
      ? previewCandidate
      : null;
  const selectedPreviewPlayer = currentPreview?.players.find(
    ({ playerId }) => playerId === workbench.selectedPlayerId,
  );
  const baselineCalculation =
    selectedPreviewPlayer?.baselineCalculation ?? selectedDetail?.calculation ?? null;
  const previewCalculation = selectedPreviewPlayer?.previewCalculation ?? null;
  const selectedCalculation = previewCalculation ?? baselineCalculation;
  const selectedValues =
    selectedPreviewPlayer?.preview ?? selectedDetail?.baseline ?? null;

  const attributeRows = useMemo<AttributeSidebarRow[]>(
    () =>
      workbench.attributes.map((attribute) => {
        const rating = numeric(selectedValues?.[attribute.name]);
        const calculation = selectedCalculation?.attributes[attribute.name];
        return {
          name: attribute.name,
          rating,
          ratingState: calculationState(calculation, rating),
          dirty:
            workbench.dirtyAttributes.has(attribute.name) ||
            workbench.dirtyScales.has(attribute.ratingScale),
        };
      }),
    [
      selectedCalculation,
      selectedValues,
      workbench.attributes,
      workbench.dirtyAttributes,
      workbench.dirtyScales,
    ],
  );

  const componentRows = useMemo<FormulaComponentEditorRow[]>(() => {
    if (!selectedEditor) return [];
    const normalizedWeights = normalizedComponentWeights(
      selectedEditor.components.map(({ weight }) => weight),
    );
    return selectedEditor.components.flatMap((component, index) => {
      const metric = workbench.metricsByName.get(component.metric);
      if (!metric) return [];
      const path = `attributes.${selectedEditor.name}.components.${component.metric}`;
      return [
        {
          metric,
          weight: Number.isFinite(component.weight) ? normalizedWeights[index] ?? 0 : "",
          direction: component.direction,
          baselineDirection: component.baselineDirection,
          inverseDirection: component.direction !== component.baselineDirection,
          weightError: issueFor(workbench.validationIssues, `${path}.weight`),
          directionError: issueFor(workbench.validationIssues, `${path}.direction`),
        },
      ];
    });
  }, [selectedEditor, workbench.metricsByName, workbench.validationIssues]);

  const anchorRows = useMemo<RatingAnchorEditorRow[]>(
    () =>
      (selectedScale?.anchors ?? []).map((anchor, index) => ({
        percentile: Number.isFinite(anchor.percentile) ? anchor.percentile : "",
        rating: Number.isFinite(anchor.rating) ? anchor.rating : "",
        percentileError: issueFor(
          workbench.validationIssues,
          `ratingScales.${selectedScale?.name}.anchors.${index}.percentile`,
        ),
        ratingError: issueFor(
          workbench.validationIssues,
          `ratingScales.${selectedScale?.name}.anchors.${index}.rating`,
        ),
      })),
    [selectedScale, workbench.validationIssues],
  );

  const previewByPlayer = useMemo(
    () => new Map(currentPreview?.players.map((player) => [player.playerId, player]) ?? []),
    [currentPreview],
  );
  const comparisonRows = useMemo(() => {
    const previewFailed =
      workbench.previewPhase === "error" || workbench.previewPhase === "invalid";
    const rows = workbench.comparisonPlayers.map((player): PlayerComparisonRow => {
      const result = previewByPlayer.get(player.playerId);
      const state = rowState(result, workbench.selectedAttribute, previewFailed);
      return {
        playerId: player.playerId,
        displayName: player.displayName,
        tier:
          (typeof player.baseline.talentTier === "string" && player.baseline.talentTier) || null,
        removable: workbench.comparisonMode === "custom",
        selected: player.playerId === workbench.selectedPlayerId,
        state: state.state,
        stateMessage: state.message,
        attribute: comparisonMeasure(
          result,
          workbench.selectedAttribute,
          numeric(player.baseline[workbench.selectedAttribute]),
          result?.attributeRank.baselineRank ?? null,
          "attribute",
        ),
        overall: comparisonMeasure(
          result,
          "overall",
          numeric(player.baseline.overall),
          player.baselineRank,
          "overall",
        ),
      };
    });
    return withSignals(rows);
  }, [
    previewByPlayer,
    workbench.comparisonPlayers,
    workbench.comparisonMode,
    workbench.previewPhase,
    workbench.selectedAttribute,
    workbench.selectedPlayerId,
  ]);

  const comparisonGroups = useMemo<PlayerComparisonGroup[]>(() => {
    const rowsById = new Map(comparisonRows.map((row) => [row.playerId, row]));
    if (workbench.comparisonMode === "top25") {
      return [
        {
          id: "top-25",
          label: "Top 25 by baseline overall",
          kind: "top25",
          rows: comparisonRows,
        },
      ];
    }
    if (workbench.comparisonMode === "custom") {
      return [
        {
          id: "custom-list",
          label: "Custom list",
          kind: "custom",
          rows: comparisonRows,
        },
      ];
    }
    return workbench.representativeGroups.map((group) => ({
      id: `tier-${group.tier}`,
      label: `${identifierLabel(group.tier)} · ${group.minimum}–${group.maximum}`,
      kind: "tier" as const,
      rows: group.players.flatMap(({ playerId }) => {
        const row = rowsById.get(playerId);
        return row ? [row] : [];
      }),
    }));
  }, [comparisonRows, workbench.comparisonMode, workbench.representativeGroups]);

  const formulaValidationMessages = workbench.validationIssues
    .filter(
      ({ path }) =>
        path.startsWith(`attributes.${workbench.selectedAttribute}.`) ||
        (selectedFormula && path.startsWith(`ratingScales.${selectedFormula.ratingScale}.`)),
    )
    .map(({ message }) => message);
  const proposalVersionDirty = Boolean(
    workbench.editor &&
      workbench.editor.proposalVersion !== workbench.editor.initialProposalVersion,
  );
  const dirtyCount =
    workbench.dirtyAttributes.size +
    workbench.dirtyScales.size +
    (proposalVersionDirty ? 1 : 0);
  const previewStatus: WorkbenchPreviewStatus =
    workbench.previewPhase === "ready"
      ? "preview"
      : workbench.previewPhase === "loading"
        ? "loading"
        : workbench.previewPhase === "error" || workbench.previewPhase === "invalid"
          ? "error"
          : workbench.comparisonPlayers.length === 0
            ? "empty"
            : workbench.editor
              ? "queued"
              : "baseline";

  if (workbench.phase !== "ready") {
    const tone =
      workbench.phase === "loading"
        ? "loading"
        : workbench.phase === "stale"
          ? "stale"
          : workbench.phase === "empty"
            ? "empty"
            : "error";
    return (
      <div className="workbench-app workbench-app--status">
        <WorkbenchHeader
          context={workbench.context}
          dirty={false}
          previewStatus={workbench.phase === "loading" ? "loading" : "error"}
          onResetAll={() => undefined}
          onExport={() => undefined}
        />
        <WorkbenchNavigation page="workbench" onNavigate={onNavigate} />
        <StatusPanel
          title={
            workbench.phase === "loading"
              ? "Loading the formula workbench"
              : workbench.phase === "stale"
                ? "Workbench context changed"
                : workbench.phase === "empty"
                  ? "No formula attributes available"
                  : "Formula workbench unavailable"
          }
          tone={tone}
          action={
            workbench.phase === "loading" ? null : (
              <button className="button button--primary" type="button" onClick={workbench.reload}>
                Reload workbench
              </button>
            )
          }
        >
          {workbench.loadMessage ?? "Loading the active formula and preview cohort."}
        </StatusPanel>
      </div>
    );
  }

  return (
    <div className="workbench-app">
      <WorkbenchHeader
        context={workbench.context}
        dirty={dirtyCount > 0}
        dirtyCount={dirtyCount}
        previewStatus={previewStatus}
        previewStatusMessage={
          workbench.previewPhase === "ready"
            ? `Validated in ${workbench.preview?.elapsedMs.toFixed(0)} ms`
            : workbench.previewError ?? undefined
        }
        proposalVersion={workbench.editor?.proposalVersion}
        canExport={Boolean(
          currentPreview &&
            workbench.previewPhase === "ready" &&
            !workbench.validationIssues.length,
        )}
        onResetAll={workbench.resetSession}
        onExport={workbench.exportProposal}
      />
      <WorkbenchNavigation page="workbench" onNavigate={onNavigate} />

      <div className="workbench-shell">
        <aside className="workbench-rail">
          <AttributeSidebar
            attributes={attributeRows}
            selectedAttribute={workbench.selectedAttribute}
            onSelect={workbench.selectAttribute}
          />
        </aside>

        <main className="workbench-main">
          <section className="proposal-version-card" aria-labelledby="proposal-version-title">
            <div>
              <p className="eyebrow">Portable proposal</p>
              <h2 id="proposal-version-title">Proposal identity</h2>
              <p>
                The API validates this version inside the exact formula document available for
                export. Nothing is saved to active configuration.
              </p>
              <SectionHelp title="How proposal identity works">
                <p>
                  This value becomes the formula version inside the exported proposal. It labels
                  the temporary design, but it does not replace the active formula or write
                  anything to the server. Export uses the exact full document returned by the
                  latest successful preview rather than rebuilding it from browser edits.
                </p>
              </SectionHelp>
            </div>
            <label className="field-control" htmlFor="proposal-version">
              <span>Formula version</span>
              <input
                id="proposal-version"
                type="text"
                value={workbench.editor?.proposalVersion ?? ""}
                onChange={(event) => workbench.updateProposalVersion(event.target.value)}
                aria-invalid={Boolean(
                  issueFor(workbench.validationIssues, "adjustments.formulaVersion"),
                )}
                aria-describedby="proposal-version-help"
              />
              <small id="proposal-version-help">
                {issueFor(workbench.validationIssues, "adjustments.formulaVersion") ??
                  `Active version: ${workbench.editor?.baseFormulaVersion}`}
              </small>
            </label>
          </section>

          <FormulaInspector
            attribute={selectedFormula ?? null}
            formulaVersion={workbench.context?.formula.formulaVersion ?? "—"}
            eligibilityRule={
              selectedFormula
                ? workbench.formula?.eligibilityRules[selectedFormula.eligibilityRule] ?? null
                : null
            }
            cohort={
              selectedFormula
                ? workbench.formula?.cohorts[selectedFormula.cohort] ?? null
                : null
            }
            ratingScale={activeScale ?? null}
            components={componentRows}
            anchors={anchorRows}
            dirty={
              workbench.dirtyAttributes.has(workbench.selectedAttribute) ||
              Boolean(selectedFormula && workbench.dirtyScales.has(selectedFormula.ratingScale))
            }
            validationMessages={formulaValidationMessages}
            onWeightChange={(metric, value) =>
              workbench.updateWeight(
                workbench.selectedAttribute,
                metric,
                value,
              )
            }
            onInverseDirectionChange={(metric, inverse) => {
              const component = selectedEditor?.components.find((item) => item.metric === metric);
              if (!component) return;
              workbench.updateDirection(
                workbench.selectedAttribute,
                metric,
                inverse
                  ? inverseDirection(component.baselineDirection)
                  : component.baselineDirection,
              );
            }}
            onAnchorChange={(index, field, value) => {
              if (!selectedScale) return;
              const anchors = selectedScale.anchors.map((anchor) => ({ ...anchor }));
              const anchor = anchors[index];
              if (!anchor) return;
              anchor[field] = value.trim() ? Number(value) : Number.NaN;
              workbench.updateAnchors(selectedScale.name, anchors);
            }}
            onResetAttribute={workbench.resetSelectedAttribute}
          />

          <div className="calculation-preview-pane">
            <CalculationInspector
              player={
                selectedPreviewPlayer
                  ? {
                      playerId: selectedPreviewPlayer.playerId,
                      displayName: selectedPreviewPlayer.displayName,
                      season: selectedPreviewPlayer.season,
                    }
                  : selectedDetail?.player ?? null
              }
              attributeName={workbench.selectedAttribute}
              baseline={
                baselineCalculation?.attributes[workbench.selectedAttribute] ?? null
              }
              preview={
                previewCalculation?.attributes[workbench.selectedAttribute] ?? null
              }
              metrics={workbench.metrics}
              pending={
                workbench.previewPhase === "loading" &&
                Boolean(baselineCalculation?.attributes[workbench.selectedAttribute])
              }
              previewError={
                workbench.previewPhase === "error" || workbench.previewPhase === "invalid"
                  ? workbench.previewError ?? "The proposed formula could not be previewed."
                  : undefined
              }
              status={
                !workbench.selectedPlayerId
                  ? "empty"
                  : workbench.detailPhase === "loading" && !baselineCalculation
                    ? "loading"
                    : workbench.detailError && !baselineCalculation
                      ? "error"
                      : baselineCalculation?.attributes[workbench.selectedAttribute]
                        ? "ready"
                        : "unsupported"
              }
              statusMessage={workbench.previewError ?? workbench.detailError ?? undefined}
            />
          </div>

          <div className="comparison-workspace">
            <section
              className="comparison-mode-card workbench-panel"
              aria-labelledby="comparison-mode-title"
            >
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Comparison players</p>
                  <h2 id="comparison-mode-title">Choose a player set</h2>
                  <p>
                    Switch the visible players without changing the full season population used for
                    formula calculations and ranks.
                  </p>
                </div>
              </div>
              <SectionHelp title="How comparison sets affect the preview">
                <p>
                  The selected tab controls which players receive detailed results in the table.
                  It does not shrink the calculation population: percentiles and ranks still use
                  every eligible player in the complete configured season. The Python preview API
                  performs that work, while the browser only chooses the active list and displays
                  the returned impact.
                </p>
              </SectionHelp>

              <ComparisonModeTabs
                selectedMode={workbench.comparisonMode}
                onModeChange={workbench.setComparisonMode}
              >
                {workbench.comparisonMode === "tiers" ? (
                  <div className="comparison-mode-content comparison-mode-content--split">
                    <div>
                      <h3>Tier sample</h3>
                      <p>
                        Review the highest baseline-overall players from every populated talent
                        tier, preserving coverage across the rating curve.
                      </p>
                      <SectionHelp title="How the tier sample supports tuning">
                        <p>
                          The default shows three players from each populated tier. Changing the
                          selector changes only the visible sample; every preview still calculates
                          ratings and ranks against the complete fixed season cohort.
                        </p>
                      </SectionHelp>
                    </div>
                    <label className="field-control" htmlFor="representatives-per-tier">
                      <span>Players per tier</span>
                      <select
                        id="representatives-per-tier"
                        value={workbench.representativesPerTier}
                        onChange={(event) =>
                          workbench.setRepresentativesPerTier(Number(event.target.value))
                        }
                      >
                        <option value="1">1 · five-player scan</option>
                        <option value="2">2 · ten-player scan</option>
                        <option value="3">3 · recommended 15</option>
                      </select>
                    </label>
                  </div>
                ) : workbench.comparisonMode === "top25" ? (
                  <div className="comparison-mode-content">
                    <h3>Top 25 by baseline overall</h3>
                    <p>
                      This fixed list is selected and ordered by the active formula’s baseline
                      overall rank. Preview ratings and ranks can change as you tune the model, but
                      membership does not reshuffle, so before-and-after impact stays comparable.
                    </p>
                  </div>
                ) : (
                  <PlayerSearch
                    query={workbench.searchQuery}
                    results={workbench.searchResults}
                    selectedPlayerIds={workbench.customPlayers.map(({ playerId }) => playerId)}
                    loading={workbench.searchPhase === "loading"}
                    error={workbench.searchError ?? workbench.customError}
                    maxPlayers={MAX_CUSTOM_PLAYERS}
                    onQueryChange={workbench.setSearchQuery}
                    onSubmit={() => workbench.setSearchQuery(workbench.searchQuery.trim())}
                    onAdd={(player) => void workbench.addCustomPlayer(player)}
                  />
                )}
              </ComparisonModeTabs>
            </section>

            <PlayerComparison
              selectedAttributeLabel={identifierLabel(workbench.selectedAttribute)}
              groups={comparisonGroups}
              loading={
                (workbench.comparisonMode === "tiers" &&
                  workbench.representativePhase === "loading") ||
                (workbench.comparisonMode === "top25" && workbench.topPhase === "loading") ||
                (workbench.comparisonPlayers.length > 0 &&
                  workbench.previewPhase === "loading")
              }
              error={
                workbench.comparisonMode === "tiers" && workbench.representativePhase === "error"
                  ? workbench.loadMessage
                  : workbench.comparisonMode === "top25" && workbench.topPhase === "error"
                    ? workbench.topError
                    : workbench.previewPhase === "error" || workbench.previewPhase === "invalid"
                      ? workbench.previewError
                      : null
              }
              emptyTitle={
                workbench.comparisonMode === "custom"
                  ? "Build your custom comparison"
                  : "No comparison players"
              }
              emptyMessage={
                workbench.comparisonMode === "custom"
                  ? `Search above and add up to ${MAX_CUSTOM_PLAYERS} players. Only this custom list will be included in its preview.`
                  : "The active player set did not return any players."
              }
              onSelect={workbench.selectPlayer}
              onRemove={workbench.removeCustomPlayer}
            />
          </div>
        </main>
      </div>
    </div>
  );
}
