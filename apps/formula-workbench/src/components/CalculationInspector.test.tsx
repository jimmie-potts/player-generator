import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { makeCalculation } from "../test/fixtures";
import {
  CalculationInspector,
  buildCalculationComponentRows,
  buildCalculationRawMetricRows,
} from "./CalculationInspector";

afterEach(cleanup);

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

  it("explains an excluded calculation with its authoritative reason", () => {
    const baseline = overallCalculation();
    baseline.eligible = false;
    baseline.ineligibilityReasons = [
      { kind: "minimumSample", metric: "gamesPlayed", minimum: 10, actual: 4 },
    ];

    render(
      <CalculationInspector
        player={{ playerId: "player-test", displayName: "Test Player", season: 2026 }}
        attributeName="overall"
        baseline={baseline}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Excluded from this attribute cohort" }),
    ).toBeTruthy();
    expect(screen.getByText("Games Played: 4 observed; 10 required.")).toBeTruthy();
    expect(screen.getByText("Excluded", { selector: ".eligibility-badge" })).toBeTruthy();
  });

  it("keeps the result summary separate from native collapsible calculation details", () => {
    const { container } = render(
      <CalculationInspector
        player={{ playerId: "player-test", displayName: "Test Player", season: 2026 }}
        attributeName="overall"
        baseline={overallCalculation()}
      />,
    );

    const summary = container.querySelector(".calculation-inspector__summary");
    const inspector = screen.getByRole("region", {
      name: "Overall authoritative explanation for Test Player",
    });
    expect(inspector.getAttribute("tabindex")).toBe("0");
    expect(summary).toBeTruthy();
    expect(summary?.querySelector('[aria-label="Calculation summary"]')).toBeTruthy();
    expect(summary?.textContent).toContain("How to read this authoritative explanation");

    const rawHeading = screen.getByRole("heading", { name: "Raw metrics", level: 3 });
    const rawDetails = rawHeading.closest("details") as HTMLDetailsElement | null;
    expect(rawDetails?.open).toBe(true);
    expect(rawDetails?.querySelector("summary")).toBeTruthy();
    expect(rawDetails?.textContent).toContain("How to read raw metrics");

    const componentHeading = screen.getByRole("heading", {
      name: "Component breakdown",
      level: 3,
    });
    const componentDetails = componentHeading.closest("details") as HTMLDetailsElement | null;
    expect(componentDetails?.open).toBe(true);
    expect(componentDetails?.querySelector("summary")).toBeTruthy();
    expect(componentDetails?.textContent).toContain("How to read the component breakdown");

    fireEvent.click(rawDetails!.querySelector("summary")!);
    expect(rawDetails?.open).toBe(false);
  });

  it("keeps baseline stats visible while authoritative preview values are pending", () => {
    const { container } = render(
      <CalculationInspector
        player={{ playerId: "player-test", displayName: "Test Player", season: 2026 }}
        attributeName="overall"
        baseline={overallCalculation()}
        pending
      />,
    );

    const inspector = container.querySelector(".calculation-inspector");
    expect(inspector?.getAttribute("aria-busy")).toBe("true");
    expect(screen.getByRole("heading", { name: "Test Player" })).toBeTruthy();
    expect(screen.getByText(/Baseline stats remain visible/)).toBeTruthy();
    expect(screen.getByText("90", { selector: ".calculation-scoreboard strong" })).toBeTruthy();
    expect(screen.getAllByText("Preview updating…")).toHaveLength(3);

    const rawTable = screen.getByRole("region", { name: "Raw metric values" });
    expect(within(rawTable).getAllByText("Updating…").length).toBeGreaterThan(0);
    const componentTable = screen.getByRole("region", {
      name: "Component calculation breakdown",
    });
    expect(within(componentTable).getAllByText("Updating…").length).toBeGreaterThan(0);
    expect(screen.queryByRole("heading", { name: "Loading calculation" })).toBeNull();
  });

  it("renders an explicit unsupported status without calculation tables", () => {
    render(
      <CalculationInspector
        player={{ playerId: "player-test", displayName: "Test Player", season: 2026 }}
        attributeName="futureAttribute"
        baseline={null}
        status="unsupported"
        statusMessage="The API does not support this attribute for the loaded formula."
      />,
    );

    expect(screen.getByRole("heading", { name: "Attribute unsupported" })).toBeTruthy();
    expect(
      screen.getByText("The API does not support this attribute for the loaded formula."),
    ).toBeTruthy();
    expect(
      screen.queryByRole("region", { name: "Component calculation breakdown" }),
    ).toBeNull();
  });
});
