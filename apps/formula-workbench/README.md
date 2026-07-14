# Formula workbench

This application contains an independently runnable React and TypeScript client boundary and the
Python formula preview API. The React client still renders a static status shell and deliberately
contains no player data, API calls, formula calculations, search, editing, or persistence until
EPIC-06.

```bash
npm install
npm run workbench:dev
npm run workbench:test
npm run workbench:build
```

The in-progress US-010 API can be run separately after a local version 2 reference package exists:

```bash
formula-preview-api --config apps/formula-workbench/api/config/default.yaml
# or: make formula-api
```

It exposes read-only `/api/v1` inspection, player, and temporary preview endpoints while the shared
Python attribute engine remains authoritative for every calculation. See the
[API README](api/README.md) for its versioned contract, configured bounds, and no-write behavior.
React inspection and editing behavior remain planned in EPIC-06.
