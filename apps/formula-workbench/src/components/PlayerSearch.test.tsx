import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { SearchHit } from "../api/types";
import { PlayerSearch } from "./PlayerSearch";

afterEach(cleanup);

const PLAYER: SearchHit = {
  playerId: "player-1",
  displayName: "Example Player",
  season: 2026,
  baselineRank: 14,
  overall: 82,
};

function renderSearch(
  overrides: Partial<React.ComponentProps<typeof PlayerSearch>> = {},
) {
  const onAdd = vi.fn();
  render(
    <PlayerSearch
      query="Example"
      results={[PLAYER]}
      selectedPlayerIds={[]}
      onQueryChange={vi.fn()}
      onSubmit={vi.fn()}
      onAdd={onAdd}
      {...overrides}
    />,
  );
  return onAdd;
}

describe("PlayerSearch", () => {
  it("adds a search result to a 25-player custom list", () => {
    const onAdd = renderSearch();

    expect(screen.getByRole("heading", { name: "Build a custom list" })).toBeTruthy();
    expect(screen.getByText("0/25 selected")).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: "Add Example Player to custom list" }),
    );
    expect(onAdd).toHaveBeenCalledWith(PLAYER);
  });

  it("marks an existing custom player as added", () => {
    renderSearch({ selectedPlayerIds: [PLAYER.playerId] });

    const button = screen.getByRole("button", {
      name: "Example Player is in the custom list",
    }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(button.textContent).toBe("Added");
    expect(screen.getByText("1/25 selected")).toBeTruthy();
  });

  it("prevents another addition when the custom list is full", () => {
    renderSearch({ selectedPlayerIds: ["one", "two"], maxPlayers: 2 });

    const button = screen.getByRole("button", {
      name: "Custom list is full; cannot add Example Player",
    }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(button.textContent).toBe("List full");
    expect(screen.getByText("2/2 selected")).toBeTruthy();
  });
});
