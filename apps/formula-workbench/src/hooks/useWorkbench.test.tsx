import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { PlayerDetailResponse } from "../api/types";
import {
  FakePreviewApiClient,
  makePlayerDetail,
  SPECIAL_PLAYER,
} from "../test/fixtures";
import { useWorkbench } from "./useWorkbench";

afterEach(cleanup);

describe("useWorkbench session isolation", () => {
  it("ignores a pin failure that arrives after the session reloads", async () => {
    const client = new FakePreviewApiClient();
    let rejectOldPin!: (reason?: unknown) => void;
    const oldPin = new Promise<PlayerDetailResponse>((_resolve, reject) => {
      rejectOldPin = reject;
    });
    client.getPlayer.mockImplementation(async (playerId) =>
      playerId === SPECIAL_PLAYER.playerId ? oldPin : makePlayerDetail(playerId),
    );
    const { result } = renderHook(() => useWorkbench(client));

    await waitFor(() => expect(result.current.phase).toBe("ready"));
    const previousLoadCount = client.getFormula.mock.calls.length;
    let pinPromise!: Promise<void>;
    act(() => {
      pinPromise = result.current.pinPlayer(SPECIAL_PLAYER);
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
      rejectOldPin(new Error("old pin lookup failed"));
      await pinPromise;
    });

    expect(result.current.phase).toBe("ready");
    expect(result.current.pinError).toBeNull();
    expect(result.current.pinnedPlayers).toEqual([]);
    expect(result.current.selectedPlayerId).not.toBe(SPECIAL_PLAYER.playerId);
  });
});
