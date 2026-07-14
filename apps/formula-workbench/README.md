# Formula workbench

This application contains an independently runnable React and TypeScript formula-design client and
the Python formula preview API. The client inspects the active declarative formula and authoritative
player explanations, previews supported edits, compares players across talent tiers, and exports a
validated formula proposal without writing active configuration.

```bash
npm install
npm run workbench:test
npm run workbench:build
```

Run the API after a local version 2 reference package exists, then start the Vite client in a second
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

The default comparison shows three highest-ranked eligible players from each populated talent tier.
A designer can search the fixed cohort and add up to ten session-only pins, inspect calculation
inputs and contributions, and preview changes to existing component weights, directions, rating
anchors, and the proposed formula version. Preview requests are debounced and superseded requests
are cancelled. Context mismatches invalidate the view rather than mixing package, formula, or season
state.

The API returns the exact validated full formula document used for each successful preview. Export
downloads that JSON for use with `roster-generator generate --formula`; it does not persist or
activate it. Reloading clears edits and pins. Authentication, named sessions, arbitrary metric or
expression editing, deployment, and production hosting remain out of scope. See the
[API README](api/README.md) for the complete contract, bounds, and no-write behavior.
