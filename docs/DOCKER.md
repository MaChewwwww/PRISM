# Docker

## Local stack

Copy `.env.example` to an untracked `.env`, replace the development-only authentication values, and run `pnpm docker:up`. Direct development through `pnpm dev` uses frontend port 3000 and backend port 8000. The base Compose stack defaults to frontend port 3005, backend port 8005, PostgreSQL port 5439, and optional Redis port 6385.

Compose starts PostgreSQL, runs `alembic upgrade head` in a one-shot `migrate` service, then starts FastAPI after migration succeeds. The frontend starts after backend readiness. FastAPI startup does not create tables. The frontend receives only its internal API URL, environment name, and server-side authentication values; Alpaca and LLM credentials remain confined to backend services.

Readiness validates required configuration and database connectivity. Liveness only proves that the process can answer. `/api/v1/system/status` is authenticated and is not a Compose health-check target.

## Production override

```bash
docker compose -f compose.yml -f compose.production.yml up -d --build
```

The production override publishes only Nginx on `{PRISM_HTTP_PORT:-80}`. Application and data services use private networks, and PostgreSQL/Redis have no host ports. Staging adds `compose.staging.yml` and publishes Nginx on `{STAGING_HTTP_PORT:-3005}` under a distinct Compose project.

Validate the resolved production topology with `pnpm docker:config`. Execution remains disabled by default and fails closed without valid paper configuration, an active ruleset, and a current authorization.

Never bake environment files, credentials, local data, build caches, or MCP configuration into images.
