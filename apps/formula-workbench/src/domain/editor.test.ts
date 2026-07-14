import { describe, expect, it } from "vitest";

import type { FormulaDocument } from "../api/types";
import {
  buildPreviewAdjustments,
  createFormulaEditorState,
  dirtyAttributeNames,
  dirtyRatingScaleNames,
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

  it("validates finite nonnegative weights and a positive attribute sum", () => {
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
    state = setComponentWeight(state, "overall", "impact", 0.75);
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
    state = setComponentWeight(state, "overall", "impact", 0.8);
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
    expect(() => setRatingScaleAnchors(state, "missing", [])).toThrow(
      "Unknown formula rating scale",
    );
  });
});
