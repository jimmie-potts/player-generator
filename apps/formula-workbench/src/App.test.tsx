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
  FakePreviewApiClient,
  FORMULA_DOCUMENT,
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

function overallWeightInput(index = 0): HTMLInputElement {
  return screen.getAllByRole("spinbutton", { name: "Weight" })[index] as HTMLInputElement;
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

    const breakdown = screen.getByRole("region", {
      name: "Component calculation breakdown",
    });
    const pointsRow = within(breakdown).getByRole("row", {
      name: /Points scored per game/,
    });
    const pointsCells = within(pointsRow).getAllByRole("cell");
    expect(pointsCells.map((cell) => cell.textContent)).toEqual([
      "90%",
      "90%",
      "60%",
      "60%",
      "0.54",
      "0.54",
    ]);
  });

  it("debounces formula edits and renders the server-owned preview breakdown", async () => {
    const client = await renderReadyWorkbench();
    const previousCallCount = client.preview.mock.calls.length;

    fireEvent.change(overallWeightInput(), { target: { value: "0.7" } });

    expect(client.preview).toHaveBeenCalledTimes(previousCallCount);
    await waitForNextPreview(client, previousCallCount);

    const latestRequest = client.preview.mock.calls.at(-1)?.[0];
    expect(latestRequest?.adjustments.components).toEqual([
      { attribute: "overall", metric: "pointsPerGame", weight: 0.7 },
    ]);
    const breakdown = screen.getByRole("region", {
      name: "Component calculation breakdown",
    });
    const pointsRow = within(breakdown).getByRole("row", {
      name: /Points scored per game/,
    });
    expect(within(pointsRow).getAllByRole("cell").map((cell) => cell.textContent)).toEqual([
      "90%",
      "90%",
      "60%",
      "70%",
      "0.54",
      "0.63",
    ]);
    expect(screen.getAllByText("Largest gain").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Largest loss").length).toBeGreaterThan(0);
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

    const firstWeightInput = overallWeightInput();
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
    expect(latestRequest?.adjustments.components[0]?.weight).toBe(0.8);
  });

  it("blocks invalid client input immediately without sending it to the preview API", async () => {
    const client = await renderReadyWorkbench();
    const previousCallCount = client.preview.mock.calls.length;

    fireEvent.change(overallWeightInput(), { target: { value: "-1" } });

    expect(
      (await screen.findAllByText("Weight must be a finite, nonnegative number.")).length,
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

    fireEvent.change(overallWeightInput(), { target: { value: "0.7" } });
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
    expect(overallWeightInput().value).toBe("0.6");
    expect(client.preview.mock.calls.at(-1)?.[0].adjustments.components).toEqual([]);
    expect(
      (screen.getByRole("button", { name: "Reset all" }) as HTMLButtonElement).disabled,
    ).toBe(true);

    previousCallCount = client.preview.mock.calls.length;
    fireEvent.change(overallWeightInput(), { target: { value: "0.75" } });
    await waitForNextPreview(client, previousCallCount);
    previousCallCount = client.preview.mock.calls.length;
    fireEvent.click(screen.getByRole("button", { name: "Reset all" }));
    await waitForNextPreview(client, previousCallCount);
    expect(overallWeightInput().value).toBe("0.6");
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
    fireEvent.change(overallWeightInput(), { target: { value: "0.75" } });
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

  it("searches by a partial name and pins and unpins a player without replacing tier samples", async () => {
    const client = await renderReadyWorkbench();

    fireEvent.change(screen.getByRole("searchbox", { name: "Player search" }), {
      target: { value: "Spec" },
    });
    expect(await screen.findByText("Bench Specialist", {}, { timeout: 1_500 })).toBeTruthy();
    expect(client.searchPlayers).toHaveBeenCalledWith(
      "Spec",
      expect.objectContaining({ limit: 10, signal: expect.any(AbortSignal) }),
    );

    fireEvent.click(screen.getByRole("button", { name: "Pin Bench Specialist" }));
    expect(
      await screen.findByRole("heading", { name: "Session pins" }, { timeout: 2_500 }),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: "Unpin Bench Specialist" })).toBeTruthy();
    expect(
      await screen.findByRole(
        "heading",
        { name: "Superstar · 90–99" },
        { timeout: 2_500 },
      ),
    ).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Unpin Bench Specialist" }));
    await waitFor(() => {
      expect(screen.queryByRole("heading", { name: "Session pins" })).toBeNull();
    });
    expect(
      await screen.findByRole(
        "heading",
        { name: "Superstar · 90–99" },
        { timeout: 2_500 },
      ),
    ).toBeTruthy();
  });

  it("clears prior comparison results and labels an authoritative preview failure", async () => {
    const client = await renderReadyWorkbench();
    expect(screen.getByRole("region", { name: "Superstar · 90–99 player comparison" })).toBeTruthy();
    client.previewHandler = async () => {
      throw new Error("preview service exploded");
    };

    fireEvent.change(overallWeightInput(), { target: { value: "0.7" } });

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
  });
});
