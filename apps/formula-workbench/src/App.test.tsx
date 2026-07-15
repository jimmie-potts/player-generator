import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { PreviewResponse } from "./api/types";
import { App } from "./App";
import {
  CONTEXT,
  FakePreviewApiClient,
  FORMULA_DOCUMENT,
  METRICS,
  REPRESENTATIVE_GROUPS,
  SPECIAL_PLAYER,
  TOP_PLAYERS,
  makePreviewResponse,
} from "./test/fixtures";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

async function renderReadyWorkbench(client = new FakePreviewApiClient()) {
  render(<App client={client} />);
  await screen.findByRole("heading", { name: "Overall" });
  await screen.findByText("Preview current", {}, { timeout: 2_000 });
  return client;
}

function weightSlider(metricLabel: string): HTMLInputElement {
  return screen.getByRole("slider", {
    name: `${metricLabel} weight`,
  }) as HTMLInputElement;
}

function overallWeightSlider(): HTMLInputElement {
  return weightSlider("Points scored per game");
}

async function waitForNextPreview(
  client: FakePreviewApiClient,
  previousCallCount: number,
) {
  await waitFor(
    () => expect(client.preview).toHaveBeenCalledTimes(previousCallCount + 1),
    { timeout: 1_500 },
  );
  await screen.findByText("Preview current", {}, { timeout: 1_500 });
}

function tierPlayerIds(perTier = 3): string[] {
  return REPRESENTATIVE_GROUPS.flatMap((group) =>
    group.players.slice(0, perTier).map(({ playerId }) => playerId),
  );
}

function selectComparisonMode(name: "Tier sample" | "Top 25" | "Custom list") {
  fireEvent.click(screen.getByRole("tab", { name }));
  expect(screen.getByRole("tab", { name }).getAttribute("aria-selected")).toBe("true");
}

async function addSpecialPlayer(client: FakePreviewApiClient) {
  fireEvent.change(screen.getByRole("searchbox", { name: "Player search" }), {
    target: { value: "Spec" },
  });
  expect(await screen.findByText("Bench Specialist", {}, { timeout: 1_500 })).toBeTruthy();
  expect(client.searchPlayers).toHaveBeenLastCalledWith(
    "Spec",
    expect.objectContaining({ limit: 10, signal: expect.any(AbortSignal) }),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Add Bench Specialist to custom list" }),
  );
}

async function readBlob(blob: Blob): Promise<string> {
  if ("text" in blob && typeof blob.text === "function") {
    return blob.text();
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => resolve(String(reader.result)));
    reader.addEventListener("error", () => reject(reader.error));
    reader.readAsText(blob);
  });
}

describe("Formula Workbench", () => {
  it("loads the authoritative formula, default tier sample, and exact API calculation values", async () => {
    const client = await renderReadyWorkbench();

    expect(screen.getByText("Formula · vattributes-2026.1")).toBeTruthy();
    expect(screen.getByText("240 players")).toBeTruthy();
    expect(
      await screen.findByRole(
        "heading",
        { name: "Superstar · 90–99" },
        { timeout: 2_500 },
      ),
    ).toBeTruthy();
    expect(screen.getByRole("heading", { name: "All Star · 80–89" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Starter · 70–79" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Rotation · 60–69" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Fringe · 25–59" })).toBeTruthy();
    expect(client.getTierRepresentatives).toHaveBeenCalledWith(
      expect.objectContaining({ perTier: 3, signal: expect.any(AbortSignal) }),
    );
    expect(
      screen.getByRole("tab", { name: "Tier sample" }).getAttribute("aria-selected"),
    ).toBe("true");
    expect(client.preview.mock.calls.at(-1)?.[0].selectedPlayerIds).toEqual(
      tierPlayerIds(),
    );

    const breakdown = screen.getByRole("region", {
      name: "Component calculation breakdown",
    });
    const pointsRow = within(breakdown).getByRole("row", {
      name: /Points scored per game/,
    });
    const pointsCells = within(pointsRow).getAllByRole("cell");
    expect([pointsCells[0], pointsCells[2], pointsCells[4]].map((cell) => cell.textContent)).toEqual([
      "90%",
      "60%",
      "0.54",
    ]);
    expect(
      [pointsCells[1], pointsCells[3], pointsCells[5]].map(
        (cell) => cell.querySelector(".preview-change__value")?.textContent,
      ),
    ).toEqual(["90%", "60%", "0.54"]);
    expect(pointsRow.querySelectorAll(".preview-value--unchanged")).toHaveLength(3);

    fireEvent.change(screen.getByRole("combobox", { name: "Players per tier" }), {
      target: { value: "1" },
    });

    await waitFor(() => {
      expect(client.getTierRepresentatives).toHaveBeenLastCalledWith(
        expect.objectContaining({ perTier: 1, signal: expect.any(AbortSignal) }),
      );
    });
    await waitFor(
      () => {
        const superstarComparison = screen.getByRole("region", {
          name: "Superstar · 90–99 player comparison",
        });
        expect(within(superstarComparison).getAllByRole("row")).toHaveLength(2);
      },
      { timeout: 2_500 },
    );
    expect(screen.getAllByText("1 representative")).toHaveLength(5);
  });

  it("debounces formula edits and renders the server-owned preview breakdown", async () => {
    const client = await renderReadyWorkbench();
    const previousCallCount = client.preview.mock.calls.length;

    fireEvent.change(overallWeightSlider(), { target: { value: "0.7" } });

    expect(client.preview).toHaveBeenCalledTimes(previousCallCount);
    await waitForNextPreview(client, previousCallCount);

    const latestRequest = client.preview.mock.calls.at(-1)?.[0];
    expect(latestRequest?.adjustments.components).toEqual([
      { attribute: "overall", metric: "pointsPerGame", weight: 0.7 },
      { attribute: "overall", metric: "assistsPerGame", weight: 0.3 },
    ]);
    const breakdown = screen.getByRole("region", {
      name: "Component calculation breakdown",
    });
    const pointsRow = within(breakdown).getByRole("row", {
      name: /Points scored per game/,
    });
    const pointsCells = within(pointsRow).getAllByRole("cell");
    expect([pointsCells[0], pointsCells[2], pointsCells[4]].map((cell) => cell.textContent)).toEqual([
      "90%",
      "60%",
      "0.54",
    ]);
    expect(
      [pointsCells[1], pointsCells[3], pointsCells[5]].map(
        (cell) => cell.querySelector(".preview-change__value")?.textContent,
      ),
    ).toEqual(["90%", "70%", "0.63"]);
    expect(pointsRow.querySelectorAll(".preview-value--increase")).toHaveLength(1);
    expect(pointsRow.querySelectorAll(".preview-value--allocation-change")).toHaveLength(1);
    expect(screen.getAllByText("Largest gain").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Largest loss").length).toBeGreaterThan(0);
  });

  it("keeps the selected attribute at an exact 100 percent allocation while a slider moves", async () => {
    const client = await renderReadyWorkbench();
    const previousCallCount = client.preview.mock.calls.length;

    const allocation = screen.getByRole("img", {
      name: "Overall component allocation totals 100 percent",
    });
    expect(
      Array.from(allocation.children).map(
        (segment) => (segment as HTMLElement).style.width,
      ),
    ).toEqual(["60%", "40%"]);

    fireEvent.change(weightSlider("Assists per game"), {
      target: { value: "0.65" },
    });

    expect(Number(overallWeightSlider().value)).toBeCloseTo(0.35);
    expect(weightSlider("Assists per game").value).toBe("0.65");
    expect(
      Number(overallWeightSlider().value) +
        Number(weightSlider("Assists per game").value),
    ).toBe(1);
    expect(
      Array.from(allocation.children).map(
        (segment) => (segment as HTMLElement).style.width,
      ),
    ).toEqual(["35%", "65%"]);

    await waitForNextPreview(client, previousCallCount);
    expect(client.preview.mock.calls.at(-1)?.[0].adjustments.components).toEqual([
      { attribute: "overall", metric: "pointsPerGame", weight: 0.35 },
      { attribute: "overall", metric: "assistsPerGame", weight: 0.65 },
    ]);
  });

  it("selects another supported attribute and requests its authoritative preview", async () => {
    const client = await renderReadyWorkbench();
    const previousCallCount = client.preview.mock.calls.length;

    fireEvent.click(screen.getByRole("button", { name: /^Shooting/ }));

    expect(await screen.findByRole("heading", { name: "Shooting" })).toBeTruthy();
    await waitForNextPreview(client, previousCallCount);
    expect(client.preview.mock.calls.at(-1)?.[0].selectedAttribute).toBe("shooting");
    expect(screen.getAllByRole("columnheader", { name: "Shooting" }).length).toBe(5);
  });

  it("fixes a single-component attribute at a disabled 100 percent slider", async () => {
    const client = await renderReadyWorkbench();
    const previousCallCount = client.preview.mock.calls.length;

    fireEvent.click(screen.getByRole("button", { name: /^Shooting/ }));
    await screen.findByRole("heading", { name: "Shooting" });
    await waitForNextPreview(client, previousCallCount);

    const slider = weightSlider("Points scored per game");
    expect(slider.value).toBe("1");
    expect(slider.disabled).toBe(true);
    expect(slider.getAttribute("aria-valuetext")).toBe("100 percent");
    expect(
      screen.getByRole("img", {
        name: "Shooting component allocation totals 100 percent",
      }),
    ).toBeTruthy();
    expect(screen.getAllByText("The only component remains fixed at 100%.")).toHaveLength(1);
  });

  it("cancels a superseded preview and prevents its late response replacing the latest result", async () => {
    const client = await renderReadyWorkbench();
    let resolveOld!: (response: PreviewResponse) => void;
    let oldResponse!: PreviewResponse;
    let oldSignal: AbortSignal | undefined;
    let editRequestIndex = 0;

    client.previewHandler = async (request, options, response) => {
      editRequestIndex += 1;
      if (editRequestIndex === 1) {
        oldResponse = { ...response, elapsedMs: 111 };
        oldSignal = options.signal;
        return new Promise((resolve) => {
          resolveOld = resolve;
        });
      }
      return { ...response, elapsedMs: 222 };
    };

    const firstWeightInput = overallWeightSlider();
    fireEvent.change(firstWeightInput, { target: { value: "0.7" } });
    await waitFor(() => expect(editRequestIndex).toBe(1), { timeout: 1_500 });

    expect(firstWeightInput.disabled).toBe(false);
    fireEvent.change(firstWeightInput, { target: { value: "0.8" } });
    await waitFor(() => expect(oldSignal?.aborted).toBe(true));
    await waitFor(() => expect(editRequestIndex).toBe(2), { timeout: 1_500 });
    await screen.findByText("Validated in 222 ms");

    await act(async () => {
      resolveOld(oldResponse);
      await Promise.resolve();
    });

    expect(screen.getByText("Validated in 222 ms")).toBeTruthy();
    const latestRequest = client.preview.mock.calls.at(-1)?.[0];
    expect(latestRequest?.adjustments.components).toEqual([
      { attribute: "overall", metric: "pointsPerGame", weight: 0.8 },
      { attribute: "overall", metric: "assistsPerGame", weight: 0.2 },
    ]);
  });

  it("blocks invalid client input immediately without sending it to the preview API", async () => {
    const client = await renderReadyWorkbench();
    const previousCallCount = client.preview.mock.calls.length;

    fireEvent.change(screen.getByRole("textbox", { name: /^Formula version/ }), {
      target: { value: "   " },
    });

    expect(
      (await screen.findAllByText("A proposed formula version is required.")).length,
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByText("Resolve formula validation issues to request a preview.").length,
    ).toBeGreaterThan(0);
    await new Promise((resolve) => window.setTimeout(resolve, 450));
    expect(client.preview).toHaveBeenCalledTimes(previousCallCount);
    expect(
      (screen.getByRole("button", { name: "Export proposal" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
  });

  it("resets an attribute and the full session to the active formula", async () => {
    const client = await renderReadyWorkbench();
    let previousCallCount = client.preview.mock.calls.length;

    fireEvent.change(overallWeightSlider(), { target: { value: "0.7" } });
    await waitForNextPreview(client, previousCallCount);
    expect(
      (screen.getByRole("button", { name: "Reset attribute" }) as HTMLButtonElement)
        .disabled,
    ).toBe(false);
    expect(
      (screen.getByRole("button", { name: "Reset all" }) as HTMLButtonElement).disabled,
    ).toBe(false);

    previousCallCount = client.preview.mock.calls.length;
    fireEvent.click(screen.getByRole("button", { name: "Reset attribute" }));
    await waitForNextPreview(client, previousCallCount);
    expect(overallWeightSlider().value).toBe("0.6");
    expect(client.preview.mock.calls.at(-1)?.[0].adjustments.components).toEqual([]);
    expect(
      (screen.getByRole("button", { name: "Reset all" }) as HTMLButtonElement).disabled,
    ).toBe(true);

    previousCallCount = client.preview.mock.calls.length;
    fireEvent.change(overallWeightSlider(), { target: { value: "0.75" } });
    await waitForNextPreview(client, previousCallCount);
    previousCallCount = client.preview.mock.calls.length;
    fireEvent.click(screen.getByRole("button", { name: "Reset all" }));
    await waitForNextPreview(client, previousCallCount);
    expect(overallWeightSlider().value).toBe("0.6");
    expect(
      (screen.getByRole("button", { name: "Reset all" }) as HTMLButtonElement).disabled,
    ).toBe(true);
  });

  it("exports the exact full formula document validated by the server", async () => {
    const client = await renderReadyWorkbench();
    const previousCallCount = client.preview.mock.calls.length;

    fireEvent.change(screen.getByRole("textbox", { name: /^Formula version/ }), {
      target: { value: "designer-balance-v2" },
    });
    fireEvent.change(overallWeightSlider(), { target: { value: "0.75" } });
    await waitForNextPreview(client, previousCallCount);

    let exportedBlob: Blob | undefined;
    const createObjectUrl = vi.fn((blob: Blob) => {
      exportedBlob = blob;
      return "blob:formula-proposal";
    });
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: createObjectUrl,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);

    fireEvent.click(screen.getByRole("button", { name: "Export proposal" }));

    expect(createObjectUrl).toHaveBeenCalledTimes(1);
    expect(exportedBlob).toBeDefined();
    const latestRequest = client.preview.mock.calls.at(-1)?.[0];
    const expectedDocument = makePreviewResponse(latestRequest!).previewDocument;
    expect(await readBlob(exportedBlob!)).toBe(
      `${JSON.stringify(expectedDocument, null, 2)}\n`,
    );
    expect(expectedDocument.formulaVersion).toBe("designer-balance-v2");
    expect(expectedDocument).not.toEqual(FORMULA_DOCUMENT);
  });

  it("loads the fixed top 25 and previews exactly those baseline-ranked players", async () => {
    const client = await renderReadyWorkbench();
    const previousCallCount = client.preview.mock.calls.length;

    selectComparisonMode("Top 25");

    await waitFor(() => {
      expect(client.getPlayers).toHaveBeenCalledWith(
        expect.objectContaining({ limit: 25, signal: expect.any(AbortSignal) }),
      );
    });
    await waitForNextPreview(client, previousCallCount);

    const topComparison = await screen.findByRole("region", {
      name: "Top 25 by baseline overall player comparison",
    });
    expect(within(topComparison).getAllByRole("row")).toHaveLength(26);
    expect(client.preview.mock.calls.at(-1)?.[0].selectedPlayerIds).toEqual(
      TOP_PLAYERS.map(({ playerId }) => playerId),
    );
    expect(
      client.preview.mock.calls.at(-1)?.[0].selectedPlayerIds,
    ).not.toEqual(expect.arrayContaining(tierPlayerIds()));
    expect(
      screen.queryByRole("region", { name: "Superstar · 90–99 player comparison" }),
    ).toBeNull();
  });

  it("retries a failed Top 25 load without leaving the active tab", async () => {
    const client = new FakePreviewApiClient();
    client.getPlayers.mockRejectedValueOnce(new Error("top-player service unavailable"));
    await renderReadyWorkbench(client);

    selectComparisonMode("Top 25");

    const errorHeading = await screen.findByRole("heading", {
      name: "Player comparison unavailable",
    });
    const alert = errorHeading.closest<HTMLElement>('[role="alert"]');
    expect(alert).not.toBeNull();
    expect(within(alert!).getByText(/top-player service unavailable/)).toBeTruthy();
    expect(client.getPlayers).toHaveBeenCalledTimes(1);

    fireEvent.click(within(alert!).getByRole("button", { name: "Retry Top 25" }));

    await waitFor(() => expect(client.getPlayers).toHaveBeenCalledTimes(2));
    expect(
      await screen.findByRole(
        "region",
        { name: "Top 25 by baseline overall player comparison" },
        { timeout: 2_500 },
      ),
    ).toBeTruthy();
    await waitFor(() =>
      expect(client.preview.mock.calls.at(-1)?.[0].selectedPlayerIds).toEqual(
        TOP_PLAYERS.map(({ playerId }) => playerId),
      ),
    );
  });

  it("does not request a preview for an empty custom list", async () => {
    const client = await renderReadyWorkbench();
    const previousCallCount = client.preview.mock.calls.length;

    selectComparisonMode("Custom list");

    expect(await screen.findByRole("heading", { name: "Build a custom list" })).toBeTruthy();
    expect(
      await screen.findByRole("heading", { name: "Build your custom comparison" }),
    ).toBeTruthy();
    expect(screen.getByText("0/25 selected")).toBeTruthy();
    expect(screen.getByText("Select comparison players")).toBeTruthy();
    await new Promise((resolve) => window.setTimeout(resolve, 450));
    expect(client.preview).toHaveBeenCalledTimes(previousCallCount);
    expect(screen.queryByRole("region", { name: /player comparison$/i })).toBeNull();
  });

  it("adds and removes a custom player while previewing only the custom list", async () => {
    const client = await renderReadyWorkbench();
    selectComparisonMode("Custom list");
    const previousCallCount = client.preview.mock.calls.length;

    await addSpecialPlayer(client);

    await waitForNextPreview(client, previousCallCount);
    const customComparison = await screen.findByRole("region", {
      name: "Custom list player comparison",
    });
    expect(within(customComparison).getAllByRole("row")).toHaveLength(2);
    expect(client.getPlayer).toHaveBeenCalledWith(SPECIAL_PLAYER.playerId);
    expect(client.preview.mock.calls.at(-1)?.[0].selectedPlayerIds).toEqual([
      SPECIAL_PLAYER.playerId,
    ]);
    expect(screen.getByText("1/25 selected")).toBeTruthy();

    const previewCallCount = client.preview.mock.calls.length;
    fireEvent.click(
      screen.getByRole("button", {
        name: "Remove Bench Specialist from custom list",
      }),
    );

    expect(
      await screen.findByRole("heading", { name: "Build your custom comparison" }),
    ).toBeTruthy();
    expect(screen.getByText("0/25 selected")).toBeTruthy();
    await new Promise((resolve) => window.setTimeout(resolve, 450));
    expect(client.preview).toHaveBeenCalledTimes(previewCallCount);
  });

  it("keeps comparison requests isolated and restores each mode's selected player", async () => {
    const client = await renderReadyWorkbench();

    fireEvent.click(screen.getByRole("button", { name: /superstar player 2/i }));
    expect(
      screen
        .getByRole("button", { name: /superstar player 2/i })
        .getAttribute("aria-current"),
    ).toBe("true");

    let previousCallCount = client.preview.mock.calls.length;
    selectComparisonMode("Top 25");
    await waitForNextPreview(client, previousCallCount);
    fireEvent.click(
      screen.getByRole("button", { name: "Top player 2, Superstar" }),
    );
    expect(
      screen
        .getByRole("button", { name: "Top player 2, Superstar" })
        .getAttribute("aria-current"),
    ).toBe("true");

    selectComparisonMode("Custom list");
    previousCallCount = client.preview.mock.calls.length;
    await addSpecialPlayer(client);
    await waitForNextPreview(client, previousCallCount);
    expect(client.preview.mock.calls.at(-1)?.[0].selectedPlayerIds).toEqual([
      SPECIAL_PLAYER.playerId,
    ]);

    previousCallCount = client.preview.mock.calls.length;
    selectComparisonMode("Tier sample");
    await waitForNextPreview(client, previousCallCount);
    expect(client.preview.mock.calls.at(-1)?.[0].selectedPlayerIds).toEqual(
      tierPlayerIds(),
    );
    expect(
      screen
        .getByRole("button", { name: /superstar player 2/i })
        .getAttribute("aria-current"),
    ).toBe("true");

    previousCallCount = client.preview.mock.calls.length;
    selectComparisonMode("Top 25");
    await waitForNextPreview(client, previousCallCount);
    expect(client.preview.mock.calls.at(-1)?.[0].selectedPlayerIds).toEqual(
      TOP_PLAYERS.map(({ playerId }) => playerId),
    );
    expect(
      screen
        .getByRole("button", { name: "Top player 2, Superstar" })
        .getAttribute("aria-current"),
    ).toBe("true");

    previousCallCount = client.preview.mock.calls.length;
    selectComparisonMode("Custom list");
    await waitForNextPreview(client, previousCallCount);
    expect(client.preview.mock.calls.at(-1)?.[0].selectedPlayerIds).toEqual([
      SPECIAL_PLAYER.playerId,
    ]);
    expect(
      screen
        .getByRole("button", { name: "Bench Specialist, Rotation" })
        .getAttribute("aria-current"),
    ).toBe("true");
  });

  it("keeps baseline calculation stats visible while a new preview is pending", async () => {
    const client = await renderReadyWorkbench();
    client.previewHandler = async () => new Promise<PreviewResponse>(() => undefined);

    fireEvent.change(overallWeightSlider(), { target: { value: "0.7" } });

    const inspector = screen.getByRole("region", {
      name: /Overall authoritative explanation for superstar player 1/i,
    });
    expect(inspector.getAttribute("aria-busy")).toBe("true");
    expect(
      within(inspector).getByText(/Baseline stats remain visible while prior preview values/),
    ).toBeTruthy();
    const rawMetrics = within(inspector).getByRole("region", {
      name: "Raw metric values",
    });
    const pointsRow = within(rawMetrics).getByRole("row", {
      name: /Points Per Game/,
    });
    expect(within(pointsRow).getAllByRole("cell").map((cell) => cell.textContent)).toEqual([
      "27.5",
      "Updating…",
      "Pending",
    ]);
    expect(within(inspector).getByLabelText("Calculation summary")).toBeTruthy();
  });

  it("searches by a partial name only within the custom comparison mode", async () => {
    const client = await renderReadyWorkbench();
    selectComparisonMode("Custom list");

    fireEvent.change(screen.getByRole("searchbox", { name: "Player search" }), {
      target: { value: "Spec" },
    });
    expect(await screen.findByText("Bench Specialist", {}, { timeout: 1_500 })).toBeTruthy();
    expect(client.searchPlayers).toHaveBeenCalledWith(
      "Spec",
      expect.objectContaining({ limit: 10, signal: expect.any(AbortSignal) }),
    );
    expect(
      screen.getByRole("button", { name: "Add Bench Specialist to custom list" }),
    ).toBeTruthy();
  });

  it("opens a semantic glossary with the active formula model catalog", async () => {
    await renderReadyWorkbench();

    fireEvent.click(screen.getByRole("button", { name: "Glossary" }));

    expect(await screen.findByRole("heading", { name: "Glossary", level: 1 })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Glossary" }).getAttribute("aria-current")).toBe(
      "page",
    );
    expect(screen.getByText("Normalized weight")).toBeTruthy();
    expect(screen.getByText("Fixed cohort")).toBeTruthy();

    const catalogHeading = screen.getByRole("heading", {
      name: "Loaded model catalog",
    });
    const catalog = catalogHeading.closest("section");
    expect(catalog).not.toBeNull();
    expect(within(catalog!).getByText(/Active formula/).textContent).toContain(
      "attributes-2026.1",
    );
    expect(within(catalog!).getByRole("heading", { name: "Overall" })).toBeTruthy();
    expect(within(catalog!).getByRole("heading", { name: "Shooting" })).toBeTruthy();
    expect(
      within(catalog!).getAllByText("Scoring production per appearance."),
    ).toHaveLength(3);
  });

  it("preserves session edits and the custom list while navigating through the glossary", async () => {
    const client = await renderReadyWorkbench();
    const previousCallCount = client.preview.mock.calls.length;

    fireEvent.change(overallWeightSlider(), { target: { value: "0.72" } });
    await waitForNextPreview(client, previousCallCount);
    selectComparisonMode("Custom list");
    const customPreviewCallCount = client.preview.mock.calls.length;
    await addSpecialPlayer(client);
    await waitForNextPreview(client, customPreviewCallCount);
    const previewCallCount = client.preview.mock.calls.length;

    fireEvent.click(screen.getByRole("button", { name: "Glossary" }));
    await screen.findByRole("heading", { name: "Glossary", level: 1 });
    fireEvent.click(screen.getByRole("button", { name: "Workbench" }));
    await screen.findByRole("heading", { name: "Overall" });

    expect(overallWeightSlider().value).toBe("0.72");
    expect(Number(weightSlider("Assists per game").value)).toBeCloseTo(0.28);
    expect(
      screen.getByRole("button", { name: "Remove Bench Specialist from custom list" }),
    ).toBeTruthy();
    expect(screen.getByText("1/25 selected")).toBeTruthy();
    expect(
      screen.getByRole("tab", { name: "Custom list" }).getAttribute("aria-selected"),
    ).toBe("true");
    expect(
      (screen.getByRole("button", { name: "Reset all" }) as HTMLButtonElement).disabled,
    ).toBe(false);
    expect(client.getFormula).toHaveBeenCalledTimes(1);
    expect(client.preview).toHaveBeenCalledTimes(previewCallCount);
  });

  it("clears stale search hits while the next query is debounced", async () => {
    const client = await renderReadyWorkbench();
    selectComparisonMode("Custom list");
    const searchbox = screen.getByRole("searchbox", { name: "Player search" });

    fireEvent.change(searchbox, { target: { value: "Spec" } });
    expect(await screen.findByText("Bench Specialist", {}, { timeout: 1_500 })).toBeTruthy();
    const previousCallCount = client.searchPlayers.mock.calls.length;

    fireEvent.change(searchbox, { target: { value: "Nobody" } });

    expect(screen.queryByText("Bench Specialist")).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Add Bench Specialist to custom list" }),
    ).toBeNull();
    expect(
      screen.getByRole("heading", { name: "Searching the loaded cohort" }),
    ).toBeTruthy();
    expect(client.searchPlayers).toHaveBeenCalledTimes(previousCallCount);

    await waitFor(
      () => expect(client.searchPlayers).toHaveBeenCalledTimes(previousCallCount + 1),
      { timeout: 1_500 },
    );
    expect(client.searchPlayers).toHaveBeenLastCalledWith(
      "Nobody",
      expect.objectContaining({ limit: 10, signal: expect.any(AbortSignal) }),
    );
    expect(await screen.findByRole("heading", { name: "No matching players" })).toBeTruthy();
  });

  it("clears a failed custom add when the designer starts another search", async () => {
    const client = await renderReadyWorkbench();
    selectComparisonMode("Custom list");
    client.getPlayer.mockRejectedValueOnce(new Error("player detail unavailable"));

    await addSpecialPlayer(client);

    expect(
      await screen.findByRole("heading", { name: "Player search failed" }),
    ).toBeTruthy();
    expect(screen.getByText("player detail unavailable")).toBeTruthy();
    expect(
      screen.queryByRole("button", { name: "Add Bench Specialist to custom list" }),
    ).toBeNull();

    fireEvent.change(screen.getByRole("searchbox", { name: "Player search" }), {
      target: { value: "Bench" },
    });

    expect(
      await screen.findByRole(
        "button",
        { name: "Add Bench Specialist to custom list" },
        { timeout: 1_500 },
      ),
    ).toBeTruthy();
    expect(screen.queryByText("player detail unavailable")).toBeNull();
  });

  it("starts a fresh browser session without edits or custom players after remount", async () => {
    const client = new FakePreviewApiClient();
    const firstSession = render(<App client={client} />);
    await screen.findByRole("heading", { name: "Overall" });
    await screen.findByText("Preview current", {}, { timeout: 2_000 });

    const previousCallCount = client.preview.mock.calls.length;
    fireEvent.change(screen.getByRole("textbox", { name: /^Formula version/ }), {
      target: { value: "session-only-proposal" },
    });
    fireEvent.change(overallWeightSlider(), { target: { value: "0.75" } });
    await waitForNextPreview(client, previousCallCount);
    expect(
      (screen.getByRole("textbox", { name: /^Formula version/ }) as HTMLInputElement).value,
    ).toBe("session-only-proposal");
    expect(overallWeightSlider().value).toBe("0.75");

    selectComparisonMode("Custom list");
    const customPreviewCallCount = client.preview.mock.calls.length;
    await addSpecialPlayer(client);
    await waitForNextPreview(client, customPreviewCallCount);
    expect(screen.getByText("1/25 selected")).toBeTruthy();

    firstSession.unmount();
    render(<App client={client} />);
    await screen.findByRole("heading", { name: "Overall" });
    await screen.findByText("Preview current", {}, { timeout: 2_000 });

    expect(
      (screen.getByRole("textbox", { name: /^Formula version/ }) as HTMLInputElement).value,
    ).toBe("attributes-2026.1-proposal.1");
    expect(overallWeightSlider().value).toBe("0.6");
    expect(
      (screen.getByRole("button", { name: "Reset all" }) as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(
      screen.getByRole("tab", { name: "Tier sample" }).getAttribute("aria-selected"),
    ).toBe("true");
    selectComparisonMode("Custom list");
    expect(screen.getByText("0/25 selected")).toBeTruthy();
    expect(
      screen.queryByRole("button", { name: "Remove Bench Specialist from custom list" }),
    ).toBeNull();
  });

  it("stops at a stale state when initial formula and metric contexts disagree", async () => {
    const client = new FakePreviewApiClient();
    const staleContext = structuredClone(CONTEXT);
    staleContext.referencePackage.contentHash = "different-reference-package";
    client.getMetrics.mockResolvedValueOnce({
      context: staleContext,
      metrics: structuredClone(METRICS),
    });

    render(<App client={client} />);

    expect(
      await screen.findByRole("heading", { name: "Workbench context changed" }),
    ).toBeTruthy();
    expect(screen.getByText(/referencePackage.contentHash/)).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Overall" })).toBeNull();
    expect(client.getTierRepresentatives).not.toHaveBeenCalled();
  });

  it("shows an initial API failure without rendering partial formula data", async () => {
    const client = new FakePreviewApiClient();
    client.getFormula.mockRejectedValueOnce(new Error("formula service unavailable"));

    render(<App client={client} />);

    expect(
      await screen.findByRole("heading", { name: "Formula workbench unavailable" }),
    ).toBeTruthy();
    expect(screen.getByText("formula service unavailable")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Overall" })).toBeNull();
    expect(client.getTierRepresentatives).not.toHaveBeenCalled();
  });

  it("clears prior comparison results but keeps baseline stats after preview failure", async () => {
    const client = await renderReadyWorkbench();
    expect(screen.getByRole("region", { name: "Superstar · 90–99 player comparison" })).toBeTruthy();
    client.previewHandler = async () => {
      throw new Error("preview service exploded");
    };

    fireEvent.change(overallWeightSlider(), { target: { value: "0.7" } });

    const comparisonFailure = await screen.findByRole(
      "heading",
      { name: "Player comparison unavailable" },
      { timeout: 1_500 },
    );
    const alert = comparisonFailure.closest<HTMLElement>('[role="alert"]');
    expect(alert).not.toBeNull();
    expect(within(alert!).getByText("Player comparison unavailable")).toBeTruthy();
    expect(within(alert!).getByText(/preview service exploded/)).toBeTruthy();
    expect(
      within(alert!).getByText(/Prior preview results are not shown as current/),
    ).toBeTruthy();
    expect(
      screen.queryByRole("region", { name: "Superstar · 90–99 player comparison" }),
    ).toBeNull();
    const previewFailure = screen.getByRole("heading", { name: "Preview unavailable" });
    const calculationAlert = previewFailure.closest<HTMLElement>('[role="alert"]');
    expect(calculationAlert).not.toBeNull();
    expect(within(calculationAlert!).getByText(/Baseline stats remain available/)).toBeTruthy();
    const inspector = screen.getByRole("region", {
      name: /Overall authoritative explanation for superstar player 1/i,
    });
    expect(within(inspector).getByRole("region", { name: "Raw metric values" })).toBeTruthy();
    expect(within(inspector).getByLabelText("Calculation summary")).toBeTruthy();
  });
});
