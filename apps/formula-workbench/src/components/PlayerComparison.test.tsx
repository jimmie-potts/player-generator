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

  it("uses readable tiers and separated accessible names for player selection", () => {
    renderComparison([
      {
        id: "tiers",
        label: "Tier sample",
        kind: "tier",
        rows: [
          row(),
          row({
            playerId: "player-2",
            displayName: "Untiered Player",
            tier: null,
          }),
        ],
      },
    ]);

    expect(screen.getByRole("button", { name: "Example Player, All Star" })).toBeTruthy();
    expect(screen.getByText("All Star")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Untiered Player, No tier" })).toBeTruthy();
    expect(screen.getByText("No tier")).toBeTruthy();
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

  it("offers an explicit retry action for a recoverable comparison error", () => {
    const onRetry = vi.fn();
    renderComparison([], {
      error: "The Top 25 could not be loaded.",
      retryLabel: "Retry Top 25",
      onRetry,
    });

    fireEvent.click(screen.getByRole("button", { name: "Retry Top 25" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("highlights every rating and rank impact with color-independent direction cues", () => {
    const negativeMeasure: ComparisonMeasure = {
      baseline: 87,
      preview: 85,
      delta: -2,
      baselineRank: 9,
      previewRank: 12,
      rankMovement: -3,
    };
    const { container } = render(
      <PlayerComparison
        selectedAttributeLabel="Overall"
        groups={[
          {
            id: "tiers",
            label: "Tier sample",
            kind: "tier",
            rows: [row({ attribute: MEASURE, overall: negativeMeasure })],
          },
        ]}
        onSelect={vi.fn()}
        onRemove={vi.fn()}
      />,
    );

    expect(container.querySelectorAll(".delta-value .impact-value--positive")).toHaveLength(1);
    expect(container.querySelectorAll(".delta-value .impact-value--negative")).toHaveLength(1);
    expect(container.querySelector(".delta-value .impact-value--positive")?.textContent).toContain(
      "▲ +2",
    );
    expect(container.querySelector(".delta-value .impact-value--negative")?.textContent).toContain(
      "▼ -2",
    );
    expect(screen.getByText("Rating increased by 2.")).toBeTruthy();
    expect(screen.getByText("Rating decreased by 2.")).toBeTruthy();

    const positiveRank = screen.getByLabelText(
      "Rank 12 to 9. Moved 3 places toward rank one.",
    );
    const negativeRank = screen.getByLabelText(
      "Rank 9 to 12. Moved 3 places away from rank one.",
    );
    expect(positiveRank.classList.contains("impact-value--positive")).toBe(true);
    expect(negativeRank.classList.contains("impact-value--negative")).toBe(true);
  });

  it("shows a neutral unsigned zero when a rating does not change", () => {
    const unchanged: ComparisonMeasure = {
      baseline: 85,
      preview: 85,
      delta: 0,
      baselineRank: 12,
      previewRank: 12,
      rankMovement: 0,
    };
    const { container } = render(
      <PlayerComparison
        selectedAttributeLabel="Overall"
        groups={[
          {
            id: "tiers",
            label: "Tier sample",
            kind: "tier",
            rows: [row({ attribute: unchanged, overall: unchanged, state: "no-change" })],
          },
        ]}
        onSelect={vi.fn()}
        onRemove={vi.fn()}
      />,
    );

    const deltas = [...container.querySelectorAll(".delta-value")].map(
      (cell) => cell.textContent,
    );
    expect(deltas).toHaveLength(2);
    expect(deltas.every((value) => value?.includes("= 0"))).toBe(true);
    expect(screen.getAllByText("Rating did not change.")).toHaveLength(2);
    expect(deltas.join(" ")).not.toContain("+0");
  });
});
