import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type {
  BaselineResponse,
  PlayerDetailResponse,
  PlayerSummary,
  SearchHit,
  TierRepresentativeGroup,
} from "../api/types";
import {
  CONTEXT,
  FakePreviewApiClient,
  makePlayerDetail,
  REPRESENTATIVE_GROUPS,
  SPECIAL_PLAYER,
  TOP_PLAYERS,
} from "../test/fixtures";
import { MAX_CUSTOM_PLAYERS, useWorkbench } from "./useWorkbench";

afterEach(cleanup);

function searchHit(player: PlayerSummary): SearchHit {
  return {
    playerId: player.playerId,
    displayName: player.displayName,
    season: player.season,
    baselineRank: player.baselineRank,
    overall: typeof player.baseline.overall === "number" ? player.baseline.overall : null,
  };
}

async function readyWorkbench(client: FakePreviewApiClient) {
  const hook = renderHook(() => useWorkbench(client));
  await waitFor(() => expect(hook.result.current.phase).toBe("ready"));
  await waitFor(() => expect(hook.result.current.representativePhase).toBe("ready"));
  return hook;
}

describe("useWorkbench comparison modes", () => {
  it("blocks an oversized tier sample before it can exceed the preview API limit", async () => {
    const client = new FakePreviewApiClient();
    const sourcePlayers = REPRESENTATIVE_GROUPS[0]!.players;
    const groups: TierRepresentativeGroup[] = Array.from({ length: 9 }, (_, tierIndex) => ({
      tier: `tier-${tierIndex + 1}`,
      minimum: 25 + tierIndex,
      maximum: 25 + tierIndex,
      players: sourcePlayers.map((player, playerIndex) => ({
        ...structuredClone(player),
        playerId: `many-tier-${tierIndex + 1}-${playerIndex + 1}`,
        displayName: `Tier ${tierIndex + 1} Player ${playerIndex + 1}`,
      })),
    }));
    client.getTierRepresentatives.mockImplementation(async (options = {}) => ({
      context: CONTEXT,
      perTier: options.perTier ?? 3,
      tiers: groups.map((group) => ({
        ...structuredClone(group),
        players: structuredClone(group.players.slice(0, options.perTier ?? 3)),
      })),
    }));

    const { result } = renderHook(() => useWorkbench(client));
    await waitFor(() => expect(result.current.phase).toBe("ready"));
    await waitFor(() => expect(result.current.representativePhase).toBe("error"));

    expect(result.current.comparisonPlayers).toEqual([]);
    expect(result.current.loadMessage).toContain(
      "27 players, exceeding the preview limit of 25",
    );
    expect(client.preview).not.toHaveBeenCalled();

    act(() => result.current.setRepresentativesPerTier(2));
    await waitFor(() => expect(result.current.representativePhase).toBe("ready"));
    await waitFor(() => expect(client.preview).toHaveBeenCalledTimes(1));
    expect(client.preview.mock.calls[0]![0].selectedPlayerIds).toHaveLength(18);
  });

  it("lazy-loads and caches the top 25 while preserving each mode's selection", async () => {
    const client = new FakePreviewApiClient();
    const { result } = await readyWorkbench(client);
    const tierSelection = REPRESENTATIVE_GROUPS[0].players[1].playerId;

    expect(result.current.comparisonMode).toBe("tiers");
    expect(result.current.topPhase).toBe("idle");
    expect(client.getPlayers).not.toHaveBeenCalled();

    act(() => result.current.selectPlayer(tierSelection));
    expect(result.current.selectedPlayerId).toBe(tierSelection);

    act(() => result.current.setComparisonMode("top25"));
    await waitFor(() => expect(result.current.topPhase).toBe("ready"));

    expect(client.getPlayers).toHaveBeenCalledTimes(1);
    expect(client.getPlayers).toHaveBeenCalledWith({
      limit: 25,
      signal: expect.any(AbortSignal),
    });
    expect(result.current.topPlayers).toHaveLength(25);
    expect(result.current.comparisonPlayers.map(({ playerId }) => playerId)).toEqual(
      TOP_PLAYERS.map(({ playerId }) => playerId),
    );

    const topSelection = TOP_PLAYERS[4].playerId;
    act(() => result.current.selectPlayer(topSelection));
    expect(result.current.selectedPlayerId).toBe(topSelection);

    act(() => result.current.setComparisonMode("tiers"));
    expect(result.current.selectedPlayerId).toBe(tierSelection);
    act(() => result.current.setComparisonMode("top25"));
    expect(result.current.selectedPlayerId).toBe(topSelection);
    expect(client.getPlayers).toHaveBeenCalledTimes(1);

    await waitFor(() => {
      const request = client.preview.mock.calls.at(-1)?.[0];
      expect(request?.selectedPlayerIds).toEqual(
        TOP_PLAYERS.map(({ playerId }) => playerId),
      );
    });
  });

  it("keeps a custom list separate, deduplicated, removable, and active in previews", async () => {
    const client = new FakePreviewApiClient();
    const { result } = await readyWorkbench(client);
    const first = searchHit(TOP_PLAYERS[10]);
    const second = searchHit(TOP_PLAYERS[11]);

    await act(async () => result.current.addCustomPlayer(first));
    await act(async () => result.current.addCustomPlayer(second));

    expect(result.current.comparisonMode).toBe("custom");
    expect(result.current.customPlayers.map(({ playerId }) => playerId)).toEqual([
      first.playerId,
      second.playerId,
    ]);
    expect(result.current.comparisonPlayers).toEqual(result.current.customPlayers);
    expect(result.current.selectedPlayerId).toBe(second.playerId);

    await act(async () => result.current.addCustomPlayer(first));
    expect(result.current.customPlayers).toHaveLength(2);
    expect(result.current.selectedPlayerId).toBe(first.playerId);
    expect(
      client.getPlayer.mock.calls.filter(
        (arguments_) => arguments_[0] === first.playerId && arguments_.length === 1,
      ),
    ).toHaveLength(1);

    await waitFor(() => {
      const request = client.preview.mock.calls.at(-1)?.[0];
      expect(request?.selectedPlayerIds).toEqual([first.playerId, second.playerId]);
    });

    act(() => result.current.setComparisonMode("tiers"));
    expect(result.current.comparisonPlayers).toHaveLength(15);
    act(() => result.current.setComparisonMode("custom"));
    expect(result.current.selectedPlayerId).toBe(first.playerId);

    act(() => result.current.removeCustomPlayer(first.playerId));
    expect(result.current.customPlayers.map(({ playerId }) => playerId)).toEqual([
      second.playerId,
    ]);
    expect(result.current.selectedPlayerId).toBe(second.playerId);

    act(() => result.current.removeCustomPlayer(second.playerId));
    expect(result.current.customPlayers).toEqual([]);
    expect(result.current.comparisonPlayers).toEqual([]);
    expect(result.current.selectedPlayerId).toBeNull();
    await waitFor(() => expect(result.current.previewPhase).toBe("idle"));
  });

  it("caps the custom list at 25 players without starting a 26th detail request", async () => {
    const client = new FakePreviewApiClient();
    const { result } = await readyWorkbench(client);

    await act(async () => {
      for (const player of TOP_PLAYERS) {
        await result.current.addCustomPlayer(searchHit(player));
      }
    });

    expect(result.current.customPlayers).toHaveLength(MAX_CUSTOM_PLAYERS);
    const specialRequestsBefore = client.getPlayer.mock.calls.filter(
      ([playerId]) => playerId === SPECIAL_PLAYER.playerId,
    ).length;

    await act(async () => result.current.addCustomPlayer(SPECIAL_PLAYER));

    expect(result.current.customPlayers).toHaveLength(MAX_CUSTOM_PLAYERS);
    expect(result.current.customError).toBe(
      "At most 25 players can be added to the custom list.",
    );
    expect(
      client.getPlayer.mock.calls.filter(
        ([playerId]) => playerId === SPECIAL_PLAYER.playerId,
      ),
    ).toHaveLength(specialRequestsBefore);
  });

  it("ignores an unfinished top-player response after leaving that mode", async () => {
    const client = new FakePreviewApiClient();
    let resolveTop!: (response: BaselineResponse) => void;
    const delayedTop = new Promise<BaselineResponse>((resolve) => {
      resolveTop = resolve;
    });
    client.getPlayers.mockImplementation(async () => delayedTop);
    const { result } = await readyWorkbench(client);

    act(() => result.current.setComparisonMode("top25"));
    await waitFor(() => expect(client.getPlayers).toHaveBeenCalledTimes(1));
    act(() => result.current.setComparisonMode("tiers"));

    await act(async () => {
      resolveTop({
        context: CONTEXT,
        defaultSampleSize: 25,
        players: structuredClone(TOP_PLAYERS),
      });
      await delayedTop;
    });

    expect(result.current.comparisonMode).toBe("tiers");
    expect(result.current.topPlayers).toEqual([]);
    expect(result.current.topPhase).toBe("idle");
  });

  it("marks the workbench stale when the lazy top response has mismatched context", async () => {
    const client = new FakePreviewApiClient();
    client.getPlayers.mockResolvedValue({
      context: { ...CONTEXT, season: CONTEXT.season + 1 },
      defaultSampleSize: 25,
      players: structuredClone(TOP_PLAYERS),
    });
    const { result } = await readyWorkbench(client);

    act(() => result.current.setComparisonMode("top25"));

    await waitFor(() => expect(result.current.phase).toBe("stale"));
    expect(result.current.topPlayers).toEqual([]);
  });
});

describe("useWorkbench session isolation", () => {
  it("ignores a custom-player failure that arrives after the session reloads", async () => {
    const client = new FakePreviewApiClient();
    let rejectOldLookup!: (reason?: unknown) => void;
    const oldLookup = new Promise<PlayerDetailResponse>((_resolve, reject) => {
      rejectOldLookup = reject;
    });
    client.getPlayer.mockImplementation(async (playerId) =>
      playerId === SPECIAL_PLAYER.playerId ? oldLookup : makePlayerDetail(playerId),
    );
    const { result } = await readyWorkbench(client);

    const previousLoadCount = client.getFormula.mock.calls.length;
    let addPromise!: Promise<void>;
    act(() => {
      addPromise = result.current.addCustomPlayer(SPECIAL_PLAYER);
    });
    await waitFor(() =>
      expect(client.getPlayer).toHaveBeenCalledWith(SPECIAL_PLAYER.playerId),
    );

    act(() => result.current.reload());
    await waitFor(() =>
      expect(client.getFormula).toHaveBeenCalledTimes(previousLoadCount + 1),
    );
    await waitFor(() => expect(result.current.phase).toBe("ready"));

    await act(async () => {
      rejectOldLookup(new Error("old custom-player lookup failed"));
      await addPromise;
    });

    expect(result.current.phase).toBe("ready");
    expect(result.current.comparisonMode).toBe("tiers");
    expect(result.current.customError).toBeNull();
    expect(result.current.customPlayers).toEqual([]);
    expect(result.current.topPlayers).toEqual([]);
    expect(result.current.selectedPlayerId).not.toBe(SPECIAL_PLAYER.playerId);
  });
});
