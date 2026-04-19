# System Design: Agent-Maintained Local Full-Stack Application

## 1. Design Principles

Every choice in this document optimizes for one thing: **reliability when AI coding agents are the primary developers.** That means choosing technologies with the deepest training-data coverage, the simplest mental models, the fewest "gotcha" failure modes, and explicit, discoverable context at every level of the project.

---

## 2. Technology Choices & Rationale

### 2.1 Frontend: Vite + React + TypeScript + Tailwind CSS

**React** is the clear winner for agent-written frontends. It has the largest representation in LLM training data by a wide margin, the most StackOverflow answers, the most blog posts, and the most open-source examples. Agents produce significantly more reliable React code than Svelte, Vue, or Solid — not because those are worse frameworks, but because the training signal is stronger.

**Vite** over Create React App (deprecated) or Next.js. Next.js adds server-side rendering, file-based routing, middleware, and server actions — none of which we need for a locally-hosted app, and all of which create surface area for agent mistakes. Vite is fast, minimal, and does one thing well: bundle a client-side app with hot module replacement.

**TypeScript** is non-negotiable. Agents make fewer errors when types constrain them. Type errors caught at build time are far cheaper than runtime bugs an agent has to debug. Use strict mode (`"strict": true` in tsconfig).

**Tailwind CSS** over CSS modules, styled-components, or plain CSS. Tailwind keeps styling co-located with markup (no file-switching), uses a finite vocabulary of utility classes that agents have memorized, and eliminates naming decisions that cause agents to drift in inconsistent directions.

### 2.2 Backend: Bun + Express + TypeScript + SQLite (bun:sqlite)

**Same language as frontend (TypeScript everywhere).** This is the single most important backend decision. When agents work on a full-stack codebase, sharing one language eliminates an entire class of context-switching errors. Shared type definitions between frontend and backend become trivial.

**Express** over Fastify, Hono, or Koa. Express has been the default Node.js server framework for over a decade. Agents have seen more Express code than every other Node framework combined. It's not the fastest or the most modern, but agents almost never produce incorrect Express code. That reliability matters more than performance for a local application, and Express runs flawlessly on Bun.

**Built-in SQLite (bun:sqlite)** over PostgreSQL, MySQL, Prisma, Drizzle, or JSON files:

- **Why not Postgres/MySQL?** They require a running database server. For a locally-hosted app, that's unnecessary operational complexity. SQLite is an embedded database — it's just a file.
- **Why not Prisma/Drizzle?** ORMs add a layer of abstraction, a schema migration system, and generated code. For a small dataset (hundreds to thousands of rows), raw SQL is simpler, more transparent, and less likely to confuse agents. Agents know SQL extremely well.
- **Why not JSON files?** They work for trivially small datasets, but have no query capability, no concurrency safety, and no schema enforcement. SQLite gives us all of that for nearly zero additional complexity.
- **Why bun:sqlite specifically?** Bun has a highly optimized, native, synchronous SQLite engine built directly into the runtime. It requires zero configuration, no external dependencies, and no native C bindings to compile (minimizing environmental "gotcha" errors for agents). Its synchronous API mirrors `better-sqlite3`, which means agents produce fewer bugs because they don't have to manage async/await for simple database queries.

### 2.3 Monorepo Structure: Bun Workspaces

Use Bun workspaces (built into Bun, using the standard package.json `"workspaces"` array) to manage frontend, backend, and a shared types package. This avoids Turborepo, Nx, Lerna, or any other monorepo tool — agents understand plain workspaces, and Bun automatically handles cross-workspace linking with blazing fast installations.

---

## 3. Project Structure

```
project-root/
├── agents.md                          # THE entry point for all AI agents (see §5)
├── package.json                       # Workspace root
├── tsconfig.base.json                 # Shared TS config
│
├── docs/
│   ├── decisions/                     # Architecture Decision Records
│   │   ├── 001-initial-stack.md
│   │   └── _TEMPLATE.md
│   └── api.md                         # API endpoint documentation
│
├── shared/
│   ├── package.json
│   ├── README.md
│   └── src/
│       └── types/
│           ├── index.ts               # Re-exports everything
│           ├── api.ts                  # Request/response types for every endpoint
│           └── models.ts              # Domain model types (match DB schema)
│
├── backend/
│   ├── package.json
│   ├── README.md                      # Backend-specific conventions & patterns
│   ├── tsconfig.json
│   ├── src/
│   │   ├── index.ts                   # Server entry point
│   │   ├── db/
│   │   │   ├── connection.ts          # SQLite connection singleton
│   │   │   ├── migrations/            # Numbered SQL migration files
│   │   │   │   └── 001-initial.sql
│   │   │   └── migrate.ts             # Simple migration runner
│   │   ├── routes/
│   │   │   ├── index.ts               # Route aggregator
│   │   │   └── [resource].ts          # One file per resource
│   │   └── middleware/
│   │       ├── errorHandler.ts
│   │       └── cors.ts
│   └── data/
│       └── app.db                     # SQLite database file (gitignored)
│
└── frontend/
    ├── package.json
    ├── README.md                      # Frontend-specific conventions & patterns
    ├── tsconfig.json
    ├── index.html
    ├── vite.config.ts
    └── src/
        ├── main.tsx                   # App entry point
        ├── App.tsx                    # Root component + routing
        ├── components/
        │   ├── ui/                    # Reusable primitives (Button, Input, Card, etc.)
        │   └── [feature]/             # Feature-grouped components
        ├── pages/                     # One component per route
        ├── hooks/                     # Custom React hooks
        ├── api/
        │   └── client.ts             # Fetch wrapper, typed to shared API types
        └── lib/
            └── utils.ts              # Pure utility functions
```

---

## 4. Implementation Details

### 4.1 Root package.json

```jsonc
{
  "name": "project-root",
  "private": true,
  "workspaces": ["shared", "backend", "frontend"],
  "scripts": {
    "dev": "bun --cwd backend run dev & bun --cwd frontend run dev",
    "build": "bun --cwd shared run build && bun --cwd backend run build && bun --cwd frontend run build",
    "lint": "eslint . --ext .ts,.tsx",
    "typecheck": "tsc --build"
  },
  "devDependencies": {
    "typescript": "^5.4.0",
    "eslint": "^8.0.0",
    "@typescript-eslint/eslint-plugin": "^7.0.0",
    "@typescript-eslint/parser": "^7.0.0"
  }
}
```

### 4.2 Shared Types Package

The shared package is the **contract** between frontend and backend. Every API endpoint must have its request and response types defined here. This is enforced by convention (documented in agents.md) and by TypeScript's type checker.

```typescript
// shared/src/types/models.ts
// Every database table gets a corresponding TypeScript interface.
// Field names match column names exactly (snake_case in DB, snake_case here too —
// keep it simple, don't add a mapping layer).

export interface ExampleItem {
  id: number;
  name: string;
  description: string | null;
  created_at: string;  // ISO 8601 — SQLite stores text, we parse on frontend if needed
  updated_at: string;
}
```

```typescript
// shared/src/types/api.ts
// One request/response pair per endpoint.
// Naming convention: [Method][Resource][Request|Response]

import type { ExampleItem } from './models';

export interface GetExampleItemsResponse {
  items: ExampleItem[];
  total: number;
}

export interface CreateExampleItemRequest {
  name: string;
  description?: string;
}

export interface CreateExampleItemResponse {
  item: ExampleItem;
}
```

### 4.3 Backend Patterns

#### Server Entry Point

```typescript
// backend/src/index.ts
import express from 'express';
import cors from 'cors';
import { runMigrations } from './db/migrate';
import { routes } from './routes';
import { errorHandler } from './middleware/errorHandler';

const app = express();
const PORT = process.env.PORT || 3002;

app.use(cors({ origin: 'http://localhost:5173' }));  // Vite's default port
app.use(express.json());

// Run migrations on startup
runMigrations();

// Mount all routes
app.use('/api', routes);

// Global error handler (must be last)
app.use(errorHandler);

app.listen(PORT, () => {
  console.log(`Backend running on http://localhost:${PORT}`);
});
```

#### Database Connection

```typescript
// backend/src/db/connection.ts
import { Database } from 'bun:sqlite';
import path from 'path';

const DB_PATH = path.join(__dirname, '../../data/app.db');

// Single connection, reused everywhere. bun:sqlite is synchronous
// and handles concurrent access within a single process fine.
const db = new Database(DB_PATH);

// Enable WAL mode for better read performance
db.exec('PRAGMA journal_mode = WAL;');
// Enable foreign keys (off by default in SQLite)
db.exec('PRAGMA foreign_keys = ON;');

export default db;
```

#### Migration Runner

```typescript
// backend/src/db/migrate.ts
import db from './connection';
import fs from 'fs';
import path from 'path';

export function runMigrations(): void {
  // Create migrations tracking table if it doesn't exist
  db.exec(`
    CREATE TABLE IF NOT EXISTS _migrations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE,
      applied_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
  `);

  const migrationsDir = path.join(__dirname, 'migrations');
  const files = fs.readdirSync(migrationsDir)
    .filter(f => f.endsWith('.sql'))
    .sort(); // Lexicographic sort — numbering prefix ensures correct order

  const applied = new Set(
    db.prepare('SELECT name FROM _migrations').all().map((r: any) => r.name)
  );

  for (const file of files) {
    if (!applied.has(file)) {
      const sql = fs.readFileSync(path.join(migrationsDir, file), 'utf-8');
      db.exec(sql);
      db.prepare('INSERT INTO _migrations (name) VALUES (?)').run(file);
      console.log(`Applied migration: ${file}`);
    }
  }
}
```

#### Route Pattern

Every resource gets one file. Each file exports an Express Router. The route aggregator mounts them all.

```typescript
// backend/src/routes/exampleItems.ts
import { Router } from 'express';
import db from '../db/connection';
import type {
  GetExampleItemsResponse,
  CreateExampleItemRequest,
  CreateExampleItemResponse,
} from '@shared/types/api';

const router = Router();

router.get('/', (req, res) => {
  const items = db.prepare('SELECT * FROM example_items ORDER BY created_at DESC').all();
  const total = db.prepare('SELECT COUNT(*) as count FROM example_items').get() as any;
  const response: GetExampleItemsResponse = { items: items as any, total: total.count };
  res.json(response);
});

router.post('/', (req, res) => {
  const body = req.body as CreateExampleItemRequest;
  // Validate required fields
  if (!body.name) {
    res.status(400).json({ error: 'name is required' });
    return;
  }
  const result = db.prepare(
    'INSERT INTO example_items (name, description) VALUES (?, ?)'
  ).run(body.name, body.description ?? null);

  const item = db.prepare('SELECT * FROM example_items WHERE id = ?').get(result.lastInsertRowid);
  const response: CreateExampleItemResponse = { item: item as any };
  res.status(201).json(response);
});

export default router;
```

```typescript
// backend/src/routes/index.ts
import { Router } from 'express';
import exampleItems from './exampleItems';

const router = Router();

router.use('/example-items', exampleItems);
// Add new resource routes here. One line per resource.

export { router as routes };
```

#### Error Handler

```typescript
// backend/src/middleware/errorHandler.ts
import { Request, Response, NextFunction } from 'express';

export function errorHandler(err: Error, req: Request, res: Response, next: NextFunction) {
  console.error(`[ERROR] ${req.method} ${req.path}:`, err.message);
  res.status(500).json({ error: 'Internal server error', message: err.message });
}
```

### 4.4 Frontend Patterns

#### API Client

A single, typed fetch wrapper. Every API call goes through this — agents should never use raw `fetch` elsewhere.

```typescript
// frontend/src/api/client.ts
const BASE_URL = 'http://localhost:3002/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(error.message || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};
```

#### Routing

Use `react-router-dom` v6 with simple route definitions in `App.tsx`. No file-based routing — explicit route declarations are easier for agents to reason about.

```tsx
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { HomePage } from './pages/HomePage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        {/* Add new routes here */}
      </Routes>
    </BrowserRouter>
  );
}
```

#### Component Pattern

Functional components with hooks. No class components, no HOCs, no render props. One pattern, used everywhere.

```tsx
// frontend/src/pages/HomePage.tsx
import { useState, useEffect } from 'react';
import { api } from '../api/client';
import type { GetExampleItemsResponse } from '@shared/types/api';

export function HomePage() {
  const [data, setData] = useState<GetExampleItemsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<GetExampleItemsResponse>('/example-items')
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-4">Loading...</div>;
  if (error) return <div className="p-4 text-red-600">Error: {error}</div>;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Example Items</h1>
      <p className="text-gray-600 mb-4">Total: {data?.total}</p>
      <ul className="space-y-2">
        {data?.items.map(item => (
          <li key={item.id} className="p-3 bg-white rounded shadow">
            <span className="font-medium">{item.name}</span>
            {item.description && (
              <p className="text-sm text-gray-500 mt-1">{item.description}</p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### 4.5 Vite Configuration

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@shared': path.resolve(__dirname, '../shared/src'),
    },
  },
  server: {
    port: 5173,
    // Proxy API requests in development to avoid CORS issues
    proxy: {
      '/api': {
        target: 'http://localhost:3002',
        changeOrigin: true,
      },
    },
  },
});
```

**Note:** When the Vite proxy is active, the frontend `api/client.ts` `BASE_URL` can be simplified to just `'/api'` instead of the full URL. This is the preferred setup — it avoids CORS entirely.

### 4.6 Backend Dev Script

```jsonc
// backend/package.json (relevant scripts only)
{
  "scripts": {
    "dev": "bun --watch src/index.ts",
    "build": "tsc"
  },
  "dependencies": {
    "express": "^4.18.0",
    "cors": "^2.8.5"
  },
  "devDependencies": {
    "@types/bun": "^1.0.0",
    "@types/express": "^4.17.0",
    "@types/cors": "^2.8.0"
  }
}
```

`bun --watch` gives us blazing fast native TypeScript execution with hot reload and zero config.

---

## 5. AI Agent Context System

This is the most critical part of the design. A codebase without discoverable context degrades rapidly under agent maintenance. The system below is designed around one principle: **agents must never have to guess where context lives or what conventions to follow.**

### 5.1 The agents.md File (Root Entry Point)

Every AI agent that touches this codebase **must read agents.md first.** This file is the single source of truth for project-wide context. It lives at the repo root and is named `agents.md` because this serves as a canonical file for intelligent agents to discover rules.

agents.md contains:

```markdown
# Project: [Name]

## What This Is
[2-3 sentence description of the project's purpose]

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

### When making an architectural decision:
1. Create a new file in `docs/decisions/` using the template in `_TEMPLATE.md`
2. Number it sequentially (e.g., `002-auth-approach.md`)
3. Update this file if the decision changes project-wide conventions

### General rules:
- All functions and components must have JSDoc comments explaining their purpose
- All route handlers must validate input before processing
- Never commit `backend/data/app.db` — it's gitignored
- Run `npm run typecheck` before considering any change complete

## Current State
[Updated by agents: what's been built, what's in progress, known issues]

## File Index
- `docs/decisions/` — Architecture Decision Records (read before making big changes)
- `docs/api.md` — Complete API endpoint documentation
- `shared/src/types/` — All TypeScript types shared between frontend and backend
- `backend/README.md` — Backend-specific patterns and conventions
- `frontend/README.md` — Frontend-specific patterns and conventions
```

### 5.2 Directory-Level README Files

Each major directory (`frontend/`, `backend/`, `shared/`) gets its own `README.md` with:

1. **Purpose** of this part of the codebase
2. **Patterns** used here (with examples)
3. **Gotchas** — things that have gone wrong before and how to avoid them
4. **Checklist** — steps to follow when modifying this area

These READMEs are referenced from the root CLAUDE.md, so agents always know they exist.

### 5.3 Architecture Decision Records (ADRs)

Every non-trivial decision gets recorded in `docs/decisions/`. The template:

```markdown
# [Number]: [Title]

**Date:** YYYY-MM-DD
**Status:** Accepted | Superseded by [XXX] | Deprecated

## Context
What situation prompted this decision?

## Decision
What did we decide?

## Consequences
What are the tradeoffs? What does this make easier or harder?
```

This is critical for agent continuity. When a new agent session starts and encounters a design choice it might want to change, the ADR explains **why** the choice was made. Without this, agents tend to "improve" things in circles — refactoring back and forth between approaches.

### 5.4 API Documentation

`docs/api.md` is a flat file listing every endpoint:

```markdown
# API Documentation

## GET /api/example-items
Returns all items.
**Response:** `GetExampleItemsResponse` (see shared/src/types/api.ts)

## POST /api/example-items
Creates a new item.
**Request:** `CreateExampleItemRequest`
**Response:** `CreateExampleItemResponse` (201)
**Errors:** 400 if `name` is missing
```

This is deliberately simple — no Swagger, no OpenAPI spec generation. Those tools add complexity that agents struggle with. A flat markdown file is trivially readable, trivially editable, and never out of sync if agents follow the convention in agents.md.

### 5.5 Code-Level Documentation

JSDoc comments on every exported function and component. Not verbose essays — just enough for an agent to understand intent without reading the implementation.

```typescript
/** Fetches all items, sorted by creation date descending. */
router.get('/', (req, res) => { ... });

/**
 * Reusable card component for displaying a single item.
 * Used on the HomePage list and the ItemDetailPage sidebar.
 */
export function ItemCard({ item }: { item: ExampleItem }) { ... }
```

### 5.6 Enforcing Context Maintenance

The hardest part isn't creating context — it's keeping it updated. Three mechanisms enforce this:

1. **agents.md checklists** spell out exactly which files to update for each type of change. Agents follow checklists reliably.

2. **TypeScript strict mode** catches type drift between shared types and actual usage. If an agent changes a type in `shared/` but forgets to update a route handler, the build fails.

3. **The "Current State" section** in agents.md acts as a living changelog. Every agent session should begin by reading it and end by updating it. The instruction to do this is written directly in agents.md.

---

## 6. Reusability Across Projects

This architecture is designed to be a **template.** To start a new project:

1. Clone/copy the structure
2. Delete `backend/data/app.db` and migration files
3. Replace the types in `shared/src/types/`
4. Replace the routes in `backend/src/routes/`
5. Replace the pages/components in `frontend/src/`
6. Update agents.md with the new project's context

The infrastructure — migration runner, API client, error handler, project structure, context system — stays identical. Agents that have worked on one project using this template will immediately understand another.

---

## 7. Dependencies (Complete List)

### Root
- `typescript` — shared compiler
- `eslint` + TypeScript plugins — linting

### Backend
- `express` — HTTP server
- `cors` — CORS middleware
*(SQLite driver and TypeScript execution are natively built into Bun)*
- `@types/*` (dev) — type definitions

### Frontend
- `react` + `react-dom` — UI library
- `react-router-dom` — client-side routing
- `@vitejs/plugin-react` (dev) — Vite React plugin
- `vite` (dev) — dev server and bundler
- `tailwindcss` + `postcss` + `autoprefixer` (dev) — utility CSS

**Total: 14 dependencies** (including dev). This is deliberately minimal. Every added dependency is a potential source of agent confusion.

---

## 8. What This Design Intentionally Avoids

| Excluded | Why |
|----------|-----|
| Next.js / Remix | SSR complexity is unnecessary for local hosting; agents make more mistakes with these |
| Prisma / Drizzle | ORM abstraction adds indirection; agents write better raw SQL for small datasets |
| PostgreSQL / MySQL | Requires running a separate server; SQLite is zero-config |
| Redux / Zustand | Global state management adds boilerplate; React's built-in `useState`/`useContext` suffice at this scale |
| Storybook | Component isolation tool is overkill when agents can just run the app |
| Docker | Local app doesn't need containerization; adds complexity for agents |
| Swagger / OpenAPI | Auto-generated API docs require tooling; a markdown file is simpler and more reliable |
| CSS-in-JS | Runtime overhead and API surface; Tailwind is more predictable for agents |
| Monorepo tools (Nx, Turbo) | npm workspaces handles our simple case; no need for build graph optimization |

---

## 9. Implementation Checklist

An implementing agent should follow this order:

1. **Initialize the repo**: `bun init`, set up workspaces in root `package.json`
2. **Create `shared/`**: Set up the types package with `models.ts` and `api.ts`
3. **Create `backend/`**: Express server, SQLite connection, migration runner, one example route
4. **Create `frontend/`**: Vite + React app, API client, one example page that calls the backend
5. **Verify the loop works**: `bun run dev` should start both servers; frontend should display data from the backend
6. **Set up context system**: Write agents.md, directory READMEs, ADR template, api.md
7. **Set up tooling**: ESLint config, tsconfig files, .gitignore
8. **Test the "new feature" workflow**: Add a second resource end-to-end (new type → new migration → new route → new page) following only the instructions in agents.md, to verify the context system actually works
