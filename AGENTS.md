# AGENTS.md — zq-platform

Enterprise admin panel: FastAPI backend + Vue 3 / Vben Admin frontend (Element Plus). Monorepo with `backend/` and `web/` as independent halves.

## Repository structure

```
zq-platform/
├── backend/          # FastAPI (Python 3.12+, SQLAlchemy async, Alembic)
├── web/              # Vue 3 monorepo (pnpm + Turbo, Vben Admin v5)
└── README.zh-CN.md   # root docs (says "backend-fastapi" but actual dir is backend/)
```

## Backend (FastAPI)

### Commands (run from `backend/`)
```bash
pip install -r requirements.txt
cp env/example.env env/dev.env          # then edit DB/Redis credentials
alembic revision --autogenerate -m "init tables"
alembic upgrade head
python scripts/loaddata.py db_init.json # optional seed data
python main.py                          # or: uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Key details
- **Config**: loaded from `env/{ENV}.env` where `ENV` env var defaults to `"dev"` (see `app/config.py:140`). `DATABASE_URL` and `REDIS_URL` are auto-constructed from individual fields if not set explicitly.
- **Alembic**: `alembic.ini` has a fallback `sqlite+aiosqlite:///./app.db`, but `alembic/env.py` overrides `sqlalchemy.url` with `settings.DATABASE_URL` at runtime. Auto-discovers models by scanning `zq_demo/`, `core/`, `scheduler/` for `*model.py` files.
- **Module pattern**: each feature = `model.py`, `schema.py`, `service.py`, `api.py` inside its own directory under `core/`. Register the router in `core/router.py`.
- **Data import/export**: `python scripts/dumpdata.py [app_name] -o data.json -f`, `python scripts/loaddata.py db_init.json`.
- **Tests**: None configured (no pytest config, no test files found).
- **Entrypoint**: `backend/main.py` — FastAPI app with lifespan handler (APScheduler startup, Redis cleanup).

### API prefixes
| Prefix | Routes |
|--------|--------|
| `/api/v1` | zq_demo (example modules) |
| `/api/core` | Core business (user, role, menu, dept, etc.) |
| `/api` | Scheduler |
| (none) | WebSocket |

### Swagger
- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## Frontend (Vue 3 monorepo)

### Commands (run from `web/`)
```bash
pnpm install                    # uses pnpm@10.14.0 (enforced via preinstall)
pnpm dev                        # starts @vben/web-ele on port 5777
pnpm build:ele                  # production build of Element Plus app
pnpm run build --filter=@vben/web-ele  # same as build:ele
pnpm lint                       # lint check (vsh lint)
pnpm format                     # auto-fix lint issues
pnpm check:type                 # turbo run typecheck (vue-tsc)
pnpm test:unit                  # vitest run --dom (happy-dom)
pnpm test:e2e                   # Playwright E2E
pnpm commit                     # launch czg for conventional commit
```

### Key details
- **Package manager**: pnpm >=9.12.0 (Node >=20.10.0). Locked to `pnpm@10.14.0` in package.json `packageManager` field. `.npmrc` sets npmmirror registry.
- **Dev proxy** (`vite.config.mts`): `/basic-api` → `http://localhost:8000`, `/ws` → `ws://localhost:8000`.
- **Monorepo layout**: `apps/web-ele/` (main app), `packages/@core/`, `packages/effects/`, `internal/`, `scripts/`. Workspace config in `pnpm-workspace.yaml`.
- **Main app entry**: `apps/web-ele/src/main.ts` → `bootstrap.ts`.
- **Linting**: ESLint (flat config via `@vben/eslint-config`), Prettier, Stylelint. Custom wrapper: `vsh lint` / `vsh lint --format`.
- **Typecheck**: `vue-tsc --noEmit --skipLibCheck` (per app, via turbo).
- **Testing**: Vitest with `happy-dom` environment. Tests co-located next to source as `__tests__/*.test.ts`. Command: `pnpm test:unit`.
- **Git hooks**: Lefthook runs pre-commit (prettier + eslint + stylelint on staged files) and commit-msg (commitlint). Post-merge runs `pnpm install`.
- **Commit convention**: Conventional commits via commitlint (`@vben/commitlint-config`). Use `pnpm commit` to launch `czg` interactive prompt.
- **Versioning**: Changesets (`pnpm changeset`, `pnpm version`).
- **Postinstall**: runs `pnpm -r run stub --if-present` (generates `.d.ts` stubs for workspace packages).
- **Env files**: `apps/web-ele/.env.development` (dev), `.env.production` (build). Tracked in git (see root `.gitignore:129`).

## General notes
- **No CI/CD** in this repo (no `.github/workflows/`).
- **No opencode.json, CLAUDE.md, or .cursorrules** exists.
- Root `.gitignore` is comprehensive — don't accidentally commit `env/*.env` (except `example.env`), `node_modules/`, `dist/`, or `__pycache__/`.
