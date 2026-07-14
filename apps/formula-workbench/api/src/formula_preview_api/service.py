from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import unicodedata
from collections.abc import Mapping, Sequence
from numbers import Real
from time import perf_counter
from typing import Any

import pandas as pd
from player_attribute_engine import (
    EvaluationError,
    FormulaContractError,
    FormulaDocument,
    MetricDefinition,
    evaluate_player_attributes,
    load_formula_payload_snapshot,
    parse_formula_document,
)
from player_data_contracts import (
    ReferencePackageIntegrityError,
    load_reference_package_tables,
)

from formula_preview_api.config import PreviewSettings
from formula_preview_api.errors import FieldError, PreviewAPIError
from formula_preview_api.models import (
    APIContext,
    AttributeRank,
    BaselineResponse,
    ComponentUsage,
    FormulaIdentity,
    FormulaResponse,
    MetricMetadata,
    MetricsResponse,
    PlayerDetailResponse,
    PlayerSummary,
    PreviewPlayerResult,
    PreviewRequest,
    PreviewResponse,
    ReferencePackageIdentity,
    RepresentativesResponse,
    RepresentativeTier,
    SearchHit,
    SearchResponse,
    ValueChange,
)

_IDENTITY_FIELDS = ("playerSeasonId", "playerId", "season")
_OUTPUT_METADATA_FIELDS = {"playerId", "formulaVersion"}


def _normalized_search_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in normalized if character.isalnum())


def _label(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", " ", name).replace("_", " ").title()


def _metric_description(metric: MetricDefinition) -> str:
    kind = metric.kind
    if kind == "input":
        return f"Reference input field {_label(str(metric.field))}."
    inputs = tuple(str(value) for value in metric.inputs)
    if kind == "ratio":
        return f"Ratio of {_label(inputs[0])} to {_label(inputs[1])}."
    if kind == "stabilizedPercentage":
        prior = float(metric.prior_attempts or 0)
        return (
            f"Season-stabilized {_label(inputs[0])} divided by {_label(inputs[1])} "
            f"using {prior:g} prior attempts."
        )
    if kind == "scheduledRatio":
        return f"Schedule-relative ratio of {_label(inputs[0])} for the declared season."
    return f"Formula metric {_label(metric.name)}."


def _rank_by_attribute(
    rows: Sequence[Mapping[str, Any]],
    attribute: str,
) -> dict[str, int | None]:
    values = pd.Series(
        {str(row["playerId"]): row.get(attribute) for row in rows},
        dtype="Float64",
    )
    ranked = values.rank(method="min", ascending=False, na_option="keep")
    return {
        player_id: None if pd.isna(rank) else int(rank)
        for player_id, rank in ranked.items()
    }


def _formula_hash(
    payload: Mapping[str, Any],
    active_payload: Mapping[str, Any],
    active: str,
) -> str:
    if payload == active_payload:
        return active
    content = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def _number_delta(baseline: object, preview: object) -> float | None:
    if (
        isinstance(baseline, Real)
        and not isinstance(baseline, bool)
        and isinstance(preview, Real)
        and not isinstance(preview, bool)
    ):
        return float(preview) - float(baseline)
    return None


class PreviewService:
    """Immutable in-memory baseline plus temporary shared-engine previews."""

    def __init__(self, settings: PreviewSettings) -> None:
        self.settings = settings
        try:
            package = load_reference_package_tables(
                settings.reference_package,
                allowed_versions=(2,),
            )
        except ReferencePackageIntegrityError as error:
            raise ValueError(f"Unable to load preview reference package: {error}") from error

        payload, formula, formula_hash = load_formula_payload_snapshot()
        if formula.reference_contract_version > package.package_version:
            raise ValueError(
                "Active formula requires reference contract version "
                f"{formula.reference_contract_version}, but the preview package provides "
                f"version {package.package_version}."
            )

        cohort, published = self._cohort_frames(package.tables, settings.season)
        if cohort.empty:
            raise ValueError(
                f"Reference package has no player rows for configured preview season "
                f"{settings.season}."
            )
        if len(cohort) > settings.max_cohort_size:
            raise ValueError(
                f"Configured preview season {settings.season} has {len(cohort)} rows; "
                f"maximum is {settings.max_cohort_size}."
            )

        try:
            batch = evaluate_player_attributes(cohort, formula)
        except EvaluationError as error:
            raise ValueError(
                f"Unable to evaluate configured preview season {settings.season}: {error}"
            ) from error
        self._verify_output_identity(cohort, batch.rows)

        manifest = package.manifest
        published_formula_version = manifest.get("formulaVersion")
        published_formula_hash = manifest.get("formulaDocumentHash")
        if (
            published_formula_version == formula.formula_version
            and published_formula_hash == formula_hash
        ):
            self._verify_published_baseline(batch.rows, published)

        self._package = package
        self._formula_payload = payload
        self._formula = formula
        self._formula_hash = formula_hash
        self._cohort = cohort
        self._baseline_rows = {
            str(row["playerId"]): copy.deepcopy(row) for row in batch.rows
        }
        self._baseline_explanations = {
            str(row["playerId"]): copy.deepcopy(row) for row in batch.explanations
        }
        self._attribute_names = frozenset(
            attribute.name for attribute in self._formula.attributes
        )
        self._baseline_attribute_ranks = {
            attribute: _rank_by_attribute(batch.rows, attribute)
            for attribute in self._attribute_names
        }
        self._baseline_ranks = self._baseline_attribute_ranks["overall"]
        self._display_names = {
            str(row.playerId): str(row.displayName)
            for row in cohort[["playerId", "displayName"]].itertuples(index=False)
        }
        self._ordered_player_ids = tuple(
            sorted(
                self._baseline_rows,
                key=lambda player_id: (
                    self._baseline_rows[player_id].get("overall") is None,
                    -int(self._baseline_rows[player_id].get("overall") or 0),
                    player_id,
                ),
            )
        )

    @staticmethod
    def _cohort_frames(
        tables: Mapping[str, list[dict[str, object]]],
        season: int,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        frames = {name: pd.DataFrame(rows) for name, rows in tables.items()}
        seasons = frames["player_seasons.csv"]
        seasons = seasons.loc[seasons["season"] == season].copy()
        keys = list(_IDENTITY_FIELDS)
        try:
            cohort = seasons.merge(
                frames["players.csv"],
                on="playerId",
                how="left",
                sort=False,
                validate="many_to_one",
            ).merge(
                frames["player_stats.csv"],
                on=keys,
                how="left",
                sort=False,
                validate="one_to_one",
            ).merge(
                frames["player_advanced_stats.csv"],
                on=keys,
                how="left",
                sort=False,
                validate="one_to_one",
            )
        except pd.errors.MergeError as error:
            raise ValueError(
                "Preview reference tables must join one-to-one at player-season grain."
            ) from error
        cohort = cohort.sort_values("playerId", kind="stable").reset_index(drop=True)
        published = frames["player_attributes.csv"]
        published = published.loc[published["season"] == season].copy()
        return cohort, published

    @staticmethod
    def _verify_output_identity(
        cohort: pd.DataFrame,
        rows: Sequence[Mapping[str, Any]],
    ) -> None:
        expected = [str(value) for value in cohort["playerId"]]
        actual = [str(row.get("playerId")) for row in rows]
        if actual != expected:
            raise ValueError("Attribute engine output player identity/order mismatch.")

    @staticmethod
    def _verify_published_baseline(
        evaluated: Sequence[Mapping[str, Any]],
        published: pd.DataFrame,
    ) -> None:
        expected_by_player = {
            str(row["playerId"]): row for row in published.to_dict(orient="records")
        }
        if set(expected_by_player) != {str(row["playerId"]) for row in evaluated}:
            raise ValueError(
                "Published attributes do not cover the configured preview season cohort."
            )
        for row in evaluated:
            player_id = str(row["playerId"])
            expected = expected_by_player[player_id]
            for field, actual in row.items():
                if field == "playerId":
                    continue
                published_value = expected.get(field)
                if actual is None and (
                    published_value is None or bool(pd.isna(published_value))
                ):
                    continue
                if isinstance(actual, Real) and isinstance(published_value, Real):
                    if math.isclose(
                        float(actual),
                        float(published_value),
                        rel_tol=1e-12,
                        abs_tol=1e-12,
                    ):
                        continue
                elif actual == published_value:
                    continue
                raise ValueError(
                    "Published reference attributes do not match shared-engine baseline for "
                    f"player {player_id!r} field {field!r}."
                )

    def context(self) -> APIContext:
        return APIContext(
            reference_package=ReferencePackageIdentity(
                package_version=self._package.package_version,
                content_hash=self._package.content_hash,
                published_formula_version=self._package.manifest.get("formulaVersion"),
                published_formula_document_hash=self._package.manifest.get(
                    "formulaDocumentHash"
                ),
            ),
            formula=FormulaIdentity(
                schema_version=self._formula.schema_version,
                formula_version=self._formula.formula_version,
                document_hash=self._formula_hash,
            ),
            season=self.settings.season,
            cohort_size=len(self._cohort),
        )

    def formula(self) -> FormulaResponse:
        return FormulaResponse(
            context=self.context(),
            document=copy.deepcopy(self._formula_payload),
        )

    def metrics(self) -> MetricsResponse:
        usages: dict[str, list[ComponentUsage]] = {
            name: [] for name in self._formula.metrics
        }
        for attribute in self._formula.attributes:
            for component in attribute.components:
                usages[component.metric].append(
                    ComponentUsage(
                        attribute=attribute.name,
                        weight=component.weight,
                        direction=component.direction,
                    )
                )
        metadata = []
        for name, metric in self._formula.metrics.items():
            metadata.append(
                MetricMetadata(
                    name=name,
                    label=_label(name),
                    description=_metric_description(metric),
                    kind=metric.kind,
                    field=metric.field,
                    inputs=list(metric.inputs),
                    prior_attempts=metric.prior_attempts,
                    schedule=dict(metric.schedule),
                    used_by=usages[name],
                )
            )
        return MetricsResponse(context=self.context(), metrics=metadata)

    def _search_hit(self, player_id: str) -> SearchHit:
        baseline = self._baseline_rows[player_id]
        return SearchHit(
            player_id=player_id,
            display_name=self._display_names[player_id],
            season=self.settings.season,
            baseline_rank=self._baseline_ranks[player_id],
            overall=baseline.get("overall"),
        )

    def baseline(
        self,
        *,
        limit: int | None = None,
        pinned_player_ids: Sequence[str] = (),
    ) -> BaselineResponse:
        sample_size = self.settings.default_sample_size if limit is None else limit
        fields: list[FieldError] = []
        if sample_size <= 0 or sample_size > self.settings.default_sample_size:
            fields.append(
                FieldError(
                    "limit",
                    "out_of_range",
                    f"limit must be between 1 and {self.settings.default_sample_size}.",
                )
            )
        pins = tuple(pinned_player_ids)
        if len(pins) > self.settings.max_pinned_players:
            fields.append(
                FieldError(
                    "pinnedPlayerId",
                    "too_many",
                    f"At most {self.settings.max_pinned_players} pinned players are allowed.",
                )
            )
        if len(set(pins)) != len(pins):
            fields.append(
                FieldError(
                    "pinnedPlayerId",
                    "duplicate",
                    "Pinned player IDs must be unique.",
                )
            )
        missing = [player_id for player_id in pins if player_id not in self._baseline_rows]
        if missing:
            fields.append(
                FieldError(
                    "pinnedPlayerId",
                    "missing_player",
                    f"Players are unavailable in season {self.settings.season}: "
                    + ", ".join(missing),
                )
            )
        if fields:
            raise PreviewAPIError(
                status_code=422,
                code="invalid_request",
                message="Baseline request validation failed.",
                fields=fields,
            )

        default_ids = list(self._ordered_player_ids[:sample_size])
        selected_ids = [*default_ids, *(value for value in pins if value not in default_ids)]
        pinned_set = set(pins)
        players = [
            PlayerSummary(
                player_id=player_id,
                display_name=self._display_names[player_id],
                season=self.settings.season,
                baseline_rank=self._baseline_ranks[player_id],
                baseline=copy.deepcopy(self._baseline_rows[player_id]),
                pinned=player_id in pinned_set,
            )
            for player_id in selected_ids
        ]
        return BaselineResponse(
            context=self.context(),
            default_sample_size=self.settings.default_sample_size,
            players=players,
        )

    def representatives(self, *, per_tier: int = 3) -> RepresentativesResponse:
        if per_tier < 1 or per_tier > 5:
            raise PreviewAPIError(
                status_code=422,
                code="invalid_request",
                message="Representative-player request validation failed.",
                fields=[
                    FieldError(
                        "perTier",
                        "out_of_range",
                        "perTier must be between 1 and 5.",
                    )
                ],
            )

        groups: list[RepresentativeTier] = []
        ordered_tiers = sorted(
            self._formula.talent_tiers,
            key=lambda tier: (tier.minimum, tier.maximum, tier.name),
            reverse=True,
        )
        for tier in ordered_tiers:
            player_ids = [
                player_id
                for player_id in self._ordered_player_ids
                if self._baseline_rows[player_id].get("talentTier") == tier.name
                and self._baseline_ranks[player_id] is not None
            ][:per_tier]
            if not player_ids:
                continue
            groups.append(
                RepresentativeTier(
                    tier=tier.name,
                    minimum=tier.minimum,
                    maximum=tier.maximum,
                    players=[
                        PlayerSummary(
                            player_id=player_id,
                            display_name=self._display_names[player_id],
                            season=self.settings.season,
                            baseline_rank=self._baseline_ranks[player_id],
                            baseline=copy.deepcopy(self._baseline_rows[player_id]),
                            pinned=False,
                        )
                        for player_id in player_ids
                    ],
                )
            )
        return RepresentativesResponse(
            context=self.context(),
            per_tier=per_tier,
            tiers=groups,
        )

    def search(self, query: str, *, limit: int | None = None) -> SearchResponse:
        normalized = _normalized_search_text(query)
        if not normalized:
            raise PreviewAPIError(
                status_code=422,
                code="invalid_request",
                message="Search request validation failed.",
                fields=[FieldError("q", "required", "q must contain searchable text.")],
            )
        result_limit = self.settings.max_search_results if limit is None else limit
        if result_limit <= 0 or result_limit > self.settings.max_search_results:
            raise PreviewAPIError(
                status_code=422,
                code="invalid_request",
                message="Search request validation failed.",
                fields=[
                    FieldError(
                        "limit",
                        "out_of_range",
                        f"limit must be between 1 and {self.settings.max_search_results}.",
                    )
                ],
            )
        matches = []
        for player_id in self._baseline_rows:
            normalized_id = _normalized_search_text(player_id)
            normalized_name = _normalized_search_text(self._display_names[player_id])
            if normalized in normalized_id or normalized in normalized_name:
                matches.append(player_id)
        matches.sort(
            key=lambda player_id: (
                _normalized_search_text(player_id) != normalized,
                not _normalized_search_text(self._display_names[player_id]).startswith(normalized),
                self._baseline_ranks[player_id] is None,
                self._baseline_ranks[player_id] or 10**9,
                self._display_names[player_id].casefold(),
                player_id,
            )
        )
        return SearchResponse(
            context=self.context(),
            query=query,
            players=[self._search_hit(player_id) for player_id in matches[:result_limit]],
        )

    def detail(self, player_id: str) -> PlayerDetailResponse:
        if player_id not in self._baseline_rows:
            raise PreviewAPIError(
                status_code=404,
                code="player_not_found",
                message=f"Player {player_id!r} is unavailable in season {self.settings.season}.",
                fields=[FieldError("playerId", "missing_player", "Player was not found.")],
            )
        return PlayerDetailResponse(
            context=self.context(),
            player=self._search_hit(player_id),
            baseline=copy.deepcopy(self._baseline_rows[player_id]),
            calculation=copy.deepcopy(self._baseline_explanations[player_id]),
        )

    def _validate_preview_context(self, request: PreviewRequest) -> None:
        stale: list[FieldError] = []
        if request.reference_package_hash != self._package.content_hash:
            stale.append(
                FieldError(
                    "referencePackageHash",
                    "stale_reference_package",
                    "Reference package content hash does not match the loaded package.",
                )
            )
        if request.formula_version != self._formula.formula_version:
            stale.append(
                FieldError(
                    "formulaVersion",
                    "stale_formula",
                    "Formula version does not match the active formula.",
                )
            )
        if request.formula_document_hash != self._formula_hash:
            stale.append(
                FieldError(
                    "formulaDocumentHash",
                    "stale_formula",
                    "Formula document hash does not match the active formula.",
                )
            )
        if request.season != self.settings.season:
            stale.append(
                FieldError(
                    "season",
                    "stale_season",
                    "Season does not match the loaded preview cohort.",
                )
            )
        if stale:
            raise PreviewAPIError(
                status_code=409,
                code="stale_context",
                message="Preview context no longer matches the loaded baseline.",
                fields=stale,
            )

    def _validate_selected_players(self, player_ids: Sequence[str]) -> None:
        fields: list[FieldError] = []
        if len(player_ids) > self.settings.max_pinned_players:
            fields.append(
                FieldError(
                    "selectedPlayerIds",
                    "too_many",
                    f"At most {self.settings.max_pinned_players} players are allowed.",
                )
            )
        if len(set(player_ids)) != len(player_ids):
            fields.append(
                FieldError(
                    "selectedPlayerIds",
                    "duplicate",
                    "Selected player IDs must be unique.",
                )
            )
        missing = [player_id for player_id in player_ids if player_id not in self._baseline_rows]
        if missing:
            fields.append(
                FieldError(
                    "selectedPlayerIds",
                    "missing_player",
                    f"Players are unavailable in season {self.settings.season}: "
                    + ", ".join(missing),
                )
            )
        if fields:
            raise PreviewAPIError(
                status_code=422,
                code="invalid_request",
                message="Preview request validation failed.",
                fields=fields,
            )

    def _validate_selected_attribute(self, attribute: str) -> None:
        if attribute not in self._attribute_names:
            raise PreviewAPIError(
                status_code=422,
                code="invalid_request",
                message="Preview request validation failed.",
                fields=[
                    FieldError(
                        "selectedAttribute",
                        "unknown_attribute",
                        f"Unknown formula attribute {attribute!r}.",
                    )
                ],
            )

    def _preview_formula(
        self,
        request: PreviewRequest,
    ) -> tuple[FormulaDocument, str, dict[str, Any]]:
        payload = copy.deepcopy(self._formula_payload)
        if request.adjustments.formula_version is not None:
            payload["formulaVersion"] = request.adjustments.formula_version
        attributes = {
            str(attribute["name"]): attribute for attribute in payload["attributes"]
        }
        component_edits: set[tuple[str, str]] = set()
        errors: list[FieldError] = []
        for index, adjustment in enumerate(request.adjustments.components):
            path = f"adjustments.components.{index}"
            key = (adjustment.attribute, adjustment.metric)
            if key in component_edits:
                errors.append(
                    FieldError(path, "duplicate", "Component adjustment is duplicated.")
                )
                continue
            component_edits.add(key)
            attribute = attributes.get(adjustment.attribute)
            if attribute is None:
                errors.append(
                    FieldError(
                        f"{path}.attribute",
                        "unknown_attribute",
                        f"Unknown attribute {adjustment.attribute!r}.",
                    )
                )
                continue
            components = {
                str(component["metric"]): component for component in attribute["components"]
            }
            component = components.get(adjustment.metric)
            if component is None:
                errors.append(
                    FieldError(
                        f"{path}.metric",
                        "unknown_component",
                        f"Metric {adjustment.metric!r} is not a component of "
                        f"{adjustment.attribute!r}.",
                    )
                )
                continue
            if adjustment.weight is not None:
                component["weight"] = adjustment.weight
            if adjustment.inverse_direction is not None:
                baseline_direction = str(component["direction"])
                component["direction"] = (
                    "lower"
                    if adjustment.inverse_direction and baseline_direction == "higher"
                    else "higher"
                    if adjustment.inverse_direction and baseline_direction == "lower"
                    else baseline_direction
                )

        scales = payload["ratingScales"]
        edited_scales: set[str] = set()
        for index, adjustment in enumerate(request.adjustments.rating_scales):
            path = f"adjustments.ratingScales.{index}"
            if adjustment.scale in edited_scales:
                errors.append(FieldError(path, "duplicate", "Rating scale edit is duplicated."))
                continue
            edited_scales.add(adjustment.scale)
            if adjustment.scale not in scales:
                errors.append(
                    FieldError(
                        f"{path}.scale",
                        "unknown_rating_scale",
                        f"Unknown rating scale {adjustment.scale!r}.",
                    )
                )
                continue
            scales[adjustment.scale]["anchors"] = [
                anchor.model_dump(by_alias=True) for anchor in adjustment.anchors
            ]
        if errors:
            raise PreviewAPIError(
                status_code=422,
                code="invalid_request",
                message="Preview adjustments are invalid.",
                fields=errors,
            )
        try:
            formula = parse_formula_document(payload)
        except FormulaContractError as error:
            raise PreviewAPIError(
                status_code=422,
                code="invalid_formula",
                message="Preview adjustments do not produce a valid formula.",
                fields=[FieldError("adjustments", "invalid_formula", str(error))],
            ) from error
        return (
            formula,
            _formula_hash(payload, self._formula_payload, self._formula_hash),
            payload,
        )

    def preview(self, request: PreviewRequest) -> PreviewResponse:
        self._validate_preview_context(request)
        self._validate_selected_players(request.selected_player_ids)
        self._validate_selected_attribute(request.selected_attribute)
        formula, preview_hash, preview_document = self._preview_formula(request)
        started = perf_counter()
        try:
            batch = evaluate_player_attributes(
                self._cohort,
                formula,
                explanation_player_ids=request.selected_player_ids,
            )
        except EvaluationError as error:
            raise PreviewAPIError(
                status_code=422,
                code="evaluation_failed",
                message="Preview formula could not be evaluated.",
                fields=[FieldError("adjustments", "evaluation_failed", str(error))],
            ) from error
        preview_rows = {str(row["playerId"]): row for row in batch.rows}
        preview_explanations = {
            str(row["playerId"]): row for row in batch.explanations
        }
        preview_ranks = _rank_by_attribute(batch.rows, "overall")
        baseline_attribute_ranks = self._baseline_attribute_ranks[
            request.selected_attribute
        ]
        preview_attribute_ranks = (
            preview_ranks
            if request.selected_attribute == "overall"
            else _rank_by_attribute(batch.rows, request.selected_attribute)
        )
        elapsed_ms = (perf_counter() - started) * 1000

        output_fields = [
            field for field in self._formula.output_fields if field not in _OUTPUT_METADATA_FIELDS
        ]
        players: list[PreviewPlayerResult] = []
        for player_id in request.selected_player_ids:
            baseline = self._baseline_rows[player_id]
            preview = preview_rows[player_id]
            baseline_rank = self._baseline_ranks[player_id]
            preview_rank = preview_ranks[player_id]
            rank_movement = (
                None
                if baseline_rank is None or preview_rank is None
                else baseline_rank - preview_rank
            )
            baseline_attribute_rank = baseline_attribute_ranks[player_id]
            preview_attribute_rank = preview_attribute_ranks[player_id]
            attribute_rank_movement = (
                None
                if baseline_attribute_rank is None or preview_attribute_rank is None
                else baseline_attribute_rank - preview_attribute_rank
            )
            changes = {
                field: ValueChange(
                    baseline_value=baseline.get(field),
                    preview_value=preview.get(field),
                    delta=_number_delta(baseline.get(field), preview.get(field)),
                )
                for field in output_fields
            }
            players.append(
                PreviewPlayerResult(
                    player_id=player_id,
                    display_name=self._display_names[player_id],
                    season=self.settings.season,
                    baseline_rank=baseline_rank,
                    preview_rank=preview_rank,
                    rank_movement=rank_movement,
                    attribute_rank=AttributeRank(
                        attribute=request.selected_attribute,
                        baseline_rank=baseline_attribute_rank,
                        preview_rank=preview_attribute_rank,
                        rank_movement=attribute_rank_movement,
                    ),
                    baseline=copy.deepcopy(baseline),
                    preview=copy.deepcopy(preview),
                    changes=changes,
                    baseline_calculation=copy.deepcopy(
                        self._baseline_explanations[player_id]
                    ),
                    preview_calculation=copy.deepcopy(preview_explanations[player_id]),
                )
            )
        return PreviewResponse(
            context=self.context(),
            preview_formula_hash=preview_hash,
            preview_document=copy.deepcopy(preview_document),
            elapsed_ms=elapsed_ms,
            players=players,
        )
