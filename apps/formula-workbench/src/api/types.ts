export type Direction = "higher" | "lower";

export type MetricKind =
  | "input"
  | "ratio"
  | "scheduledRatio"
  | "stabilizedPercentage";

export type JsonScalar = boolean | number | string | null;

export interface ReferencePackageIdentity {
  packageVersion: number;
  contentHash: string;
  publishedFormulaVersion: string | null;
  publishedFormulaDocumentHash: string | null;
}

export interface FormulaIdentity {
  schemaVersion: number;
  formulaVersion: string;
  documentHash: string;
}

export interface ApiContext {
  apiVersion: "1";
  referencePackage: ReferencePackageIdentity;
  formula: FormulaIdentity;
  season: number;
  cohortSize: number;
}

export interface FormulaRules {
  nullHandling: "exclude";
  tieMethod: "average";
  percentileMethod: "rankPct";
  ratingRounding: "halfEven";
}

export interface InputMetricDefinition {
  kind: "input";
  field: string;
}

export interface RatioMetricDefinition {
  kind: "ratio";
  inputs: [string, string];
}

export interface StabilizedPercentageMetricDefinition {
  kind: "stabilizedPercentage";
  inputs: [string, string];
  priorAttempts: number;
}

export interface ScheduledRatioMetricDefinition {
  kind: "scheduledRatio";
  inputs: [string, string];
  schedule: Record<string, number>;
}

export type FormulaMetricDefinition =
  | InputMetricDefinition
  | RatioMetricDefinition
  | ScheduledRatioMetricDefinition
  | StabilizedPercentageMetricDefinition;

export interface FormulaCohort {
  groupBy: string[];
}

export interface EligibilityRule {
  requiredMetrics: string[];
  minimumSamples: Record<string, number>;
}

export interface PercentileAnchor {
  percentile: number;
  rating: number;
}

export interface RatingScale {
  minimum: number;
  maximum: number;
  anchors: PercentileAnchor[];
}

export interface FormulaComponent {
  metric: string;
  weight: number;
  direction: Direction;
}

export interface AttributeFormula {
  name: string;
  components: FormulaComponent[];
  eligibilityRule: string;
  cohort: string;
  ratingScale: string;
  rerankComposite: boolean;
  percentileOutput?: string;
}

export interface TalentTier {
  name: string;
  minimum: number;
  maximum: number;
}

export interface FormulaDocument {
  schemaVersion: number;
  formulaVersion: string;
  referenceContractVersion: number;
  outputFields: string[];
  rules: FormulaRules;
  metrics: Record<string, FormulaMetricDefinition>;
  cohorts: Record<string, FormulaCohort>;
  eligibilityRules: Record<string, EligibilityRule>;
  ratingScales: Record<string, RatingScale>;
  attributes: AttributeFormula[];
  talentTiers: TalentTier[];
}

export interface FormulaResponse {
  context: ApiContext;
  document: FormulaDocument;
}

export interface ComponentUsage {
  attribute: string;
  weight: number;
  direction: Direction;
}

export interface MetricMetadata {
  name: string;
  label: string;
  description: string;
  kind: MetricKind;
  field: string | null;
  inputs: string[];
  priorAttempts: number | null;
  schedule: Record<string, number>;
  usedBy: ComponentUsage[];
}

export interface MetricsResponse {
  context: ApiContext;
  metrics: MetricMetadata[];
}

export type PlayerAttributeValues = Record<string, JsonScalar>;

export interface PlayerSummary {
  playerId: string;
  displayName: string;
  season: number;
  baselineRank: number | null;
  baseline: PlayerAttributeValues;
  pinned: boolean;
}

export interface BaselineResponse {
  context: ApiContext;
  defaultSampleSize: number;
  players: PlayerSummary[];
}

export interface TierRepresentativeGroup {
  tier: string;
  minimum: number;
  maximum: number;
  players: PlayerSummary[];
}

export interface TierRepresentativesResponse {
  context: ApiContext;
  perTier: number;
  tiers: TierRepresentativeGroup[];
}

export interface SearchHit {
  playerId: string;
  displayName: string;
  season: number;
  baselineRank: number | null;
  overall: number | null;
}

export interface SearchResponse {
  context: ApiContext;
  query: string;
  players: SearchHit[];
}

export interface IneligibilityReason {
  kind: string;
  metric: string;
  minimum?: number;
  actual?: number | null;
}

export interface CalculationCohort {
  name: string;
  values: Record<string, JsonScalar>;
  eligibleCount: number;
}

export interface MetricCalculation {
  kind: string;
  value: number | null;
  field?: string;
  inputs?: Record<string, MetricCalculation>;
  priorAttempts?: number;
  season?: number;
  leagueAverage?: number | null;
  zeroDenominatorValue?: number;
  scheduledGames?: number | null;
  minimum?: number;
  maximum?: number;
}

export interface AttributeCalculation {
  eligible: boolean;
  ineligibilityReasons: IneligibilityReason[];
  cohort: CalculationCohort;
  rawInputs: Record<string, number | null>;
  metricDetails: Record<string, MetricCalculation>;
  componentPercentiles: Record<string, number | null>;
  normalizedWeights: Record<string, number>;
  contributions: Record<string, number | null>;
  composite: number | null;
  compositePercentile: number | null;
  rating: number | null;
}

export interface PlayerCalculation {
  playerId: string;
  season: number | null;
  formulaVersion: string;
  attributes: Record<string, AttributeCalculation>;
}

export interface PlayerDetailResponse {
  context: ApiContext;
  player: SearchHit;
  baseline: PlayerAttributeValues;
  calculation: PlayerCalculation;
}

export interface ComponentAdjustment {
  attribute: string;
  metric: string;
  weight?: number;
  inverseDirection?: boolean;
}

export interface RatingScaleAdjustment {
  scale: string;
  anchors: PercentileAnchor[];
}

export interface PreviewAdjustments {
  formulaVersion: string;
  components: ComponentAdjustment[];
  ratingScales: RatingScaleAdjustment[];
}

export interface PreviewRequest {
  apiVersion: "1";
  referencePackageHash: string;
  formulaVersion: string;
  formulaDocumentHash: string;
  season: number;
  selectedAttribute: string;
  selectedPlayerIds: string[];
  adjustments: PreviewAdjustments;
}

export interface ValueChange {
  baselineValue: JsonScalar;
  previewValue: JsonScalar;
  delta: number | null;
}

export interface AttributeRank {
  attribute: string;
  baselineRank: number | null;
  previewRank: number | null;
  rankMovement: number | null;
}

export interface PreviewPlayerResult {
  playerId: string;
  displayName: string;
  season: number;
  baselineRank: number | null;
  previewRank: number | null;
  rankMovement: number | null;
  attributeRank: AttributeRank;
  baseline: PlayerAttributeValues;
  preview: PlayerAttributeValues;
  changes: Record<string, ValueChange>;
  baselineCalculation: PlayerCalculation;
  previewCalculation: PlayerCalculation;
}

export interface PreviewResponse {
  context: ApiContext;
  previewFormulaHash: string;
  elapsedMs: number;
  previewDocument: FormulaDocument;
  players: PreviewPlayerResult[];
}

export interface ErrorField {
  path: string;
  code: string;
  message: string;
}

export interface ErrorDetail {
  code: string;
  message: string;
  fields: ErrorField[];
}

export interface ErrorResponse {
  error: ErrorDetail;
}
