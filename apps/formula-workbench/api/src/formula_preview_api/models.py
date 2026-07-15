from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from formula_preview_api.config import API_V1_MAX_SELECTED_PLAYERS


def _camel_case(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in tail)


class APIModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel_case,
        populate_by_name=True,
        extra="forbid",
        allow_inf_nan=False,
    )


class APIInputModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel_case,
        populate_by_name=False,
        extra="forbid",
        allow_inf_nan=False,
        strict=True,
    )


class ReferencePackageIdentity(APIModel):
    package_version: int
    content_hash: str
    published_formula_version: str | None = None
    published_formula_document_hash: str | None = None


class FormulaIdentity(APIModel):
    schema_version: int
    formula_version: str
    document_hash: str


class APIContext(APIModel):
    api_version: Literal["1"] = "1"
    reference_package: ReferencePackageIdentity
    formula: FormulaIdentity
    season: int
    cohort_size: int


class FormulaResponse(APIModel):
    context: APIContext
    document: dict[str, Any]


class ComponentUsage(APIModel):
    attribute: str
    weight: float
    direction: Literal["higher", "lower"]


class MetricMetadata(APIModel):
    name: str
    label: str
    description: str
    kind: str
    field: str | None = None
    inputs: list[str] = Field(default_factory=list)
    prior_attempts: float | None = None
    schedule: dict[str, int] = Field(default_factory=dict)
    used_by: list[ComponentUsage] = Field(default_factory=list)


class MetricsResponse(APIModel):
    context: APIContext
    metrics: list[MetricMetadata]


class PlayerSummary(APIModel):
    player_id: str
    display_name: str
    season: int
    baseline_rank: int | None
    baseline: dict[str, Any]
    pinned: bool = False


class BaselineResponse(APIModel):
    context: APIContext
    default_sample_size: int
    players: list[PlayerSummary]


class RepresentativeTier(APIModel):
    tier: str
    minimum: int
    maximum: int
    players: list[PlayerSummary]


class RepresentativesResponse(APIModel):
    context: APIContext
    per_tier: int
    tiers: list[RepresentativeTier]


class SearchHit(APIModel):
    player_id: str
    display_name: str
    season: int
    baseline_rank: int | None
    overall: int | None


class SearchResponse(APIModel):
    context: APIContext
    query: str
    players: list[SearchHit]


class PlayerDetailResponse(APIModel):
    context: APIContext
    player: SearchHit
    baseline: dict[str, Any]
    calculation: dict[str, Any]


class PercentileAnchorInput(APIInputModel):
    percentile: float = Field(ge=0, le=1)
    rating: float = Field(ge=25, le=99)


class ComponentAdjustment(APIInputModel):
    attribute: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    weight: float | None = Field(default=None, ge=0)
    inverse_direction: bool | None = None

    @model_validator(mode="after")
    def require_a_change(self) -> ComponentAdjustment:
        if self.weight is None and self.inverse_direction is None:
            raise ValueError("weight or inverseDirection is required")
        return self


class RatingScaleAdjustment(APIInputModel):
    scale: str = Field(min_length=1)
    anchors: list[PercentileAnchorInput] = Field(min_length=2, max_length=32)


class PreviewAdjustments(APIInputModel):
    formula_version: str | None = Field(default=None, min_length=1)
    components: list[ComponentAdjustment] = Field(default_factory=list, max_length=100)
    rating_scales: list[RatingScaleAdjustment] = Field(default_factory=list, max_length=16)


class PreviewRequest(APIInputModel):
    api_version: Literal["1"]
    reference_package_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    formula_version: str = Field(min_length=1)
    formula_document_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    season: int = Field(ge=1)
    selected_player_ids: list[str] = Field(
        min_length=1,
        max_length=API_V1_MAX_SELECTED_PLAYERS,
    )
    selected_attribute: str = Field(default="overall", min_length=1)
    adjustments: PreviewAdjustments = Field(default_factory=PreviewAdjustments)


class ValueChange(APIModel):
    baseline_value: Any
    preview_value: Any
    delta: float | None


class AttributeRank(APIModel):
    attribute: str
    baseline_rank: int | None
    preview_rank: int | None
    rank_movement: int | None


class PreviewPlayerResult(APIModel):
    player_id: str
    display_name: str
    season: int
    baseline_rank: int | None
    preview_rank: int | None
    rank_movement: int | None
    attribute_rank: AttributeRank
    baseline: dict[str, Any]
    preview: dict[str, Any]
    changes: dict[str, ValueChange]
    baseline_calculation: dict[str, Any]
    preview_calculation: dict[str, Any]


class PreviewResponse(APIModel):
    context: APIContext
    preview_formula_hash: str
    preview_document: dict[str, Any]
    elapsed_ms: float
    players: list[PreviewPlayerResult]


class ErrorField(APIModel):
    path: str
    code: str
    message: str


class ErrorDetail(APIModel):
    code: str
    message: str
    fields: list[ErrorField]


class ErrorResponse(APIModel):
    error: ErrorDetail
