import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  PlayerComparison,
  type ComparisonMeasure,
  type PlayerComparisonGroup,
  type PlayerComparisonRow,
} from "./PlayerComparison";

afterEach(cleanup);

const MEASURE: ComparisonMeasure = {
  baseline: 85,
  preview: 87,
  delta: 2,
  baselineRank: 12,
  previewRank: 9,
  rankMovement: 3,
};

function row(overrides: Partial<PlayerComparisonRow> = {}): PlayerComparisonRow {
  return {
    playerId: "player-1",
    displayName: "Example Player",
    tier: "all_star",
    removable: false,
    state: "changed",
    attribute: MEASURE,
    overall: MEASURE,
    ...overrides,
  };
}

function renderComparison(
  groups: readonly PlayerComparisonGroup[],
  overrides: Partial<React.ComponentProps<typeof PlayerComparison>> = {},
) {
  const onRemove = vi.fn();
  render(
    <PlayerComparison
      selectedAttributeLabel="Overall"
      groups={groups}
      onSelect={vi.fn()}
      onRemove={onRemove}
      {...overrides}
    />,
  );
  return onRemove;
}

describe("PlayerComparison", () => {
  it("uses a bounded region and neutral count for the top-25 group", () => {
    renderComparison([
      { id: "top-25", label: "Top 25 by baseline overall", kind: "top25", rows: [row()] },
    ]);

    expect(screen.getByText("1 baseline-ranked player")).toBeTruthy();
    expect(
      screen
        .getByRole("region", { name: "Top 25 by baseline overall player comparison" })
        .classList.contains("comparison-table-wrap--bounded"),
    ).toBe(true);
  });

  it("removes only rows marked removable from a custom list", () => {
    const onRemove = renderComparison([
      {
        id: "custom-list",
        label: "Custom list",
        kind: "custom",
        rows: [row({ removable: true })],
      },
    ]);

    expect(screen.getByText("1 custom player")).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: "Remove Example Player from custom list" }),
    );
    expect(onRemove).toHaveBeenCalledWith("player-1");
  });

  it("accepts custom empty-state copy", () => {
    renderComparison([], {
      emptyTitle: "Your custom list is empty",
      emptyMessage: "Search for up to 25 players to compare.",
    });

    expect(screen.getByRole("heading", { name: "Your custom list is empty" })).toBeTruthy();
    expect(screen.getByText("Search for up to 25 players to compare.")).toBeTruthy();
  });
});
