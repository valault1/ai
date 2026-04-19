# Backend Package

## Purpose
The API that serves the frontend. Written in Express.js + better-sqlite3 but executing entirely using Bun.

## Patterns
- All routes reside in `src/routes/[resource].ts` and are aggregated in `src/routes/index.ts`.
- Types should be exclusively sourced from the `shared` workspace — do not redefine types here.
- SQLite is used seamlessly using built-in `bun`.

## Gotchas
- Since SQLite runs synchronously here, do not use `async`/`await` on db calls. This ensures maximal determinism.
- Make sure to export your routes in the aggregator file.
