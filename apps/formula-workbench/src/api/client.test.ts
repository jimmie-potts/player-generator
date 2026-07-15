import { describe, expect, it, vi } from "vitest";

import { createPreviewApiClient, PreviewApiError } from "./client";
import type { PreviewRequest } from "./types";

type FetchImplementation = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Promise<Response>;

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("preview API client", () => {
  it("uses relative v1 routes, encodes search, and repeats pin parameters", async () => {
    const fetchMock = vi.fn<FetchImplementation>(async () => jsonResponse({ players: [] }));
    const client = createPreviewApiClient({
      baseUrl: "/api/v1/",
      fetchImplementation: fetchMock as typeof fetch,
    });

    await client.searchPlayers("José Example / 42", { limit: 7 });
    await client.getPlayers({
      limit: 15,
      pinnedPlayerIds: ["player/a", "player-b"],
    });
    await client.getTierRepresentatives({ perTier: 3 });

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/api/v1/players/search?q=Jos%C3%A9+Example+%2F+42&limit=7",
    );
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      "/api/v1/players?limit=15&pinnedPlayerId=player%2Fa&pinnedPlayerId=player-b",
    );
    expect(fetchMock.mock.calls[2]?.[0]).toBe(
      "/api/v1/players/representatives?perTier=3",
    );
  });

  it("posts the complete preview request and forwards its AbortSignal", async () => {
    const fetchMock = vi.fn<FetchImplementation>(async () => jsonResponse({ players: [] }));
    const client = createPreviewApiClient({
      baseUrl: "https://preview.example/api/v1",
      fetchImplementation: fetchMock as typeof fetch,
    });
    const controller = new AbortController();
    const request: PreviewRequest = {
      apiVersion: "1",
      referencePackageHash: "a".repeat(64),
      formulaVersion: "1.0.0",
      formulaDocumentHash: "b".repeat(64),
      season: 2026,
      selectedAttribute: "overall",
      selectedPlayerIds: ["player-one"],
      adjustments: {
        formulaVersion: "1.1.0-proposal",
        components: [
          {
            attribute: "overall",
            metric: "impact",
            weight: 0.5,
          },
        ],
        ratingScales: [],
      },
    };

    await client.preview(request, { signal: controller.signal });

    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("https://preview.example/api/v1/previews");
    expect(init).toMatchObject({
      method: "POST",
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
    });
    expect(JSON.parse(String(init?.body))).toEqual(request);
  });

  it("turns the structured API error contract into a typed error", async () => {
    const fetchMock = vi.fn<FetchImplementation>(async () =>
      jsonResponse(
        {
          error: {
            code: "invalid_formula",
            message: "The proposal is invalid.",
            fields: [
              {
                path: "adjustments.formulaVersion",
                code: "duplicate_version",
                message: "Choose a new formula version.",
              },
            ],
          },
        },
        422,
      ),
    );
    const client = createPreviewApiClient({
      baseUrl: "/api/v1",
      fetchImplementation: fetchMock as typeof fetch,
    });

    await expect(client.getFormula()).rejects.toEqual(
      expect.objectContaining<Partial<PreviewApiError>>({
        name: "PreviewApiError",
        status: 422,
        code: "invalid_formula",
        message: "The proposal is invalid.",
        fields: [
          {
            path: "adjustments.formulaVersion",
            code: "duplicate_version",
            message: "Choose a new formula version.",
          },
        ],
      }),
    );
  });

  it("does not convert a superseded request abort into an API failure", async () => {
    const fetchMock = vi.fn<FetchImplementation>(
      async (_input, init) =>
        await new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener(
            "abort",
            () => reject(new DOMException("Superseded", "AbortError")),
            { once: true },
          );
        }),
    );
    const client = createPreviewApiClient({
      baseUrl: "/api/v1",
      fetchImplementation: fetchMock as typeof fetch,
    });
    const controller = new AbortController();

    const pending = client.searchPlayers("first edit", { signal: controller.signal });
    controller.abort();

    await expect(pending).rejects.toMatchObject({ name: "AbortError" });
    await expect(pending).rejects.not.toBeInstanceOf(PreviewApiError);
  });

  it("does not convert an abort while reading the response body into invalid JSON", async () => {
    const abortError = new DOMException("Superseded", "AbortError");
    const response = {
      json: vi.fn().mockRejectedValue(abortError),
      ok: true,
      status: 200,
    } as unknown as Response;
    const client = createPreviewApiClient({
      baseUrl: "/api/v1",
      fetchImplementation: vi.fn<FetchImplementation>(async () => response) as typeof fetch,
    });

    const pending = client.getMetrics();

    await expect(pending).rejects.toBe(abortError);
    await expect(pending).rejects.not.toBeInstanceOf(PreviewApiError);
  });

  it("reports non-contract and invalid JSON responses without leaking stale data", async () => {
    const httpFailure = createPreviewApiClient({
      baseUrl: "/api/v1",
      fetchImplementation: vi.fn<FetchImplementation>(async () =>
        jsonResponse({ detail: "proxy failure" }, 502),
      ) as typeof fetch,
    });
    const invalidJson = createPreviewApiClient({
      baseUrl: "/api/v1",
      fetchImplementation: vi.fn<FetchImplementation>(async () =>
        new Response("not json", { status: 200 }),
      ) as typeof fetch,
    });

    await expect(httpFailure.getMetrics()).rejects.toMatchObject({
      status: 502,
      code: "http_error",
    });
    await expect(invalidJson.getMetrics()).rejects.toMatchObject({
      status: 200,
      code: "invalid_response",
    });
  });
});
