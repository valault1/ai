# Shared Package

## Purpose
This package acts as the strict contract between the `frontend` and `backend` workspaces. It defines:
- **Models:** The exact shape of data returned from the SQLite database.
- **API Types:** The strict request and response shapes for every endpoint.

## Patterns
- Keep models simple and exact matches to DB schemas. Use `snake_case` exactly as they appear in the database to avoid hydration mappings.
- Use `[Method][Resource][Request|Response]` naming convention.

## Gotchas
- Do NOT import things from `frontend` or `backend` here. `shared` is fully independent.
- Run `bun run typecheck` in the root when changing types here to ensure you didn't break the frontend or backend.
