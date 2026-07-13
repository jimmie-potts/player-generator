"""Validated declarative player-attribute formula contracts."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from player_data_contracts.reference import (
    REFERENCE_CONTRACT_VERSION,
    load_reference_contract,
)


class FormulaContractError(ValueError):
    """Raised when a formula document does not satisfy schema version 1."""


@dataclass(frozen=True)
class MetricDefinition:
    name: str
    kind: str
    field: str | None = None
    inputs: tuple[str, ...] = ()
    prior_attempts: float | None = None
    schedule: Mapping[str, int] = MappingProxyType({})

    @property
    def dependencies(self) -> tuple[str, ...]:
        return self.inputs


@dataclass(frozen=True)
class FormulaComponent:
    metric: str
    weight: float
    direction: str
    normalized_weight: float


@dataclass(frozen=True)
class PercentileAnchor:
    percentile: float
    rating: float


@dataclass(frozen=True)
class RatingScale:
    name: str
    minimum: int
    maximum: int
    anchors: tuple[PercentileAnchor, ...]


@dataclass(frozen=True)
class EligibilityRule:
    name: str
    required_metrics: tuple[str, ...]
    minimum_samples: Mapping[str, float]


@dataclass(frozen=True)
class PercentileCohort:
    name: str
    group_by: tuple[str, ...]


@dataclass(frozen=True)
class TalentTier:
    name: str
    minimum: int
    maximum: int


@dataclass(frozen=True)
class AttributeFormula:
    name: str
    components: tuple[FormulaComponent, ...]
    eligibility_rule: str
    cohort: str
    rating_scale: str
    rerank_composite: bool
    percentile_output: str | None = None


@dataclass(frozen=True)
class FormulaDocument:
    schema_version: int
    formula_version: str
    reference_contract_version: int
    output_fields: tuple[str, ...]
    rules: Mapping[str, str]
    metrics: Mapping[str, MetricDefinition]
    cohorts: Mapping[str, PercentileCohort]
    eligibility_rules: Mapping[str, EligibilityRule]
    rating_scales: Mapping[str, RatingScale]
    attributes: tuple[AttributeFormula, ...]
    talent_tiers: tuple[TalentTier, ...]


_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_TOP_LEVEL_KEYS = {
    "schemaVersion",
    "formulaVersion",
    "referenceContractVersion",
    "outputFields",
    "rules",
    "metrics",
    "cohorts",
    "eligibilityRules",
    "ratingScales",
    "attributes",
    "talentTiers",
}
_RULES = {
    "nullHandling": "exclude",
    "percentileMethod": "rankPct",
    "tieMethod": "average",
    "ratingRounding": "halfEven",
}
_RESERVED_ATTRIBUTE_NAMES = {
    "playerId",
    "formulaVersion",
    "impactPercentile",
    "talentTier",
}
_RESERVED_PERCENTILE_OUTPUTS = {"playerId", "formulaVersion", "talentTier"}


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FormulaContractError(f"{path} must be an object.")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise FormulaContractError(f"{path} must be an array.")
    return value


def _keys(value: Mapping[str, Any], required: set[str], optional: set[str], path: str) -> None:
    actual = set(value)
    missing = required - actual
    unknown = actual - required - optional
    if missing:
        raise FormulaContractError(f"{path} is missing keys: {', '.join(sorted(missing))}.")
    if unknown:
        raise FormulaContractError(f"{path} has unknown keys: {', '.join(sorted(unknown))}.")


def _name(value: Any, path: str) -> str:
    if not isinstance(value, str) or not _NAME.fullmatch(value):
        raise FormulaContractError(f"{path} must be a non-empty field name.")
    return value


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FormulaContractError(f"{path} must be a non-empty string.")
    return value


def _number(value: Any, path: str, *, nonnegative: bool = False, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FormulaContractError(f"{path} must be a finite number.")
    result = float(value)
    if not math.isfinite(result):
        raise FormulaContractError(f"{path} must be a finite number.")
    if nonnegative and result < 0:
        raise FormulaContractError(f"{path} must be nonnegative.")
    if positive and result <= 0:
        raise FormulaContractError(f"{path} must be positive.")
    return result


def _integer(value: Any, path: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise FormulaContractError(f"{path} must be an integer.")
    if minimum is not None and value < minimum:
        raise FormulaContractError(f"{path} must be at least {minimum}.")
    return value


def _unique_names(values: list[Any], path: str) -> tuple[str, ...]:
    names = tuple(_name(value, f"{path}[{index}]") for index, value in enumerate(values))
    if len(names) != len(set(names)):
        raise FormulaContractError(f"{path} contains duplicate names.")
    return names


def _parse_rules(raw: Any) -> Mapping[str, str]:
    rules = _mapping(raw, "rules")
    _keys(rules, set(_RULES), set(), "rules")
    for key, expected in _RULES.items():
        if rules[key] != expected:
            raise FormulaContractError(f"rules.{key} must equal {expected!r}.")
    return MappingProxyType(dict(_RULES))


def _parse_metrics(raw: Any) -> Mapping[str, MetricDefinition]:
    values = _mapping(raw, "metrics")
    if not values:
        raise FormulaContractError("metrics must not be empty.")
    metrics: dict[str, MetricDefinition] = {}
    for raw_name, raw_definition in values.items():
        name = _name(raw_name, "metrics key")
        definition = _mapping(raw_definition, f"metrics.{name}")
        kind = definition.get("kind")
        if kind == "input":
            _keys(definition, {"kind", "field"}, set(), f"metrics.{name}")
            metrics[name] = MetricDefinition(
                name=name,
                kind=kind,
                field=_name(definition["field"], f"metrics.{name}.field"),
            )
        elif kind in {"ratio", "stabilizedPercentage", "scheduledRatio"}:
            required = {"kind", "inputs"}
            if kind == "stabilizedPercentage":
                required.add("priorAttempts")
            if kind == "scheduledRatio":
                required.add("schedule")
            _keys(definition, required, set(), f"metrics.{name}")
            inputs = _unique_names(
                _list(definition["inputs"], f"metrics.{name}.inputs"),
                f"metrics.{name}.inputs",
            )
            expected_inputs = 2
            if len(inputs) != expected_inputs:
                raise FormulaContractError(
                    f"metrics.{name}.inputs must contain exactly {expected_inputs} metrics."
                )
            prior_attempts = None
            schedule: Mapping[str, int] = MappingProxyType({})
            if kind == "stabilizedPercentage":
                prior_attempts = _number(
                    definition["priorAttempts"],
                    f"metrics.{name}.priorAttempts",
                    positive=True,
                )
            if kind == "scheduledRatio":
                raw_schedule = _mapping(definition["schedule"], f"metrics.{name}.schedule")
                if not raw_schedule:
                    raise FormulaContractError(f"metrics.{name}.schedule must not be empty.")
                parsed_schedule: dict[str, int] = {}
                for season, games in raw_schedule.items():
                    if isinstance(season, bool) or not isinstance(season, (str, int)):
                        raise FormulaContractError(
                            f"metrics.{name}.schedule keys must be seasons."
                        )
                    season_key = str(season)
                    if not re.fullmatch(r"[1-9][0-9]{3}", season_key):
                        raise FormulaContractError(
                            f"metrics.{name}.schedule keys must be canonical four-digit seasons."
                        )
                    if season_key in parsed_schedule:
                        raise FormulaContractError(
                            f"metrics.{name}.schedule contains a duplicate season."
                        )
                    parsed_schedule[season_key] = _integer(
                        games,
                        f"metrics.{name}.schedule[{season_key}]",
                        minimum=1,
                    )
                schedule = MappingProxyType(dict(sorted(parsed_schedule.items())))
            metrics[name] = MetricDefinition(
                name=name,
                kind=kind,
                inputs=inputs,
                prior_attempts=prior_attempts,
                schedule=schedule,
            )
        else:
            raise FormulaContractError(
                f"metrics.{name}.kind must be input, ratio, stabilizedPercentage, "
                "or scheduledRatio."
            )

    for metric in metrics.values():
        for dependency in metric.dependencies:
            if dependency not in metrics:
                raise FormulaContractError(
                    f"metrics.{metric.name} references unknown metric {dependency!r}."
                )
    if any(metric.kind == "stabilizedPercentage" for metric in metrics.values()):
        season = metrics.get("season")
        if season is None:
            raise FormulaContractError(
                "stabilizedPercentage metrics require the conventional 'season' metric."
            )
        if season.kind != "input" or season.field != "season":
            raise FormulaContractError(
                "stabilizedPercentage metrics require the conventional 'season' metric to be "
                "an input mapped to the reference 'season' field."
            )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visiting:
            raise FormulaContractError(f"metrics contain a dependency cycle at {name!r}.")
        if name in visited:
            return
        visiting.add(name)
        for dependency in metrics[name].dependencies:
            visit(dependency)
        visiting.remove(name)
        visited.add(name)

    for name in metrics:
        visit(name)
    return MappingProxyType(metrics)


def _validate_reference_metric_fields(metrics: Mapping[str, MetricDefinition]) -> None:
    contract = load_reference_contract(REFERENCE_CONTRACT_VERSION)
    supported: set[str] = set()
    for file_name in ("player_seasons.csv", "player_stats.csv", "player_advanced_stats.csv"):
        for column in contract["files"][file_name]["columns"]:
            if column["type"] in {"integer", "number"}:
                supported.add(str(column["name"]))
    unknown = sorted(
        metric.field
        for metric in metrics.values()
        if metric.kind == "input" and metric.field not in supported
    )
    if unknown:
        raise FormulaContractError(
            "input metrics reference fields outside reference contract version 1: "
            f"{', '.join(unknown)}."
        )


def _parse_cohorts(
    raw: Any, metrics: Mapping[str, MetricDefinition]
) -> Mapping[str, PercentileCohort]:
    values = _mapping(raw, "cohorts")
    if not values:
        raise FormulaContractError("cohorts must not be empty.")
    cohorts: dict[str, PercentileCohort] = {}
    for raw_name, raw_definition in values.items():
        name = _name(raw_name, "cohorts key")
        definition = _mapping(raw_definition, f"cohorts.{name}")
        _keys(definition, {"groupBy"}, set(), f"cohorts.{name}")
        group_by = _unique_names(
            _list(definition["groupBy"], f"cohorts.{name}.groupBy"),
            f"cohorts.{name}.groupBy",
        )
        if not group_by:
            raise FormulaContractError(f"cohorts.{name}.groupBy must not be empty.")
        unknown = set(group_by) - set(metrics)
        if unknown:
            raise FormulaContractError(
                f"cohorts.{name}.groupBy references unknown metrics: {', '.join(sorted(unknown))}."
            )
        cohorts[name] = PercentileCohort(name, group_by)
    return MappingProxyType(cohorts)


def _parse_eligibility(
    raw: Any, metrics: Mapping[str, MetricDefinition]
) -> Mapping[str, EligibilityRule]:
    values = _mapping(raw, "eligibilityRules")
    if not values:
        raise FormulaContractError("eligibilityRules must not be empty.")
    rules: dict[str, EligibilityRule] = {}
    for raw_name, raw_definition in values.items():
        name = _name(raw_name, "eligibilityRules key")
        definition = _mapping(raw_definition, f"eligibilityRules.{name}")
        _keys(
            definition,
            {"requiredMetrics", "minimumSamples"},
            set(),
            f"eligibilityRules.{name}",
        )
        required_metrics = _unique_names(
            _list(definition["requiredMetrics"], f"eligibilityRules.{name}.requiredMetrics"),
            f"eligibilityRules.{name}.requiredMetrics",
        )
        minimum_samples_raw = _mapping(
            definition["minimumSamples"], f"eligibilityRules.{name}.minimumSamples"
        )
        minimum_samples: dict[str, float] = {}
        for metric, threshold in minimum_samples_raw.items():
            metric_name = _name(metric, f"eligibilityRules.{name}.minimumSamples key")
            minimum_samples[metric_name] = _number(
                threshold,
                f"eligibilityRules.{name}.minimumSamples.{metric_name}",
                nonnegative=True,
            )
        referenced = set(required_metrics) | set(minimum_samples)
        unknown = referenced - set(metrics)
        if unknown:
            raise FormulaContractError(
                f"eligibilityRules.{name} references unknown metrics: "
                f"{', '.join(sorted(unknown))}."
            )
        thresholds_without_requirement = set(minimum_samples) - set(required_metrics)
        if thresholds_without_requirement:
            raise FormulaContractError(
                f"eligibilityRules.{name}.minimumSamples metrics must also be required: "
                f"{', '.join(sorted(thresholds_without_requirement))}."
            )
        rules[name] = EligibilityRule(
            name,
            required_metrics,
            MappingProxyType(dict(sorted(minimum_samples.items()))),
        )
    return MappingProxyType(rules)


def _parse_scales(raw: Any) -> Mapping[str, RatingScale]:
    values = _mapping(raw, "ratingScales")
    if not values:
        raise FormulaContractError("ratingScales must not be empty.")
    scales: dict[str, RatingScale] = {}
    for raw_name, raw_definition in values.items():
        name = _name(raw_name, "ratingScales key")
        definition = _mapping(raw_definition, f"ratingScales.{name}")
        _keys(definition, {"minimum", "maximum", "anchors"}, set(), f"ratingScales.{name}")
        minimum = _integer(definition["minimum"], f"ratingScales.{name}.minimum")
        maximum = _integer(definition["maximum"], f"ratingScales.{name}.maximum")
        if (minimum, maximum) != (25, 99):
            raise FormulaContractError(f"ratingScales.{name} must use the 25-99 scale.")
        raw_anchors = _list(definition["anchors"], f"ratingScales.{name}.anchors")
        if len(raw_anchors) < 2:
            raise FormulaContractError(f"ratingScales.{name}.anchors needs at least two anchors.")
        anchors: list[tuple[float, float]] = []
        for index, raw_anchor in enumerate(raw_anchors):
            anchor = _mapping(raw_anchor, f"ratingScales.{name}.anchors[{index}]")
            _keys(
                anchor,
                {"percentile", "rating"},
                set(),
                f"ratingScales.{name}.anchors[{index}]",
            )
            percentile = _number(
                anchor["percentile"], f"ratingScales.{name}.anchors[{index}].percentile"
            )
            rating = _number(anchor["rating"], f"ratingScales.{name}.anchors[{index}].rating")
            if not 0 <= percentile <= 1:
                raise FormulaContractError(f"ratingScales.{name} percentiles must be within 0-1.")
            if not minimum <= rating <= maximum:
                raise FormulaContractError(
                    f"ratingScales.{name} ratings must be within the 25-99 scale."
                )
            anchors.append((percentile, rating))
        if anchors[0][0] != 0 or anchors[-1][0] != 1:
            raise FormulaContractError(
                f"ratingScales.{name} anchors must start at 0 and end at 1."
            )
        if any(
            left[0] >= right[0] for left, right in zip(anchors, anchors[1:], strict=False)
        ):
            raise FormulaContractError(
                f"ratingScales.{name} percentile anchors must be strictly increasing."
            )
        if any(left[1] > right[1] for left, right in zip(anchors, anchors[1:], strict=False)):
            raise FormulaContractError(f"ratingScales.{name} ratings must be monotonic.")
        scales[name] = RatingScale(
            name,
            minimum,
            maximum,
            tuple(PercentileAnchor(percentile, rating) for percentile, rating in anchors),
        )
    return MappingProxyType(scales)


def _parse_attributes(
    raw: Any,
    metrics: Mapping[str, MetricDefinition],
    eligibility: Mapping[str, EligibilityRule],
    cohorts: Mapping[str, PercentileCohort],
    scales: Mapping[str, RatingScale],
) -> tuple[AttributeFormula, ...]:
    values = _list(raw, "attributes")
    if not values:
        raise FormulaContractError("attributes must not be empty.")
    attributes: list[AttributeFormula] = []
    names: set[str] = set()
    for index, raw_definition in enumerate(values):
        path = f"attributes[{index}]"
        definition = _mapping(raw_definition, path)
        _keys(
            definition,
            {
                "name",
                "components",
                "eligibilityRule",
                "cohort",
                "ratingScale",
                "rerankComposite",
            },
            {"percentileOutput"},
            path,
        )
        name = _name(definition["name"], f"{path}.name")
        if name in _RESERVED_ATTRIBUTE_NAMES:
            raise FormulaContractError(
                f"{path}.name collides with reserved output field {name!r}."
            )
        if name in names:
            raise FormulaContractError(f"attributes contains duplicate attribute {name!r}.")
        names.add(name)
        raw_components = _list(definition["components"], f"{path}.components")
        if not raw_components:
            raise FormulaContractError(f"{path}.components must not be empty.")
        parsed_components: list[tuple[str, float, str]] = []
        component_metrics: set[str] = set()
        for component_index, raw_component in enumerate(raw_components):
            component_path = f"{path}.components[{component_index}]"
            component = _mapping(raw_component, component_path)
            _keys(component, {"metric", "weight", "direction"}, set(), component_path)
            metric = _name(component["metric"], f"{component_path}.metric")
            if metric not in metrics:
                raise FormulaContractError(
                    f"{component_path} references unknown metric {metric!r}."
                )
            if metric in component_metrics:
                raise FormulaContractError(f"{path} contains duplicate component {metric!r}.")
            component_metrics.add(metric)
            weight = _number(component["weight"], f"{component_path}.weight", nonnegative=True)
            direction = component["direction"]
            if direction not in {"higher", "lower"}:
                raise FormulaContractError(
                    f"{component_path}.direction must be 'higher' or 'lower'."
                )
            parsed_components.append((metric, weight, direction))
        maximum_weight = max(weight for _, weight, _ in parsed_components)
        if maximum_weight <= 0:
            raise FormulaContractError(f"{path} component weights must have a positive sum.")
        scaled_weights = [weight / maximum_weight for _, weight, _ in parsed_components]
        scaled_total = sum(scaled_weights)
        components = tuple(
            FormulaComponent(metric, weight, direction, scaled_weight / scaled_total)
            for (metric, weight, direction), scaled_weight in zip(
                parsed_components, scaled_weights, strict=True
            )
        )
        eligibility_rule = _name(definition["eligibilityRule"], f"{path}.eligibilityRule")
        cohort = _name(definition["cohort"], f"{path}.cohort")
        rating_scale = _name(definition["ratingScale"], f"{path}.ratingScale")
        if eligibility_rule not in eligibility:
            raise FormulaContractError(f"{path} references unknown eligibility rule.")
        if cohort not in cohorts:
            raise FormulaContractError(f"{path} references unknown cohort.")
        if rating_scale not in scales:
            raise FormulaContractError(f"{path} references unknown rating scale.")
        rerank_composite = definition["rerankComposite"]
        if not isinstance(rerank_composite, bool):
            raise FormulaContractError(f"{path}.rerankComposite must be a boolean.")
        percentile_output = definition.get("percentileOutput")
        if percentile_output is not None:
            percentile_output = _name(percentile_output, f"{path}.percentileOutput")
            if percentile_output in _RESERVED_PERCENTILE_OUTPUTS:
                raise FormulaContractError(
                    f"{path}.percentileOutput collides with reserved output field "
                    f"{percentile_output!r}."
                )
        attributes.append(
            AttributeFormula(
                name,
                components,
                eligibility_rule,
                cohort,
                rating_scale,
                rerank_composite,
                percentile_output,
            )
        )
    return tuple(attributes)


def _parse_tiers(
    raw: Any,
    attributes: tuple[AttributeFormula, ...],
    scales: Mapping[str, RatingScale],
) -> tuple[TalentTier, ...]:
    values = _list(raw, "talentTiers")
    if not values:
        raise FormulaContractError("talentTiers must not be empty.")
    tiers: list[TalentTier] = []
    names: set[str] = set()
    for index, raw_definition in enumerate(values):
        path = f"talentTiers[{index}]"
        definition = _mapping(raw_definition, path)
        _keys(definition, {"name", "minimum", "maximum"}, set(), path)
        name = _name(definition["name"], f"{path}.name")
        if name in names:
            raise FormulaContractError(f"talentTiers contains duplicate tier {name!r}.")
        names.add(name)
        minimum = _integer(definition["minimum"], f"{path}.minimum")
        maximum = _integer(definition["maximum"], f"{path}.maximum")
        if not 25 <= minimum <= maximum <= 99:
            raise FormulaContractError(f"{path} must define an ordered range within 25-99.")
        tiers.append(TalentTier(name, minimum, maximum))
    ordered = sorted(tiers, key=lambda tier: tier.minimum)
    if any(
        left.maximum >= right.minimum
        for left, right in zip(ordered, ordered[1:], strict=False)
    ):
        raise FormulaContractError("talentTiers ranges must not overlap.")
    overall = next((attribute for attribute in attributes if attribute.name == "overall"), None)
    if overall is not None:
        anchors = scales[overall.rating_scale].anchors
        expected = range(round(anchors[0].rating), round(anchors[-1].rating) + 1)
        for rating in expected:
            matches = sum(tier.minimum <= rating <= tier.maximum for tier in tiers)
            if matches != 1:
                raise FormulaContractError(
                    "talentTiers must cover every rating produced by the overall scale."
                )
    return tuple(tiers)


def parse_formula_document(document: Mapping[str, Any]) -> FormulaDocument:
    """Parse and validate a declarative formula document using schema version 1."""

    root = _mapping(document, "formula document")
    _keys(root, _TOP_LEVEL_KEYS, set(), "formula document")
    schema_version = _integer(root["schemaVersion"], "schemaVersion")
    if schema_version != 1:
        raise FormulaContractError(
            f"Unsupported formula schema version {schema_version}; supported version is 1."
        )
    formula_version = _text(root["formulaVersion"], "formulaVersion")
    reference_contract_version = _integer(
        root["referenceContractVersion"], "referenceContractVersion", minimum=1
    )
    if reference_contract_version != REFERENCE_CONTRACT_VERSION:
        raise FormulaContractError(
            "Unsupported reference contract version "
            f"{reference_contract_version}; supported version is {REFERENCE_CONTRACT_VERSION}."
        )
    output_fields = _unique_names(_list(root["outputFields"], "outputFields"), "outputFields")
    if not output_fields:
        raise FormulaContractError("outputFields must not be empty.")
    rules = _parse_rules(root["rules"])
    metrics = _parse_metrics(root["metrics"])
    _validate_reference_metric_fields(metrics)
    cohorts = _parse_cohorts(root["cohorts"], metrics)
    eligibility = _parse_eligibility(root["eligibilityRules"], metrics)
    scales = _parse_scales(root["ratingScales"])
    attributes = _parse_attributes(root["attributes"], metrics, eligibility, cohorts, scales)
    tiers = _parse_tiers(root["talentTiers"], attributes, scales)

    overall = next((attribute for attribute in attributes if attribute.name == "overall"), None)
    if overall is None:
        raise FormulaContractError("attributes must define an overall formula.")
    if overall.percentile_output != "impactPercentile":
        raise FormulaContractError(
            "The overall formula must declare percentileOutput 'impactPercentile'."
        )
    percentile_outputs = tuple(
        attribute.percentile_output
        for attribute in attributes
        if attribute.percentile_output is not None
    )
    if len(percentile_outputs) != len(set(percentile_outputs)):
        raise FormulaContractError("attributes contain duplicate percentile outputs.")
    collisions = set(percentile_outputs) & {attribute.name for attribute in attributes}
    if collisions:
        raise FormulaContractError(
            "attribute percentile outputs collide with attribute names: "
            f"{', '.join(sorted(collisions))}."
        )
    expected_output_fields = (
        "playerId",
        *(attribute.name for attribute in attributes),
        *percentile_outputs,
        "talentTier",
        "formulaVersion",
    )
    if output_fields != expected_output_fields:
        raise FormulaContractError(
            "outputFields must exactly match the ordered formula outputs: "
            f"{', '.join(expected_output_fields)}."
        )
    return FormulaDocument(
        schema_version,
        formula_version,
        reference_contract_version,
        output_fields,
        rules,
        metrics,
        cohorts,
        eligibility,
        scales,
        attributes,
        tiers,
    )
