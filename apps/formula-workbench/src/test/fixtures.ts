import { vi } from "vitest";

import type { PreviewApiClient, RequestOptions } from "../api/client";
import type {
  ApiContext,
  AttributeCalculation,
  FormulaDocument,
  MetricMetadata,
  PlayerCalculation,
  PlayerDetailResponse,
  PlayerSummary,
  PreviewRequest,
  PreviewResponse,
  SearchHit,
  TierRepresentativeGroup,
} from "../api/types";

export const CONTEXT: ApiContext = {
  apiVersion: "1",
  referencePackage: {
    packageVersion: 2,
    contentHash: "reference-package-hash-2026",
    publishedFormulaVersion: "attributes-2026.1",
    publishedFormulaDocumentHash: "formula-document-hash-2026",
  },
  formula: {
    schemaVersion: 1,
    formulaVersion: "attributes-2026.1",
    documentHash: "formula-document-hash-2026",
  },
  season: 2026,
  cohortSize: 240,
};

export const FORMULA_DOCUMENT: FormulaDocument = {
  schemaVersion: 1,
  formulaVersion: "attributes-2026.1",
  referenceContractVersion: 2,
  outputFields: ["overall", "shooting"],
  rules: {
    nullHandling: "exclude",
    tieMethod: "average",
    percentileMethod: "rankPct",
    ratingRounding: "halfEven",
  },
  metrics: {
    pointsPerGame: { kind: "input", field: "pointsPerGame" },
    assistsPerGame: { kind: "input", field: "assistsPerGame" },
  },
  cohorts: {
    season: { groupBy: ["season"] },
  },
  eligibilityRules: {
    standard: {
      requiredMetrics: ["pointsPerGame", "assistsPerGame"],
      minimumSamples: { gamesPlayed: 10 },
    },
  },
  ratingScales: {
    standard: {
      minimum: 25,
      maximum: 99,
      anchors: [
        { percentile: 0, rating: 25 },
        { percentile: 0.5, rating: 70 },
        { percentile: 1, rating: 99 },
      ],
    },
  },
  attributes: [
    {
      name: "overall",
      components: [
        { metric: "pointsPerGame", weight: 0.6, direction: "higher" },
        { metric: "assistsPerGame", weight: 0.4, direction: "higher" },
      ],
      eligibilityRule: "standard",
      cohort: "season",
      ratingScale: "standard",
      rerankComposite: true,
      percentileOutput: "overallPercentile",
    },
    {
      name: "shooting",
      components: [{ metric: "pointsPerGame", weight: 1, direction: "higher" }],
      eligibilityRule: "standard",
      cohort: "season",
      ratingScale: "standard",
      rerankComposite: false,
    },
  ],
  talentTiers: [
    { name: "superstar", minimum: 90, maximum: 99 },
    { name: "all_star", minimum: 80, maximum: 89 },
    { name: "starter", minimum: 70, maximum: 79 },
    { name: "rotation", minimum: 60, maximum: 69 },
    { name: "fringe", minimum: 25, maximum: 59 },
  ],
};

export const METRICS: MetricMetadata[] = [
  {
    name: "pointsPerGame",
    label: "Points scored per game",
    description: "Scoring production per appearance.",
    kind: "input",
    field: "pointsPerGame",
    inputs: [],
    priorAttempts: null,
    schedule: {},
    usedBy: [
      { attribute: "overall", weight: 0.6, direction: "higher" },
      { attribute: "shooting", weight: 1, direction: "higher" },
    ],
  },
  {
    name: "assistsPerGame",
    label: "Assists per game",
    description: "Playmaking production per appearance.",
    kind: "input",
    field: "assistsPerGame",
    inputs: [],
    priorAttempts: null,
    schedule: {},
    usedBy: [{ attribute: "overall", weight: 0.4, direction: "higher" }],
  },
];

const TIER_SPECS = [
  ["superstar", 90, 99],
  ["all_star", 80, 89],
  ["starter", 70, 79],
  ["rotation", 60, 69],
  ["fringe", 25, 59],
] as const;

function representative(
  tier: string,
  tierIndex: number,
  index: number,
): PlayerSummary {
  const rating = Math.max(25, 96 - tierIndex * 9 - index);
  return {
    playerId: `${tier}-${index + 1}`,
    displayName: `${tier.replaceAll("_", " ")} player ${index + 1}`,
    season: 2026,
    baselineRank: tierIndex * 10 + index + 1,
    baseline: {
      overall: rating,
      shooting: rating - 2,
      talentTier: tier,
    },
    pinned: false,
  };
}

export const REPRESENTATIVE_GROUPS: TierRepresentativeGroup[] = TIER_SPECS.map(
  ([tier, minimum, maximum], tierIndex) => ({
    tier,
    minimum,
    maximum,
    players: [0, 1, 2].map((index) => representative(tier, tierIndex, index)),
  }),
);

function tierForRating(rating: number): string {
  return (
    TIER_SPECS.find(([, minimum, maximum]) => rating >= minimum && rating <= maximum)?.[0] ??
    "fringe"
  );
}

export const TOP_PLAYERS: PlayerSummary[] = Array.from({ length: 25 }, (_, index) => {
  const rating = 99 - index;
  return {
    playerId: `top-${String(index + 1).padStart(2, "0")}`,
    displayName: `Top player ${index + 1}`,
    season: 2026,
    baselineRank: index + 1,
    baseline: {
      overall: rating,
      shooting: rating - 2,
      talentTier: tierForRating(rating),
    },
    pinned: false,
  };
});

export const SPECIAL_PLAYER: SearchHit = {
  playerId: "player-special-42",
  displayName: "Bench Specialist",
  season: 2026,
  baselineRank: 144,
  overall: 63,
};

export function makeCalculation(
  playerId: string,
  options: { adjusted?: boolean; rating?: number } = {},
): PlayerCalculation {
  const adjusted = options.adjusted ?? false;
  const rating = options.rating ?? (adjusted ? 92 : 90);
  const overall: AttributeCalculation = {
    eligible: true,
    ineligibilityReasons: [],
    cohort: { name: "season", values: { season: 2026 }, eligibleCount: 225 },
    rawInputs: { pointsPerGame: 27.5, assistsPerGame: 7.2 },
    metricDetails: {
      pointsPerGame: { kind: "input", value: 27.5, field: "pointsPerGame" },
      assistsPerGame: { kind: "input", value: 7.2, field: "assistsPerGame" },
    },
    componentPercentiles: { pointsPerGame: 0.9, assistsPerGame: 0.7 },
    normalizedWeights: adjusted
      ? { pointsPerGame: 0.7, assistsPerGame: 0.3 }
      : { pointsPerGame: 0.6, assistsPerGame: 0.4 },
    contributions: adjusted
      ? { pointsPerGame: 0.63, assistsPerGame: 0.21 }
      : { pointsPerGame: 0.54, assistsPerGame: 0.28 },
    composite: adjusted ? 0.84 : 0.82,
    compositePercentile: adjusted ? 0.88 : 0.85,
    rating,
  };
  const shooting: AttributeCalculation = {
    ...structuredClone(overall),
    rawInputs: { pointsPerGame: 27.5 },
    metricDetails: {
      pointsPerGame: { kind: "input", value: 27.5, field: "pointsPerGame" },
    },
    componentPercentiles: { pointsPerGame: 0.9 },
    normalizedWeights: { pointsPerGame: 1 },
    contributions: { pointsPerGame: 0.9 },
    composite: 0.9,
    compositePercentile: 0.9,
    rating: adjusted ? 94 : 93,
  };
  return {
    playerId,
    season: 2026,
    formulaVersion: adjusted ? "attributes-2026.1-proposal.1" : "attributes-2026.1",
    attributes: { overall, shooting },
  };
}

function allPlayers(): PlayerSummary[] {
  return [...TOP_PLAYERS, ...REPRESENTATIVE_GROUPS.flatMap((group) => group.players)];
}

export function makePlayerDetail(playerId: string): PlayerDetailResponse {
  const summary = allPlayers().find((player) => player.playerId === playerId);
  const player =
    playerId === SPECIAL_PLAYER.playerId
      ? SPECIAL_PLAYER
      : summary
        ? {
            playerId: summary.playerId,
            displayName: summary.displayName,
            season: summary.season,
            baselineRank: summary.baselineRank,
            overall:
              typeof summary.baseline.overall === "number" ? summary.baseline.overall : null,
          }
        : null;
  if (!player) {
    throw new Error(`Unknown fixture player ${playerId}.`);
  }
  const overall = player.overall ?? 63;
  return {
    context: CONTEXT,
    player,
    baseline: {
      overall,
      shooting: overall - 2,
      talentTier:
        playerId === SPECIAL_PLAYER.playerId
          ? "rotation"
          : summary?.baseline.talentTier ?? null,
    },
    calculation: makeCalculation(playerId, { rating: overall }),
  };
}

function proposalDocument(request: PreviewRequest): FormulaDocument {
  const document = structuredClone(FORMULA_DOCUMENT);
  document.formulaVersion = request.adjustments.formulaVersion;
  for (const adjustment of request.adjustments.components) {
    const component = document.attributes
      .find((attribute) => attribute.name === adjustment.attribute)
      ?.components.find((candidate) => candidate.metric === adjustment.metric);
    if (!component) continue;
    if (adjustment.weight !== undefined) component.weight = adjustment.weight;
    if (adjustment.inverseDirection) {
      component.direction = component.direction === "higher" ? "lower" : "higher";
    }
  }
  for (const adjustment of request.adjustments.ratingScales) {
    const scale = document.ratingScales[adjustment.scale];
    if (scale) scale.anchors = structuredClone(adjustment.anchors);
  }
  return document;
}

export function makePreviewResponse(request: PreviewRequest): PreviewResponse {
  const adjusted =
    request.adjustments.components.length > 0 || request.adjustments.ratingScales.length > 0;
  return {
    context: CONTEXT,
    previewFormulaHash: adjusted ? "adjusted-preview-hash" : "baseline-preview-hash",
    elapsedMs: adjusted ? 41.25 : 26.5,
    previewDocument: proposalDocument(request),
    players: request.selectedPlayerIds.map((playerId, index) => {
      const detail = makePlayerDetail(playerId);
      const baselineOverall =
        typeof detail.baseline.overall === "number" ? detail.baseline.overall : null;
      const baselineShooting =
        typeof detail.baseline.shooting === "number" ? detail.baseline.shooting : null;
      const overallDelta = adjusted ? (index % 2 === 0 ? 2 : -1) : 0;
      const attributeDelta = adjusted ? (index % 2 === 0 ? 3 : -2) : 0;
      const previewOverall = baselineOverall === null ? null : baselineOverall + overallDelta;
      const previewShooting =
        baselineShooting === null ? null : baselineShooting + attributeDelta;
      const selectedBaseline =
        request.selectedAttribute === "shooting" ? baselineShooting : baselineOverall;
      const selectedPreview =
        request.selectedAttribute === "shooting" ? previewShooting : previewOverall;
      const baselineCalculation = makeCalculation(playerId, {
        rating: baselineOverall ?? undefined,
      });
      const previewCalculation = makeCalculation(playerId, {
        adjusted,
        rating: previewOverall ?? undefined,
      });
      return {
        playerId,
        displayName: detail.player.displayName,
        season: detail.player.season,
        baselineRank: detail.player.baselineRank,
        previewRank:
          detail.player.baselineRank === null
            ? null
            : Math.max(1, detail.player.baselineRank - overallDelta),
        rankMovement: overallDelta,
        attributeRank: {
          attribute: request.selectedAttribute,
          baselineRank: detail.player.baselineRank,
          previewRank:
            detail.player.baselineRank === null
              ? null
              : Math.max(1, detail.player.baselineRank - attributeDelta),
          rankMovement: attributeDelta,
        },
        baseline: detail.baseline,
        preview: {
          ...detail.baseline,
          overall: previewOverall,
          shooting: previewShooting,
        },
        changes: {
          overall: {
            baselineValue: baselineOverall,
            previewValue: previewOverall,
            delta: overallDelta,
          },
          shooting: {
            baselineValue: baselineShooting,
            previewValue: previewShooting,
            delta: attributeDelta,
          },
          [request.selectedAttribute]: {
            baselineValue: selectedBaseline,
            previewValue: selectedPreview,
            delta: request.selectedAttribute === "shooting" ? attributeDelta : overallDelta,
          },
        },
        baselineCalculation,
        previewCalculation,
      };
    }),
  };
}

export type PreviewHandler = (
  request: PreviewRequest,
  options: RequestOptions,
  response: PreviewResponse,
) => Promise<PreviewResponse>;

export class FakePreviewApiClient implements PreviewApiClient {
  previewHandler: PreviewHandler | null = null;

  getFormula = vi.fn<PreviewApiClient["getFormula"]>(async () => ({
    context: CONTEXT,
    document: structuredClone(FORMULA_DOCUMENT),
  }));

  getMetrics = vi.fn<PreviewApiClient["getMetrics"]>(async () => ({
    context: CONTEXT,
    metrics: structuredClone(METRICS),
  }));

  getPlayers = vi.fn<PreviewApiClient["getPlayers"]>(async (options = {}) => ({
    context: CONTEXT,
    defaultSampleSize: 25,
    players: structuredClone(TOP_PLAYERS.slice(0, options.limit ?? 25)),
  }));

  getTierRepresentatives = vi.fn<PreviewApiClient["getTierRepresentatives"]>(
    async (options = {}) => {
      const perTier = options.perTier ?? 3;
      return {
        context: CONTEXT,
        perTier,
        tiers: REPRESENTATIVE_GROUPS.map((group) => ({
          ...structuredClone(group),
          players: structuredClone(group.players.slice(0, perTier)),
        })),
      };
    },
  );

  searchPlayers = vi.fn<PreviewApiClient["searchPlayers"]>(async (query) => {
    const normalized = query.trim().toLocaleLowerCase();
    const candidates = [SPECIAL_PLAYER];
    return {
      context: CONTEXT,
      query,
      players: candidates.filter(
        (player) =>
          player.displayName.toLocaleLowerCase().includes(normalized) ||
          player.playerId.toLocaleLowerCase() === normalized,
      ),
    };
  });

  getPlayer = vi.fn<PreviewApiClient["getPlayer"]>(async (playerId) =>
    makePlayerDetail(playerId),
  );

  preview = vi.fn<PreviewApiClient["preview"]>(async (request, options = {}) => {
    const response = makePreviewResponse(request);
    return this.previewHandler
      ? this.previewHandler(request, options, response)
      : response;
  });
}
