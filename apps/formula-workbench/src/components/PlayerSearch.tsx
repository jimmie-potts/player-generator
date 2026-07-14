import type { FormEvent } from "react";

import type { SearchHit } from "../api/types";
import { formatNumber } from "../domain/format";
import { StatusPanel } from "./StatusPanel";

export interface PlayerSearchProps {
  query: string;
  results: readonly SearchHit[];
  pinnedPlayerIds: readonly string[];
  loading?: boolean;
  error?: string | null;
  maxPins?: number;
  disabled?: boolean;
  onQueryChange: (query: string) => void;
  onSubmit: () => void;
  onPin: (player: SearchHit) => void;
}

export function PlayerSearch({
  query,
  results,
  pinnedPlayerIds,
  loading = false,
  error = null,
  maxPins = 10,
  disabled = false,
  onQueryChange,
  onSubmit,
  onPin,
}: PlayerSearchProps) {
  const pinned = new Set(pinnedPlayerIds);
  const atCapacity = pinned.size >= maxPins;
  const hasQuery = Boolean(query.trim());

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <section className="player-search workbench-panel" aria-labelledby="player-search-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Session roster</p>
          <h2 id="player-search-title">Find and pin players</h2>
          <p>Search a partial display name or exact stable player ID.</p>
        </div>
        <span className="capacity-badge" aria-live="polite">
          {pinned.size}/{maxPins} pinned
        </span>
      </div>

      <form className="search-form" role="search" onSubmit={submit}>
        <label htmlFor="player-search-query">Player search</label>
        <div className="search-form__controls">
          <input
            id="player-search-query"
            name="playerSearch"
            type="search"
            autoComplete="off"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="e.g. Duren or player-001"
            disabled={disabled}
            aria-describedby="player-search-help"
          />
          <button
            className="button button--primary"
            type="submit"
            disabled={disabled || loading || !hasQuery}
          >
            {loading ? "Searching…" : "Search"}
          </button>
        </div>
        <small id="player-search-help">
          Pins live only in this browser session and never alter reference data.
        </small>
      </form>

      {error ? (
        <StatusPanel title="Player search failed" tone="error" compact>
          {error}
        </StatusPanel>
      ) : loading ? (
        <StatusPanel title="Searching the loaded cohort" tone="loading" compact>
          Matching normalized names and stable IDs.
        </StatusPanel>
      ) : hasQuery && !results.length ? (
        <StatusPanel title="No matching players" tone="empty" compact>
          Try a shorter name fragment or verify the stable player ID.
        </StatusPanel>
      ) : results.length ? (
        <ul className="search-results" aria-label="Player search results">
          {results.map((player) => {
            const isPinned = pinned.has(player.playerId);
            return (
              <li key={player.playerId}>
                <div className="search-result__identity">
                  <strong>{player.displayName}</strong>
                  <span>{player.playerId}</span>
                </div>
                <dl className="search-result__facts">
                  <div>
                    <dt>OVR</dt>
                    <dd>{formatNumber(player.overall)}</dd>
                  </div>
                  <div>
                    <dt>Rank</dt>
                    <dd>{player.baselineRank ?? "—"}</dd>
                  </div>
                </dl>
                <button
                  className="button button--small button--secondary"
                  type="button"
                  onClick={() => onPin(player)}
                  disabled={disabled || isPinned || atCapacity}
                  aria-label={
                    isPinned
                      ? `${player.displayName} is pinned`
                      : atCapacity
                        ? `Pin limit reached; cannot pin ${player.displayName}`
                        : `Pin ${player.displayName}`
                  }
                >
                  {isPinned ? "Pinned" : atCapacity ? "Limit reached" : "Pin player"}
                </button>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="player-search__prompt">Search results will appear here.</p>
      )}
    </section>
  );
}
