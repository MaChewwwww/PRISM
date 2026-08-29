# PRISM staging server maintenance cheatsheet

This runbook covers runtime maintenance for the BGH host. Application code,
Dockerfiles, Compose definitions, and repository configuration must be changed
through a reviewed pull request. SSH is reserved for service operations and
server-side runtime environment files.

## Current PRISM runtime roots

- Staging: `/opt/bgh/prism-staging`
- Production: `/opt/bgh/prism-production`

Each root has its own `.env` and paper Alpaca credentials. Never copy a
credential between environments, print an environment file, or commit it.
Compose reads the server `.env` for the backend and migration services.

## Safe connection and inspection

Parse `.env.devops` locally for `STAGING_SSH_HOST`, `STAGING_SSH_USER`,
`STAGING_SSH_PORT`, and `STAGING_SSH_KEY_PATH`; do not source it and never use
`DEPLOY_USER_PASSWORD` or `GITHUB_PAT`.

```bash
ssh -i <STAGING_SSH_KEY_PATH> -p <STAGING_SSH_PORT> \
  <STAGING_SSH_USER>@<STAGING_SSH_HOST>
```

Inspect only non-secret configuration keys:

```bash
grep -E '^(ENVIRONMENT|EXECUTION_ENABLED|ACTIVE_RULESET_VERSION|AUTONOMOUS_TRADING_ENABLED|AUTONOMOUS_TRADING_START_AT|AUTONOMOUS_TRADING_END_AT)=' .env
```

Before editing an environment file, create a timestamped backup under the
same environment root's `.env-backups/` directory and show the intended key
diff without exposing credentials.

## Compose and deployment operations

Use a login shell so the host's Compose overlay is loaded. Serialize operations
that pull, recreate, restart, or stop services with the deployment lock:

```bash
flock /tmp/bgh-staging-deploy.lock bash -lc '
  cd /opt/bgh/prism-staging
  docker compose -f compose.yml -f compose.production.yml -f compose.staging.yml \
    --env-file .env config --quiet
'
```

The production stack resolves `compose.yml` with `compose.production.yml`; the
staging stack adds `compose.staging.yml`. The one-shot `migrate` service must
complete before `backend` is healthy. Do not run `docker compose down -v` or
delete volumes without explicit approval.

Verify after a change:

```bash
docker compose --env-file .env ps
curl --fail --silent --show-error http://localhost:3005/api/v1/health/ready  # staging
curl --fail --silent --show-error http://localhost/api/v1/health/ready     # production
```

Execution remains paper-only and disabled by default. Production autonomous
windows must remain inside the BA-authorized hackathon window. Staging may use
a separate bounded rehearsal interval, but it still requires paper mode and
the deterministic authorization gate.
