import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { FORMULA_DOCUMENT, METRICS } from "../test/fixtures";
import { GlossaryPage } from "./GlossaryPage";
import { SectionHelp } from "./SectionHelp";

afterEach(cleanup);

describe("SectionHelp", () => {
  it("provides a collapsed native disclosure with configurable copy", () => {
    render(
      <SectionHelp title="About formula weights">
        Formula weights describe the complete allocation.
      </SectionHelp>,
    );

    const summary = screen.getByText("About formula weights");
    const disclosure = summary.closest("details");
    expect(disclosure?.open).toBe(false);

    fireEvent.click(summary);
    expect(disclosure?.open).toBe(true);
    expect(screen.getByText("Formula weights describe the complete allocation.")).toBeTruthy();
  });
});

describe("GlossaryPage", () => {
  it("renders categorized definitions and navigation landmarks", () => {
    render(<GlossaryPage formula={FORMULA_DOCUMENT} metrics={METRICS} />);

    expect(screen.getByRole("main").getAttribute("aria-labelledby")).toBe("glossary-title");
    expect(screen.getByRole("heading", { name: "Glossary", level: 1 })).toBeTruthy();
    expect(screen.getByRole("navigation", { name: "Glossary sections" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Formula design" }).getAttribute("href")).toBe(
      "#glossary-formula-design",
    );
    expect(screen.getByText("Authoritative", { selector: "dfn" })).toBeTruthy();
    expect(screen.getByText("Fixed cohort", { selector: "dfn" })).toBeTruthy();
    expect(screen.getByText("Stale context", { selector: "dfn" })).toBeTruthy();
  });

  it("derives the loaded attribute and metric catalog from API data", () => {
    render(<GlossaryPage formula={FORMULA_DOCUMENT} metrics={METRICS} />);

    const catalog = screen
      .getByRole("heading", { name: "Loaded model catalog", level: 2 })
      .closest("section");
    expect(catalog).not.toBeNull();
    const view = within(catalog!);

    expect(view.getByText("attributes-2026.1")).toBeTruthy();
    expect(view.getByRole("heading", { name: "Overall", level: 4 })).toBeTruthy();
    expect(view.getByRole("heading", { name: "Shooting", level: 4 })).toBeTruthy();
    expect(view.getAllByText("Points scored per game").length).toBeGreaterThan(0);
    expect(view.getAllByText("Scoring production per appearance.").length).toBeGreaterThan(0);
    expect(view.getByText(/60% · Higher is better/)).toBeTruthy();
    expect(view.getByText(/Used by: Overall \(60%, higher\); Shooting \(100%, higher\)/)).toBeTruthy();
    expect(view.getByText("All Star")).toBeTruthy();
    expect(view.getByText("80–89")).toBeTruthy();
  });

  it("presents positive source weights as normalized component shares", () => {
    const formula = structuredClone(FORMULA_DOCUMENT);
    formula.attributes[0]!.components[0]!.weight = 2;
    formula.attributes[0]!.components[1]!.weight = 1;

    render(<GlossaryPage formula={formula} metrics={METRICS} />);

    const overall = screen
      .getByRole("heading", { name: "Overall", level: 4 })
      .closest("article");
    expect(overall).not.toBeNull();
    expect(within(overall!).getByText(/66\.7% · Higher is better/)).toBeTruthy();
    expect(within(overall!).getByText(/33\.3% · Higher is better/)).toBeTruthy();
    expect(screen.getByText(/Used by: Overall \(66\.7%, higher\)/)).toBeTruthy();
  });

  it("explains when the formula or metric catalog is unavailable", () => {
    render(<GlossaryPage formula={null} metrics={[]} />);

    expect(
      screen.getByText(/Load the workbench to see the active attributes/),
    ).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Attributes", level: 3 })).toBeNull();
  });
});
