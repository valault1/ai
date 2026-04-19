# Project: Agent Full-Stack Native Bun App

## What This Is
A fully functioning, robust, agent-maintained local full-stack application built using native Bun for blazing speed and minimal context surface area.

## Architecture
- **Frontend**: React + TypeScript + Tailwind, served by Vite on :5173
- **Backend**: Bun + Express + TypeScript + SQLite on :3002
- **Shared types**: `shared/src/types/` — the contract between frontend and backend
- **Database**: SQLite at `backend/data/app.db` (via bun:sqlite)

## Commands
- `bun run dev` — starts both frontend and backend with hot reload
- `bun run build` — full production build
- `bun run typecheck` — check all TypeScript errors
- `bun run lint` — lint all files

## Conventions (YOU MUST FOLLOW THESE)

### When adding a new API endpoint:
1. Add request/response types to `shared/src/types/api.ts`
2. If new DB table needed, create a migration in `backend/src/db/migrations/`
3. Create or update the route file in `backend/src/routes/`
4. Register the route in `backend/src/routes/index.ts`
5. Update `docs/api.md` with the new endpoint
6. Use the typed `api` client in frontend code — never raw `fetch`

### When adding a new frontend page:
1. Create the page component in `frontend/src/pages/`
2. Add the route to `frontend/src/App.tsx`
3. Use existing UI components from `frontend/src/components/ui/` where possible

### When adding a new UI component:
1. Reusable/generic → `frontend/src/components/ui/`
2. Feature-specific → `frontend/src/components/[feature]/`
3. Always use Tailwind utility classes, never inline styles or CSS files
4. **CRITICAL FRONTEND DESIGN RULE**: Before making UI design decisions or updating the frontend, you MUST read `frontend/DESIGN_PHILOSOPHY.md` to ensure the "Linear/Modern" aesthetic is preserved.

### When making an architectural decision:
1. Create a new file in `docs/decisions/` using the template in `_TEMPLATE.md`
2. Number it sequentially (e.g., `002-auth-approach.md`)
3. Update this file if the decision changes project-wide conventions

### General rules:
- All functions and components must have JSDoc comments explaining their purpose
- All route handlers must validate input before processing
- Never commit `backend/data/app.db` — it's gitignored
- Run `bun run typecheck` before considering any change complete

## Current State
Initial scaffold complete. Everything is natively typed to Bun Workspaces. Built-in bun:sqlite deployed. 

## File Index
- `docs/decisions/` — Architecture Decision Records (read before making big changes)
- `docs/api.md` — Complete API endpoint documentation
- `shared/src/types/` — All TypeScript types shared between frontend and backend
- `backend/README.md` — Backend-specific patterns and conventions
- `frontend/README.md` — Frontend-specific patterns and conventions
