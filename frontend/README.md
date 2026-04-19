# Frontend Package

## Purpose
The Single Page Application (SPA) providing the user interface. Built with React, TypeScript, Tailwind CSS, and powered by Vite.

## Patterns
- Fetch wrapper `api.ts` must be used for ALL API requests instead of `fetch` or `axios`.
- Components in `pages/` shouldn't do complex layout; they map directly to routes.
- Types fetched from the backend must use types imported from the `shared` workspace.

## Gotchas
- Do not use absolute URLs like `http://localhost:3001` in code. Use `/api/` and Vite's proxy will handle it during development.
