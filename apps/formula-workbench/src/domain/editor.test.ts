import { describe, expect, it } from "vitest";

import type { FormulaDocument } from "../api/types";
import {
  buildPreviewAdjustments,
  createFormulaEditorState,
  dirtyAttributeNames,
  dirtyRatingScaleNames,
  normalizedComponentWeights,
  rebalanceComponentWeight,
  resetAll,
  resetAttribute,
  setComponentDirection,
  setComponentWeight,
  setProposalVersion,
  setRatingScaleAnchors,
  validateFormulaEditorState,
} from "./editor";

function formula(): FormulaDocument {
  return {
    schemaVersion: 1,
    formulaVersion: "1.0.0",
    referenceContractVersion: 2,
    outputFields: ["playerId", "overall", "formulaVersion"],
    rules: {
      nullHandling: "exclude",
      tieMethod: "average",
      percentileMethod: "rankPct",
      ratingRounding: "halfEven",
    },
    metrics: {
      impact: { kind: "input", field: "impact" },
      scoring: { kind: "input", field: "scoring" },
    },
    cohorts: { season: { groupBy: ["season"] } },
    eligibilityRules: {
      standard: { requiredMetrics: ["impact"], minimumSamples: { games: 20 } },
    },
    ratingScales: {
      overall: {
        minimum: 25,
        maximum: 99,
        anchors: [
          { percentile: 0, rating: 50 },
          { percentile: 0.5, rating: 70 },
          { percentile: 1, rating: 99 },
        ],
      },
    },
    attributes: [
      {
        name: "overall",
        components: [
          { metric: "impact", weight: 0.6, direction: "higher" },
          { metric: "scoring", weight: 0.4, direction: "higher" },
        ],
        eligibilityRule: "standard",
        cohort: "season",
        ratingScale: "overall",
        rerankComposite: true,
      },
    ],
    talentTiers: [{ name: "starter", minimum: 76, maximum: 83 }],
  };
}

function formulaWithWeights(weights: readonly number[]): FormulaDocument {
  const document = formula();
  const metrics = Object.fromEntries(
    weights.map((_, index) => [
      `metric${index + 1}`,
      { kind: "input" as const, field: `metric${index + 1}` },
    ]),
  );
  document.metrics = metrics;
  document.attributes[0]!.components = weights.map((weight, index) => ({
    metric: `metric${index + 1}`,
    weight,
    direction: "higher",
  }));
  return document;
}

function componentWeights(state: ReturnType<typeof createFormulaEditorState>): number[] {
  return state.attributes[0]!.components.map(({ weight }) => weight);
}

describe("formula editor domain", () => {
  it("creates an independent session copy and requires a proposal version", () => {
    const document = formula();
    const state = createFormulaEditorState(document);
    state.ratingScales[0]?.anchors.splice(1, 1);

    expect(document.ratingScales.overall?.anchors).toHaveLength(3);
    expect(validateFormulaEditorState(createFormulaEditorState(document))).toContainEqual(
      expect.objectContaining({ code: "empty_version" }),
    );
    expect(
      validateFormulaEditorState(createFormulaEditorState(document, "1.1.0-proposal")),
    ).toEqual([]);
  });

  it("validates finite nonnegative weights and an exact edited attribute total", () => {
    let state = createFormulaEditorState(formula(), "1.1.0");
    state = setComponentWeight(state, "overall", "impact", -0.1);

    expect(validateFormulaEditorState(state)).toContainEqual(
      expect.objectContaining({ code: "invalid_weight", path: expect.stringContaining("impact") }),
    );

    state = setComponentWeight(state, "overall", "impact", 0);
    state = setComponentWeight(state, "overall", "scoring", 0);
    expect(validateFormulaEditorState(state)).toContainEqual(
      expect.objectContaining({
        code: "invalid_weight_sum",
        path: "attributes.overall.components",
      }),
    );

    state = setComponentWeight(state, "overall", "impact", Number.NaN);
    expect(validateFormulaEditorState(state)).toContainEqual(
      expect.objectContaining({ code: "invalid_weight" }),
    );

    const aboveTotal = setComponentWeight(
      createFormulaEditorState(formula(), "1.1.0"),
      "overall",
      "impact",
      0.7,
    );
    expect(validateFormulaEditorState(aboveTotal)).toContainEqual({
      path: "attributes.overall.components",
      code: "invalid_weight_sum",
      message: "Edited component weights must total 1.",
    });

    const withinTolerance = setComponentWeight(
      createFormulaEditorState(formula(), "1.1.0"),
      "overall",
      "impact",
      0.6000000001,
    );
    expect(validateFormulaEditorState(withinTolerance)).toEqual([]);
  });

  it("accepts positive-sum source weights and exposes their normalized authoring shares", () => {
    const state = createFormulaEditorState(formulaWithWeights([2, 1]), "1.1.0");

    expect(validateFormulaEditorState(state)).toEqual([]);
    expect(normalizedComponentWeights(componentWeights(state))).toEqual([
      2 / 3,
      1 / 3,
    ]);

    const adjusted = rebalanceComponentWeight(state, "overall", "metric1", 0.7);
    expect(componentWeights(adjusted)).toEqual([0.7, 0.3]);
    expect(validateFormulaEditorState(adjusted)).toEqual([]);
  });

  it("rebalances peers proportionally in exact one-percent units", () => {
    const state = rebalanceComponentWeight(
      createFormulaEditorState(
        formulaWithWeights([0.35, 0.2, 0.15, 0.12, 0.1, 0.08]),
        "1.1.0",
      ),
      "overall",
      "metric1",
      0.5,
    );

    expect(componentWeights(state)).toEqual([0.5, 0.15, 0.12, 0.09, 0.08, 0.06]);
    expect(componentWeights(state).reduce((total, weight) => total + weight, 0)).toBeCloseTo(1);
    expect(validateFormulaEditorState(state)).toEqual([]);
  });

  it("uses document order to resolve equal largest remainders", () => {
    const state = rebalanceComponentWeight(
      createFormulaEditorState(formulaWithWeights([0.5, 0.25, 0.25]), "1.1.0"),
      "overall",
      "metric1",
      0.99,
    );

    expect(componentWeights(state)).toEqual([0.99, 0.01, 0]);
  });

  it("rebalances large finite peer weights without overflowing", () => {
    const state = rebalanceComponentWeight(
      createFormulaEditorState(
        formulaWithWeights([0, Number.MAX_VALUE, Number.MAX_VALUE]),
        "1.1.0",
      ),
      "overall",
      "metric1",
      0.5,
    );

    expect(componentWeights(state)).toEqual([0.5, 0.25, 0.25]);
  });

  it("restores zeroed peers from baseline proportions and clamps slider overflow", () => {
    let state = createFormulaEditorState(formulaWithWeights([0.6, 0.3, 0.1]), "1.1.0");
    state = rebalanceComponentWeight(state, "overall", "metric1", 2);
    expect(componentWeights(state)).toEqual([1, 0, 0]);

    state = rebalanceComponentWeight(state, "overall", "metric1", 0.5);
    expect(componentWeights(state)).toEqual([0.5, 0.38, 0.12]);

    state = rebalanceComponentWeight(state, "overall", "metric1", -1);
    expect(componentWeights(state)).toEqual([0, 0.76, 0.24]);
  });

  it("falls back to equal peer shares and fixes singleton attributes at 100 percent", () => {
    const zeroPeerBaseline = createFormulaEditorState(
      formulaWithWeights([1, 0, 0]),
      "1.1.0",
    );
    expect(
      componentWeights(
        rebalanceComponentWeight(zeroPeerBaseline, "overall", "metric1", 0.5),
      ),
    ).toEqual([0.5, 0.25, 0.25]);

    const singleton = rebalanceComponentWeight(
      createFormulaEditorState(formulaWithWeights([1]), "1.1.0"),
      "overall",
      "metric1",
      0.2,
    );
    expect(componentWeights(singleton)).toEqual([1]);
    expect(validateFormulaEditorState(singleton)).toEqual([]);
  });

  it("rejects nonfinite rebalance values", () => {
    const state = createFormulaEditorState(formula(), "1.1.0");

    expect(() =>
      rebalanceComponentWeight(state, "overall", "impact", Number.NaN),
    ).toThrow("finite number");
  });

  it("requires complete ordered anchors with contract rating bounds", () => {
    let state = createFormulaEditorState(formula(), "1.1.0");
    state = setRatingScaleAnchors(state, "overall", [
      { percentile: 0.1, rating: 50 },
      { percentile: 0.8, rating: 100 },
      { percentile: 0.7, rating: 80 },
    ]);

    expect(validateFormulaEditorState(state)).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ code: "invalid_anchors", message: expect.stringContaining("0") }),
        expect.objectContaining({ code: "invalid_anchors", message: expect.stringContaining("1") }),
        expect.objectContaining({ code: "invalid_rating" }),
        expect.objectContaining({
          code: "invalid_anchors",
          message: expect.stringContaining("strictly increasing"),
        }),
        expect.objectContaining({
          code: "invalid_anchors",
          message: expect.stringContaining("nondecreasing"),
        }),
      ]),
    );
  });

  it("builds only changed component and complete scale adjustments", () => {
    let state = createFormulaEditorState(formula(), "1.1.0");
    state = rebalanceComponentWeight(state, "overall", "impact", 0.75);
    state = setComponentDirection(state, "overall", "scoring", "lower");
    state = setRatingScaleAnchors(state, "overall", [
      { percentile: 0, rating: 45 },
      { percentile: 1, rating: 98 },
    ]);

    expect(dirtyAttributeNames(state)).toEqual(["overall"]);
    expect(dirtyRatingScaleNames(state)).toEqual(["overall"]);
    expect(buildPreviewAdjustments(state)).toEqual({
      formulaVersion: "1.1.0",
      components: [
        { attribute: "overall", metric: "impact", weight: 0.75 },
        {
          attribute: "overall",
          metric: "scoring",
          weight: 0.25,
          inverseDirection: true,
        },
      ],
      ratingScales: [
        {
          scale: "overall",
          anchors: [
            { percentile: 0, rating: 45 },
            { percentile: 1, rating: 98 },
          ],
        },
      ],
    });
  });

  it("resets one attribute without resetting its shared scale and resets the whole session", () => {
    let state = createFormulaEditorState(formula(), "initial-proposal");
    state = setProposalVersion(state, "changed-proposal");
    state = rebalanceComponentWeight(state, "overall", "impact", 0.8);
    state = setRatingScaleAnchors(state, "overall", [
      { percentile: 0, rating: 40 },
      { percentile: 1, rating: 95 },
    ]);

    const attributeReset = resetAttribute(state, "overall");
    expect(dirtyAttributeNames(attributeReset)).toEqual([]);
    expect(dirtyRatingScaleNames(attributeReset)).toEqual(["overall"]);
    expect(attributeReset.proposalVersion).toBe("changed-proposal");

    const reset = resetAll(state);
    expect(reset.proposalVersion).toBe("initial-proposal");
    expect(dirtyAttributeNames(reset)).toEqual([]);
    expect(dirtyRatingScaleNames(reset)).toEqual([]);
    expect(buildPreviewAdjustments(reset)).toEqual({
      formulaVersion: "initial-proposal",
      components: [],
      ratingScales: [],
    });
  });

  it("rejects unknown attribute, component, and scale targets", () => {
    const state = createFormulaEditorState(formula(), "1.1.0");

    expect(() => setComponentWeight(state, "missing", "impact", 1)).toThrow(
      "Unknown formula attribute",
    );
    expect(() => setComponentWeight(state, "overall", "missing", 1)).toThrow(
      "is not a component",
    );
    expect(() => rebalanceComponentWeight(state, "missing", "impact", 1)).toThrow(
      "Unknown formula attribute",
    );
    expect(() => rebalanceComponentWeight(state, "overall", "missing", 1)).toThrow(
      "is not a component",
    );
    expect(() => setRatingScaleAnchors(state, "missing", [])).toThrow(
      "Unknown formula rating scale",
    );
  });
});
