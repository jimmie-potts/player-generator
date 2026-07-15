# Formula workbench

This application contains an independently runnable React and TypeScript formula-design client and
the Python formula preview API. The client inspects the active declarative formula and authoritative
player explanations, previews supported edits, compares tier, Top 25, or custom player sets, and
exports a validated formula proposal without writing active configuration.

```bash
npm install
npm run workbench:test
npm run workbench:build
```

Run the API after a local version 1 reference profile exists, then start the Vite client in a second
terminal:

```bash
# terminal 1
formula-preview-api --config apps/formula-workbench/api/config/default.yaml
# or: make formula-api

# terminal 2
npm run workbench:dev
```

Vite proxies `/api` to `http://127.0.0.1:8000` during local development. The client loads formula,
metric, representative-player, search, detail, and preview data through that versioned boundary. It
never evaluates rating formulas in TypeScript.

Player Comparison has three mutually exclusive views. `Tier sample` is the default and shows three
highest-ranked eligible players from each populated talent tier, adjustable from one through three
per tier. `Top 25` shows a fixed baseline-overall list whose membership and order do not reshuffle
after temporary edits. `Custom list` searches the configured reference cohort and holds up to 25
unique players for the current page session. Only the active view's player IDs request detailed
preview results; ratings, percentiles, and ranks are still calculated by the API over the complete
fixed season cohort. No view may exceed the API's 25-player detail bound. If an unusually large
talent-tier model makes the chosen per-tier sample exceed that bound, the workbench blocks the
preview and asks the designer to reduce the per-tier count or choose another view. A designer can
inspect calculation inputs and contributions and preview changes to existing component weights,
directions, rating anchors, and the proposed formula version. Preview requests are debounced and
superseded requests are cancelled. Context mismatches invalidate the view rather than mixing
package, formula, or season state.

Comparison errors include recovery where the user can act. Starting another player search or
removing a custom player clears an earlier custom-list add error so fresh results remain available.
Pending add responses are scoped to the interaction that started them, so a late failure or success
cannot hide results or erase a newer query.
If the active Top 25 list fails to load, its error panel offers `Retry Top 25` without requiring a
mode switch. Player-selection controls announce the display name followed by a human-readable tier,
with explicit separation for assistive technology.

Changed authoritative preview values are highlighted wherever the designer evaluates impact. Green
with an upward arrow or positive signed value marks an outcome increase; red with a downward arrow
or negative signed value marks a decrease. Rank movement uses green for movement toward rank 1 and
red for movement away. A normalized-weight change is blue because it is an allocation shift rather
than an inherently positive or negative outcome. The selected-player summary, component breakdown,
and player-comparison table always pair color with visible directional text or symbols, and only
display values returned by the preview API.

On desktop, the Formula and Authoritative Explanation panes have matching viewport-bounded heights.
Formula content scrolls independently, while the selected player's rating summary remains visible
and secondary calculation details can be expanded as needed. Narrow layouts restore normal document
flow instead of retaining nested scrolling or sticky positioning. Expandable guidance describes each
major section, and the Glossary view combines stable workbench definitions with a catalog generated
from the formula and metric metadata loaded from the API. Switching views does not persist or deploy
session state outside the browser, and it does not clear the current in-memory edits, comparison
mode, or custom list.

Each component weight uses a native range slider in one-percentage-point steps. A stacked allocation
bar summarizes all component shares for the selected attribute; it is explanatory rather than a
second editing control. Moving one slider reserves its requested integer percentage and distributes
the remaining units proportionally across the other current weights. The client floors each quota,
awards leftover units by largest fractional remainder, and uses formula document order to break
ties. If every other current weight is zero, it uses baseline proportions and then equal shares as
deterministic fallbacks. A single component remains fixed at 100%, and every edit leaves the selected
attribute at exactly `1.00` total weight.

The shared formula contract also accepts untouched finite nonnegative component weights with any
positive sum because the engine normalizes them. The workbench presents those source weights as
normalized shares in the sliders, stacked bar, and glossary without changing the loaded document.
The exact `1.00` authoring rule begins when the designer moves a component slider.

That exact-allocation behavior is a browser authoring policy, not rating logic. The API validates the
complete temporary formula, and the shared Python attribute engine remains solely responsible for
normalizing supported inputs and calculating percentiles, contributions, ratings, tiers, and ranks.

The API returns the exact validated full formula document used for each successful preview. Export
downloads that JSON for use with `roster-generator generate --formula`; it does not persist or
activate it. Reloading clears edits and the custom list. Authentication, named sessions, arbitrary
metric or expression editing, deployment, and production hosting remain out of scope. See the
[API README](api/README.md) for the complete contract, bounds, and no-write behavior.
