import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { assertMatchingContext, StaleContextError } from "../api/context";
import {
  isAbortError,
  PreviewApiError,
  previewApi,
  type PreviewApiClient,
} from "../api/client";
import type {
  ApiContext,
  AttributeFormula,
  FormulaDocument,
  MetricMetadata,
  PlayerDetailResponse,
  PlayerSummary,
  PreviewRequest,
  PreviewResponse,
  SearchHit,
  TierRepresentativeGroup,
} from "../api/types";
import {
  buildPreviewAdjustments,
  createFormulaEditorState,
  dirtyAttributeNames,
  dirtyRatingScaleNames,
  rebalanceComponentWeight,
  resetAll,
  resetAttribute,
  resetRatingScale,
  setComponentDirection,
  setProposalVersion,
  setRatingScaleAnchors,
  validateFormulaEditorState,
  type FormulaEditorState,
} from "../domain/editor";

const DEFAULT_REPRESENTATIVES_PER_TIER = 3;
const MAX_PREVIEW_PLAYERS = 25;
const TOP_PLAYER_LIMIT = MAX_PREVIEW_PLAYERS;
export const MAX_CUSTOM_PLAYERS = MAX_PREVIEW_PLAYERS;

export type ComparisonMode = "tiers" | "top25" | "custom";

export type LoadPhase = "loading" | "ready" | "empty" | "error" | "stale";
export type RequestPhase = "idle" | "loading" | "ready" | "error";

function errorMessage(error: unknown): string {
  if (error instanceof PreviewApiError || error instanceof StaleContextError) {
    return error.message;
  }
  return error instanceof Error ? error.message : "An unexpected workbench error occurred.";
}

function defaultProposalVersion(activeVersion: string): string {
  return `${activeVersion}-proposal.1`;
}

function flattenRepresentatives(groups: readonly TierRepresentativeGroup[]): PlayerSummary[] {
  return groups.flatMap((group) => group.players);
}

function customSummary(detail: PlayerDetailResponse): PlayerSummary {
  return {
    playerId: detail.player.playerId,
    displayName: detail.player.displayName,
    season: detail.player.season,
    baselineRank: detail.player.baselineRank,
    baseline: detail.baseline,
    pinned: false,
  };
}

export interface WorkbenchController {
  phase: LoadPhase;
  loadMessage: string | null;
  context: ApiContext | null;
  formula: FormulaDocument | null;
  metrics: MetricMetadata[];
  metricsByName: ReadonlyMap<string, MetricMetadata>;
  attributes: AttributeFormula[];
  selectedAttribute: string;
  selectAttribute: (attribute: string) => void;
  editor: FormulaEditorState | null;
  validationIssues: ReturnType<typeof validateFormulaEditorState>;
  dirtyAttributes: ReadonlySet<string>;
  dirtyScales: ReadonlySet<string>;
  updateProposalVersion: (version: string) => void;
  updateWeight: (attribute: string, metric: string, weight: number) => void;
  updateDirection: (
    attribute: string,
    metric: string,
    direction: "higher" | "lower",
  ) => void;
  updateAnchors: (
    scale: string,
    anchors: ReadonlyArray<{ percentile: number; rating: number }>,
  ) => void;
  resetSelectedAttribute: () => void;
  resetSession: () => void;
  representativesPerTier: number;
  setRepresentativesPerTier: (count: number) => void;
  representativeGroups: TierRepresentativeGroup[];
  representativePhase: RequestPhase;
  comparisonMode: ComparisonMode;
  setComparisonMode: (mode: ComparisonMode) => void;
  topPlayers: PlayerSummary[];
  topPhase: RequestPhase;
  topError: string | null;
  retryTopPlayers: () => void;
  customPlayers: PlayerSummary[];
  customError: string | null;
  addCustomPlayer: (player: SearchHit) => Promise<void>;
  removeCustomPlayer: (playerId: string) => void;
  comparisonPlayers: PlayerSummary[];
  selectedPlayerId: string | null;
  selectPlayer: (playerId: string) => void;
  detail: PlayerDetailResponse | null;
  detailPhase: RequestPhase;
  detailError: string | null;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  searchResults: SearchHit[];
  searchPhase: RequestPhase;
  searchError: string | null;
  preview: PreviewResponse | null;
  previewPhase: RequestPhase | "invalid";
  previewError: string | null;
  reload: () => void;
  exportProposal: () => void;
}

export function useWorkbench(
  client: PreviewApiClient = previewApi,
): WorkbenchController {
  const [reloadToken, setReloadToken] = useState(0);
  const [phase, setPhase] = useState<LoadPhase>("loading");
  const [loadMessage, setLoadMessage] = useState<string | null>(null);
  const [context, setContext] = useState<ApiContext | null>(null);
  const [formula, setFormula] = useState<FormulaDocument | null>(null);
  const [metrics, setMetrics] = useState<MetricMetadata[]>([]);
  const [selectedAttribute, setSelectedAttribute] = useState("overall");
  const [editor, setEditor] = useState<FormulaEditorState | null>(null);
  const [representativesPerTier, setRepresentativesPerTierState] = useState(
    DEFAULT_REPRESENTATIVES_PER_TIER,
  );
  const [representativeGroups, setRepresentativeGroups] = useState<
    TierRepresentativeGroup[]
  >([]);
  const [representativePhase, setRepresentativePhase] =
    useState<RequestPhase>("idle");
  const [comparisonMode, setComparisonModeState] =
    useState<ComparisonMode>("tiers");
  const [topPlayers, setTopPlayers] = useState<PlayerSummary[]>([]);
  const [topPhase, setTopPhase] = useState<RequestPhase>("idle");
  const [topError, setTopError] = useState<string | null>(null);
  const [topRequestToken, setTopRequestToken] = useState(0);
  const [customPlayers, setCustomPlayers] = useState<PlayerSummary[]>([]);
  const customPlayerIds = useRef(new Set<string>());
  const pendingCustomPlayerIds = useRef(new Set<string>());
  const sessionGeneration = useRef(0);
  const customInteractionGeneration = useRef(0);
  const [customError, setCustomError] = useState<string | null>(null);
  const [selectedPlayerIdsByMode, setSelectedPlayerIdsByMode] = useState<
    Record<ComparisonMode, string | null>
  >({ tiers: null, top25: null, custom: null });
  const [detail, setDetail] = useState<PlayerDetailResponse | null>(null);
  const [detailPhase, setDetailPhase] = useState<RequestPhase>("idle");
  const [detailError, setDetailError] = useState<string | null>(null);
  const [searchQuery, setSearchQueryState] = useState("");
  const [searchResults, setSearchResults] = useState<SearchHit[]>([]);
  const [searchPhase, setSearchPhase] = useState<RequestPhase>("idle");
  const [searchError, setSearchError] = useState<string | null>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [previewPhase, setPreviewPhase] = useState<RequestPhase | "invalid">("idle");
  const [previewError, setPreviewError] = useState<string | null>(null);

  const invalidatePreview = useCallback(() => {
    setPreview(null);
    setPreviewError(null);
    setPreviewPhase("loading");
  }, []);

  const makeStale = useCallback((message: string) => {
    setPhase("stale");
    setLoadMessage(message);
    setDetail(null);
    setPreview(null);
    setSearchResults([]);
  }, []);

  useEffect(() => {
    sessionGeneration.current += 1;
    customInteractionGeneration.current += 1;
    const controller = new AbortController();
    setPhase("loading");
    setLoadMessage(null);
    setContext(null);
    setFormula(null);
    setMetrics([]);
    setEditor(null);
    setRepresentativePhase("idle");
    setRepresentativeGroups([]);
    setComparisonModeState("tiers");
    setTopPlayers([]);
    setTopPhase("idle");
    setTopError(null);
    customPlayerIds.current.clear();
    pendingCustomPlayerIds.current.clear();
    setCustomPlayers([]);
    setCustomError(null);
    setSelectedPlayerIdsByMode({ tiers: null, top25: null, custom: null });
    setDetail(null);
    setDetailPhase("idle");
    setDetailError(null);
    setPreview(null);
    setPreviewPhase("idle");
    setPreviewError(null);
    setSearchQueryState("");
    setSearchResults([]);
    setSearchPhase("idle");
    setSearchError(null);

    void Promise.all([
      client.getFormula({ signal: controller.signal }),
      client.getMetrics({ signal: controller.signal }),
    ])
      .then(([formulaResponse, metricsResponse]) => {
        if (controller.signal.aborted) return;
        assertMatchingContext(formulaResponse.context, metricsResponse.context);
        if (!formulaResponse.document.attributes.length) {
          setPhase("empty");
          setLoadMessage("The active formula does not declare any attributes.");
          return;
        }
        const initialAttribute =
          formulaResponse.document.attributes.find(({ name }) => name === "overall")?.name ??
          formulaResponse.document.attributes[0].name;
        setContext(formulaResponse.context);
        setFormula(formulaResponse.document);
        setMetrics(metricsResponse.metrics);
        setSelectedAttribute(initialAttribute);
        setEditor(
          createFormulaEditorState(
            formulaResponse.document,
            defaultProposalVersion(formulaResponse.document.formulaVersion),
          ),
        );
        setPhase("ready");
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || isAbortError(error)) return;
        if (error instanceof StaleContextError) {
          makeStale(error.message);
          return;
        }
        setPhase("error");
        setLoadMessage(errorMessage(error));
      });

    return () => {
      sessionGeneration.current += 1;
      controller.abort();
    };
  }, [client, makeStale, reloadToken]);

  useEffect(() => {
    if (!context || phase !== "ready") return;
    const controller = new AbortController();
    setRepresentativePhase("loading");
    void client
      .getTierRepresentatives({
        perTier: representativesPerTier,
        signal: controller.signal,
      })
      .then((response) => {
        if (controller.signal.aborted) return;
        assertMatchingContext(context, response.context);
        const players = flattenRepresentatives(response.tiers);
        if (players.length > MAX_PREVIEW_PLAYERS) {
          setRepresentativeGroups([]);
          setRepresentativePhase("error");
          setLoadMessage(
            `The tier sample returned ${players.length} players, exceeding the preview limit of ${MAX_PREVIEW_PLAYERS}. Reduce players per tier or choose another comparison set.`,
          );
          setSelectedPlayerIdsByMode((current) => ({ ...current, tiers: null }));
          return;
        }
        setRepresentativeGroups(response.tiers);
        setRepresentativePhase("ready");
        setLoadMessage(null);
        setSelectedPlayerIdsByMode((current) => ({
          ...current,
          tiers:
            current.tiers && players.some(({ playerId }) => playerId === current.tiers)
              ? current.tiers
              : players[0]?.playerId ?? null,
        }));
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || isAbortError(error)) return;
        if (error instanceof StaleContextError) {
          makeStale(error.message);
          return;
        }
        setRepresentativeGroups([]);
        setRepresentativePhase("error");
        setLoadMessage(errorMessage(error));
      });
    return () => controller.abort();
  }, [client, context, makeStale, phase, representativesPerTier]);

  useEffect(() => {
    if (
      comparisonMode !== "top25" ||
      !context ||
      phase !== "ready" ||
      topPhase !== "idle"
    ) {
      return;
    }
    const controller = new AbortController();
    setTopError(null);
    setTopPhase("loading");
    void client
      .getPlayers({ limit: TOP_PLAYER_LIMIT, signal: controller.signal })
      .then((response) => {
        if (controller.signal.aborted) return;
        assertMatchingContext(context, response.context);
        setTopPlayers(response.players);
        setTopPhase("ready");
        setSelectedPlayerIdsByMode((current) => ({
          ...current,
          top25:
            current.top25 &&
            response.players.some(({ playerId }) => playerId === current.top25)
              ? current.top25
              : response.players[0]?.playerId ?? null,
        }));
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || isAbortError(error)) return;
        if (error instanceof StaleContextError) {
          makeStale(error.message);
          return;
        }
        setTopPlayers([]);
        setTopError(errorMessage(error));
        setTopPhase("error");
      });
    return () => {
      controller.abort();
      setTopPhase((current) => (current === "loading" ? "idle" : current));
    };
  }, [client, comparisonMode, context, makeStale, phase, topRequestToken]);

  const representativePlayers = useMemo(
    () => flattenRepresentatives(representativeGroups),
    [representativeGroups],
  );
  const comparisonPlayers = useMemo(() => {
    if (comparisonMode === "top25") return topPlayers;
    if (comparisonMode === "custom") return customPlayers;
    return representativePlayers;
  }, [comparisonMode, customPlayers, representativePlayers, topPlayers]);
  const storedSelectedPlayerId = selectedPlayerIdsByMode[comparisonMode];
  const selectedPlayerId =
    storedSelectedPlayerId &&
    comparisonPlayers.some(({ playerId }) => playerId === storedSelectedPlayerId)
      ? storedSelectedPlayerId
      : comparisonPlayers[0]?.playerId ?? null;

  useEffect(() => {
    if (storedSelectedPlayerId === selectedPlayerId) return;
    setSelectedPlayerIdsByMode((current) => ({
      ...current,
      [comparisonMode]: selectedPlayerId,
    }));
  }, [comparisonMode, selectedPlayerId, storedSelectedPlayerId]);

  useEffect(() => {
    if (!context || !selectedPlayerId || phase !== "ready") {
      setDetail(null);
      setDetailPhase("idle");
      return;
    }
    const controller = new AbortController();
    setDetail(null);
    setDetailError(null);
    setDetailPhase("loading");
    void client
      .getPlayer(selectedPlayerId, { signal: controller.signal })
      .then((response) => {
        if (controller.signal.aborted) return;
        assertMatchingContext(context, response.context);
        setDetail(response);
        setDetailPhase("ready");
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || isAbortError(error)) return;
        if (error instanceof StaleContextError) {
          makeStale(error.message);
          return;
        }
        setDetailError(errorMessage(error));
        setDetailPhase("error");
      });
    return () => controller.abort();
  }, [client, context, makeStale, phase, selectedPlayerId]);

  useEffect(() => {
    const query = searchQuery.trim();
    if (!context || phase !== "ready" || query.length < 1) {
      setSearchResults([]);
      setSearchPhase("idle");
      setSearchError(null);
      return;
    }
    const controller = new AbortController();
    setSearchResults([]);
    setSearchPhase("loading");
    setSearchError(null);
    const timeout = window.setTimeout(() => {
      void client
        .searchPlayers(query, { limit: 10, signal: controller.signal })
        .then((response) => {
          if (controller.signal.aborted) return;
          assertMatchingContext(context, response.context);
          setSearchResults(response.players);
          setSearchPhase("ready");
        })
        .catch((error: unknown) => {
          if (controller.signal.aborted || isAbortError(error)) return;
          if (error instanceof StaleContextError) {
            makeStale(error.message);
            return;
          }
          setSearchResults([]);
          setSearchError(errorMessage(error));
          setSearchPhase("error");
        });
    }, 250);
    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [client, context, makeStale, phase, searchQuery]);

  const validationIssues = useMemo(
    () => (editor ? validateFormulaEditorState(editor) : []),
    [editor],
  );
  const selectedPlayerIds = useMemo(
    () => comparisonPlayers.map(({ playerId }) => playerId),
    [comparisonPlayers],
  );

  useEffect(() => {
    if (!context || !editor || phase !== "ready" || !selectedPlayerIds.length) {
      setPreview(null);
      setPreviewError(null);
      setPreviewPhase("idle");
      return;
    }
    if (validationIssues.length) {
      setPreview(null);
      setPreviewError("Resolve formula validation issues to request a preview.");
      setPreviewPhase("invalid");
      return;
    }

    const controller = new AbortController();
    setPreview(null);
    setPreviewError(null);
    setPreviewPhase("loading");
    const timeout = window.setTimeout(() => {
      const request: PreviewRequest = {
        apiVersion: context.apiVersion,
        referencePackageHash: context.referencePackage.contentHash,
        formulaVersion: context.formula.formulaVersion,
        formulaDocumentHash: context.formula.documentHash,
        season: context.season,
        selectedAttribute,
        selectedPlayerIds,
        adjustments: buildPreviewAdjustments(editor),
      };
      void client
        .preview(request, { signal: controller.signal })
        .then((response) => {
          if (controller.signal.aborted) return;
          assertMatchingContext(context, response.context);
          setPreview(response);
          setPreviewPhase("ready");
        })
        .catch((error: unknown) => {
          if (controller.signal.aborted || isAbortError(error)) return;
          if (
            error instanceof StaleContextError ||
            (error instanceof PreviewApiError && error.code === "stale_context")
          ) {
            makeStale(error.message);
            return;
          }
          setPreview(null);
          setPreviewError(errorMessage(error));
          setPreviewPhase("error");
        });
    }, 350);
    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [
    client,
    context,
    editor,
    makeStale,
    phase,
    selectedAttribute,
    selectedPlayerIds,
    validationIssues,
  ]);

  const metricsByName = useMemo(
    () => new Map(metrics.map((metric) => [metric.name, metric])),
    [metrics],
  );
  const dirtyAttributes = useMemo(
    () => new Set(editor ? dirtyAttributeNames(editor) : []),
    [editor],
  );
  const dirtyScales = useMemo(
    () => new Set(editor ? dirtyRatingScaleNames(editor) : []),
    [editor],
  );

  const addCustomPlayer = useCallback(
    async (player: SearchHit) => {
      setCustomError(null);
      setComparisonModeState("custom");
      if (customPlayerIds.current.has(player.playerId)) {
        setSelectedPlayerIdsByMode((current) => ({
          ...current,
          custom: player.playerId,
        }));
        return;
      }
      if (pendingCustomPlayerIds.current.has(player.playerId)) return;
      if (
        customPlayerIds.current.size + pendingCustomPlayerIds.current.size >=
        MAX_CUSTOM_PLAYERS
      ) {
        setCustomError(
          `At most ${MAX_CUSTOM_PLAYERS} players can be added to the custom list.`,
        );
        return;
      }
      if (!context) return;
      const generation = sessionGeneration.current;
      const interactionGeneration = customInteractionGeneration.current;
      pendingCustomPlayerIds.current.add(player.playerId);
      try {
        const response = await client.getPlayer(player.playerId);
        if (generation !== sessionGeneration.current) return;
        assertMatchingContext(context, response.context);
        if (customPlayerIds.current.size >= MAX_CUSTOM_PLAYERS) {
          setCustomError(
            `At most ${MAX_CUSTOM_PLAYERS} players can be added to the custom list.`,
          );
          return;
        }
        customPlayerIds.current.add(player.playerId);
        invalidatePreview();
        setCustomPlayers((current) => [...current, customSummary(response)]);
        setSelectedPlayerIdsByMode((current) => ({
          ...current,
          custom: player.playerId,
        }));
        if (interactionGeneration === customInteractionGeneration.current) {
          setSearchQueryState("");
          setSearchResults([]);
        }
      } catch (error: unknown) {
        if (generation !== sessionGeneration.current) return;
        if (error instanceof StaleContextError) {
          makeStale(error.message);
          return;
        }
        if (interactionGeneration === customInteractionGeneration.current) {
          setCustomError(errorMessage(error));
        }
      } finally {
        if (generation === sessionGeneration.current) {
          pendingCustomPlayerIds.current.delete(player.playerId);
        }
      }
    }, [client, context, invalidatePreview, makeStale],
  );

  const resetSelectedAttribute = useCallback(() => {
    if (!editor || !formula) return;
    const attribute = formula.attributes.find(({ name }) => name === selectedAttribute);
    if (!attribute) return;
    invalidatePreview();
    setEditor(resetRatingScale(resetAttribute(editor, attribute.name), attribute.ratingScale));
  }, [editor, formula, invalidatePreview, selectedAttribute]);

  const removeCustomPlayer = useCallback(
    (playerId: string) => {
      if (!customPlayerIds.current.has(playerId)) return;
      customInteractionGeneration.current += 1;
      setCustomError(null);
      if (comparisonMode === "custom") invalidatePreview();
      customPlayerIds.current.delete(playerId);
      setCustomPlayers((current) =>
        current.filter((player) => player.playerId !== playerId),
      );
      setSelectedPlayerIdsByMode((current) => ({
        ...current,
        custom: current.custom === playerId ? null : current.custom,
      }));
    },
    [comparisonMode, invalidatePreview],
  );

  const updateSearchQuery = useCallback((query: string) => {
    customInteractionGeneration.current += 1;
    setCustomError(null);
    setSearchQueryState(query);
  }, []);

  const retryTopPlayers = useCallback(() => {
    if (comparisonMode !== "top25" || topPhase !== "error") return;
    setTopError(null);
    setTopPhase("idle");
    setTopRequestToken((current) => current + 1);
  }, [comparisonMode, topPhase]);

  const exportProposal = useCallback(() => {
    if (!preview || !editor || previewPhase !== "ready") return;
    const content = `${JSON.stringify(preview.previewDocument, null, 2)}\n`;
    const blob = new Blob([content], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    const version = editor.proposalVersion.trim().replace(/[^A-Za-z0-9._-]+/g, "-");
    anchor.href = url;
    anchor.download = `player-attributes-${version || "proposal"}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }, [editor, preview, previewPhase]);

  return {
    phase,
    loadMessage,
    context,
    formula,
    metrics,
    metricsByName,
    attributes: formula?.attributes ?? [],
    selectedAttribute,
    selectAttribute: (attribute) => {
      if (attribute === selectedAttribute) return;
      invalidatePreview();
      setSelectedAttribute(attribute);
    },
    editor,
    validationIssues,
    dirtyAttributes,
    dirtyScales,
    updateProposalVersion: (version) => {
      if (version === editor?.proposalVersion) return;
      invalidatePreview();
      setEditor((current) => (current ? setProposalVersion(current, version) : current));
    },
    updateWeight: (attribute, metric, weight) => {
      invalidatePreview();
      setEditor((current) =>
        current ? rebalanceComponentWeight(current, attribute, metric, weight) : current,
      );
    },
    updateDirection: (attribute, metric, direction) => {
      invalidatePreview();
      setEditor((current) =>
        current ? setComponentDirection(current, attribute, metric, direction) : current,
      );
    },
    updateAnchors: (scale, anchors) => {
      invalidatePreview();
      setEditor((current) =>
        current ? setRatingScaleAnchors(current, scale, anchors) : current,
      );
    },
    resetSelectedAttribute,
    resetSession: () => {
      invalidatePreview();
      setEditor((current) => (current ? resetAll(current) : current));
    },
    representativesPerTier,
    setRepresentativesPerTier: (count) => {
      const normalized = Math.max(1, Math.min(3, Math.trunc(count)));
      if (normalized === representativesPerTier) return;
      if (comparisonMode === "tiers") invalidatePreview();
      setRepresentativesPerTierState(normalized);
    },
    representativeGroups,
    representativePhase,
    comparisonMode,
    setComparisonMode: (mode) => {
      if (mode === comparisonMode) return;
      invalidatePreview();
      if (mode === "top25" && topPhase === "error") {
        setTopError(null);
        setTopPhase("idle");
      }
      setComparisonModeState(mode);
    },
    topPlayers,
    topPhase,
    topError,
    retryTopPlayers,
    customPlayers,
    customError,
    addCustomPlayer,
    removeCustomPlayer,
    comparisonPlayers,
    selectedPlayerId,
    selectPlayer: (playerId) => {
      if (!comparisonPlayers.some((player) => player.playerId === playerId)) return;
      setSelectedPlayerIdsByMode((current) => ({
        ...current,
        [comparisonMode]: playerId,
      }));
    },
    detail,
    detailPhase,
    detailError,
    searchQuery,
    setSearchQuery: updateSearchQuery,
    searchResults,
    searchPhase,
    searchError,
    preview,
    previewPhase,
    previewError,
    reload: () => setReloadToken((value) => value + 1),
    exportProposal,
  };
}
