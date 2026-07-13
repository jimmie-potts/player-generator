"""Shared declarative player-attribute contracts and calculations."""

from player_attribute_engine.contract import (
    AttributeFormula,
    EligibilityRule,
    FormulaComponent,
    FormulaContractError,
    FormulaDocument,
    MetricDefinition,
    PercentileAnchor,
    PercentileCohort,
    RatingScale,
    TalentTier,
    parse_formula_document,
)
from player_attribute_engine.evaluator import (
    EvaluationBatch,
    EvaluationError,
    evaluate_player_attributes,
)
from player_attribute_engine.formula import (
    ACTIVE_FORMULA_VERSION,
    FORMULA_SCHEMA_VERSION,
    load_formula,
)
from player_attribute_engine.ratings import (
    assign_talent_tier,
    rate_player_seasons,
)

__all__ = [
    "ACTIVE_FORMULA_VERSION",
    "FORMULA_SCHEMA_VERSION",
    "AttributeFormula",
    "EligibilityRule",
    "EvaluationBatch",
    "EvaluationError",
    "FormulaComponent",
    "FormulaContractError",
    "FormulaDocument",
    "MetricDefinition",
    "PercentileAnchor",
    "PercentileCohort",
    "RatingScale",
    "TalentTier",
    "assign_talent_tier",
    "evaluate_player_attributes",
    "load_formula",
    "parse_formula_document",
    "rate_player_seasons",
]

__version__ = "0.2.0"
