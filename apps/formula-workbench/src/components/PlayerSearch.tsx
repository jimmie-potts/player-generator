import type { FormEvent } from "react";

import type { SearchHit } from "../api/types";
import { formatNumber } from "../domain/format";
import { SectionHelp } from "./SectionHelp";
import { StatusPanel } from "./StatusPanel";

export interface PlayerSearchProps {
  query: string;
  results: readonly SearchHit[];
  selectedPlayerIds: readonly string[];
  loading?: boolean;
  error?: string | null;
  maxPlayers?: number;
  disabled?: boolean;
  onQueryChange: (query: string) => void;
  onSubmit: () => void;
  onAdd: (player: SearchHit) => void;
}

export function PlayerSearch({
  query,
  results,
  selectedPlayerIds,
  loading = false,
  error = null,
  maxPlayers = 25,
  disabled = false,
  onQueryChange,
  onSubmit,
  onAdd,
}: PlayerSearchProps) {
  const selected = new Set(selectedPlayerIds);
  const atCapacity = selected.size >= maxPlayers;
  const hasQuery = Boolean(query.trim());

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <section className="player-search workbench-panel" aria-labelledby="player-search-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Custom comparison</p>
          <h2 id="player-search-title">Build a custom list</h2>
          <p>
            Search a partial display name or exact stable player ID, then add up to {maxPlayers}
            players for a focused comparison.
          </p>
        </div>
        <span className="capacity-badge" aria-live="polite">
          {selected.size}/{maxPlayers} selected
        </span>
      </div>
      <SectionHelp title="How search and custom lists work">
        <p>
          Search the configured season by a partial display name or an exact stable player ID, then
          add any result to this browser session&apos;s custom comparison list. The list can contain
          up to {maxPlayers} unique players. It never modifies the active formula, reference
          package, or server and disappears when the page session ends.
        </p>
      </SectionHelp>

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
          Your custom list lives only in this browser session and never alters reference data.
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
            const isSelected = selected.has(player.playerId);
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
                  onClick={() => onAdd(player)}
                  disabled={disabled || isSelected || atCapacity}
                  aria-label={
                    isSelected
                      ? `${player.displayName} is in the custom list`
                      : atCapacity
                        ? `Custom list is full; cannot add ${player.displayName}`
                        : `Add ${player.displayName} to custom list`
                  }
                >
                  {isSelected ? "Added" : atCapacity ? "List full" : "Add player"}
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
