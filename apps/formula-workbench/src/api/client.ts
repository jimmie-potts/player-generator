import type {
  BaselineResponse,
  ErrorField,
  ErrorResponse,
  FormulaResponse,
  MetricsResponse,
  PlayerDetailResponse,
  PreviewRequest,
  PreviewResponse,
  SearchResponse,
  TierRepresentativesResponse,
} from "./types";

export interface RequestOptions {
  signal?: AbortSignal;
}

export interface PlayerListOptions extends RequestOptions {
  limit?: number;
  pinnedPlayerIds?: readonly string[];
}

export interface SearchOptions extends RequestOptions {
  limit?: number;
}

export interface RepresentativeOptions extends RequestOptions {
  perTier?: number;
}

export interface PreviewApiClient {
  getFormula(options?: RequestOptions): Promise<FormulaResponse>;
  getMetrics(options?: RequestOptions): Promise<MetricsResponse>;
  getPlayers(options?: PlayerListOptions): Promise<BaselineResponse>;
  getTierRepresentatives(
    options?: RepresentativeOptions,
  ): Promise<TierRepresentativesResponse>;
  searchPlayers(query: string, options?: SearchOptions): Promise<SearchResponse>;
  getPlayer(playerId: string, options?: RequestOptions): Promise<PlayerDetailResponse>;
  preview(request: PreviewRequest, options?: RequestOptions): Promise<PreviewResponse>;
}

export interface PreviewApiClientOptions {
  baseUrl?: string;
  fetchImplementation?: typeof fetch;
}

export class PreviewApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fields: ErrorField[];

  constructor(status: number, code: string, message: string, fields: ErrorField[] = []) {
    super(message);
    this.name = "PreviewApiError";
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

function normalizedBaseUrl(value: string): string {
  const normalized = value.trim().replace(/\/+$/, "");
  if (!normalized) {
    throw new Error("Preview API base URL must not be empty.");
  }
  return normalized;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isErrorResponse(value: unknown): value is ErrorResponse {
  if (!isRecord(value) || !isRecord(value.error)) {
    return false;
  }
  const error = value.error;
  return (
    typeof error.code === "string" &&
    typeof error.message === "string" &&
    Array.isArray(error.fields)
  );
}

async function responsePayload(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch (error) {
    if (isAbortError(error)) {
      throw error;
    }
    return null;
  }
}

export function isAbortError(error: unknown): boolean {
  return (
    (error instanceof DOMException && error.name === "AbortError") ||
    (isRecord(error) && error.name === "AbortError")
  );
}

export function createPreviewApiClient(
  options: PreviewApiClientOptions = {},
): PreviewApiClient {
  const baseUrl = normalizedBaseUrl(
    options.baseUrl ?? import.meta.env.VITE_PREVIEW_API_URL ?? "/api/v1",
  );
  const fetchImplementation = options.fetchImplementation ?? fetch;

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    let response: Response;
    try {
      response = await fetchImplementation(`${baseUrl}${path}`, {
        ...init,
        headers: {
          Accept: "application/json",
          ...init.headers,
        },
      });
    } catch (error) {
      if (isAbortError(error)) {
        throw error;
      }
      throw new PreviewApiError(
        0,
        "network_error",
        error instanceof Error ? error.message : "Unable to reach the formula preview API.",
      );
    }

    const payload = await responsePayload(response);
    if (!response.ok) {
      if (isErrorResponse(payload)) {
        throw new PreviewApiError(
          response.status,
          payload.error.code,
          payload.error.message,
          payload.error.fields,
        );
      }
      throw new PreviewApiError(
        response.status,
        "http_error",
        `Formula preview API request failed with status ${response.status}.`,
      );
    }
    if (payload === null) {
      throw new PreviewApiError(
        response.status,
        "invalid_response",
        "Formula preview API returned an invalid JSON response.",
      );
    }
    return payload as T;
  }

  return {
    getFormula: (requestOptions = {}) =>
      request<FormulaResponse>("/formula", { signal: requestOptions.signal }),

    getMetrics: (requestOptions = {}) =>
      request<MetricsResponse>("/metrics", { signal: requestOptions.signal }),

    getPlayers: (requestOptions = {}) => {
      const parameters = new URLSearchParams();
      if (requestOptions.limit !== undefined) {
        parameters.set("limit", String(requestOptions.limit));
      }
      for (const playerId of requestOptions.pinnedPlayerIds ?? []) {
        parameters.append("pinnedPlayerId", playerId);
      }
      const query = parameters.size ? `?${parameters.toString()}` : "";
      return request<BaselineResponse>(`/players${query}`, {
        signal: requestOptions.signal,
      });
    },

    getTierRepresentatives: (requestOptions = {}) => {
      const parameters = new URLSearchParams();
      if (requestOptions.perTier !== undefined) {
        parameters.set("perTier", String(requestOptions.perTier));
      }
      const query = parameters.size ? `?${parameters.toString()}` : "";
      return request<TierRepresentativesResponse>(`/players/representatives${query}`, {
        signal: requestOptions.signal,
      });
    },

    searchPlayers: (query, requestOptions = {}) => {
      const parameters = new URLSearchParams({ q: query });
      if (requestOptions.limit !== undefined) {
        parameters.set("limit", String(requestOptions.limit));
      }
      return request<SearchResponse>(`/players/search?${parameters.toString()}`, {
        signal: requestOptions.signal,
      });
    },

    getPlayer: (playerId, requestOptions = {}) =>
      request<PlayerDetailResponse>(`/players/${encodeURIComponent(playerId)}`, {
        signal: requestOptions.signal,
      }),

    preview: (previewRequest, requestOptions = {}) =>
      request<PreviewResponse>("/previews", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(previewRequest),
        signal: requestOptions.signal,
      }),
  };
}

export const previewApi = createPreviewApiClient();
