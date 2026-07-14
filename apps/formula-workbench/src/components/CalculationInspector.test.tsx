import { describe, expect, it } from "vitest";

import { makeCalculation } from "../test/fixtures";
import {
  buildCalculationComponentRows,
  buildCalculationRawMetricRows,
} from "./CalculationInspector";

function overallCalculation() {
  return makeCalculation("player-test").attributes.overall;
}

describe("CalculationInspector row builders", () => {
  it("falls back to baseline values when no preview calculation exists", () => {
    const baseline = overallCalculation();

    const raw = buildCalculationRawMetricRows(baseline, null).find(
      ({ metric }) => metric === "pointsPerGame",
    );
    const component = buildCalculationComponentRows(baseline, null).find(
      ({ metric }) => metric === "pointsPerGame",
    );

    expect(raw).toMatchObject({
      baseline: 27.5,
      preview: 27.5,
      state: "available",
    });
    expect(component).toMatchObject({
      baselinePercentile: 0.9,
      previewPercentile: 0.9,
      baselineWeight: 0.6,
      previewWeight: 0.6,
      baselineContribution: 0.54,
      previewContribution: 0.54,
      state: "available",
    });
  });

  it("preserves explicit preview nulls and marks their rows missing", () => {
    const baseline = overallCalculation();
    const preview = structuredClone(baseline);
    preview.rawInputs.pointsPerGame = null;
    preview.componentPercentiles.pointsPerGame = null;
    preview.contributions.pointsPerGame = null;

    const raw = buildCalculationRawMetricRows(baseline, preview).find(
      ({ metric }) => metric === "pointsPerGame",
    );
    const component = buildCalculationComponentRows(baseline, preview).find(
      ({ metric }) => metric === "pointsPerGame",
    );

    expect(raw).toMatchObject({ preview: null, state: "missing" });
    expect(component).toMatchObject({
      previewPercentile: null,
      previewContribution: null,
      state: "missing",
    });
  });

  it("treats a missing preview value for a baseline-supported component as missing", () => {
    const baseline = overallCalculation();
    const preview = structuredClone(baseline);
    delete preview.contributions.pointsPerGame;

    const component = buildCalculationComponentRows(baseline, preview).find(
      ({ metric }) => metric === "pointsPerGame",
    );

    expect(component).toMatchObject({
      baselineContribution: 0.54,
      previewContribution: undefined,
      state: "missing",
    });
    expect(component?.state).not.toBe("unsupported");
  });
});
