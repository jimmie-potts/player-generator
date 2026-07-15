import { identifierLabel } from "../domain/format";
import { SectionHelp } from "./SectionHelp";

export type AttributeRatingState =
  | "available"
  | "excluded"
  | "failure"
  | "missing"
  | "unsupported";

export interface AttributeSidebarRow {
  name: string;
  label?: string;
  rating?: number | null;
  ratingState?: AttributeRatingState;
  dirty?: boolean;
}

export interface AttributeSidebarProps {
  attributes: readonly AttributeSidebarRow[];
  selectedAttribute: string | null;
  onSelect: (attributeName: string) => void;
  disabled?: boolean;
}

const RATING_STATE_LABELS: Record<Exclude<AttributeRatingState, "available">, string> = {
  excluded: "Excluded",
  failure: "Failed",
  missing: "Missing",
  unsupported: "Unsupported",
};

export function AttributeSidebar({
  attributes,
  selectedAttribute,
  onSelect,
  disabled = false,
}: AttributeSidebarProps) {
  return (
    <nav className="attribute-sidebar" aria-label="Player attributes">
      <div className="panel-heading attribute-sidebar__heading">
        <div>
          <p className="eyebrow">Rating model</p>
          <h2>Attributes</h2>
        </div>
        <span className="count-badge">{attributes.length}</span>
      </div>
      <SectionHelp title="How attribute ratings update" className="attribute-sidebar__help">
        <p>
          Select an attribute to edit its component allocation and inspect the selected player’s
          calculation. Each displayed rating comes from the latest validated server preview when
          available, otherwise from the active-formula baseline. Changed shared scales and
          attributes are marked; missing or excluded values are never estimated in the browser.
        </p>
      </SectionHelp>

      {attributes.length ? (
        <ul className="attribute-sidebar__list">
          {attributes.map((attribute) => {
            const selected = attribute.name === selectedAttribute;
            const state = attribute.ratingState ?? "available";
            const hasRating = state === "available" && typeof attribute.rating === "number";
            const stateLabel = state === "available" ? null : RATING_STATE_LABELS[state];

            return (
              <li key={attribute.name}>
                <button
                  className={`attribute-nav-item${selected ? " attribute-nav-item--selected" : ""}`}
                  type="button"
                  onClick={() => onSelect(attribute.name)}
                  aria-current={selected ? "page" : undefined}
                  disabled={disabled}
                >
                  <span className="attribute-nav-item__name">
                    {attribute.label ?? identifierLabel(attribute.name)}
                    {attribute.dirty ? (
                      <span className="dirty-marker" title="Session changes" aria-label="Changed">
                        ●
                      </span>
                    ) : null}
                  </span>
                  {hasRating ? (
                    <strong className="rating-chip" aria-label={`Rating ${attribute.rating}`}>
                      {attribute.rating}
                    </strong>
                  ) : stateLabel ? (
                    <span className={`value-state value-state--${state}`}>{stateLabel}</span>
                  ) : (
                    <span className="rating-chip rating-chip--empty" aria-label="Rating unavailable">
                      —
                    </span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="panel-empty">No supported attributes were returned.</p>
      )}
    </nav>
  );
}
