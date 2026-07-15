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

  it("highlights authoritative preview increases and decreases with visible direction cues", () => {
    const baseline = overallCalculation();
    const preview = makeCalculation("player-test", { adjusted: true }).attributes.overall;
    const { container } = render(
      <CalculationInspector
        player={{ playerId: "player-test", displayName: "Test Player", season: 2026 }}
        attributeName="overall"
        baseline={baseline}
        preview={preview}
      />,
    );

    const scoreboard = container.querySelector(".calculation-scoreboard");
    expect(scoreboard?.querySelectorAll(".preview-impact--increase")).toHaveLength(3);
    expect(scoreboard?.textContent).toContain("Preview 92");
    expect(scoreboard?.textContent).toContain("▲ +2 increase");
    expect(
      within(scoreboard as HTMLElement).getByText(
        "Preview 92. Increased by 2 from baseline 90.",
      ),
    ).toBeTruthy();
    expect(screen.getByRole("status").textContent).toContain(
      "Authoritative preview updated. Rating increased to 92.",
    );

    const componentTable = screen.getByRole("region", {
      name: "Component calculation breakdown",
    });
    expect(componentTable.querySelectorAll(".preview-value--increase")).toHaveLength(1);
    expect(componentTable.querySelectorAll(".preview-value--decrease")).toHaveLength(1);
    expect(componentTable.querySelectorAll(".preview-value--allocation-change")).toHaveLength(2);
    expect(componentTable.querySelectorAll(".preview-value--unchanged")).toHaveLength(2);
    expect(componentTable.textContent).toContain("▲ +10% increase");
    expect(componentTable.textContent).toContain("▼ -10% decrease");
  });

  it("keeps zero and very small deltas consistent with their direction cues", () => {
    const baseline = overallCalculation();
    const preview = structuredClone(baseline);
    preview.compositePercentile = baseline.compositePercentile! + 0.000001;
    preview.composite = baseline.composite! + 0.000001;

    const { container } = render(
      <CalculationInspector
        player={{ playerId: "player-test", displayName: "Test Player", season: 2026 }}
        attributeName="overall"
        baseline={baseline}
        preview={preview}
      />,
    );

    const scoreboard = container.querySelector(".calculation-scoreboard");
    expect(scoreboard?.querySelector(".preview-impact--unchanged")?.textContent).toContain(
      "= 0 no change",
    );
    expect(scoreboard?.textContent).not.toContain("= +0 no change");
    expect(scoreboard?.textContent).toContain("▲ +<0.001% increase");
    expect(scoreboard?.textContent).toContain("▲ +<0.0001 increase");
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
