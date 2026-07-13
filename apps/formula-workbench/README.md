# Formula workbench

This is the independently runnable React and TypeScript boundary for the planned formula workbench.
It currently renders a static status shell and deliberately contains no player data, API calls,
formula calculations, search, editing, or persistence.

```bash
npm install
npm run workbench:dev
npm run workbench:test
npm run workbench:build
```

The shared Python attribute engine remains authoritative for calculations. Formula preview API
behavior is planned in EPIC-05, and inspection and editing behavior are planned in EPIC-06.
